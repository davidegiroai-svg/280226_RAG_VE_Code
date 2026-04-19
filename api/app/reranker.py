"""
Re-ranking LLM post-retrieval.

Dopo il retrieval vettoriale/ibrido, usa l'LLM cloud per assegnare uno score
di rilevanza (0-10) a ciascun estratto rispetto alla query, poi riordina.
Fallback sicuro: in caso di errore restituisce i sources originali (top_k).
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_RERANK_PROMPT_TEMPLATE = """\
Hai ricevuto una domanda e una lista di estratti numerati. \
Assegna a ogni estratto uno score di rilevanza da 0 a 10 rispetto alla domanda.
0 = completamente irrilevante, 10 = risponde direttamente alla domanda.

Domanda: {query}

Estratti:
{excerpts}

Rispondi SOLO con un JSON array di numeri interi nell'ordine degli estratti:
[score_0, score_1, ..., score_n]"""


def _call_llm_for_scores(
    query: str,
    excerpts: list[str],
    model: str,
    base_url: str,
    timeout: int,
) -> list[int]:
    """Chiama Ollama /api/chat e parsifica la lista di score JSON.

    Raises:
        Exception: se la chiamata fallisce o il JSON non è parsabile.
    """
    numbered = "\n".join(f"[{i}] {e[:400]}" for i, e in enumerate(excerpts))
    prompt = _RERANK_PROMPT_TEMPLATE.format(query=query, excerpts=numbered)

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    resp = requests.post(
        f"{base_url}/api/chat",
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["message"]["content"].strip()

    # Rimuove eventuale markdown fence ```json ... ```
    content = re.sub(r"^```[a-zA-Z]*\n?", "", content)
    content = re.sub(r"\n?```$", "", content)

    scores = json.loads(content)
    if not isinstance(scores, list):
        raise ValueError(f"Risposta non è una lista: {scores}")
    return [int(s) for s in scores]


def rerank_with_llm(
    query: str,
    sources: list[dict],
    top_k: int = 10,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: Optional[int] = None,
) -> list[dict]:
    """Re-rank sources usando LLM per score rilevanza 0-10.

    Args:
        query: domanda originale dell'utente
        sources: lista di dict con chiave 'excerpt' (almeno)
        top_k: quanti risultati restituire dopo il re-ranking
        model: modello Ollama (default: env OLLAMA_LLM_MODEL)
        base_url: base URL Ollama (default: env OLLAMA_BASE_URL)
        timeout: timeout HTTP in secondi (default: env LLM_TIMEOUT_S)

    Returns:
        Lista di top_k sources riordinati per score LLM DESC.
        In caso di errore: restituisce sources[:top_k] nell'ordine originale.
    """
    if not sources:
        return []

    _model = model or os.getenv("OLLAMA_LLM_MODEL", "qwen3-next-cloud:latest")
    _base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    _timeout = timeout or int(os.getenv("LLM_TIMEOUT_S", "60"))

    excerpts = [s.get("excerpt", "") for s in sources]

    try:
        scores = _call_llm_for_scores(query, excerpts, _model, _base_url, _timeout)

        if len(scores) != len(sources):
            logger.warning(
                "rerank: LLM returned %d scores for %d sources — fallback",
                len(scores), len(sources),
            )
            return sources[:top_k]

        # Accosta score a sources e ordina per score DESC
        scored = sorted(
            zip(scores, sources),
            key=lambda x: x[0],
            reverse=True,
        )
        return [src for _, src in scored[:top_k]]

    except Exception as e:
        logger.warning("rerank_with_llm error: %s — returning original order", e)
        return sources[:top_k]
