"""tests/test_query.py — TDD per query pipeline: parse_results, build_query_sql.

Testa la propagazione di doc_metadata dalla colonna chunks.metadata JSONB.
"""
import pytest


def test_parse_results_include_doc_metadata(monkeypatch):
    """parse_results deve includere doc_metadata dai chunk results."""
    from app.query import parse_results
    rows = [{
        "id": "uuid-1",
        "kb_namespace": "programmi",
        "excerpt": "Testo di prova.",
        "source_path": "/data/inbox/programmi/PNRR.pdf",
        "distance": 0.2,
        "doc_metadata": {"targets": ["Minori"], "ambiti": ["Child guarantee"]},
    }]
    results = parse_results(rows)
    assert results[0]["doc_metadata"] == {"targets": ["Minori"], "ambiti": ["Child guarantee"]}


def test_parse_results_doc_metadata_none_se_assente(monkeypatch):
    """parse_results restituisce doc_metadata={} se la colonna è NULL."""
    from app.query import parse_results
    rows = [{
        "id": "uuid-2",
        "kb_namespace": "programmi",
        "excerpt": "Testo.",
        "source_path": None,
        "distance": 0.3,
        "doc_metadata": None,
    }]
    results = parse_results(rows)
    assert results[0]["doc_metadata"] == {}
