# RAG VE API - LLM synthesis via Ollama
import os
import requests
from typing import Optional, List, Dict, Any

# Prompt di sistema per il Comune di Venezia (in italiano)
PROMPT_SISTEMA = (
    "Sei un assistente del Comune di Venezia. "
    "Rispondi basandoti SOLO sui seguenti documenti forniti. "
    "Se le informazioni necessarie non sono presenti nei documenti, "
    "dì chiaramente che non hai informazioni sufficienti per rispondere. "
    "Rispondi in italiano in modo chiaro e conciso."
)


def synthesize_answer(
    query: str,
    chunks: List[Dict[str, Any]],
    model: str,
) -> Optional[str]:
    """Genera una risposta sintetica tramite LLM Ollama usando /api/chat.

    Args:
        query:  Testo della domanda originale dell'utente.
        chunks: Lista di dict con chiavi 'excerpt', 'source_path', 'kb_namespace'.
        model:  Nome del modello Ollama (es. llama3.2, mistral).

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

    # Messaggio utente con contesto + domanda
    user_message = f"Documenti:\n{contesto}\n\nDomanda: {query}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": PROMPT_SISTEMA},
            {"role": "user", "content": user_message},
        ],
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
        # Fallback silenzioso: LLM non disponibile
        return None
    except Exception:
        # Qualsiasi altro errore (HTTP 4xx/5xx, formato JSON inatteso)
        return None
