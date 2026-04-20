"""backfill_metadata.py — Auto-classifica documenti esistenti privi di metadati.

Uso:
    python -m app.backfill_metadata              # tutti i KB
    python -m app.backfill_metadata --kb bandi   # solo KB specifico
    python -m app.backfill_metadata --dry-run    # solo conteggio, nessuna modifica
"""
import argparse
import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    ap = argparse.ArgumentParser(description="Backfill metadati per documenti senza classificazione")
    ap.add_argument("--kb", default=None, help="namespace KB da processare (default: tutti)")
    ap.add_argument("--dry-run", action="store_true", help="solo conteggio, nessuna modifica")
    args = ap.parse_args()

    import psycopg2
    from psycopg2.extras import RealDictCursor, Json
    from app.metadata_extractor import extract_metadata_for_file, save_sidecar_meta

    conn = psycopg2.connect(
        __import__("app.db", fromlist=["get_db_url"]).get_db_url()
    )
    conn.autocommit = False

    model = os.getenv("OLLAMA_LLM_MODEL", "qwen3-next-cloud:latest")
    timeout = int(os.getenv("METADATA_EXTRACT_TIMEOUT", "120"))

    try:
        # --- Trova documenti non eliminati ---
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            where_parts = ["(d.is_deleted IS NULL OR d.is_deleted = false)"]
            params: list = []
            if args.kb:
                where_parts.append("kb.namespace = %s")
                params.append(args.kb)

            where_clause = " AND ".join(where_parts)

            # Documenti i cui chunk NON hanno tipo_documento nei metadati
            sql = f"""
                SELECT d.id AS doc_id,
                       d.source_uri,
                       d.titolo,
                       kb.namespace AS kb_namespace
                FROM documents d
                JOIN knowledge_base kb ON kb.id = d.kb_id
                WHERE {where_clause}
                  AND NOT EXISTS (
                      SELECT 1 FROM chunks c
                      WHERE c.document_id = d.id
                        AND c.metadata->>'tipo_documento' IS NOT NULL
                        AND c.metadata->>'tipo_documento' != ''
                  )
                ORDER BY kb.namespace, d.created_at
            """
            cur.execute(sql, params)
            docs = cur.fetchall()

        logger.info("Backfill metadata: %d documenti senza classificazione", len(docs))

        if args.dry_run:
            logger.info("Dry-run: nessuna modifica effettuata.")
            return

        if not docs:
            logger.info("Nessun documento da classificare. Niente da fare.")
            return

        # --- Processa documento per documento (best-effort) ---
        ok_count = 0
        skip_count = 0
        err_count = 0

        for doc in docs:
            doc_id = doc["doc_id"]
            ns = doc["kb_namespace"]
            source_uri = doc["source_uri"] or ""
            titolo = doc["titolo"] or ""

            try:
                # Concatena testo di tutti i chunk del documento
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT testo FROM chunks WHERE document_id = %s ORDER BY chunk_index",
                        (doc_id,),
                    )
                    chunk_rows = cur.fetchall()

                full_text = " ".join(r["testo"] for r in chunk_rows if r["testo"])
                if not full_text.strip():
                    logger.info("  [%s] %s — skip (testo vuoto)", ns, titolo)
                    skip_count += 1
                    continue

                # Costruisci path dal source_uri per extract_metadata_for_file
                file_path = Path(source_uri) if source_uri else Path(titolo)

                # Estrai metadati via LLM
                extracted = extract_metadata_for_file(file_path, model, full_text, timeout=timeout)

                if not extracted.get("tipo_documento"):
                    logger.info("  [%s] %s — skip (LLM non ha estratto tipo_documento)", ns, titolo)
                    skip_count += 1
                    continue

                # Aggiorna metadata JSONB di tutti i chunk del documento
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE chunks
                        SET metadata = metadata || %s
                        WHERE document_id = %s
                        """,
                        (Json(extracted), doc_id),
                    )

                conn.commit()

                # Salva sidecar se il file e' accessibile
                if source_uri and Path(source_uri).exists():
                    try:
                        save_sidecar_meta(Path(source_uri), extracted)
                    except Exception:
                        pass  # best-effort, non critico

                ok_count += 1
                logger.info("  [%s] %s — OK (tipo: %s)", ns, titolo, extracted["tipo_documento"])

            except Exception as e:
                # Best-effort: logga errore e continua
                try:
                    conn.rollback()
                except Exception:
                    pass
                err_count += 1
                logger.warning("  [%s] %s — ERRORE: %s", ns, titolo, e)

        logger.info(
            "Backfill metadata completato: %d classificati, %d skip, %d errori",
            ok_count, skip_count, err_count,
        )

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
