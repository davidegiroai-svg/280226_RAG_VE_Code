"""
Filesystem ingest worker (M0)
- Creates/gets KB by namespace
- Inserts documents with dedup (kb_id, content_hash)
- Splits text into chunks (size 1200, overlap 200)
- Inserts chunks with metadata including source_path
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable, Tuple

import psycopg2
from psycopg2.extras import Json


def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v not in (None, "") else default


def get_conn():
    host = _env("DB_HOST", "db")
    port = int(_env("DB_PORT", "5432"))
    user = _env("POSTGRES_USER", "rag")
    pwd = _env("POSTGRES_PASSWORD", "rag_password_change_me")
    db = _env("POSTGRES_DB", "rag")

    return psycopg2.connect(host=host, port=port, user=user, password=pwd, dbname=db)


def sha256_text(text: str) -> str:
    h = hashlib.sha256()
    h.update(text.encode("utf-8", errors="ignore"))
    return h.hexdigest()


def read_text_file(p: Path) -> str:
    """Read text file with robust encoding handling.

    Tries utf-8-sig first (removes BOM), falls back to utf-8 with errors=ignore.
    Also strips BOM character explicitly for safety.
    """
    try:
        # Try utf-8-sig first (auto-removes BOM)
        content = p.read_text(encoding="utf-8-sig", errors="ignore")
    except Exception:
        # Fallback to utf-8 with errors=ignore
        content = p.read_text(encoding="utf-8", errors="ignore")
    # Explicit BOM removal as safety net
    return content.replace("\ufeff", "")


def chunk_text(text: str, size: int = 1200, overlap: int = 200) -> Iterable[Tuple[int, str]]:
    text = text.strip()
    if not text:
        return
    if overlap >= size:
        overlap = max(0, size // 5)

    start = 0
    idx = 0
    n = len(text)
    step = max(1, size - overlap)

    while start < n:
        end = min(start + size, n)
        yield idx, text[start:end]
        idx += 1
        if end >= n:
            break
        start += step


def ensure_kb(cur, namespace: str) -> str:
    cur.execute("SELECT id::text FROM knowledge_base WHERE namespace = %s", (namespace,))
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute(
        "INSERT INTO knowledge_base (namespace, nome, descrizione) VALUES (%s, %s, %s) RETURNING id::text",
        (namespace, namespace, f"KB auto-created for namespace '{namespace}'"),
    )
    return cur.fetchone()[0]


def upsert_document(cur, kb_id: str, source_uri: str, titolo: str, content_hash: str):
    cur.execute(
        """
        INSERT INTO documents (kb_id, source_uri, titolo, content_hash)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (kb_id, content_hash) DO NOTHING
        RETURNING id::text
        """,
        (kb_id, source_uri, titolo, content_hash),
    )
    row = cur.fetchone()
    if row:
        return row[0], True

    cur.execute("SELECT id::text FROM documents WHERE kb_id=%s AND content_hash=%s", (kb_id, content_hash))
    row2 = cur.fetchone()
    if not row2:
        raise RuntimeError("Cannot retrieve existing document after conflict")
    return row2[0], False


def insert_chunks(cur, kb_id: str, kb_namespace: str, doc_id: str, source_path: str, file_name: str, text: str) -> int:
    inserted = 0
    for chunk_index, chunk in chunk_text(text, 1200, 200):
        meta = {"source_path": source_path, "file_name": file_name, "chunk_index": chunk_index}
        cur.execute(
            """
            INSERT INTO chunks (document_id, kb_id, kb_namespace, chunk_index, testo, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (doc_id, kb_id, kb_namespace, chunk_index, chunk, Json(meta)),
        )
        inserted += 1
    return inserted


def list_files(root: Path):
    exts = {".txt", ".md", ".csv", ".json"}
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            yield p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", default="demo")
    ap.add_argument("--path", default="/data/inbox")
    args = ap.parse_args()

    kb_namespace = args.kb.strip()
    in_path = Path(args.path)

    if not kb_namespace:
        raise SystemExit("ERROR: --kb is empty")
    if not in_path.exists() or not in_path.is_dir():
        raise SystemExit(f"ERROR: path not found or not a dir: {in_path}")

    files = list(list_files(in_path))
    if not files:
        print(f"INFO: No supported files found in {in_path}")
        return

    conn = get_conn()
    conn.autocommit = False

    files_read = 0
    docs_new = 0
    docs_skipped = 0
    chunks_inserted = 0

    try:
        with conn.cursor() as cur:
            kb_id = ensure_kb(cur, kb_namespace)

            for fp in files:
                files_read += 1
                text = read_text_file(fp)
                if not text.strip():
                    continue

                source_path = fp.as_posix()
                content_hash = sha256_text(text)
                titolo = fp.name

                doc_id, inserted_new = upsert_document(cur, kb_id, source_path, titolo, content_hash)
                if not inserted_new:
                    docs_skipped += 1
                    continue

                docs_new += 1
                chunks_inserted += insert_chunks(cur, kb_id, kb_namespace, doc_id, source_path, fp.name, text)

        conn.commit()
        print("OK ingest completed")
        print(json.dumps({
            "kb": kb_namespace,
            "path": str(in_path),
            "files_found": len(files),
            "files_read": files_read,
            "documents_new": docs_new,
            "documents_skipped_existing": docs_skipped,
            "chunks_inserted": chunks_inserted
        }, indent=2))

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
