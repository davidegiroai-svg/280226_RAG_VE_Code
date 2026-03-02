# api/app/embedding.py
# RAG VE - Embedding Adapter (ollama + dummy)

from __future__ import annotations

import hashlib
import os
import random
import logging
from dataclasses import dataclass
from typing import List, Tuple, Sequence, Optional

import requests

logger = logging.getLogger(__name__)


class EmbeddingError(RuntimeError):
    """Generic embedding error."""


class EmbeddingDimMismatchError(EmbeddingError):
    """Raised when returned vector dimension mismatches expected."""

    def __init__(self, expected: int, got: int, provider: str, model: str):
        super().__init__(
            f"Embedding dimension mismatch: expected={expected} got={got} "
            f"(provider={provider}, model={model})"
        )


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: str
    model: str
    dim: int
    ollama_base_url: str
    timeout_s: float


def _get_env(name: str, default: str) -> str:
    return os.getenv(name, default)


def load_config() -> EmbeddingConfig:
    provider = _get_env("EMBEDDING_PROVIDER", "ollama").strip().lower()
    model = _get_env("EMBEDDING_MODEL", "nomic-embed-text").strip()
    dim = int(_get_env("EMBEDDING_DIM", "768"))
    ollama_base_url = _get_env("OLLAMA_BASE_URL", "http://host.docker.internal:11434").strip().rstrip("/")
    timeout_s = float(_get_env("EMBEDDING_TIMEOUT_S", "30"))
    return EmbeddingConfig(
        provider=provider,
        model=model,
        dim=dim,
        ollama_base_url=ollama_base_url,
        timeout_s=timeout_s,
    )


def _log_metadata(cfg: EmbeddingConfig, text_len: int, batch_size: Optional[int] = None) -> None:
    # Log SOLO metadati (mai testo)
    extra = {"provider": cfg.provider, "model": cfg.model, "dim": cfg.dim, "text_len": text_len}
    if batch_size is not None:
        extra["batch_size"] = batch_size
    logger.info("embedding.request", extra=extra)


def _dummy_vector(text: str, dim: int) -> List[float]:
    # deterministico: seed dal digest sha256
    digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).digest()
    rnd = random.Random(digest)
    return [float(rnd.uniform(-1.0, 1.0)) for _ in range(dim)]


def _ollama_embed_batch(cfg: EmbeddingConfig, texts: Sequence[str]) -> List[List[float]]:
    """
    Prefer /api/embed (batch): {model, input:[...]} -> {embeddings:[[...],...]}
    Fallback /api/embeddings (legacy): {model, prompt} -> {embedding:[...]} per testo
    """
    # 1) /api/embed
    try:
        url = f"{cfg.ollama_base_url}/api/embed"
        payload = {"model": cfg.model, "input": list(texts)}
        r = requests.post(url, json=payload, timeout=cfg.timeout_s)
        r.raise_for_status()
        data = r.json()
        vecs = data.get("embeddings")
        if not isinstance(vecs, list) or not vecs:
            raise EmbeddingError(f"Ollama /api/embed returned invalid payload (missing embeddings)")
        return vecs
    except Exception as e:
        last_err = e

    # 2) fallback legacy /api/embeddings (per-item)
    vecs: List[List[float]] = []
    url = f"{cfg.ollama_base_url}/api/embeddings"
    for t in texts:
        payload = {"model": cfg.model, "prompt": t}
        r = requests.post(url, json=payload, timeout=cfg.timeout_s)
        r.raise_for_status()
        data = r.json()
        vec = data.get("embedding")
        if not isinstance(vec, list) or not vec:
            raise EmbeddingError("Ollama /api/embeddings returned invalid payload (missing embedding)")
        vecs.append(vec)

    if not vecs:
        raise EmbeddingError(f"Ollama embedding failed: {last_err}")
    return vecs


def embed_text(text: str) -> Tuple[List[float], str, int]:
    cfg = load_config()
    _log_metadata(cfg, text_len=len(text))

    if cfg.provider == "dummy":
        vec = _dummy_vector(text, cfg.dim)
        return vec, f"dummy:{cfg.model}", cfg.dim

    if cfg.provider == "ollama":
        vecs = _ollama_embed_batch(cfg, [text])
        vec = vecs[0]
        if len(vec) != cfg.dim:
            raise EmbeddingDimMismatchError(cfg.dim, len(vec), cfg.provider, cfg.model)
        return vec, f"ollama:{cfg.model}", cfg.dim

    raise EmbeddingError(f"Unsupported EMBEDDING_PROVIDER={cfg.provider}")


def embed_texts(texts: List[str]) -> Tuple[List[List[float]], str, int]:
    cfg = load_config()
    if not texts:
        return [], f"{cfg.provider}:{cfg.model}", cfg.dim

    _log_metadata(cfg, text_len=len(texts[0]), batch_size=len(texts))

    if cfg.provider == "dummy":
        vecs = [_dummy_vector(t, cfg.dim) for t in texts]
        return vecs, f"dummy:{cfg.model}", cfg.dim

    if cfg.provider == "ollama":
        vecs = _ollama_embed_batch(cfg, texts)
        # validate dims
        for v in vecs:
            if len(v) != cfg.dim:
                raise EmbeddingDimMismatchError(cfg.dim, len(v), cfg.provider, cfg.model)
        return vecs, f"ollama:{cfg.model}", cfg.dim

    raise EmbeddingError(f"Unsupported EMBEDDING_PROVIDER={cfg.provider}")