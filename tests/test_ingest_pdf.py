"""tests/test_ingest_pdf.py — TDD tests per PDF ingest (Phase 6)

RED:   fallenti prima dell'implementazione in ingest_fs.py
GREEN: dopo l'aggiunta di read_pdf_chunks(), estensione list_files(), insert_chunks()
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _make_fake_pymupdf(pages: list) -> MagicMock:
    """Crea un mock di pymupdf4llm con to_markdown configurato."""
    mock = MagicMock()
    mock.to_markdown.return_value = pages
    return mock


FAKE_PAGES_1 = [
    {"text": "Testo della prima pagina.", "metadata": {"page": 1}},
]

FAKE_PAGES_3 = [
    {"text": "Pagina uno.", "metadata": {"page": 1}},
    {"text": "Pagina due.", "metadata": {"page": 2}},
    {"text": "Pagina tre.", "metadata": {"page": 3}},
]


# ─────────────────────────────────────────────
# Test 1: read_pdf_chunks ritorna lista con chiave 'testo'
# ─────────────────────────────────────────────

def test_read_pdf_chunks_returns_list_with_testo(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "pymupdf4llm", _make_fake_pymupdf(FAKE_PAGES_1))

    from app.ingest_fs import read_pdf_chunks

    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    result = read_pdf_chunks(pdf)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["testo"] == "Testo della prima pagina."


# ─────────────────────────────────────────────
# Test 2: read_pdf_chunks include page_start e page_end
# ─────────────────────────────────────────────

def test_read_pdf_chunks_has_page_start_and_page_end(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "pymupdf4llm", _make_fake_pymupdf(FAKE_PAGES_1))

    from app.ingest_fs import read_pdf_chunks

    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    result = read_pdf_chunks(pdf)

    assert result[0]["page_start"] == 1
    assert result[0]["page_end"] == 1


# ─────────────────────────────────────────────
# Test 3: section_title è None per default
# ─────────────────────────────────────────────

def test_read_pdf_chunks_section_title_is_none(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "pymupdf4llm", _make_fake_pymupdf(FAKE_PAGES_1))

    from app.ingest_fs import read_pdf_chunks

    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    result = read_pdf_chunks(pdf)

    assert result[0]["section_title"] is None


# ─────────────────────────────────────────────
# Test 4: 3 pagine restituiscono 3 dict
# ─────────────────────────────────────────────

def test_read_pdf_chunks_multiple_pages(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "pymupdf4llm", _make_fake_pymupdf(FAKE_PAGES_3))

    from app.ingest_fs import read_pdf_chunks

    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    result = read_pdf_chunks(pdf)

    assert len(result) == 3
    assert result[2]["page_start"] == 3
    assert result[2]["testo"] == "Pagina tre."


# ─────────────────────────────────────────────
# Test 5b: pagina lunga produce più sub-chunk
# ─────────────────────────────────────────────

def test_read_pdf_chunks_pagina_lunga_produce_sub_chunk(monkeypatch, tmp_path):
    """Una pagina con testo > 800 char deve produrre più sub-chunk (retrieval focalizzato)."""
    testo_lungo = "A" * 900  # 900 char > size=800 → almeno 2 chunk
    fake_pages = [{"text": testo_lungo, "metadata": {"page": 1}}]
    monkeypatch.setitem(sys.modules, "pymupdf4llm", _make_fake_pymupdf(fake_pages))

    from app.ingest_fs import read_pdf_chunks
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    result = read_pdf_chunks(pdf)

    assert len(result) >= 2, "Una pagina di 900 char deve produrre almeno 2 sub-chunk"
    for chunk in result:
        assert chunk["page_start"] == 1
        assert chunk["page_end"] == 1
        assert len(chunk["testo"]) <= 800


# ─────────────────────────────────────────────
# Test 5: list_files include .pdf, esclude .docx
# ─────────────────────────────────────────────

def test_list_files_includes_pdf(tmp_path):
    (tmp_path / "doc.txt").write_text("ciao", encoding="utf-8")
    (tmp_path / "doc.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "doc.docx").write_bytes(b"fake docx")

    from app.ingest_fs import list_files

    files = list(list_files(tmp_path))
    extensions = {f.suffix.lower() for f in files}

    assert ".pdf" in extensions
    assert ".docx" in extensions


# ─────────────────────────────────────────────
# Test 6: insert_chunks con PDF salva page_start e page_end nel DB
# ─────────────────────────────────────────────

def test_insert_chunks_pdf_stores_pagination(monkeypatch, tmp_path):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
    monkeypatch.setenv("EMBEDDING_DIM", "768")
    monkeypatch.setitem(sys.modules, "pymupdf4llm", _make_fake_pymupdf(FAKE_PAGES_1))

    from app.ingest_fs import insert_chunks

    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    mock_cur = MagicMock()

    result = insert_chunks(
        mock_cur, "kb-uuid", "demo", "doc-uuid",
        str(pdf), "doc.pdf", text="",
        file_path=pdf,
    )

    assert result == 1

    insert_call = next(
        (c for c in mock_cur.execute.call_args_list if "INSERT INTO chunks" in str(c)),
        None,
    )
    assert insert_call is not None, "INSERT INTO chunks non trovato nelle chiamate al cursore"
    sql = insert_call[0][0]
    assert "page_start" in sql
    assert "page_end" in sql


# ─────────────────────────────────────────────
# Test 7: pagine PDF con testo vuoto vengono saltate
# ─────────────────────────────────────────────

def test_insert_chunks_pdf_empty_pages_skipped(monkeypatch, tmp_path):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
    monkeypatch.setenv("EMBEDDING_DIM", "768")

    pages_con_vuoti = [
        {"text": "Testo valido.", "metadata": {"page": 1}},
        {"text": "   ", "metadata": {"page": 2}},   # spazio → saltata
        {"text": "", "metadata": {"page": 3}},       # vuota → saltata
    ]
    monkeypatch.setitem(sys.modules, "pymupdf4llm", _make_fake_pymupdf(pages_con_vuoti))

    from app.ingest_fs import insert_chunks

    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    mock_cur = MagicMock()

    result = insert_chunks(
        mock_cur, "kb-uuid", "demo", "doc-uuid",
        str(pdf), "doc.pdf", text="",
        file_path=pdf,
    )

    assert result == 1  # solo la pagina 1 è valida


# ─────────────────────────────────────────────
# Test 8: read_sidecar_meta — letttura .meta.json
# ─────────────────────────────────────────────

def test_read_sidecar_meta_legge_json_se_esiste(tmp_path):
    """read_sidecar_meta legge il .meta.json accanto al documento."""
    from app.ingest_fs import read_sidecar_meta
    doc = tmp_path / "doc.pdf"
    doc.write_bytes(b"%PDF-1.4")
    meta_file = tmp_path / "doc.meta.json"
    meta_file.write_text('{"titolo": "Test", "targets": ["Minori"]}', encoding="utf-8")

    result = read_sidecar_meta(doc)
    assert result["titolo"] == "Test"
    assert result["targets"] == ["Minori"]


def test_read_sidecar_meta_ritorna_dict_vuoto_se_assente(tmp_path):
    """read_sidecar_meta ritorna {} se il .meta.json non esiste."""
    from app.ingest_fs import read_sidecar_meta
    doc = tmp_path / "doc.pdf"
    doc.write_bytes(b"%PDF-1.4")

    result = read_sidecar_meta(doc)
    assert result == {}


def test_read_sidecar_meta_ritorna_dict_vuoto_se_json_malformato(tmp_path):
    """read_sidecar_meta ritorna {} se il .meta.json è malformato (no crash)."""
    from app.ingest_fs import read_sidecar_meta
    doc = tmp_path / "doc.pdf"
    doc.write_bytes(b"%PDF-1.4")
    (tmp_path / "doc.meta.json").write_text("{ INVALID JSON }", encoding="utf-8")

    result = read_sidecar_meta(doc)
    assert result == {}
