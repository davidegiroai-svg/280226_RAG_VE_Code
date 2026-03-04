# RAG VE API - LLM synthesis via Ollama
import os
import requests
from typing import Optional, List, Dict, Any

# Prompt di sistema per il Comune di Venezia — consulente esperto con Markdown
PROMPT_SISTEMA = (
    "Sei un consulente esperto del Comune di Venezia specializzato nell'analisi di documenti. "
    "Rispondi basandoti SOLO sui documenti forniti nella domanda corrente. "
    "Usa Markdown per strutturare le risposte: usa **grassetto** per i concetti chiave, "
    "elenchi puntati per liste di elementi, tabelle comparative quando confronti più opzioni. "
    "Tieni conto della conversazione precedente per rispondere in modo contestuale e non ripetere "
    "informazioni già fornite, a meno che non sia necessario per chiarezza. "
    "Se le informazioni necessarie non sono presenti nei documenti forniti, "
    "dì chiaramente che non hai informazioni sufficienti per rispondere. "
    "Rispondi sempre in italiano in modo chiaro e preciso."
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
    timeout = int(os.environ.get("LLM_TIMEOUT_S", "30"))

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
    except (requests.ConnectionError, requests.Timeout):
        return None
    except Exception:
        return None
