"""
TDD — filtri metadata: file_type, year_from, year_to
Questi test DEVONO fallire prima che i filtri siano implementati.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

from app.query import build_query_sql, execute_search
from app.hybrid import fts_search


def _make_chunk_row(idx: int = 0, file_type: str = "pdf", year: int = 2022) -> dict:
    return {
        "id": f"uuid-{idx}",
        "kb_namespace": "demo",
        "excerpt": f"Estratto {idx}",
        "source_path": f"/data/inbox/demo/doc{idx}.{file_type}",
        "doc_metadata": {"file_type": file_type},
        "distance": 0.2,
        "rank": 0.8,
    }


# ── build_query_sql ──────────────────────────────────────────────────────────

def test_filter_by_file_type_in_vector_sql():
    """build_query_sql: con file_type='pdf', SQL include filtro metadata->>'file_type'."""
    sql, params = build_query_sql(
        query_text="test",
        kb_namespace=None,
        top_k=5,
        query_vec=[0.0] * 768,
        file_type="pdf",
    )
    assert "file_type" in sql.lower() or "metadata" in sql.lower(), (
        "SQL deve includere filtro su file_type nel metadata JSONB"
    )
    assert "pdf" in params, "Valore 'pdf' deve essere nei params"


def test_filter_by_year_range_in_vector_sql():
    """build_query_sql: con year_from/year_to, SQL include filtro su ingest_date."""
    sql, params = build_query_sql(
        query_text="test",
        kb_namespace=None,
        top_k=5,
        query_vec=[0.0] * 768,
        year_from=2020,
        year_to=2024,
    )
    assert "year" in sql.lower() or "ingest_date" in sql.lower(), (
        "SQL deve includere filtro su anno (EXTRACT YEAR FROM ingest_date)"
    )
    assert 2020 in params and 2024 in params, "year_from e year_to devono essere nei params"


def test_filter_by_file_type_in_fts():
    """fts_search: con file_type='pdf', SQL include filtro metadata->>'file_type'."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []

    fts_search("bando", mock_cursor, kb_namespace=None, top_k=5, file_type="pdf")

    # Verifica che execute sia stato chiamato con SQL che include 'file_type'
    call_args = mock_cursor.execute.call_args
    sql_called = call_args[0][0]
    params_called = call_args[0][1]
    assert "file_type" in sql_called.lower() or "metadata" in sql_called.lower(), (
        "FTS SQL deve filtrare per file_type"
    )
    assert "pdf" in params_called


def test_no_filter_returns_all():
    """Senza filtri, build_query_sql non aggiunge WHERE clause metadata."""
    sql, params = build_query_sql(
        query_text="test",
        kb_namespace=None,
        top_k=5,
        query_vec=[0.0] * 768,
    )
    # Senza filtri, nessuna clausola metadata nel WHERE
    assert "file_type" not in sql
    assert "ingest_date" not in sql or "EXTRACT" not in sql
