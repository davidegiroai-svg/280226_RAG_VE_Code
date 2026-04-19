"""test_entity_extractor.py — Test per api/app/entity_extractor.py (M7 GraphRAG)."""
import json
from unittest.mock import MagicMock, patch, call

import pytest

from app.entity_extractor import (
    _canonicalize,
    _normalize_extracted,
    extract_and_save,
    extract_entities_from_text,
    save_entities_for_document,
    save_relations,
)


# ─────────────────────────────────────────────────────────────
# _canonicalize
# ─────────────────────────────────────────────────────────────

def test_canonicalize_lowercase_strip():
    assert _canonicalize("  FESR  ") == "fesr"


def test_canonicalize_collapses_whitespace():
    assert _canonicalize("PR  Veneto  FESR") == "pr veneto fesr"


# ─────────────────────────────────────────────────────────────
# _normalize_extracted
# ─────────────────────────────────────────────────────────────

def test_normalize_filters_invalid_entity_type():
    raw = {"entities": [{"type": "fantasma", "name": "X"}], "relations": []}
    result = _normalize_extracted(raw)
    assert result["entities"] == []


def test_normalize_keeps_valid_entity_types():
    raw = {
        "entities": [
            {"type": "fonte", "name": "FESR"},
            {"type": "programma", "name": "PR Veneto"},
        ],
        "relations": [],
    }
    result = _normalize_extracted(raw)
    assert len(result["entities"]) == 2


def test_normalize_deduplicates_entities():
    raw = {
        "entities": [
            {"type": "fonte", "name": "FESR"},
            {"type": "fonte", "name": "fesr"},  # same canonical
        ],
        "relations": [],
    }
    result = _normalize_extracted(raw)
    assert len(result["entities"]) == 1


def test_normalize_filters_invalid_relation():
    raw = {
        "entities": [{"type": "fonte", "name": "A"}, {"type": "bando", "name": "B"}],
        "relations": [{"from": "A", "relation": "inventata", "to": "B"}],
    }
    result = _normalize_extracted(raw)
    assert result["relations"] == []


def test_normalize_keeps_valid_relation():
    raw = {
        "entities": [{"type": "bando", "name": "Avviso 42"}, {"type": "fonte", "name": "FESR"}],
        "relations": [{"from": "Avviso 42", "relation": "finanziato_da", "to": "FESR"}],
    }
    result = _normalize_extracted(raw)
    assert len(result["relations"]) == 1
    assert result["relations"][0]["relation"] == "finanziato_da"


# ─────────────────────────────────────────────────────────────
# extract_entities_from_text
# ─────────────────────────────────────────────────────────────

def _make_ollama_response(entities, relations):
    """Helper: costruisce MagicMock risposta Ollama con JSON valido."""
    body = json.dumps({"entities": entities, "relations": relations})
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"message": {"content": body}}
    return mock_resp


def test_extract_returns_entities_on_success():
    entities = [{"type": "fonte", "name": "FESR"}]
    relations = []
    with patch("app.entity_extractor.requests.post", return_value=_make_ollama_response(entities, relations)):
        result = extract_entities_from_text("Bando finanziato da FESR")
    assert len(result["entities"]) == 1
    assert result["entities"][0]["name"] == "FESR"


def test_extract_returns_empty_on_connection_error():
    with patch("app.entity_extractor.requests.post", side_effect=ConnectionError("down")):
        result = extract_entities_from_text("testo")
    assert result == {"entities": [], "relations": []}


def test_extract_returns_empty_on_invalid_json():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"message": {"content": "non è json"}}
    with patch("app.entity_extractor.requests.post", return_value=mock_resp):
        result = extract_entities_from_text("testo")
    assert result == {"entities": [], "relations": []}


def test_extract_strips_markdown_backticks():
    body = '```json\n{"entities": [{"type": "fonte", "name": "PNRR"}], "relations": []}\n```'
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"message": {"content": body}}
    with patch("app.entity_extractor.requests.post", return_value=mock_resp):
        result = extract_entities_from_text("testo PNRR")
    assert len(result["entities"]) == 1
    assert result["entities"][0]["name"] == "PNRR"


def test_extract_returns_empty_for_empty_text():
    with patch("app.entity_extractor.requests.post") as mock_post:
        result = extract_entities_from_text("")
    mock_post.assert_not_called()
    assert result == {"entities": [], "relations": []}


def test_extract_reads_ollama_url_from_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://custom-host:9999")
    mock_resp = _make_ollama_response([], [])
    with patch("app.entity_extractor.requests.post", return_value=mock_resp) as mock_post:
        extract_entities_from_text("testo qualsiasi con contenuto")
    called_url = mock_post.call_args[0][0]
    assert "custom-host:9999" in called_url


def test_extract_disabled_by_env_var_not_called_here(monkeypatch):
    """extract_entities_from_text non ha il gate — extract_and_save lo ha."""
    # Qui testiamo solo che la funzione risponde normalmente (il gate è in extract_and_save)
    monkeypatch.setenv("ENTITY_EXTRACTION_ENABLED", "false")
    with patch("app.entity_extractor.requests.post") as mock_post:
        # extract_entities_from_text non controlla la var — lo fa extract_and_save
        mock_post.return_value = _make_ollama_response([], [])
        result = extract_entities_from_text("testo")
    assert result == {"entities": [], "relations": []}


# ─────────────────────────────────────────────────────────────
# save_entities_for_document
# ─────────────────────────────────────────────────────────────

def _make_cursor(insert_row=None, select_row=None):
    """Helper: cursore mock con fetchone configurabile."""
    cur = MagicMock()
    cur.fetchone.side_effect = [insert_row, select_row] if select_row is not None else [insert_row]
    return cur


def test_save_entities_returns_name_id_map():
    cur = MagicMock()
    cur.fetchone.return_value = ("uuid-1",)
    extracted = {"entities": [{"type": "fonte", "name": "FESR"}], "relations": []}
    result = save_entities_for_document(cur, "doc-id", "kb-id", extracted)
    assert result == {"FESR": "uuid-1"}


def test_save_entities_idempotent_on_conflict():
    """INSERT ritorna None (conflitto), SELECT ritorna UUID esistente."""
    cur = MagicMock()
    cur.fetchone.side_effect = [None, ("existing-uuid",)]
    extracted = {"entities": [{"type": "fonte", "name": "FESR"}], "relations": []}
    result = save_entities_for_document(cur, "doc-id", "kb-id", extracted)
    assert result == {"FESR": "existing-uuid"}


def test_save_entities_empty_returns_empty_map():
    cur = MagicMock()
    extracted = {"entities": [], "relations": []}
    result = save_entities_for_document(cur, "doc-id", "kb-id", extracted)
    assert result == {}
    cur.execute.assert_not_called()


# ─────────────────────────────────────────────────────────────
# save_relations
# ─────────────────────────────────────────────────────────────

def test_save_relations_inserts_valid_relation():
    cur = MagicMock()
    entity_map = {"FESR": "uuid-1", "PR Veneto": "uuid-2"}
    relations = [{"from": "FESR", "relation": "finanziato_da", "to": "PR Veneto"}]
    save_relations(cur, entity_map, relations, "doc-id")
    cur.execute.assert_called_once()
    sql = cur.execute.call_args[0][0]
    assert "entity_relations" in sql


def test_save_relations_skips_unknown_entity():
    cur = MagicMock()
    entity_map = {"FESR": "uuid-1"}  # PR Veneto non in mappa
    relations = [{"from": "FESR", "relation": "finanziato_da", "to": "PR Veneto"}]
    save_relations(cur, entity_map, relations, "doc-id")
    cur.execute.assert_not_called()


def test_save_relations_empty_list():
    cur = MagicMock()
    save_relations(cur, {"A": "uuid-1"}, [], "doc-id")
    cur.execute.assert_not_called()


# ─────────────────────────────────────────────────────────────
# extract_and_save
# ─────────────────────────────────────────────────────────────

def test_extract_and_save_disabled_by_env(monkeypatch):
    monkeypatch.setenv("ENTITY_EXTRACTION_ENABLED", "false")
    cur = MagicMock()
    with patch("app.entity_extractor.extract_entities_from_text") as mock_extract:
        extract_and_save(cur, "doc-id", "kb-id", "testo")
    mock_extract.assert_not_called()
    cur.execute.assert_not_called()


def test_extract_and_save_orchestrates_calls():
    cur = MagicMock()
    cur.fetchone.return_value = ("uuid-1",)
    extracted = {
        "entities": [{"type": "fonte", "name": "FESR"}],
        "relations": [],
    }
    with patch("app.entity_extractor.extract_entities_from_text", return_value=extracted):
        extract_and_save(cur, "doc-id", "kb-id", "testo con FESR")
    # Deve aver eseguito INSERT su entities
    assert cur.execute.called


def test_extract_and_save_graceful_on_exception():
    cur = MagicMock()
    with patch("app.entity_extractor.extract_entities_from_text", side_effect=RuntimeError("crash")):
        # Non deve propagare l'eccezione
        extract_and_save(cur, "doc-id", "kb-id", "testo")


def test_extract_and_save_skips_save_when_no_entities():
    cur = MagicMock()
    with patch("app.entity_extractor.extract_entities_from_text", return_value={"entities": [], "relations": []}):
        with patch("app.entity_extractor.save_entities_for_document") as mock_save:
            extract_and_save(cur, "doc-id", "kb-id", "testo")
    mock_save.assert_not_called()
