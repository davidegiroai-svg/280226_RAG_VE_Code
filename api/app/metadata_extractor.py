"""metadata_extractor.py — Estrazione metadati strutturati da documenti tramite LLM."""
import os
import json
import logging
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

METADATA_EXTRACTION_PROMPT = (
    "Sei un archivista esperto di documenti della Pubblica Amministrazione italiana, "
    "specializzato in fondi europei e programmazione sociale.\n\n"
    "Analizza il testo del documento fornito e restituisci SOLO un oggetto JSON valido "
    "(nessun testo aggiuntivo, nessun markdown, nessuna spiegazione) con questo schema:\n\n"
    '{"titolo": "...", '
    '"tipo_documento": "programma_operativo|avviso_bando|scheda_progetto|linee_guida|decreto|allegato|sintesi", '
    '"fonte_programma": "es. PN Inclusione, PN Metro+, PNRR, PR Veneto FESR, ...", '
    '"fondo": "FSE+|FESR|AMIF|PNRR|Fondo Povert\u00e0|null", '
    '"ente_gestore": "...", '
    '"anno": 2024, '
    '"lingua": "it|en", '
    '"targets": ["Minori","Adulti","Donne","Anziani","Famiglie","ETS","ATS/PA","Cittadini","Migranti"], '
    '"ambiti": ["Disabilit\u00e0/Non autosufficienza","Disagio socio-economico","Disagio abitativo",'
    '"Grave emarginazione","Occupabilit\u00e0","Socialit\u00e0/Comunit\u00e0","Emergenza",'
    '"Discriminazione/Lotta alla violenza","Rafforzamento capacit\u00e0 amministrativa",'
    '"Infrastrutture per l\'inclusione sociale","Child guarantee"], '
    '"dotazione_finanziaria": "...|null", '
    '"scadenza": "YYYY-MM-DD|null", '
    '"codice_avviso": "...|null", '
    '"note": "...|null"}\n\n'
    "ISTRUZIONI:\n"
    "- targets e ambiti: includi SOLO i valori dall'elenco sopra che sono effettivamente presenti nel documento\n"
    "- Se un campo non \u00e8 presente nel documento, usa null\n"
    "- Rispondi ESCLUSIVAMENTE con il JSON, senza testo prima o dopo\n"
)

_FALLBACK = {
    "titolo": None, "tipo_documento": None, "fonte_programma": None,
    "fondo": None, "ente_gestore": None, "anno": None, "lingua": "it",
    "targets": [], "ambiti": [], "dotazione_finanziaria": None,
    "scadenza": None, "codice_avviso": None, "note": None,
}


def extract_metadata_for_file(
    file_path: Path,
    model: str,
    text_snippet: str,
    timeout: int = 120,
) -> dict:
    """Estrae metadati strutturati da un documento usando l'LLM Ollama."""
    ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")

    user_content = (
        f"Nome file: {file_path.name}\n\n"
        f"Testo documento:\n{text_snippet[:6000]}"
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": METADATA_EXTRACTION_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
    }

    try:
        resp = requests.post(f"{ollama_base_url}/api/chat", json=payload, timeout=timeout)
        resp.raise_for_status()
        content = resp.json()["message"]["content"].strip()
        # Rimuovi eventuali backtick markdown
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        logger.warning("extract_metadata_for_file: errore — %s", e)
        return dict(_FALLBACK)


def save_sidecar_meta(file_path: Path, meta: dict) -> Path:
    """Salva i metadati come file .meta.json accanto al documento."""
    meta_path = file_path.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta_path
