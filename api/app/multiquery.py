"""
Multi-query expansion via Ollama LLM.

Genera riformulazioni della query utente per migliorare il recall
nella ricerca ibrida. Fallback sicuro: in caso di errore restituisce
solo la query originale (zero degradazione).
"""
from __future__ import annotations

import json
import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

_EXPAND_PROMPT_TEMPLATE = """\
Genera 3 riformulazioni in italiano della seguente domanda di ricerca. \
Restituisci SOLO un JSON array di 3 stringhe.

Domanda: {query}"""


def expand_query(
    query: str,
    model: str | None = None,
    base_url: str | None = None,
    timeout: int | None = None,
) -> list[str]:
    """Espande la query in varianti semantiche via Ollama /api/chat.

    Restituisce sempre [query_originale] + varianti (4 elementi in caso di successo).
    In caso di QUALSIASI errore: restituisce [query] (singola, zero degradazione).

    Args:
        query: domanda originale dell'utente
        model: modello Ollama (default: env OLLAMA_LLM_MODEL)
        base_url: base URL Ollama (default: env OLLAMA_BASE_URL)
        timeout: timeout HTTP in secondi (default: env LLM_TIMEOUT_S)

    Returns:
        Lista con query originale come primo elemento, seguita da varianti.
    """
    _model = model or os.getenv("OLLAMA_LLM_MODEL", "qwen3-next-cloud:latest")
    _base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    _timeout = timeout or int(os.getenv("LLM_TIMEOUT_S", "60"))

    prompt = _EXPAND_PROMPT_TEMPLATE.format(query=query)

    try:
        payload = {
            "model": _model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        resp = requests.post(
            f"{_base_url}/api/chat",
            json=payload,
            timeout=_timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["message"]["content"].strip()

        # Rimuove eventuale markdown fence ```json ... ```
        content = re.sub(r"^```[a-zA-Z]*\n?", "", content)
        content = re.sub(r"\n?```$", "", content)

        variants = json.loads(content)
        if not isinstance(variants, list):
            raise ValueError(f"Risposta non e' una lista: {variants}")

        # Filtra solo stringhe valide
        variants = [str(v).strip() for v in variants if isinstance(v, str) and v.strip()]

        return [query] + variants

    except Exception as e:
        logger.warning("expand_query error: %s — restituisco solo query originale", e)
        return [query]
