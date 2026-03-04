"""tests/test_llm_synthesis.py — TDD Phase 8: LLM Synthesis

Testa la sintesi LLM tramite Ollama con mock di requests.post.
RED:  fallenti prima dell'implementazione in llm.py + main.py
GREEN: dopo l'aggiunta di synthesize_answer() e parametro synthesize
"""
from unittest.mock import patch, MagicMock

import pytest
import requests as requests_lib
from fastapi.testclient import TestClient

from app.main import app
from app.llm import synthesize_answer

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


def _ollama_response(content: str):
    """Crea mock della risposta Ollama /api/chat."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "message": {"role": "assistant", "content": content}
    }
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


# Righe DB di esempio
MOCK_ROWS = [
    {
        "id": "uuid-chunk-1",
        "kb_namespace": "demo",
        "excerpt": "I bandi per il comune di Venezia sono aperti fino al 31 marzo.",
        "source_path": "/data/inbox/demo/bandi.pdf",
        "distance": 0.2,
    }
]


# ─────────────────────────────────────────────────────────
# Test unitari per synthesize_answer()
# ─────────────────────────────────────────────────────────

class TestSynthesizeAnswer:

    def test_ritorna_testo_llm(self, monkeypatch):
        """synthesize_answer() ritorna il testo generato da Ollama."""
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://fake-ollama:11434")
        chunks = [{"excerpt": "I bandi sono aperti.", "source_path": "/data/bandi.pdf", "kb_namespace": "demo"}]

        with patch("app.llm.requests.post") as mock_post:
            mock_post.return_value = _ollama_response("Il bando è aperto fino al 31 marzo.")
            risultato = synthesize_answer("bandi aperti", chunks, "llama3.2")

        assert risultato == "Il bando è aperto fino al 31 marzo."
        assert mock_post.called

    def test_fallback_su_connection_error(self, monkeypatch):
        """synthesize_answer() ritorna None se Ollama non è raggiungibile."""
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://fake-ollama:11434")
        chunks = [{"excerpt": "Testo.", "source_path": None, "kb_namespace": "demo"}]

        with patch("app.llm.requests.post", side_effect=requests_lib.ConnectionError("unreachable")):
            risultato = synthesize_answer("query", chunks, "llama3.2")

        assert risultato is None

    def test_fallback_su_timeout(self, monkeypatch):
        """synthesize_answer() ritorna None in caso di timeout."""
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://fake-ollama:11434")
        chunks = [{"excerpt": "Testo.", "source_path": None, "kb_namespace": "demo"}]

        with patch("app.llm.requests.post", side_effect=requests_lib.Timeout("timeout")):
            risultato = synthesize_answer("query", chunks, "llama3.2")

        assert risultato is None

    def test_chunk_incluso_nel_prompt(self, monkeypatch):
        """Il testo del chunk deve essere incluso nel payload inviato a Ollama."""
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://fake-ollama:11434")
        testo_chunk = "TESTO_UNIVOCO_BANDI_2026_XYZ"
        chunks = [{"excerpt": testo_chunk, "source_path": None, "kb_namespace": "demo"}]

        with patch("app.llm.requests.post") as mock_post:
            mock_post.return_value = _ollama_response("risposta")
            synthesize_answer("domanda", chunks, "llama3.2")

        # Verifica che il testo del chunk sia nel payload
        payload = mock_post.call_args.kwargs["json"]
        testo_messaggi = " ".join(m["content"] for m in payload["messages"])
        assert testo_chunk in testo_messaggi

    def test_modello_corretto_nel_payload(self, monkeypatch):
        """Il nome del modello richiesto deve essere nel payload Ollama."""
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://fake-ollama:11434")
        chunks = [{"excerpt": "Testo.", "source_path": None, "kb_namespace": "demo"}]

        with patch("app.llm.requests.post") as mock_post:
            mock_post.return_value = _ollama_response("ok")
            synthesize_answer("domanda", chunks, "mistral")

        payload = mock_post.call_args.kwargs["json"]
        assert payload["model"] == "mistral"
        assert payload["stream"] is False


# ─────────────────────────────────────────────────────────
# Test integrazione API POST /api/v1/query con synthesize
# ─────────────────────────────────────────────────────────

class TestQueryApiConSynthesis:

    def test_senza_synthesize_non_chiama_llm(self, monkeypatch):
        """POST /query senza synthesize non deve chiamare l'LLM."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
        ctx, _ = _mock_cursor(MOCK_ROWS)

        with patch("app.main.get_db_cursor", return_value=ctx):
            with patch("app.main.embed_text", return_value=([0.0] * 768, "dummy", 768)):
                with patch("app.llm.requests.post") as mock_post:
                    resp = client.post(
                        "/api/v1/query",
                        json={"query": "bandi", "top_k": 1},
                    )

        assert resp.status_code == 200
        assert not mock_post.called

    def test_synthesize_false_esplicito_non_chiama_llm(self, monkeypatch):
        """POST /query con synthesize=false esplicito non deve chiamare l'LLM."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
        ctx, _ = _mock_cursor(MOCK_ROWS)

        with patch("app.main.get_db_cursor", return_value=ctx):
            with patch("app.main.embed_text", return_value=([0.0] * 768, "dummy", 768)):
                with patch("app.llm.requests.post") as mock_post:
                    resp = client.post(
                        "/api/v1/query",
                        json={"query": "bandi", "top_k": 1, "synthesize": False},
                    )

        assert resp.status_code == 200
        assert not mock_post.called

    def test_synthesize_true_chiama_llm_e_restituisce_answer(self, monkeypatch):
        """POST /query con synthesize=true deve chiamare Ollama e restituire l'answer sintetica."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://fake-ollama:11434")
        ctx, _ = _mock_cursor(MOCK_ROWS)

        with patch("app.main.get_db_cursor", return_value=ctx):
            with patch("app.main.embed_text", return_value=([0.0] * 768, "dummy", 768)):
                with patch("app.llm.requests.post") as mock_post:
                    mock_post.return_value = _ollama_response("Risposta sintetica del Comune.")
                    resp = client.post(
                        "/api/v1/query",
                        json={"query": "bandi", "top_k": 1, "synthesize": True},
                    )

        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "Risposta sintetica del Comune."
        assert len(data["sources"]) == 1

    def test_synthesize_fallback_se_llm_non_disponibile(self, monkeypatch):
        """Se LLM non risponde, la query ritorna i sources senza errore (HTTP 200)."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://fake-ollama:11434")
        ctx, _ = _mock_cursor(MOCK_ROWS)

        with patch("app.main.get_db_cursor", return_value=ctx):
            with patch("app.main.embed_text", return_value=([0.0] * 768, "dummy", 768)):
                with patch("app.llm.requests.post", side_effect=requests_lib.ConnectionError("unreachable")):
                    resp = client.post(
                        "/api/v1/query",
                        json={"query": "bandi", "top_k": 1, "synthesize": True},
                    )

        assert resp.status_code == 200
        data = resp.json()
        # Fallback: sources presenti, answer non vuota (messaggio di fallback)
        assert len(data["sources"]) == 1
        assert data["answer"] != ""
        assert data["answer"] is not None

    def test_synthesize_nessun_risultato_non_chiama_llm(self, monkeypatch):
        """Con synthesize=true e nessun chunk trovato, LLM non viene chiamato."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
        ctx, _ = _mock_cursor([])  # nessun risultato

        with patch("app.main.get_db_cursor", return_value=ctx):
            with patch("app.main.embed_text", return_value=([0.0] * 768, "dummy", 768)):
                with patch("app.llm.requests.post") as mock_post:
                    resp = client.post(
                        "/api/v1/query",
                        json={"query": "bandi", "top_k": 1, "synthesize": True},
                    )

        assert resp.status_code == 200
        data = resp.json()
        assert data["sources"] == []
        # LLM non deve essere chiamato se non ci sono chunk
        assert not mock_post.called


# ─────────────────────────────────────────────────────────
# Test history conversazionale (Phase conversational)
# ─────────────────────────────────────────────────────────

class TestSynthesizeAnswerConHistory:

    def test_history_inclusa_nel_payload(self, monkeypatch):
        """I messaggi di history devono apparire nel payload inviato a Ollama."""
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://fake-ollama:11434")
        chunks = [{"excerpt": "Testo.", "source_path": None, "kb_namespace": "demo"}]
        history = [
            {"role": "user", "content": "Prima domanda"},
            {"role": "assistant", "content": "Prima risposta"},
        ]

        with patch("app.llm.requests.post") as mock_post:
            mock_post.return_value = _ollama_response("ok")
            synthesize_answer("Seconda domanda", chunks, "llama3.2", history=history)

        payload = mock_post.call_args.kwargs["json"]
        ruoli = [m["role"] for m in payload["messages"]]
        contenuti = [m["content"] for m in payload["messages"]]
        assert "Prima domanda" in contenuti
        assert "Prima risposta" in contenuti
        # Ordine: system → history... → user(context+domanda)
        assert ruoli[0] == "system"
        assert ruoli[-1] == "user"

    def test_history_vuota_funziona(self, monkeypatch):
        """history=[] non causa errori e funziona come prima."""
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://fake-ollama:11434")
        chunks = [{"excerpt": "Testo.", "source_path": None, "kb_namespace": "demo"}]

        with patch("app.llm.requests.post") as mock_post:
            mock_post.return_value = _ollama_response("risposta ok")
            risultato = synthesize_answer("domanda", chunks, "llama3.2", history=[])

        assert risultato == "risposta ok"

    def test_history_none_funziona(self, monkeypatch):
        """history=None (default) non causa errori — compatibilità retroattiva."""
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://fake-ollama:11434")
        chunks = [{"excerpt": "Testo.", "source_path": None, "kb_namespace": "demo"}]

        with patch("app.llm.requests.post") as mock_post:
            mock_post.return_value = _ollama_response("risposta ok")
            risultato = synthesize_answer("domanda", chunks, "llama3.2")

        assert risultato == "risposta ok"


class TestQueryApiConHistory:

    def test_query_api_accetta_history(self, monkeypatch):
        """POST /api/v1/query con history restituisce 200."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://fake-ollama:11434")
        ctx, _ = _mock_cursor(MOCK_ROWS)

        history_payload = [
            {"role": "user", "content": "Prima domanda"},
            {"role": "assistant", "content": "Prima risposta"},
        ]

        with patch("app.main.get_db_cursor", return_value=ctx):
            with patch("app.main.embed_text", return_value=([0.0] * 768, "dummy", 768)):
                with patch("app.llm.requests.post") as mock_post:
                    mock_post.return_value = _ollama_response("Risposta conversazionale.")
                    resp = client.post(
                        "/api/v1/query",
                        json={
                            "query": "Seconda domanda",
                            "top_k": 1,
                            "synthesize": True,
                            "history": history_payload,
                        },
                    )

        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "Risposta conversazionale."

    def test_history_passata_a_synthesize(self, monkeypatch):
        """La history ricevuta dal API deve essere inoltrata a synthesize_answer."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://fake-ollama:11434")
        ctx, _ = _mock_cursor(MOCK_ROWS)

        history_payload = [{"role": "user", "content": "MARKER_HISTORY_TEST"}]

        with patch("app.main.get_db_cursor", return_value=ctx):
            with patch("app.main.embed_text", return_value=([0.0] * 768, "dummy", 768)):
                with patch("app.llm.requests.post") as mock_post:
                    mock_post.return_value = _ollama_response("ok")
                    client.post(
                        "/api/v1/query",
                        json={"query": "domanda", "top_k": 1, "synthesize": True, "history": history_payload},
                    )

        payload = mock_post.call_args.kwargs["json"]
        testi = " ".join(m["content"] for m in payload["messages"])
        assert "MARKER_HISTORY_TEST" in testi
