"""test_graph_query.py — Test per api/app/graph_query.py (M7 GraphRAG)."""
from unittest.mock import MagicMock

import pytest

from app.graph_query import (
    enrich_sources,
    find_related_documents,
    get_document_entities,
    traverse_related,
)


def _dict_cursor(rows):
    """Cursore mock che ritorna righe come dict (simula RealDictCursor)."""
    cur = MagicMock()
    mock_rows = []
    for r in rows:
        m = MagicMock()
        m.keys = MagicMock(return_value=list(r.keys()))
        m.__getitem__ = lambda self, k, _r=r: _r[k]
        m.__iter__ = lambda self, _r=r: iter(_r.values())
        # Aggiunge accesso dict per compatibilità con dict(r)
        m.items = MagicMock(return_value=r.items())
        mock_rows.append(r)  # usa dict diretto — hasattr(dict, 'keys') == True
    cur.fetchall.return_value = mock_rows
    return cur


# ─────────────────────────────────────────────────────────────
# get_document_entities
# ─────────────────────────────────────────────────────────────

def test_get_document_entities_returns_rows():
    rows = [
        {"id": "e-1", "doc_id": "d-1", "entity_type": "fonte",
         "canonical": "fesr", "display_name": "FESR", "raw_value": None, "metadata": {}},
    ]
    cur = MagicMock()
    cur.fetchall.return_value = rows
    result = get_document_entities(cur, ["d-1"])
    assert len(result) == 1
    assert result[0]["display_name"] == "FESR"


def test_get_document_entities_empty_doc_ids():
    cur = MagicMock()
    result = get_document_entities(cur, [])
    cur.execute.assert_not_called()
    assert result == []


def test_get_document_entities_no_rows():
    cur = MagicMock()
    cur.fetchall.return_value = []
    result = get_document_entities(cur, ["d-1"])
    assert result == []


# ─────────────────────────────────────────────────────────────
# traverse_related
# ─────────────────────────────────────────────────────────────

def test_traverse_related_returns_with_depth_field():
    rows = [
        {"id": "e-1", "entity_type": "fonte", "canonical": "fesr",
         "display_name": "FESR", "depth": 0},
        {"id": "e-2", "entity_type": "programma", "canonical": "pr veneto",
         "display_name": "PR Veneto", "depth": 1},
    ]
    cur = MagicMock()
    cur.fetchall.return_value = rows
    result = traverse_related(cur, ["e-1"])
    assert len(result) == 2
    assert result[0]["depth"] == 0
    assert result[1]["depth"] == 1


def test_traverse_related_caps_depth_at_5():
    cur = MagicMock()
    cur.fetchall.return_value = []
    traverse_related(cur, ["e-1"], depth=99)
    sql = cur.execute.call_args[0][0]
    params = cur.execute.call_args[0][1]
    # Il secondo parametro nella query deve essere 5 (cap)
    assert params[1] == 5


def test_traverse_related_empty_entity_ids():
    cur = MagicMock()
    result = traverse_related(cur, [])
    cur.execute.assert_not_called()
    assert result == []


def test_traverse_related_no_rows():
    cur = MagicMock()
    cur.fetchall.return_value = []
    result = traverse_related(cur, ["e-1"])
    assert result == []


# ─────────────────────────────────────────────────────────────
# find_related_documents
# ─────────────────────────────────────────────────────────────

def test_find_related_documents_returns_related():
    entity_rows = [
        {"id": "e-1", "doc_id": "d-1", "entity_type": "fonte", "canonical": "fesr",
         "display_name": "FESR", "raw_value": None, "metadata": {}},
    ]
    traversal_rows = [
        {"id": "e-1", "entity_type": "fonte", "canonical": "fesr",
         "display_name": "FESR", "depth": 0},
        {"id": "e-2", "entity_type": "programma", "canonical": "pr veneto",
         "display_name": "PR Veneto", "depth": 1},
    ]
    related_doc_rows = [
        {"doc_id": "d-2", "source_uri": "/data/prveneto.pdf", "titolo": "PR Veneto",
         "entity_count": 1, "shared_entities": ["FESR"]},
    ]

    cur = MagicMock()
    cur.fetchall.side_effect = [entity_rows, traversal_rows, related_doc_rows]

    result = find_related_documents(cur, ["d-1"])
    assert len(result) == 1
    assert result[0]["doc_id"] == "d-2"


def test_find_related_documents_empty_doc_ids():
    cur = MagicMock()
    result = find_related_documents(cur, [])
    cur.execute.assert_not_called()
    assert result == []


def test_find_related_documents_no_entities():
    cur = MagicMock()
    cur.fetchall.return_value = []
    result = find_related_documents(cur, ["d-1"])
    assert result == []


# ─────────────────────────────────────────────────────────────
# enrich_sources
# ─────────────────────────────────────────────────────────────

def test_enrich_sources_adds_related_keys():
    """Verifica che enrich_sources aggiunga related_entities e related_docs."""
    chunk_doc_rows = [{"chunk_id": "c-1", "doc_id": "d-1"}]
    entity_rows = [
        {"id": "e-1", "doc_id": "d-1", "entity_type": "fonte", "canonical": "fesr",
         "display_name": "FESR", "raw_value": None, "metadata": {}},
    ]
    traversal_rows = [
        {"id": "e-1", "entity_type": "fonte", "canonical": "fesr",
         "display_name": "FESR", "depth": 0},
    ]
    related_doc_rows: list = []

    cur = MagicMock()
    cur.fetchall.side_effect = [chunk_doc_rows, entity_rows, traversal_rows, related_doc_rows]

    sources = [{"id": "c-1", "score": 0.9, "kb_namespace": "demo",
                "source_path": "/data/test.pdf", "excerpt": "testo"}]
    result = enrich_sources(cur, sources)

    assert len(result) == 1
    assert "related_entities" in result[0]
    assert "related_docs" in result[0]
    assert result[0]["related_entities"][0]["display_name"] == "FESR"


def test_enrich_sources_graceful_on_db_error():
    cur = MagicMock()
    cur.fetchall.side_effect = Exception("DB error")
    sources = [{"id": "c-1", "score": 0.9, "kb_namespace": "demo",
                "source_path": "/path", "excerpt": "testo"}]
    result = enrich_sources(cur, sources)
    # Deve ritornare sources originale senza crash
    assert len(result) == 1
    assert result[0]["id"] == "c-1"


def test_enrich_sources_empty_input():
    cur = MagicMock()
    result = enrich_sources(cur, [])
    assert result == []
    cur.execute.assert_not_called()
