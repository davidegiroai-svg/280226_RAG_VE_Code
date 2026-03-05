# RAG VE API - LLM synthesis via Ollama
import os
import json
import logging
import requests
from typing import Optional, List, Dict, Any, Generator

logger = logging.getLogger(__name__)

# Prompt di sistema per il Comune di Venezia — consulente esperto con Markdown
PROMPT_SISTEMA = (
    "Sei un assistente esperto del Comune di Venezia. "
    "Il tuo compito è rispondere alle query degli utenti basandoti sui documenti forniti.\n\n"
    "1. RAGIONAMENTO: Non limitarti a citare estratti. Analizza le informazioni, "
    "mettile in relazione tra loro e fornisci una spiegazione logica e discorsiva.\n\n"
    "2. STILE: Usa un tono istituzionale ma colloquiale ed esaustivo. "
    "Se utile alla chiarezza, organizza la risposta con elenchi puntati o tabelle Markdown.\n\n"
    "3. CITAZIONI: Ogni volta che affermi qualcosa basandoti sui documenti, "
    "cita la fonte usando il formato [Documento N] (es. [Documento 1]). "
    "È fondamentale per la trasparenza.\n\n"
    "4. CONTESTO: Se presente la 'history', usala per capire se l'utente sta facendo "
    "domande di approfondimento (drill-down) e rispondi di conseguenza."
)


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
    timeout = int(os.environ.get("LLM_TIMEOUT_S", "120"))

    # Costruisce il contesto dai chunk recuperati
    parti_contesto = []
    for i, chunk in enumerate(chunks, 1):
        excerpt = chunk.get("excerpt", "")
        fonte = chunk.get("source_path") or chunk.get("kb_namespace", "sconosciuta")
        parti_contesto.append(f"[Documento {i}] (fonte: {fonte})\n{excerpt}")
    contesto = "\n\n".join(parti_contesto)

    # Messaggio utente con contesto + domanda corrente
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
    timeout = int(os.environ.get("LLM_TIMEOUT_S", "120"))

    parti_contesto = []
    for i, chunk in enumerate(chunks, 1):
        excerpt = chunk.get("excerpt", "")
        fonte = chunk.get("source_path") or chunk.get("kb_namespace", "sconosciuta")
        parti_contesto.append(f"[Documento {i}] (fonte: {fonte})\n{excerpt}")
    contesto = "\n\n".join(parti_contesto)

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
