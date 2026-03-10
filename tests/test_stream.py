"""tests/test_stream.py — TDD Phase 14: Streaming SSE endpoint

Testa POST /api/v1/query/stream:
- Formato SSE corretto (data: ... eventi)
- synthesize=False: risposta immediata "Retrieval-only response."
- sources vuote: messaggio "Nessun documento trovato..."
- synthesize=True + mock LLM: token + evento [DONE]
"""
import json
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────

def _mock_cursor(rows=None):
    """Mock compatibile con 'with get_db_cursor() as cursor'."""
    mock_cur = MagicMock()
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=mock_cur)
    ctx.__exit__ = MagicMock(return_value=False)
    if rows is not None:
        mock_cur.fetchall.return_value = rows
    return ctx, mock_cur


SAMPLE_ROW = {
    "id": "test-uuid-stream-1",
    "kb_namespace": "demo",
    "excerpt": "Estratto di test per streaming SSE.",
    "source_path": "/data/inbox/demo/test.txt",
    "distance": 0.2,
}


def _parse_sse(text: str) -> list[dict]:
    """Parsea testo SSE e ritorna lista di payload (escluso [DONE])."""
    events = []
    for line in text.splitlines():
        if not line.startswith("data: "):
            continue
        payload = line[6:]
        if payload == "[DONE]":
            events.append({"__done__": True})
            continue
        try:
            events.append(json.loads(payload))
        except json.JSONDecodeError:
            pass
    return events


# ─────────────────────────────────────────────────────────
# Test 1: synthesize=False → risposta immediata retrieval-only
# ─────────────────────────────────────────────────────────

def test_stream_retrieval_only(monkeypatch):
    """synthesize=False: arriva evento sources + token 'Retrieval-only response.' + [DONE]."""
    monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
    ctx, mock_cur = _mock_cursor([SAMPLE_ROW])

    with patch("app.main.get_db_cursor", return_value=ctx):
        with patch("app.main.embed_text", return_value=([0.0] * 768, "dummy", 768)):
            resp = client.post(
                "/api/v1/query/stream",
                json={"query": "bando", "synthesize": False, "search_mode": "vector"},
            )

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    events = _parse_sse(resp.text)
    types = [e.get("type") for e in events]

    assert "sources" in types, "Manca evento sources"
    assert "token" in types, "Manca evento token"
    assert {"__done__": True} in events, "Manca evento [DONE]"

    token_event = next(e for e in events if e.get("type") == "token")
    assert token_event["content"] == "Retrieval-only response."


# ─────────────────────────────────────────────────────────
# Test 2: sources vuote → messaggio "Nessun documento trovato"
# ─────────────────────────────────────────────────────────

def test_stream_no_sources(monkeypatch):
    """Sources vuote: token contiene 'Nessun documento trovato'."""
    monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
    ctx, mock_cur = _mock_cursor([])  # nessun risultato

    with patch("app.main.get_db_cursor", return_value=ctx):
        with patch("app.main.embed_text", return_value=([0.0] * 768, "dummy", 768)):
            resp = client.post(
                "/api/v1/query/stream",
                json={"query": "query senza risultati", "synthesize": True, "search_mode": "vector"},
            )

    assert resp.status_code == 200
    events = _parse_sse(resp.text)

    sources_event = next((e for e in events if e.get("type") == "sources"), None)
    assert sources_event is not None
    assert sources_event["sources"] == []

    token_event = next((e for e in events if e.get("type") == "token"), None)
    assert token_event is not None
    assert "Nessun documento trovato" in token_event["content"]

    assert {"__done__": True} in events


# ─────────────────────────────────────────────────────────
# Test 3: synthesize=True + mock LLM → token progressivi + [DONE]
# ─────────────────────────────────────────────────────────

def test_stream_synthesize_with_llm(monkeypatch):
    """synthesize=True con LLM mockato: token arrivano + [DONE] finale.

    query_stream importa synthesize_stream localmente con 'from .llm import',
    quindi patchare app.llm.synthesize_stream è sufficiente per intercettarla.
    """
    monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
    ctx, mock_cur = _mock_cursor([SAMPLE_ROW])

    def fake_stream(query, chunks, model, history=None):
        yield "Ciao "
        yield "mondo "
        yield "test."

    with patch("app.main.get_db_cursor", return_value=ctx):
        with patch("app.main.embed_text", return_value=([0.0] * 768, "dummy", 768)):
            with patch("app.llm.synthesize_stream", new=fake_stream):
                resp = client.post(
                    "/api/v1/query/stream",
                    json={"query": "domanda test", "synthesize": True, "search_mode": "vector"},
                )

    assert resp.status_code == 200
    events = _parse_sse(resp.text)

    token_events = [e for e in events if e.get("type") == "token"]
    assert len(token_events) == 3, f"Attesi 3 token, ricevuti {len(token_events)}"
    assert token_events[0]["content"] == "Ciao "
    assert token_events[1]["content"] == "mondo "
    assert token_events[2]["content"] == "test."

    assert {"__done__": True} in events
