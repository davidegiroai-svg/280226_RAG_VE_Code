"""Test per il modulo multi-query expansion via Ollama."""
import json
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.multiquery import expand_query
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Test unitari per expand_query()
# ---------------------------------------------------------------------------

def test_expand_query_returns_variants():
    """Mock Ollama risponde con JSON array valido — 4 risultati (originale + 3)."""
    variants = ["riformulazione 1", "riformulazione 2", "riformulazione 3"]
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "message": {"content": json.dumps(variants)}
    }

    with patch("app.multiquery.requests.post", return_value=mock_resp):
        result = expand_query("bandi europei", model="test", base_url="http://fake", timeout=5)

    assert len(result) == 4
    assert result[0] == "bandi europei"
    assert result[1:] == variants


def test_expand_query_includes_original():
    """La query originale e' sempre il primo elemento."""
    variants = ["v1", "v2", "v3"]
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "message": {"content": json.dumps(variants)}
    }

    with patch("app.multiquery.requests.post", return_value=mock_resp):
        result = expand_query("domanda test", model="test", base_url="http://fake", timeout=5)

    assert result[0] == "domanda test"


def test_expand_query_fallback_on_error():
    """Se requests.post lancia eccezione, restituisce solo [query]."""
    with patch("app.multiquery.requests.post", side_effect=Exception("connection refused")):
        result = expand_query("domanda fallback", model="test", base_url="http://fake", timeout=5)

    assert result == ["domanda fallback"]


def test_expand_query_fallback_on_bad_json():
    """Se la risposta non e' JSON valido, restituisce solo [query]."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "message": {"content": "questo non e' json valido"}
    }

    with patch("app.multiquery.requests.post", return_value=mock_resp):
        result = expand_query("query malformata", model="test", base_url="http://fake", timeout=5)

    assert result == ["query malformata"]


def test_expand_query_strips_markdown_fences():
    """Se LLM avvolge la risposta in ```json ... ```, parsifica correttamente."""
    variants = ["var A", "var B", "var C"]
    wrapped = '```json\n' + json.dumps(variants) + '\n```'
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "message": {"content": wrapped}
    }

    with patch("app.multiquery.requests.post", return_value=mock_resp):
        result = expand_query("query fenced", model="test", base_url="http://fake", timeout=5)

    assert len(result) == 4
    assert result[0] == "query fenced"
    assert result[1:] == variants


# ---------------------------------------------------------------------------
# Test integrazione API — wiring in main.py
# ---------------------------------------------------------------------------

def _mock_db_cursor():
    """Helper: crea mock per get_db_cursor con risultati vuoti."""
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchall.return_value = []
    return mock_cursor


def test_query_api_multiquery_disabled(monkeypatch):
    """MULTIQUERY_ENABLED non settato (default false) — expand_query non chiamata."""
    monkeypatch.delenv("MULTIQUERY_ENABLED", raising=False)

    mock_cur = _mock_db_cursor()

    with patch("app.main.get_db_cursor", return_value=mock_cur):
        with patch("app.main.embed_text", return_value=([0.0] * 768, "dummy", 768)):
            with patch("app.multiquery.expand_query") as mock_expand:
                resp = client.post("/api/v1/query", json={
                    "query": "bandi europei",
                    "search_mode": "hybrid",
                    "top_k": 3,
                })

    assert resp.status_code == 200
    mock_expand.assert_not_called()


def test_query_api_multiquery_enabled_hybrid(monkeypatch):
    """MULTIQUERY_ENABLED=true + search_mode=hybrid — expand_query viene chiamata."""
    monkeypatch.setenv("MULTIQUERY_ENABLED", "true")

    mock_cur = _mock_db_cursor()

    with patch("app.main.get_db_cursor", return_value=mock_cur):
        with patch("app.main.embed_text", return_value=([0.0] * 768, "dummy", 768)):
            with patch("app.multiquery.expand_query", return_value=["bandi europei"]) as mock_expand:
                resp = client.post("/api/v1/query", json={
                    "query": "bandi europei",
                    "search_mode": "hybrid",
                    "top_k": 3,
                })

    assert resp.status_code == 200
    mock_expand.assert_called_once_with("bandi europei")


def test_query_api_multiquery_enabled_vector(monkeypatch):
    """MULTIQUERY_ENABLED=true + search_mode=vector — expand_query NON viene chiamata."""
    monkeypatch.setenv("MULTIQUERY_ENABLED", "true")

    mock_cur = _mock_db_cursor()

    with patch("app.main.get_db_cursor", return_value=mock_cur):
        with patch("app.main.embed_text", return_value=([0.0] * 768, "dummy", 768)):
            with patch("app.multiquery.expand_query") as mock_expand:
                resp = client.post("/api/v1/query", json={
                    "query": "bandi europei",
                    "search_mode": "vector",
                    "top_k": 3,
                })

    assert resp.status_code == 200
    mock_expand.assert_not_called()
