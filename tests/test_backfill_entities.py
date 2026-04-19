"""test_backfill_entities.py — Test per api/app/backfill_entities.py."""
from unittest.mock import MagicMock, patch, call


def _make_conn(doc_rows, chunk_rows_by_doc=None):
    """Costruisce un mock connection con cursor preimpostato."""
    conn = MagicMock()
    cursors = []

    def make_cursor():
        cur = MagicMock()
        cursors.append(cur)
        return cur

    ctx = MagicMock()
    ctx.__enter__ = MagicMock(side_effect=lambda s: make_cursor())
    ctx.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = ctx
    conn._cursors = cursors
    conn._doc_rows = doc_rows
    conn._chunk_rows_by_doc = chunk_rows_by_doc or {}
    return conn


# ─────────────────────────────────────────────────────────────
# test_backfill_processes_all_docs
# ─────────────────────────────────────────────────────────────

def test_backfill_processes_all_docs():
    """extract_and_save chiamato una volta per ogni doc con testo."""
    import importlib
    import sys

    doc_rows = [
        ("doc-1", "kb-1", "bandi"),
        ("doc-2", "kb-1", "bandi"),
    ]
    chunk_rows = {
        "doc-1": [("testo documento uno",)],
        "doc-2": [("testo documento due",)],
    }

    call_log = []
    fetch_call = [0]

    conn = MagicMock()

    # Primo cursor: SELECT documents
    cur_docs = MagicMock()
    cur_docs.fetchall.return_value = doc_rows

    # Per ogni doc: 1 cursore chunks + 1 cursore extract_and_save
    chunk_cursor_1 = MagicMock()
    chunk_cursor_1.fetchall.return_value = chunk_rows["doc-1"]
    chunk_cursor_2 = MagicMock()
    chunk_cursor_2.fetchall.return_value = chunk_rows["doc-2"]

    cursor_seq = [cur_docs, chunk_cursor_1, MagicMock(), chunk_cursor_2, MagicMock()]
    cursor_idx = [0]

    def make_ctx():
        ctx = MagicMock()
        idx = cursor_idx[0]
        cursor_idx[0] += 1
        cur = cursor_seq[idx] if idx < len(cursor_seq) else MagicMock()
        ctx.__enter__ = MagicMock(return_value=cur)
        ctx.__exit__ = MagicMock(return_value=False)
        return ctx

    conn.cursor.side_effect = make_ctx

    with patch("psycopg2.connect", return_value=conn), \
         patch("app.entity_extractor.extract_and_save", side_effect=lambda *a, **k: call_log.append(a[2])):
        # Importa fresh per evitare caching
        if "app.backfill_entities" in sys.modules:
            del sys.modules["app.backfill_entities"]
        from app.backfill_entities import main
        main.__globals__["__name__"] = "__main__"  # non blocca argparse
        import argparse
        with patch("argparse.ArgumentParser.parse_args",
                   return_value=argparse.Namespace(kb=None)):
            main()

    assert len(call_log) == 2


# ─────────────────────────────────────────────────────────────
# test_backfill_skips_empty_text
# ─────────────────────────────────────────────────────────────

def test_backfill_skips_empty_text():
    """Doc con chunks vuoti non chiama extract_and_save."""
    import sys, argparse

    doc_rows = [("doc-empty", "kb-1", "bandi")]
    chunk_rows = [("",), ("   ",)]  # testo vuoto

    call_log = []
    cursor_idx = [0]
    cursors = []

    cur_docs = MagicMock()
    cur_docs.fetchall.return_value = doc_rows
    cur_chunks = MagicMock()
    cur_chunks.fetchall.return_value = chunk_rows

    def make_ctx():
        ctx = MagicMock()
        seq = [cur_docs, cur_chunks]
        idx = cursor_idx[0]
        cursor_idx[0] += 1
        cur = seq[idx] if idx < len(seq) else MagicMock()
        ctx.__enter__ = MagicMock(return_value=cur)
        ctx.__exit__ = MagicMock(return_value=False)
        return ctx

    conn = MagicMock()
    conn.cursor.side_effect = make_ctx

    with patch("psycopg2.connect", return_value=conn), \
         patch("app.entity_extractor.extract_and_save", side_effect=lambda *a, **k: call_log.append(True)):
        if "app.backfill_entities" in sys.modules:
            del sys.modules["app.backfill_entities"]
        from app.backfill_entities import main
        with patch("argparse.ArgumentParser.parse_args",
                   return_value=argparse.Namespace(kb=None)):
            main()

    assert call_log == [], "extract_and_save non deve essere chiamato per testo vuoto"


# ─────────────────────────────────────────────────────────────
# test_backfill_filters_by_kb
# ─────────────────────────────────────────────────────────────

def test_backfill_filters_by_kb():
    """Con --kb bandi, la query WHERE usa il namespace corretto."""
    import sys, argparse

    cur_docs = MagicMock()
    cur_docs.fetchall.return_value = []  # nessun doc → nessuna iterazione

    cursor_idx = [0]

    def make_ctx():
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=cur_docs)
        ctx.__exit__ = MagicMock(return_value=False)
        return ctx

    conn = MagicMock()
    conn.cursor.side_effect = make_ctx

    with patch("psycopg2.connect", return_value=conn):
        if "app.backfill_entities" in sys.modules:
            del sys.modules["app.backfill_entities"]
        from app.backfill_entities import main
        with patch("argparse.ArgumentParser.parse_args",
                   return_value=argparse.Namespace(kb="bandi")):
            main()

    # Verifica che execute sia stato chiamato con il parametro namespace
    sql_call = cur_docs.execute.call_args
    assert sql_call is not None
    params = sql_call[0][1]  # secondo arg posizionale = tuple params
    assert "bandi" in params, f"Namespace 'bandi' non in params: {params}"
