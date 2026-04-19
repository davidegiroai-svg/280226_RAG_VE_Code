"""test_graph_api.py — Test per gli endpoint graph M7 e graph_enabled in query API."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _mock_db_cursor(rows=None):
    """Helper: crea un mock context manager per get_db_cursor()."""
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = rows or []
    mock_cur.fetchone.return_value = None
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=mock_cur)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx, mock_cur


# ─────────────────────────────────────────────────────────────
# GET /api/v1/graph/entities
# ─────────────────────────────────────────────────────────────

def test_graph_entities_returns_200():
    entities = [
        {"id": "e-1", "doc_id": "d-1", "entity_type": "fonte", "canonical": "fesr",
         "display_name": "FESR", "raw_value": None, "metadata": {}},
    ]
    ctx, mock_cur = _mock_db_cursor(entities)
    with patch("app.main.get_db_cursor", return_value=ctx):
        resp = client.get("/api/v1/graph/entities?doc_id=d-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["doc_id"] == "d-1"
    assert len(data["entities"]) == 1
    assert data["entities"][0]["display_name"] == "FESR"


def test_graph_entities_returns_empty_list_for_unknown_doc():
    ctx, _ = _mock_db_cursor([])
    with patch("app.main.get_db_cursor", return_value=ctx):
        resp = client.get("/api/v1/graph/entities?doc_id=unknown-doc-id")
    assert resp.status_code == 200
    assert resp.json()["entities"] == []


def test_graph_entities_requires_doc_id_param():
    resp = client.get("/api/v1/graph/entities")
    assert resp.status_code == 422


def test_graph_entities_requires_auth(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    resp = client.get("/api/v1/graph/entities?doc_id=d-1")
    assert resp.status_code in (401, 403)


# ─────────────────────────────────────────────────────────────
# GET /api/v1/graph/traverse
# ─────────────────────────────────────────────────────────────

def test_graph_traverse_returns_200():
    seed_rows = [
        {"id": "e-1", "entity_type": "fonte", "canonical": "fesr", "display_name": "FESR"},
    ]
    traversal_rows = [
        {"id": "e-1", "entity_type": "fonte", "canonical": "fesr",
         "display_name": "FESR", "depth": 0},
        {"id": "e-2", "entity_type": "programma", "canonical": "pr veneto",
         "display_name": "PR Veneto", "depth": 1},
    ]
    ctx, mock_cur = _mock_db_cursor()
    mock_cur.fetchall.side_effect = [seed_rows, traversal_rows]
    with patch("app.main.get_db_cursor", return_value=ctx):
        resp = client.get("/api/v1/graph/traverse?entity_name=FESR")
    assert resp.status_code == 200
    data = resp.json()
    assert data["seed_entity"] is not None
    assert data["seed_entity"]["display_name"] == "FESR"
    assert len(data["related_entities"]) == 2


def test_graph_traverse_returns_empty_for_unknown_name():
    ctx, mock_cur = _mock_db_cursor([])
    mock_cur.fetchall.return_value = []
    with patch("app.main.get_db_cursor", return_value=ctx):
        resp = client.get("/api/v1/graph/traverse?entity_name=inesistente")
    assert resp.status_code == 200
    data = resp.json()
    assert data["seed_entity"] is None
    assert data["related_entities"] == []


def test_graph_traverse_depth_cap_validation():
    """depth > 5 deve dare 422 per la validazione Pydantic (ge=1, le=5)."""
    resp = client.get("/api/v1/graph/traverse?entity_name=X&depth=10")
    assert resp.status_code == 422


def test_graph_traverse_depth_min_validation():
    resp = client.get("/api/v1/graph/traverse?entity_name=X&depth=0")
    assert resp.status_code == 422


def test_graph_traverse_requires_entity_name_param():
    resp = client.get("/api/v1/graph/traverse")
    assert resp.status_code == 422


def test_graph_traverse_requires_auth(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    resp = client.get("/api/v1/graph/traverse?entity_name=FESR")
    assert resp.status_code in (401, 403)


# ─────────────────────────────────────────────────────────────
# POST /api/v1/query con graph_enabled
# ─────────────────────────────────────────────────────────────

def test_query_graph_enabled_false_skips_enrichment(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
    sources = [{"id": "c-1", "score": 0.9, "kb_namespace": "demo",
                "source_path": None, "excerpt": "testo", "doc_metadata": None}]
    ctx, mock_cur = _mock_db_cursor()

    with patch("app.main.get_db_cursor", return_value=ctx), \
         patch("app.main.execute_search", return_value=sources), \
         patch("app.main.embed_text", return_value=([0.0] * 768, "dummy", 768)), \
         patch("app.graph_query.enrich_sources") as mock_enrich:
        resp = client.post("/api/v1/query", json={"query": "bando", "graph_enabled": False})

    assert resp.status_code == 200
    mock_enrich.assert_not_called()


def test_query_graph_enabled_true_calls_enrichment(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
    sources = [{"id": "c-1", "score": 0.9, "kb_namespace": "demo",
                "source_path": None, "excerpt": "testo", "doc_metadata": None}]
    enriched = [{**sources[0], "related_entities": [], "related_docs": []}]

    ctx, _ = _mock_db_cursor()

    with patch("app.main.get_db_cursor", return_value=ctx), \
         patch("app.main.execute_search", return_value=sources), \
         patch("app.main.embed_text", return_value=([0.0] * 768, "dummy", 768)), \
         patch("app.main.enrich_sources", return_value=enriched) as mock_enrich:
        resp = client.post("/api/v1/query", json={"query": "bando", "graph_enabled": True})

    assert resp.status_code == 200
    mock_enrich.assert_called_once()


def test_query_graph_enabled_graceful_degradation(monkeypatch):
    """Se enrich_sources fallisce, la query deve comunque restituire 200."""
    monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
    sources = [{"id": "c-1", "score": 0.9, "kb_namespace": "demo",
                "source_path": None, "excerpt": "testo", "doc_metadata": None}]

    ctx, _ = _mock_db_cursor()

    with patch("app.main.get_db_cursor", return_value=ctx), \
         patch("app.main.execute_search", return_value=sources), \
         patch("app.main.embed_text", return_value=([0.0] * 768, "dummy", 768)), \
         patch("app.main.enrich_sources", side_effect=Exception("crash grafo")):
        resp = client.post("/api/v1/query", json={"query": "bando", "graph_enabled": True})

    assert resp.status_code == 200
