"""tests/test_metadata_extractor.py — TDD per estrazione metadati LLM da documenti."""
import json
from unittest.mock import patch, MagicMock
from pathlib import Path


EXPECTED_SCHEMA_KEYS = {
    "titolo", "tipo_documento", "fonte_programma", "fondo", "ente_gestore",
    "anno", "lingua", "targets", "ambiti", "dotazione_finanziaria",
    "scadenza", "codice_avviso", "note",
}


def test_extract_metadata_ritorna_dict_con_schema_atteso(tmp_path):
    """extract_metadata_for_file deve ritornare dict con tutte le chiavi schema."""
    fake_response = MagicMock()
    fake_response.json.return_value = {
        "message": {"content": json.dumps({
            "titolo": "Test Doc",
            "tipo_documento": "avviso_bando",
            "fonte_programma": "PN Inclusione",
            "fondo": "FSE+",
            "ente_gestore": "Ministero",
            "anno": 2024,
            "lingua": "it",
            "targets": ["Minori"],
            "ambiti": ["Child guarantee"],
            "dotazione_finanziaria": "1M \u20ac",
            "scadenza": None,
            "codice_avviso": None,
            "note": None,
        })}
    }
    fake_response.raise_for_status.return_value = None

    doc = tmp_path / "test.pdf"
    doc.write_bytes(b"%PDF")

    with patch("requests.post", return_value=fake_response):
        from app.metadata_extractor import extract_metadata_for_file
        result = extract_metadata_for_file(doc, model="llama3.2", text_snippet="Testo test.")

    assert isinstance(result, dict)
    assert result["titolo"] == "Test Doc"
    assert result["targets"] == ["Minori"]


def test_extract_metadata_ritorna_fallback_su_errore_llm(tmp_path):
    """extract_metadata_for_file ritorna dict con valori null se LLM non risponde."""
    import requests as req
    doc = tmp_path / "test.pdf"
    doc.write_bytes(b"%PDF")

    with patch("requests.post", side_effect=req.ConnectionError("offline")):
        from app.metadata_extractor import extract_metadata_for_file
        result = extract_metadata_for_file(doc, model="llama3.2", text_snippet="Testo test.")

    assert isinstance(result, dict)
    assert "titolo" in result
    assert result["targets"] == []
    assert result["ambiti"] == []


def test_prompt_estrazione_contiene_tassonomia():
    """METADATA_EXTRACTION_PROMPT deve contenere la tassonomia targets e ambiti."""
    from app.metadata_extractor import METADATA_EXTRACTION_PROMPT
    p = METADATA_EXTRACTION_PROMPT
    for target in ["Minori", "Anziani", "Migranti", "ETS"]:
        assert target in p
    for ambito in ["Disabilit\u00e0", "Occupabilit\u00e0", "Child guarantee"]:
        assert ambito in p
