"""entity_extractor.py — M7 GraphRAG: estrazione entità + persistenza grafo.

Estrazione via Ollama /api/chat con prompt strutturato JSON.
Tutte le funzioni sono SYNC (psycopg2 cursor passato dall'esterno).
Graceful degradation: qualsiasi errore viene loggato, l'ingest non viene mai bloccato.
"""
from __future__ import annotations

import json
import logging
import os

import requests

logger = logging.getLogger(__name__)

VALID_ENTITY_TYPES: frozenset = frozenset({
    "fonte", "programma", "asse", "bando", "progetto",
    "beneficiario", "scadenza", "importo",
})

VALID_RELATIONS: frozenset = frozenset({
    "finanziato_da", "appartiene_a", "asse", "risponde_a", "gestito_da",
})

_ENTITY_SYSTEM_PROMPT = (
    "Sei un archivista esperto di documenti della Pubblica Amministrazione italiana, "
    "specializzato in fondi europei, bandi e programmazione.\n\n"
    "Estrai le entità amministrative e le relazioni dal testo fornito.\n"
    "Rispondi ESCLUSIVAMENTE con un oggetto JSON valido (nessun testo, nessun markdown):\n\n"
    '{\n'
    '  "entities": [\n'
    '    {"type": "fonte|programma|asse|bando|progetto|beneficiario|scadenza|importo",\n'
    '     "name": "nome esatto dal testo"}\n'
    '  ],\n'
    '  "relations": [\n'
    '    {"from": "nome_entità_A",\n'
    '     "relation": "finanziato_da|appartiene_a|asse|risponde_a|gestito_da",\n'
    '     "to": "nome_entità_B"}\n'
    '  ]\n'
    '}\n\n'
    "ISTRUZIONI:\n"
    "- entities: includi solo entità ESPLICITAMENTE citate nel testo\n"
    "- relations: includi solo relazioni ESPLICITE tra entità estratte\n"
    "- scadenza: formato YYYY-MM-DD se possibile, altrimenti testo originale\n"
    "- importo: includi simbolo/valuta (es. '€ 500.000')\n"
    "- Se non ci sono entità, rispondi con {\"entities\": [], \"relations\": []}\n"
)

_EMPTY: dict = {"entities": [], "relations": []}


def _canonicalize(name: str) -> str:
    """Lowercase + strip + collassa whitespace. Usata come chiave dedup."""
    return " ".join(name.strip().lower().split())


def _normalize_extracted(raw: dict) -> dict:
    """Valida e filtra l'output LLM.

    - Filtra entity_type a VALID_ENTITY_TYPES
    - Filtra relation a VALID_RELATIONS
    - Dedup entità per (type, canonical)
    """
    seen: set = set()
    entities: list = []
    for e in raw.get("entities", []):
        etype = str(e.get("type", "")).strip().lower()
        name = str(e.get("name", "")).strip()
        if not etype or not name or etype not in VALID_ENTITY_TYPES:
            continue
        key = (etype, _canonicalize(name))
        if key in seen:
            continue
        seen.add(key)
        entities.append({"type": etype, "name": name})

    relations: list = []
    for r in raw.get("relations", []):
        rel = str(r.get("relation", "")).strip().lower()
        from_name = str(r.get("from", "")).strip()
        to_name = str(r.get("to", "")).strip()
        if rel not in VALID_RELATIONS or not from_name or not to_name:
            continue
        relations.append({"from": from_name, "relation": rel, "to": to_name})

    return {"entities": entities, "relations": relations}


def extract_entities_from_text(text: str) -> dict:
    """Chiama Ollama /api/chat e restituisce entità e relazioni strutturate.

    Legge OLLAMA_BASE_URL e OLLAMA_LLM_MODEL a runtime (non a modulo load)
    per compatibilità con monkeypatch nei test.

    Returns:
        dict con chiavi 'entities' (list) e 'relations' (list).
        Ritorna {"entities": [], "relations": []} su qualsiasi errore.

    Non rilancia eccezioni.
    """
    if not text or not text.strip():
        return dict(_EMPTY)

    ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    model = os.environ.get("OLLAMA_LLM_MODEL", "llama3.2")
    timeout = int(os.environ.get("ENTITY_EXTRACTION_TIMEOUT_S", "120"))

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _ENTITY_SYSTEM_PROMPT},
            {"role": "user", "content": f"TESTO:\n{text[:4000]}"},
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
        raw = json.loads(content)
        return _normalize_extracted(raw)
    except Exception as e:
        logger.warning("extract_entities_from_text: errore — %s", e)
        return dict(_EMPTY)


def save_entities_for_document(
    cur,
    doc_id: str,
    kb_id: str,
    extracted: dict,
) -> dict:
    """Upsert entità per un documento. Ritorna {display_name: entity_id} map.

    Usa INSERT ... ON CONFLICT (doc_id, entity_type, canonical) DO NOTHING.
    Per recuperare l'UUID in caso di conflitto, esegue un SELECT successivo.
    Idempotente: re-ingestire lo stesso documento non crea duplicati.

    Args:
        cur:       cursore psycopg2 aperto (nella transazione del chiamante)
        doc_id:    UUID del documento padre (stringa)
        kb_id:     UUID della knowledge base (stringa)
        extracted: output di extract_entities_from_text() già normalizzato

    Returns:
        dict {display_name: entity_id (stringa UUID)} per tutte le entità
    """
    entity_map: dict = {}
    for e in extracted.get("entities", []):
        etype = e["type"]
        name = e["name"]
        canonical = _canonicalize(name)

        cur.execute(
            """
            INSERT INTO entities (kb_id, doc_id, entity_type, canonical, display_name)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (doc_id, entity_type, canonical) DO NOTHING
            RETURNING id::text
            """,
            (kb_id, doc_id, etype, canonical, name),
        )
        row = cur.fetchone()
        if row:
            entity_map[name] = row[0]
        else:
            # Conflitto: recupera UUID esistente
            cur.execute(
                "SELECT id::text FROM entities WHERE doc_id=%s AND entity_type=%s AND canonical=%s",
                (doc_id, etype, canonical),
            )
            row2 = cur.fetchone()
            if row2:
                entity_map[name] = row2[0]

    return entity_map


def save_relations(
    cur,
    entity_map: dict,
    relations: list,
    doc_id: str,
) -> None:
    """Inserisce righe entity_relations usando entity_map per name→UUID.

    Salta relazioni dove from_name o to_name non sono in entity_map.
    ON CONFLICT DO NOTHING — idempotente.

    Args:
        cur:        cursore psycopg2 aperto
        entity_map: {display_name: entity_id} da save_entities_for_document()
        relations:  list di {"from": str, "relation": str, "to": str}
        doc_id:     UUID del documento sorgente
    """
    for r in relations:
        from_name = r.get("from", "")
        to_name = r.get("to", "")
        relation = r.get("relation", "")

        from_id = entity_map.get(from_name)
        to_id = entity_map.get(to_name)

        if not from_id or not to_id:
            continue

        cur.execute(
            """
            INSERT INTO entity_relations (doc_id, from_id, to_id, relation)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (doc_id, from_id, to_id, relation) DO NOTHING
            """,
            (doc_id, from_id, to_id, relation),
        )


def extract_and_save(
    cur,
    doc_id: str,
    kb_id: str,
    text: str,
) -> None:
    """Orchestra estrazione entità e persistenza nel grafo. Non rilancia mai.

    Flow:
      1. Controlla ENTITY_EXTRACTION_ENABLED — esce immediatamente se disabilitato
      2. Chiama extract_entities_from_text(text)
      3. Se vuoto, log info e ritorna
      4. Chiama save_entities_for_document() → entity_map
      5. Chiama save_relations()
      6. Qualsiasi eccezione: logger.warning e ritorna

    Args:
        cur:    cursore psycopg2 aperto (transazione del chiamante — nessun commit qui)
        doc_id: UUID del documento
        kb_id:  UUID della knowledge base
        text:   testo del documento (verrà troncato internamente)
    """
    if os.environ.get("ENTITY_EXTRACTION_ENABLED", "true").lower() in ("false", "0", "no"):
        return

    try:
        extracted = extract_entities_from_text(text)
        if not extracted.get("entities"):
            logger.info("extract_and_save: nessuna entità estratta per doc_id=%s", doc_id)
            return
        entity_map = save_entities_for_document(cur, doc_id, kb_id, extracted)
        if entity_map and extracted.get("relations"):
            save_relations(cur, entity_map, extracted["relations"], doc_id)
        logger.info(
            "extract_and_save: %d entità, %d relazioni per doc_id=%s",
            len(entity_map),
            len(extracted.get("relations", [])),
            doc_id,
        )
    except Exception as e:
        logger.warning("extract_and_save: errore per doc_id=%s — %s", doc_id, e)
