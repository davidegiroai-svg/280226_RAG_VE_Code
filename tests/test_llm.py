"""tests/test_llm.py — TDD per LLM synthesis: _build_context, PROMPT_SISTEMA, grounding.

Testa la qualità del prompt, il builder contesto condiviso e l'integrazione con
synthesize_answer. NON richiede Ollama reale: tutto mockato.
"""
from unittest.mock import patch, MagicMock

import pytest


CHUNKS_ESEMPIO = [
    {
        "excerpt": "Il bando prevede un contributo massimo di €50.000 per PMI.",
        "source_path": "/data/inbox/demo/bando.pdf",
        "kb_namespace": "demo",
    },
    {
        "excerpt": "Scadenza presentazione domande: 31 marzo 2026.",
        "source_path": "/data/inbox/demo/bando.pdf",
        "kb_namespace": "demo",
    },
]


def test_build_context_include_indice_e_fonte():
    """_build_context deve numerare i documenti e includere la fonte."""
    from app.llm import _build_context
    ctx = _build_context(CHUNKS_ESEMPIO)
    assert "DOCUMENTO 1" in ctx      # ora nei delimitatori INIZIO/FINE
    assert "DOCUMENTO 2" in ctx
    assert "bando.pdf" in ctx


def test_build_context_include_delimitatori():
    """_build_context deve avvolgere ogni frammento con INIZIO/FINE."""
    from app.llm import _build_context
    ctx = _build_context(CHUNKS_ESEMPIO)
    assert "--- INIZIO DOCUMENTO 1" in ctx
    assert "--- FINE DOCUMENTO 1 ---" in ctx
    assert "--- INIZIO DOCUMENTO 2" in ctx
    assert "--- FINE DOCUMENTO 2 ---" in ctx


def test_build_context_gestisce_chunks_vuoti():
    """_build_context con lista vuota non solleva eccezione e ritorna stringa vuota."""
    from app.llm import _build_context
    ctx = _build_context([])
    assert ctx == ""


def test_build_context_usa_kb_namespace_se_no_source_path():
    """_build_context usa kb_namespace come fonte se source_path è assente."""
    from app.llm import _build_context
    chunks = [{"excerpt": "Testo di prova.", "kb_namespace": "demo"}]
    ctx = _build_context(chunks)
    assert "demo" in ctx
    assert "DOCUMENTO 1" in ctx      # aggiornato: non più [Documento 1]


def test_prompt_sistema_contiene_regola_no_allucinazione():
    """PROMPT_SISTEMA deve vietare esplicitamente l'uso di conoscenza esterna."""
    from app.llm import PROMPT_SISTEMA
    testo_lower = PROMPT_SISTEMA.lower()
    assert any(
        kw in testo_lower for kw in ["solo dai documenti", "esclusivamente", "solo le informazioni"]
    ), "PROMPT_SISTEMA deve vietare esplicitamente l'uso di conoscenza esterna"


def test_prompt_sistema_richiede_citazioni_inline():
    """PROMPT_SISTEMA deve richiedere citazioni [Documento N] dopo ogni affermazione."""
    from app.llm import PROMPT_SISTEMA
    assert "Documento N" in PROMPT_SISTEMA


def test_synthesize_answer_usa_build_context():
    """synthesize_answer deve delegare la costruzione del contesto a _build_context."""
    fake_response = MagicMock()
    fake_response.json.return_value = {"message": {"content": "Risposta di test."}}
    fake_response.raise_for_status.return_value = None

    with patch("app.llm._build_context", return_value="ctx_mock") as mock_ctx, \
         patch("requests.post", return_value=fake_response):
        from app.llm import synthesize_answer
        result = synthesize_answer("query", CHUNKS_ESEMPIO, "llama3.2")

    mock_ctx.assert_called_once_with(CHUNKS_ESEMPIO)
    assert result == "Risposta di test."


def test_synthesize_answer_ritorna_none_su_connessione_fallita():
    """synthesize_answer ritorna None (non solleva) se Ollama non è raggiungibile."""
    import requests as req

    with patch("requests.post", side_effect=req.ConnectionError("offline")):
        from app.llm import synthesize_answer
        result = synthesize_answer("query", CHUNKS_ESEMPIO, "llama3.2")

    assert result is None


def test_prompt_sistema_contiene_tassonomia_target():
    """PROMPT_SISTEMA deve elencare i TARGET del dominio."""
    from app.llm import PROMPT_SISTEMA
    p = PROMPT_SISTEMA
    for target in ["Minori", "Anziani", "Famiglie", "Migranti", "ETS"]:
        assert target in p, f"TARGET '{target}' mancante in PROMPT_SISTEMA"


def test_prompt_sistema_contiene_tassonomia_ambiti():
    """PROMPT_SISTEMA deve elencare gli AMBITI DI INTERVENTO del dominio."""
    from app.llm import PROMPT_SISTEMA
    p = PROMPT_SISTEMA
    for ambito in ["Disabilità", "Occupabilità", "Child guarantee", "Grave emarginazione"]:
        assert ambito in p, f"AMBITO '{ambito}' mancante in PROMPT_SISTEMA"


def test_prompt_sistema_contiene_regola_esclusione_target():
    """PROMPT_SISTEMA deve istruire l'LLM a ignorare frammenti di target diversi."""
    from app.llm import PROMPT_SISTEMA
    p_lower = PROMPT_SISTEMA.lower()
    assert "ignora" in p_lower or "ignorare" in p_lower or "ignora completamente" in p_lower, \
        "PROMPT_SISTEMA deve contenere una regola esplicita di esclusione (ignora) per target errati"


def test_prompt_sistema_vieta_dumping():
    """PROMPT_SISTEMA non deve più ordinare la riproduzione letterale di tabelle."""
    from app.llm import PROMPT_SISTEMA
    p_lower = PROMPT_SISTEMA.lower()
    # La vecchia regola TABELLE ordinava 'riproduci le tabelle in markdown' — deve essere assente
    assert "riproduci le tabelle" not in p_lower, \
        "PROMPT_SISTEMA non deve più ordinare la riproduzione raw delle tabelle"
    # Deve contenere il divieto di dumping
    assert any(kw in p_lower for kw in ["vietato", "è vietato", "non ripetere", "no dumping", "sintetizza"]), \
        "PROMPT_SISTEMA deve vietare esplicitamente il dump/copia pedissequa"


def test_prompt_sistema_contiene_fallback_rifiuto():
    """PROMPT_SISTEMA deve prevedere un template di risposta per assenza di match."""
    from app.llm import PROMPT_SISTEMA
    p_lower = PROMPT_SISTEMA.lower()
    assert any(kw in p_lower for kw in ["non ho trovato", "altri target", "altri ambiti"]), \
        "PROMPT_SISTEMA deve prevedere un fallback elegante quando i frammenti sono fuori target"
