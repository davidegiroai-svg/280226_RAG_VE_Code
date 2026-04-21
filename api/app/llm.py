# RAG VE API - LLM synthesis via Ollama
import os
import json
import logging
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any, Generator

logger = logging.getLogger(__name__)

# Prompt di sistema per il Comune di Venezia — v3: tassonomia TARGET/AMBITI,
# esclusione frammenti fuori dominio, anti-dumping, fallback elegante
PROMPT_SISTEMA = (
    "Sei un consulente esperto di programmazione sociale per il Comune di Venezia, "
    "specializzato in bandi, fondi europei e interventi del Piano Sociale di Zona.\n\n"

    "══════════════════════════════════════════════════\n"
    "DOMINIO DI APPLICAZIONE — TASSONOMIA OBBLIGATORIA\n"
    "══════════════════════════════════════════════════\n"
    "Il tuo dominio si limita ESCLUSIVAMENTE ai seguenti TARGET e AMBITI:\n\n"
    "TARGET: Minori · Adulti · Donne · Anziani · Famiglie · ETS (inclusi operatori) · "
    "ATS/PA (inclusi operatori) · Cittadini · Migranti\n\n"
    "AMBITI DI INTERVENTO: Disabilità/Non autosufficienza · Disagio socio-economico · "
    "Disagio abitativo · Grave emarginazione · Occupabilità · Socialità/Comunità · "
    "Emergenza · Discriminazione/Lotta alla violenza · "
    "Rafforzamento capacità amministrativa · "
    "Infrastrutture per l'inclusione sociale · Child guarantee\n\n"
    "SINONIMI E DEFINIZIONI ALTERNATIVE (usa il matching semantico, non lessicale):\n"
    "- 'persone con disabilità', 'handicap', 'non autosufficienza', 'diversamente abili' → Disabilità/Non autosufficienza\n"
    "- 'senza dimora', 'homeless', 'clochard', 'persone in strada', 'povertà estrema' → Grave emarginazione\n"
    "- 'lavoro', 'occupazione', 'formazione professionale', 'reinserimento lavorativo', 'tirocinio' → Occupabilità\n"
    "- 'rifugiati', 'richiedenti asilo', 'stranieri', 'immigrati', 'profughi', 'MSNA' → Migranti\n"
    "- 'bambini', 'ragazzi', 'giovani', 'adolescenti', 'under 18', 'NEET under 18' → Minori\n"
    "- 'persone anziane', 'over 65', 'terza età', 'senior', 'demenza', 'Alzheimer' → Anziani\n"
    "- 'nuclei familiari', 'genitori', 'caregivers informali', 'monoparentali' → Famiglie\n"
    "- 'associazioni', 'cooperative sociali', 'volontariato', 'terzo settore', 'ODV', 'APS' → ETS\n"
    "- 'povertà', 'ISEE basso', 'sussidi', 'reddito di inclusione', 'indigenza' → Disagio socio-economico\n"
    "- 'sfratto', 'emergenza abitativa', 'alloggio popolare', 'affitto sociale' → Disagio abitativo\n\n"

    "══════════════════════\n"
    "REGOLA 1 — GROUNDING\n"
    "══════════════════════\n"
    "Rispondi esclusivamente usando le informazioni contenute nei documenti forniti. "
    "Non aggiungere mai dati, numeri, date o norme che non siano esplicitamente "
    "presenti nei documenti forniti, anche se li conosci.\n\n"

    "══════════════════════════════════\n"
    "REGOLA 2 — ESCLUSIONE TARGET/AMBITO (matching semantico)\n"
    "══════════════════════════════════\n"
    "PRIMA di rispondere, identifica il TARGET e l'AMBITO richiesti dall'utente, "
    "tenendo conto dei sinonimi e delle definizioni alternative elencate sopra. "
    "Per ogni frammento [INIZIO DOCUMENTO N / FINE DOCUMENTO N] del contesto: "
    "applica un matching SEMANTICO (non lessicale) — se il frammento tratta un target "
    "o ambito che è sinonimo o definizione alternativa di quello richiesto, INCLUDILO. "
    "IGNORA COMPLETAMENTE un documento solo se è palesemente riferito a un target/ambito "
    "SEMANTICAMENTE DISTINTO (es. l'utente chiede interventi per persone con disabilità "
    "e il documento tratta esclusivamente infrastrutture stradali o fondi per migranti). "
    "In caso di dubbio, preferisci includere il frammento e segnalare l'incertezza.\n\n"

    "══════════════════════════════════════════════\n"
    "REGOLA 3 — RIFIUTO ELEGANTE (nessun match)\n"
    "══════════════════════════════════════════════\n"
    "Se TUTTI i documenti del contesto si riferiscono a TARGET o AMBITI diversi da quelli "
    "richiesti, scrivi un messaggio di risposta nel seguente formato — "
    "SOSTITUENDO le parti tra << >> con i valori reali, senza copiare le parentesi angolari: "
    "'I documenti disponibili riguardano principalmente <<descrizione sintetica dei contenuti "
    "trovati, es. riforme della PA, investimenti FESR per PMI>>. "
    "Non ho trovato nei documenti forniti disposizioni specifiche per "
    "<<il target che l'utente ha effettivamente richiesto, es. persone con disabilità>> "
    "relativamente a <<l'ambito richiesto, es. inserimento lavorativo>>.' "
    "NON copiare mai il testo tra << >> come appare — riempilo con i dati reali. "
    "NON proporre mai 'la cosa più simile che trovi' come alternativa.\n\n"

    "═══════════════════════════════════\n"
    "REGOLA 4 — SINTESI DISCORSIVA (NO DUMPING)\n"
    "═══════════════════════════════════\n"
    "È VIETATO il copia-incolla pedissequo di tabelle, elenchi numerati o liste raw "
    "dai documenti. Sintetizza SEMPRE in testo discorsivo, in tono da consulente PA. "
    "Se nei documenti trovi un elenco di fondi o importi numerici, "
    "riassumili in 1-2 frasi aggregando il totale senza ripetere gli step 1...N: "
    "es. 'Sono disponibili 3 misure di finanziamento per un totale stimato di €X, "
    "di cui la principale è [nome misura] [Documento N].'\n\n"

    "═══════════════════\n"
    "REGOLE OPERATIVE\n"
    "═══════════════════\n"
    "5. COMPLETEZZA SELETTIVA: Estrai SOLO i dati tecnici pertinenti al TARGET richiesto: "
    "importi (€), percentuali, date, scadenze, codici (CUP, CIG, OS). "
    "Ometti i dati tecnici riferiti ad altri target/ambiti.\n\n"
    "6. CITAZIONI INLINE: Dopo ogni affermazione cita la fonte come link markdown, "
    "usando ESATTAMENTE il titolo e il LINK dall'intestazione del documento: "
    "[Titolo Documento](LINK). "
    "Se il documento non ha LINK, usa solo [Titolo Documento]. "
    "Non inventare mai titoli o link. "
    "Esempio: 'Il contributo massimo è €50.000 [Bando PMI 2025](/api/v1/files/bandi/bando.pdf).'\n\n"
    "7. STRUTTURA: Usa intestazioni Markdown (##) per argomento, "
    "elenchi puntati per requisiti.\n\n"
    "8. RAGIONAMENTO BREVE: Prima di rispondere, identifica in 1-2 frasi "
    "quali documenti trattano il TARGET/AMBITO richiesto. "
    "Poi fornisci la risposta basata SOLO su quei documenti.\n\n"
    "9. CONTESTO CONVERSAZIONALE: Se presente la 'history', integra le risposte "
    "precedenti e rispondi in modo coerente con il filo della conversazione."
)


def _build_context(chunks: List[Dict[str, Any]]) -> str:
    """Costruisce la stringa contesto dai chunk recuperati.

    Ogni documento è avvolto da separatori INIZIO/FINE espliciti. Se il chunk
    ha doc_metadata (da sidecar .meta.json), aggiunge un header TARGET/AMBITI
    leggibile dall'LLM prima del testo.

    Formato per ogni chunk:
      --- INIZIO DOCUMENTO N (fonte: <path>) ---
      [TIPO: xxx | FONTE: xxx | TARGET: xxx · yyy | AMBITI: xxx · yyy]   ← se disponibile
      <excerpt>
      --- FINE DOCUMENTO N ---
    """
    if not chunks:
        return ""
    parti = []
    for i, chunk in enumerate(chunks, 1):
        excerpt = chunk.get("excerpt", "")
        fonte = chunk.get("source_path") or chunk.get("kb_namespace", "sconosciuta")
        meta = chunk.get("doc_metadata") or {}

        header_parts = []
        if meta.get("tipo_documento"):
            header_parts.append(f"TIPO: {meta['tipo_documento']}")
        if meta.get("fonte_programma"):
            header_parts.append(f"FONTE: {meta['fonte_programma']}")
        if meta.get("targets"):
            header_parts.append(f"TARGET: {' · '.join(meta['targets'])}")
        if meta.get("ambiti"):
            header_parts.append(f"AMBITI: {' · '.join(meta['ambiti'])}")

        # M7 GraphRAG: aggiunge ENTITÀ estratte dal grafo (se presenti)
        related_entities = chunk.get("related_entities") or []
        if related_entities:
            entity_parts = [
                f"{e['entity_type']}={e['display_name']}"
                for e in related_entities[:5]
            ]
            header_parts.append(f"ENTITÀ: {' · '.join(entity_parts)}")

        meta_header = ""
        if header_parts:
            meta_header = "[" + " | ".join(header_parts) + "]\n"

        doc_title = chunk.get("doc_title") or ""
        kb = chunk.get("kb_namespace", "")
        filename = Path(fonte).name if fonte and ("/" in fonte or "\\" in fonte) else ""
        doc_url = f"/api/v1/files/{kb}/{filename}" if kb and filename else ""

        title_part = f": {doc_title}" if doc_title else ""
        link_part = f" [LINK: {doc_url}]" if doc_url else ""

        parti.append(
            f"--- INIZIO DOCUMENTO {i}{title_part}{link_part} (fonte: {fonte}) ---\n"
            f"{meta_header}"
            f"{excerpt}\n"
            f"--- FINE DOCUMENTO {i} ---"
        )
    return "\n\n".join(parti)


def synthesize_answer(
    query: str,
    chunks: List[Dict[str, Any]],
    model: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> Optional[str]:
    """Genera una risposta sintetica tramite LLM Ollama usando /api/chat.

    Args:
        query:   Testo della domanda originale dell'utente.
        chunks:  Lista di dict con chiavi 'excerpt', 'source_path', 'kb_namespace'.
        model:   Nome del modello Ollama (es. llama3.2, mistral).
        history: Lista opzionale di messaggi precedenti [{"role": "user"/"assistant", "content": "..."}].
                 Viene inserita tra il sistema e il nuovo user message per contesto conversazionale.

    Returns:
        Testo generato dall'LLM, oppure None in caso di errore/timeout (fallback).
    """
    ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    timeout = int(os.environ.get("LLM_TIMEOUT_S", "600"))

    contesto = _build_context(chunks)
    user_message = f"Documenti:\n{contesto}\n\nDomanda: {query}"

    # Costruisce la lista messaggi: sistema → history → user corrente
    messages: List[Dict[str, str]] = [{"role": "system", "content": PROMPT_SISTEMA}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }

    try:
        risposta = requests.post(
            f"{ollama_base_url}/api/chat",
            json=payload,
            timeout=timeout,
        )
        risposta.raise_for_status()
        data = risposta.json()
        return data["message"]["content"]
    except (requests.ConnectionError, requests.Timeout) as e:
        logger.warning("synthesize_answer: errore rete/timeout — %s", e)
        return None
    except Exception as e:
        logger.warning("synthesize_answer: errore inatteso — %s", e)
        return None


def synthesize_stream(
    query: str,
    chunks: List[Dict[str, Any]],
    model: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> Generator[str, None, None]:
    """Generator che yield token str dal LLM Ollama con streaming NDJSON.
    In caso di errore/timeout non solleva: si interrompe silenziosamente.
    """
    ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    timeout = int(os.environ.get("LLM_TIMEOUT_S", "600"))

    contesto = _build_context(chunks)
    user_message = f"Documenti:\n{contesto}\n\nDomanda: {query}"
    messages: List[Dict[str, str]] = [{"role": "system", "content": PROMPT_SISTEMA}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    payload = {"model": model, "messages": messages, "stream": True}

    try:
        with requests.post(
            f"{ollama_base_url}/api/chat",
            json=payload,
            stream=True,
            timeout=timeout,
        ) as risposta:
            risposta.raise_for_status()
            for line in risposta.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except ValueError:
                    continue
                token = data.get("message", {}).get("content", "")
                if token:
                    yield token
                if data.get("done"):
                    break
    except Exception as e:
        logger.warning("synthesize_stream: errore — %s", e)
        return  # fallback: il frontend usa i sources
