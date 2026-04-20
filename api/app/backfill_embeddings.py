"""backfill_embeddings.py — Ri-genera embedding per tutti i chunk con prefisso contestuale.

Uso:
    python -m app.backfill_embeddings              # tutti i KB
    python -m app.backfill_embeddings --kb bandi   # solo KB specifico
    python -m app.backfill_embeddings --dry-run    # solo conteggio, nessuna modifica
    python -m app.backfill_embeddings --batch-size 100  # dimensione batch custom
"""
import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BATCH_SIZE_DEFAULT = 50


def main() -> None:
    ap = argparse.ArgumentParser(description="Backfill embedding con prefisso contestuale")
    ap.add_argument("--kb", default=None, help="namespace KB da processare (default: tutti)")
    ap.add_argument("--dry-run", action="store_true", help="solo conteggio, nessuna modifica")
    ap.add_argument("--batch-size", type=int, default=BATCH_SIZE_DEFAULT, help="chunk per batch")
    args = ap.parse_args()

    import psycopg2
    from psycopg2.extras import RealDictCursor
    from app.ingest_fs import build_context_prefix, vector_to_str
    from app.embedding import embed_texts

    conn = psycopg2.connect(
        __import__("app.db", fromlist=["get_db_url"]).get_db_url()
    )
    conn.autocommit = False

    try:
        # --- Conta chunk da processare ---
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            where_clause = ""
            params: tuple = ()
            if args.kb:
                where_clause = "WHERE kb.namespace = %s"
                params = (args.kb,)

            count_sql = f"""
                SELECT COUNT(*) AS cnt
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                JOIN knowledge_base kb ON kb.id = c.kb_id
                {where_clause}
            """
            cur.execute(count_sql, params)
            total = cur.fetchone()["cnt"]

        logger.info("Backfill embedding: %d chunk da processare", total)

        if args.dry_run:
            logger.info("Dry-run: nessuna modifica effettuata.")
            return

        if total == 0:
            logger.info("Nessun chunk trovato. Niente da fare.")
            return

        # --- Processa a batch ---
        offset = 0
        batch_num = 0
        total_updated = 0

        while offset < total:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                fetch_sql = f"""
                    SELECT c.id AS chunk_id,
                           c.testo,
                           d.titolo,
                           kb.namespace AS kb_namespace,
                           c.metadata
                    FROM chunks c
                    JOIN documents d ON d.id = c.document_id
                    JOIN knowledge_base kb ON kb.id = c.kb_id
                    {where_clause}
                    ORDER BY kb.namespace, c.id
                    LIMIT %s OFFSET %s
                """
                cur.execute(fetch_sql, (*params, args.batch_size, offset))
                rows = cur.fetchall()

            if not rows:
                break

            batch_num += 1

            # Costruisci testi con prefisso contestuale
            prefixed_texts = []
            for row in rows:
                meta = row["metadata"] or {}
                file_type = meta.get("file_type", "")
                tipo_documento = meta.get("tipo_documento", "")
                targets = meta.get("targets")
                if isinstance(targets, str):
                    targets = [targets]

                prefix = build_context_prefix(
                    row["kb_namespace"],
                    row["titolo"] or "",
                    file_type,
                    tipo_documento=tipo_documento or "",
                    targets=targets,
                )
                prefixed_texts.append(prefix + (row["testo"] or ""))

            # Genera embedding
            embeddings, embedding_model, embedding_dim = embed_texts(prefixed_texts)

            # Aggiorna nel DB
            with conn.cursor() as cur:
                for row, embedding in zip(rows, embeddings):
                    cur.execute(
                        """
                        UPDATE chunks
                        SET embedding = %s,
                            embedding_model = %s,
                            embedding_dim = %s,
                            doc_title = %s
                        WHERE id = %s
                        """,
                        (
                            vector_to_str(embedding),
                            embedding_model,
                            embedding_dim,
                            row["titolo"],
                            row["chunk_id"],
                        ),
                    )

            conn.commit()

            updated_count = len(rows)
            total_updated += updated_count
            kb_label = rows[0]["kb_namespace"] if rows else "?"
            logger.info(
                "[%s] batch %d — %d chunk aggiornati (totale: %d/%d)",
                kb_label, batch_num, updated_count, total_updated, total,
            )

            offset += args.batch_size

        logger.info("Backfill embedding completato: %d chunk aggiornati su %d totali", total_updated, total)

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
