"""backfill_entities.py — Estrae entità per documenti già ingestiti.

Uso:
    python -m app.backfill_entities              # tutti i KB
    python -m app.backfill_entities --kb bandi   # solo KB 'bandi'
"""
import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    ap = argparse.ArgumentParser(description="Backfill entità grafo per documenti esistenti")
    ap.add_argument("--kb", default=None, help="namespace KB da processare (default: tutti)")
    args = ap.parse_args()

    import psycopg2
    from app.db import get_db_url
    from app.entity_extractor import extract_and_save

    conn = psycopg2.connect(get_db_url())
    try:
        with conn.cursor() as cur:
            if args.kb:
                cur.execute(
                    """
                    SELECT d.id, d.kb_id, kb.namespace
                    FROM documents d
                    JOIN knowledge_base kb ON kb.id = d.kb_id
                    WHERE kb.namespace = %s
                      AND (d.is_deleted IS NULL OR d.is_deleted = false)
                    ORDER BY kb.namespace, d.created_at
                    """,
                    (args.kb,),
                )
            else:
                cur.execute(
                    """
                    SELECT d.id, d.kb_id, kb.namespace
                    FROM documents d
                    JOIN knowledge_base kb ON kb.id = d.kb_id
                    WHERE (d.is_deleted IS NULL OR d.is_deleted = false)
                    ORDER BY kb.namespace, d.created_at
                    """
                )
            docs = cur.fetchall()

        logger.info("Backfill: %d documenti da processare", len(docs))

        for doc_id, kb_id, ns in docs:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT testo FROM chunks WHERE document_id = %s ORDER BY chunk_index",
                    (doc_id,),
                )
                text = " ".join(r[0] for r in cur.fetchall() if r[0])

            if not text.strip():
                logger.info("  [%s] %s — skip (testo vuoto)", ns, doc_id)
                continue

            with conn.cursor() as cur:
                extract_and_save(cur, doc_id, kb_id, text)
            conn.commit()
            logger.info("  [%s] %s — OK", ns, doc_id)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
