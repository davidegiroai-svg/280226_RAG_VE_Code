# PDF Ingest (Phase 6) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the CLI ingest worker to process PDF files via pymupdf4llm, storing page_start/page_end metadata per chunk.

**Architecture:** Two-wave approach: Wave 1 is pure infrastructure (SQL migration + requirements), Wave 2 is TDD implementation of the PDF branch in ingest_fs.py. Wave 2 depends on Wave 1 completing first. No new modules — all changes are additive to existing files.

**Tech Stack:** pymupdf4llm>=0.0.17, psycopg2 SYNC, pytest, unittest.mock, Docker exec for test runs.

---

## Wave 1 — Infrastructure (no code, no tests needed)

### Task 1: Create migration SQL for existing environments

**Files:**
- Create: `scripts/migration_m2_pdf.sql`

**Step 1: Create the migration file**

```sql
-- Migration M2 — PDF: aggiunge colonne paginazione alla tabella chunks
-- Sicuro da eseguire piu' volte (ADD COLUMN IF NOT EXISTS)

ALTER TABLE chunks ADD COLUMN IF NOT EXISTS page_start integer;
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS page_end integer;
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS section_title text;
```

**Step 2: Verify the file has exactly 3 ALTER TABLE statements**

Run: `grep -c "ADD COLUMN IF NOT EXISTS" scripts/migration_m2_pdf.sql`
Expected output: `3`

**Step 3: Commit**

```bash
git add scripts/migration_m2_pdf.sql
git commit -m "feat(db): add migration_m2_pdf.sql with page_start/page_end/section_title"
```

---

### Task 2: Update db_init.sql with PDF columns

**Files:**
- Modify: `scripts/db_init.sql` (inside CREATE TABLE chunks, before `ingest_date` line)

**Step 1: Add three new columns to the CREATE TABLE chunks block**

Find the line `embedding vector(768),` in `scripts/db_init.sql`. Insert these three lines immediately after it, before `ingest_date timestamptz DEFAULT now()`:

```sql
    page_start integer,
    page_end integer,
    section_title text,
```

The resulting end of the CREATE TABLE chunks block should look like:

```sql
    embedding_model text,
    embedding_dim int,
    embedding vector(768),
    page_start integer,
    page_end integer,
    section_title text,
    ingest_date timestamptz DEFAULT now()
);
```

**Step 2: Verify the columns appear in db_init.sql**

Run: `grep -c "page_start\|page_end\|section_title" scripts/db_init.sql`
Expected output: `3`

**Step 3: Commit**

```bash
git add scripts/db_init.sql
git commit -m "feat(db): add page_start, page_end, section_title to chunks in db_init.sql"
```

---

### Task 3: Add pymupdf4llm to requirements.txt

**Files:**
- Modify: `api/requirements.txt`

**Step 1: Append the dependency**

Add this line at the end of `api/requirements.txt`:

```
pymupdf4llm>=0.0.17
```

**Step 2: Verify**

Run: `grep "pymupdf4llm" api/requirements.txt`
Expected output: `pymupdf4llm>=0.0.17`

**Step 3: Rebuild the Docker image**

Run in PowerShell:
```powershell
docker compose up -d --build
```
Expected: image rebuilds, containers restart. No errors.

**Step 4: Verify pymupdf4llm installed in container**

Run:
```powershell
docker compose exec api python -c "import pymupdf4llm; print('OK')"
```
Expected output: `OK`

**Step 5: Commit**

```bash
git add api/requirements.txt
git commit -m "feat(deps): add pymupdf4llm>=0.0.17 for PDF ingest"
```

---

## Wave 2 — TDD Implementation (depends on Wave 1)

### Task 4: Write failing tests (RED phase)

**Files:**
- Create: `tests/test_ingest_pdf.py`

**Step 1: Create the test file with all failing tests**

```python
"""Test per PDF ingest — TDD: RED phase.

Pattern: mock pymupdf4llm, embedding=dummy, no real DB.
"""
import io
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest

# Imposta embedding dummy prima di importare il modulo
import os
os.environ["EMBEDDING_PROVIDER"] = "dummy"
os.environ["EMBEDDING_DIM"] = "768"
os.environ["EMBEDDING_MODEL"] = "nomic-embed-text"


def _fake_pages(texts):
    """Costruisce output fittizio di pymupdf4llm.to_markdown(page_chunks=True)."""
    return [
        {"text": t, "metadata": {"page": i + 1}}
        for i, t in enumerate(texts)
    ]


# ---------------------------------------------------------------------------
# Test 1: read_pdf_chunks ritorna struttura corretta
# ---------------------------------------------------------------------------
def test_read_pdf_chunks_struttura(monkeypatch, tmp_path):
    """read_pdf_chunks(p) deve ritornare lista di dict con le chiavi attese."""
    from app.ingest_fs import read_pdf_chunks

    fake_pdf = tmp_path / "doc.pdf"
    fake_pdf.write_bytes(b"%PDF-fake")

    with patch("app.ingest_fs.pymupdf4llm.to_markdown") as mock_md:
        mock_md.return_value = _fake_pages(["Testo pagina uno", "Testo pagina due"])
        risultato = read_pdf_chunks(fake_pdf)

    assert len(risultato) == 2
    for item in risultato:
        assert "testo" in item
        assert "page_start" in item
        assert "page_end" in item
        assert "section_title" in item


# ---------------------------------------------------------------------------
# Test 2: read_pdf_chunks scarta pagine vuote
# ---------------------------------------------------------------------------
def test_read_pdf_chunks_scarta_pagine_vuote(monkeypatch, tmp_path):
    """Le pagine con solo whitespace devono essere escluse dall'output."""
    from app.ingest_fs import read_pdf_chunks

    fake_pdf = tmp_path / "doc.pdf"
    fake_pdf.write_bytes(b"%PDF-fake")

    with patch("app.ingest_fs.pymupdf4llm.to_markdown") as mock_md:
        mock_md.return_value = _fake_pages(["Testo valido", "   \n\t  ", ""])
        risultato = read_pdf_chunks(fake_pdf)

    assert len(risultato) == 1
    assert risultato[0]["testo"] == "Testo valido"


# ---------------------------------------------------------------------------
# Test 3: read_pdf_chunks propaga eccezioni (PDF corrotto)
# ---------------------------------------------------------------------------
def test_read_pdf_chunks_propaga_eccezione(monkeypatch, tmp_path):
    """PDF corrotti devono sollevare eccezione — NON essere catturati da read_pdf_chunks."""
    from app.ingest_fs import read_pdf_chunks

    fake_pdf = tmp_path / "corrotto.pdf"
    fake_pdf.write_bytes(b"not a pdf")

    with patch("app.ingest_fs.pymupdf4llm.to_markdown") as mock_md:
        mock_md.side_effect = Exception("PDF corrotto o criptato")
        with pytest.raises(Exception, match="corrotto"):
            read_pdf_chunks(fake_pdf)


# ---------------------------------------------------------------------------
# Test 4: list_files include .pdf
# ---------------------------------------------------------------------------
def test_list_files_include_pdf(tmp_path):
    """list_files() deve restituire file .pdf oltre a .txt/.md/.csv/.json."""
    from app.ingest_fs import list_files

    (tmp_path / "doc.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "nota.txt").write_text("testo", encoding="utf-8")
    (tmp_path / "immagine.png").write_bytes(b"\x89PNG")

    trovati = list(list_files(tmp_path))
    suffissi = {p.suffix for p in trovati}

    assert ".pdf" in suffissi, "list_files deve includere .pdf"
    assert ".png" not in suffissi, "list_files non deve includere .png"


# ---------------------------------------------------------------------------
# Test 5: insert_chunks branch PDF salva page_start/page_end
# ---------------------------------------------------------------------------
def test_insert_chunks_pdf_salva_pagine(monkeypatch, tmp_path):
    """insert_chunks() con source_ext='.pdf' deve fare INSERT con page_start e page_end."""
    monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
    monkeypatch.setenv("EMBEDDING_DIM", "768")

    from app.ingest_fs import insert_chunks

    fake_pdf = tmp_path / "doc.pdf"
    fake_pdf.write_bytes(b"%PDF-fake")

    mock_cur = MagicMock()
    mock_cur.execute = MagicMock()

    with patch("app.ingest_fs.pymupdf4llm.to_markdown") as mock_md:
        mock_md.return_value = _fake_pages(["Testo pagina uno con contenuto sufficiente"])
        n = insert_chunks(
            mock_cur,
            kb_id="kb-uuid",
            kb_namespace="test",
            doc_id="doc-uuid",
            source_path=str(fake_pdf),
            file_name="doc.pdf",
            text="",  # ignorato per PDF
            source_ext=".pdf",
        )

    assert n == 1

    # Verifica che la chiamata INSERT includa page_start e page_end
    call_args_list = mock_cur.execute.call_args_list
    insert_call = next(
        (c for c in call_args_list if "INSERT INTO chunks" in str(c)),
        None
    )
    assert insert_call is not None, "Nessuna INSERT INTO chunks trovata"
    sql_or_params = str(insert_call)
    assert "page_start" in sql_or_params or "page_end" in sql_or_params, \
        "INSERT deve includere colonne page_start/page_end"


# ---------------------------------------------------------------------------
# Test 6: insert_chunks branch TXT non rompe nulla (regressione)
# ---------------------------------------------------------------------------
def test_insert_chunks_txt_invariato(monkeypatch):
    """insert_chunks() senza source_ext (default) deve comportarsi come prima."""
    monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
    monkeypatch.setenv("EMBEDDING_DIM", "768")

    from app.ingest_fs import insert_chunks

    mock_cur = MagicMock()

    n = insert_chunks(
        mock_cur,
        kb_id="kb-uuid",
        kb_namespace="test",
        doc_id="doc-uuid",
        source_path="/data/inbox/test/file.txt",
        file_name="file.txt",
        text="Testo di esempio per il chunk con almeno trenta caratteri.",
        source_ext=".txt",
    )

    assert n >= 1, "Deve inserire almeno un chunk per testo non vuoto"


# ---------------------------------------------------------------------------
# Test 7: main() include pdfs_processed nel JSON summary
# ---------------------------------------------------------------------------
def test_main_json_include_pdfs_processed(monkeypatch, tmp_path, capsys):
    """main() deve stampare pdfs_processed nel JSON summary."""
    monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
    monkeypatch.setenv("EMBEDDING_DIM", "768")

    # Crea un PDF fittizio nella directory temporanea
    (tmp_path / "doc.pdf").write_bytes(b"%PDF-fake")

    import sys
    from unittest.mock import patch, MagicMock

    mock_conn = MagicMock()
    mock_conn.autocommit = False
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    # ensure_kb ritorna un uuid fittizio
    mock_cur.fetchone.return_value = ("kb-fake-uuid",)

    with patch("app.ingest_fs.get_conn", return_value=mock_conn), \
         patch("app.ingest_fs.pymupdf4llm.to_markdown") as mock_md, \
         patch("app.ingest_fs.insert_chunks", return_value=1), \
         patch("app.ingest_fs.upsert_document", return_value=("doc-uuid", True)), \
         patch("sys.argv", ["ingest_fs", "--kb", "test", "--path", str(tmp_path)]):

        mock_md.return_value = _fake_pages(["Testo pagina uno con sufficiente contenuto"])

        from app import ingest_fs
        ingest_fs.main()

    captured = capsys.readouterr()
    import json
    # Cerca il blocco JSON nell'output
    json_start = captured.out.index("{")
    json_str = captured.out[json_start:]
    data = json.loads(json_str)

    assert "pdfs_processed" in data, "JSON summary deve contenere 'pdfs_processed'"
    assert data["pdfs_processed"] >= 1
```

**Step 2: Verify the test file exists and has at least 60 lines**

Run: `wc -l tests/test_ingest_pdf.py`
Expected: 60+ lines

---

### Task 5: Run tests to confirm RED

**Step 1: Run new tests — expect failures**

Run:
```powershell
docker compose exec api pytest tests/test_ingest_pdf.py -v
```
Expected: Multiple `FAILED` entries. Typical errors:
- `ImportError: cannot import name 'read_pdf_chunks' from 'app.ingest_fs'`
- `TypeError: insert_chunks() got an unexpected keyword argument 'source_ext'`

This confirms RED. Do NOT proceed to implementation until you see these failures.

**Step 2: Confirm existing tests still pass**

Run:
```powershell
docker compose exec api pytest tests/test_embedding_dummy.py -v
```
Expected: `1 passed`

---

### Task 6: Implement PDF support in ingest_fs.py (GREEN phase)

**Files:**
- Modify: `api/app/ingest_fs.py`

Make all changes to `api/app/ingest_fs.py` in this order:

**Step 1: Add pymupdf4llm import at top of file (after existing imports)**

Add after the existing `from app.embedding import embed_texts, EmbeddingError` line:

```python
try:
    import pymupdf4llm
except ImportError:
    pymupdf4llm = None
```

**Step 2: Add read_pdf_chunks() function**

Add after the `read_text_file()` function (before `chunk_text()`):

```python
def read_pdf_chunks(p: Path) -> list:
    """Estrae chunks di testo da un PDF usando pymupdf4llm.

    Ritorna lista di dict con testo, page_start, page_end, section_title.
    Scarta pagine con testo vuoto. NON cattura eccezioni — risalgono al chiamante.
    """
    if pymupdf4llm is None:
        raise RuntimeError("pymupdf4llm non disponibile. Aggiungere a requirements.txt.")
    pages = pymupdf4llm.to_markdown(str(p), page_chunks=True)
    risultato = []
    for page in pages:
        testo = page.get("text", "").strip()
        if not testo:
            continue
        page_num = page.get("metadata", {}).get("page", 0)
        risultato.append({
            "testo": testo,
            "page_start": page_num,
            "page_end": page_num,
            "section_title": None,
        })
    return risultato
```

**Step 3: Extend list_files() to include .pdf**

Change the `exts` set in `list_files()`:

Old:
```python
    exts = {".txt", ".md", ".csv", ".json"}
```

New:
```python
    exts = {".txt", ".md", ".csv", ".json", ".pdf"}
```

**Step 4: Extend insert_chunks() signature and add PDF branch**

Change the function signature from:
```python
def insert_chunks(cur, kb_id: str, kb_namespace: str, doc_id: str, source_path: str, file_name: str, text: str) -> int:
```
to:
```python
def insert_chunks(cur, kb_id: str, kb_namespace: str, doc_id: str, source_path: str, file_name: str, text: str, source_ext: str = "") -> int:
```

Replace the entire body of the function with:

```python
def insert_chunks(cur, kb_id: str, kb_namespace: str, doc_id: str, source_path: str, file_name: str, text: str, source_ext: str = "") -> int:
    if source_ext == ".pdf":
        # Branch PDF: estrai chunks per pagina con pymupdf4llm
        pdf_chunks = read_pdf_chunks(Path(source_path))
        if not pdf_chunks:
            return 0

        chunk_texts_list = [c["testo"] for c in pdf_chunks]
        try:
            embeddings, embedding_model, embedding_dim = embed_texts(chunk_texts_list)
        except EmbeddingError as e:
            raise RuntimeError(f"Embedding fallito per '{file_name}': {e}")

        inserted = 0
        for chunk_index, (chunk_info, embedding) in enumerate(zip(pdf_chunks, embeddings)):
            meta = {
                "source_path": source_path,
                "file_name": file_name,
                "chunk_index": chunk_index,
                "page_start": chunk_info["page_start"],
                "page_end": chunk_info["page_end"],
            }
            cur.execute(
                """
                INSERT INTO chunks (
                    document_id, kb_id, kb_namespace, chunk_index, testo,
                    metadata, embedding, embedding_model, embedding_dim,
                    page_start, page_end, section_title
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    doc_id, kb_id, kb_namespace, chunk_index, chunk_info["testo"],
                    Json(meta), vector_to_str(embedding), embedding_model, embedding_dim,
                    chunk_info["page_start"], chunk_info["page_end"], chunk_info["section_title"],
                ),
            )
            inserted += 1
        return inserted

    else:
        # Branch originale TXT/MD/CSV/JSON: usa chunk_text()
        chunks_data = list(chunk_text(text, 1200, 200))
        if not chunks_data:
            return 0

        chunk_texts_list = [c[1] for c in chunks_data]
        try:
            embeddings, embedding_model, embedding_dim = embed_texts(chunk_texts_list)
        except EmbeddingError as e:
            raise RuntimeError(f"Embedding fallito per '{file_name}': {e}")

        inserted = 0
        for (chunk_index, chunk), embedding in zip(chunks_data, embeddings):
            meta = {"source_path": source_path, "file_name": file_name, "chunk_index": chunk_index}
            cur.execute(
                """
                INSERT INTO chunks (
                    document_id, kb_id, kb_namespace, chunk_index, testo,
                    metadata, embedding, embedding_model, embedding_dim,
                    page_start, page_end, section_title
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    doc_id, kb_id, kb_namespace, chunk_index, chunk,
                    Json(meta), vector_to_str(embedding), embedding_model, embedding_dim,
                    None, None, None,
                ),
            )
            inserted += 1
        return inserted
```

**Step 5: Update main() to handle PDF files and track pdfs_processed**

In the `main()` function body, make the following changes:

1. Add `pdfs_processed = 0` after the existing counter declarations.

2. Replace the file processing loop with:

```python
        for fp in files:
            files_read += 1
            source_ext = fp.suffix.lower()
            source_path = fp.as_posix()
            titolo = fp.name

            if source_ext == ".pdf":
                try:
                    pages = read_pdf_chunks(fp)
                    testo_completo = "".join(p["testo"] for p in pages)
                    if not testo_completo.strip():
                        continue
                    content_hash = sha256_text(testo_completo)
                except Exception as e:
                    print(f"WARNING: PDF saltato ({fp.name}): {e}")
                    continue
            else:
                text = read_text_file(fp)
                if not text.strip():
                    continue
                testo_completo = text
                content_hash = sha256_text(testo_completo)

            doc_id, inserted_new = upsert_document(cur, kb_id, source_path, titolo, content_hash)
            if not inserted_new:
                docs_skipped += 1
                continue

            docs_new += 1
            chunks_inserted += insert_chunks(
                cur, kb_id, kb_namespace, doc_id, source_path, fp.name,
                "" if source_ext == ".pdf" else testo_completo,
                source_ext=source_ext,
            )
            if source_ext == ".pdf":
                pdfs_processed += 1
```

3. Add `"pdfs_processed": pdfs_processed` to the final `json.dumps()` call.

---

### Task 7: Run tests to confirm GREEN

**Step 1: Run the PDF tests**

```powershell
docker compose exec api pytest tests/test_ingest_pdf.py -v
```
Expected: All tests show `PASSED`. Zero failures.

If tests fail, read the error carefully:
- `ImportError`: The import guard for pymupdf4llm is wrong
- `TypeError on insert_chunks`: Signature mismatch — check `source_ext` parameter
- `AssertionError on pdfs_processed`: Check the json.dumps block in main()

**Step 2: Check no regressions in existing tests**

```powershell
docker compose exec api pytest tests/ -v
```
Expected: All pass. Minimum: `test_embedding_dummy.py::test_dummy_is_deterministic_and_dim_768 PASSED`

**Step 3: Commit the implementation**

```bash
git add api/app/ingest_fs.py tests/test_ingest_pdf.py
git commit -m "feat(ingest): add PDF support with pymupdf4llm, page_start/page_end metadata (TDD)"
```

---

### Task 8: Apply migration on existing DB

**Step 1: Run migration on the running DB container**

```powershell
docker compose exec db psql -U rag -d rag -f /dev/stdin < scripts/migration_m2_pdf.sql
```

Or copy and run manually:
```powershell
Get-Content scripts/migration_m2_pdf.sql | docker compose exec -T db psql -U rag -d rag
```
Expected output:
```
ALTER TABLE
ALTER TABLE
ALTER TABLE
```

**Step 2: Verify columns exist in DB**

```powershell
docker compose exec db psql -U rag -d rag -c "\d chunks"
```
Expected: Columns `page_start`, `page_end`, `section_title` visible in output.

**Step 3: Smoke test with real PDF (optional)**

Place a small PDF in `data/inbox/demo/` and run:
```powershell
docker compose --profile manual run --rm worker --kb demo --path /data/inbox/demo
```
Expected: JSON output includes `"pdfs_processed": 1` and `"chunks_inserted": N`.

---

## Success Checklist

- [ ] `scripts/migration_m2_pdf.sql` exists with 3 idempotent ALTER TABLE statements
- [ ] `scripts/db_init.sql` has `page_start`, `page_end`, `section_title` in CREATE TABLE chunks
- [ ] `api/requirements.txt` has `pymupdf4llm>=0.0.17`
- [ ] `api/app/ingest_fs.py` has `read_pdf_chunks()` function
- [ ] `api/app/ingest_fs.py` `list_files()` includes `.pdf`
- [ ] `api/app/ingest_fs.py` `insert_chunks()` has `source_ext` param and PDF branch
- [ ] `api/app/ingest_fs.py` `main()` tracks `pdfs_processed` in JSON output
- [ ] `tests/test_ingest_pdf.py` has 7 tests, all PASSING
- [ ] No regressions in `tests/test_embedding_dummy.py`
- [ ] Migration applied to running DB container
