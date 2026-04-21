"""backfill_titles.py — Popola doc_title dai metadati JSONB sidecar per chunk esistenti.

Aggiorna chunks.doc_title e documents.titolo usando il campo 'titolo' già
presente in chunks.metadata (scritto dall'auto-classificazione LLM).

Uso:
    python -m app.backfill_titles              # tutti i KB
    python -m app.backfill_titles --kb bandi   # solo KB specifico
    python -m app.backfill_titles --dry-run    # solo conteggio, nessuna modifica
"""
import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    ap = argparse.ArgumentParser(description="Backfill doc_title da metadata JSONB sidecar")
    ap.add_argument("--kb", default=None, help="namespace KB da processare (default: tutti)")
    ap.add_argument("--dry-run", action="store_true", help="solo conteggio, nessuna modifica")
    args = ap.parse_args()

    import psycopg2
    from psycopg2.extras import RealDictCursor

    conn = psycopg2.connect(
        __import__("app.db", fromlist=["get_db_url"]).get_db_url()
    )
    conn.autocommit = False

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            # --- Conta chunk aggiornabili ---
            where_kb = ""
            params_count: list = []
            if args.kb:
                where_kb = " AND kb_namespace = %s"
                params_count.append(args.kb)

            cur.execute(
                f"""
                SELECT COUNT(*) AS cnt
                FROM chunks
                WHERE metadata->>'titolo' IS NOT NULL
                  AND metadata->>'titolo' != ''
                  AND (doc_title IS NULL OR doc_title = metadata->>'file_name')
                {where_kb}
                """,
                params_count,
            )
            count_row = cur.fetchone()
            total = count_row["cnt"] if count_row else 0
            logger.info("Chunk da aggiornare: %d", total)

            if args.dry_run:
                logger.info("Dry-run: nessuna modifica eseguita.")
                return

            if total == 0:
                logger.info("Nessun chunk da aggiornare.")
                return

            # --- Aggiorna chunks.doc_title ---
            params_upd: list = []
            where_kb_upd = ""
            if args.kb:
                where_kb_upd = " AND kb_namespace = %s"
                params_upd.append(args.kb)

            cur.execute(
                f"""
                UPDATE chunks
                SET doc_title = metadata->>'titolo'
                WHERE metadata->>'titolo' IS NOT NULL
                  AND metadata->>'titolo' != ''
                  AND (doc_title IS NULL OR doc_title = metadata->>'file_name')
                {where_kb_upd}
                """,
                params_upd,
            )
            chunks_updated = cur.rowcount
            logger.info("chunks.doc_title aggiornati: %d", chunks_updated)

            # --- Aggiorna documents.titolo ---
            params_doc: list = []
            where_kb_doc = ""
            if args.kb:
                where_kb_doc = " AND c.kb_namespace = %s"
                params_doc.append(args.kb)

            cur.execute(
                f"""
                UPDATE documents d
                SET titolo = sub.titolo,
                    updated_at = now()
                FROM (
                    SELECT DISTINCT ON (document_id)
                        document_id,
                        metadata->>'titolo' AS titolo
                    FROM chunks
                    WHERE metadata->>'titolo' IS NOT NULL
                      AND metadata->>'titolo' != ''
                    ORDER BY document_id, chunk_index
                ) sub
                WHERE d.id = sub.document_id
                  AND (d.titolo IS NULL OR d.titolo != sub.titolo)
                """,
                params_doc,
            )
            docs_updated = cur.rowcount
            logger.info("documents.titolo aggiornati: %d", docs_updated)

        conn.commit()
        logger.info("Backfill completato. chunks=%d documents=%d", chunks_updated, docs_updated)

    except Exception:
        conn.rollback()
        logger.exception("Errore durante il backfill")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
