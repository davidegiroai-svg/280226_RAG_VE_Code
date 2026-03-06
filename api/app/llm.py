# RAG VE API - LLM synthesis via Ollama
import os
import json
import logging
import requests
from typing import Optional, List, Dict, Any, Generator

logger = logging.getLogger(__name__)

# Prompt di sistema per il Comune di Venezia — grounding rigoroso + chain-of-thought
PROMPT_SISTEMA = (
    "Sei un analista esperto di documenti della Pubblica Amministrazione italiana, "
    "specializzato in bandi, programmi europei e progetti del Comune di Venezia.\n\n"
    "REGOLA FONDAMENTALE — GROUNDING ASSOLUTO:\n"
    "Rispondi esclusivamente usando le informazioni contenute nei documenti forniti qui sotto. "
    "Non aggiungere mai informazioni, numeri, date o norme che non siano esplicitamente "
    "presenti nei documenti forniti, anche se le conosci. "
    "Se l'informazione cercata non è nei documenti, scrivi: "
    "'Informazione non disponibile nei documenti forniti.'\n\n"
    "REGOLE OPERATIVE:\n"
    "1. COMPLETEZZA: Estrai TUTTI i dati tecnici presenti: importi (€), percentuali, "
    "date, scadenze, soglie, aliquote, codici (CUP, CIG, OS), nomi di misure/assi/obiettivi. "
    "Non omettere cifre o condizioni.\n\n"
    "2. CITAZIONI INLINE: Dopo ogni affermazione o dato, indica subito la fonte tra parentesi "
    "quadre come [Documento N], dove N è il numero del documento da cui proviene l'informazione. "
    "Esempio: 'Il contributo massimo è €50.000 [Documento 1].'\n\n"
    "3. TABELLE: Riproduci le tabelle dei documenti in Markdown con valori esatti. "
    "Non parafrasare i dati numerici — citali letteralmente.\n\n"
    "4. STRUTTURA: Organizza la risposta con intestazioni Markdown (##) per argomento. "
    "Usa elenchi puntati per requisiti e condizioni.\n\n"
    "5. RAGIONAMENTO BREVE: Prima di rispondere, identifica brevemente (1-2 frasi) "
    "quali documenti contengono le informazioni rilevanti, poi fornisci la risposta strutturata.\n\n"
    "6. CONTESTO CONVERSAZIONALE: Se presente la 'history', integra le risposte precedenti "
    "e rispondi in modo coerente con il filo della conversazione."
)


def _build_context(chunks: List[Dict[str, Any]]) -> str:
    """Costruisce la stringa contesto dai chunk recuperati.

    Formato per ogni chunk:
      [Documento N] (fonte: <path o namespace>)
      <excerpt>

    Args:
        chunks: Lista di dict con 'excerpt', 'source_path', 'kb_namespace'.

    Returns:
        Stringa contesto multi-documento pronta per l'LLM.
    """
    if not chunks:
        return ""
    parti = []
    for i, chunk in enumerate(chunks, 1):
        excerpt = chunk.get("excerpt", "")
        fonte = chunk.get("source_path") or chunk.get("kb_namespace", "sconosciuta")
        parti.append(f"[Documento {i}] (fonte: {fonte})\n{excerpt}")
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
