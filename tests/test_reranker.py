"""
TDD — reranker LLM
Questi test DEVONO fallire prima che reranker.py esista.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

from app.reranker import rerank_with_llm


def _make_sources(n: int = 5) -> list[dict]:
    return [
        {
            "id": f"uuid-{i}",
            "score": round(0.9 - i * 0.1, 2),
            "kb_namespace": "demo",
            "source_path": f"/data/inbox/demo/doc{i}.txt",
            "excerpt": f"Estratto numero {i} sul progetto X.",
        }
        for i in range(n)
    ]


# ── test_rerank_reorders_by_score ────────────────────────────────────────────

def test_rerank_reorders_by_score():
    """rerank_with_llm: LLM assegna score alti al doc meno rilevante → ordine cambia."""
    sources = _make_sources(3)
    # LLM risponde con score invertiti: doc2 > doc1 > doc0
    fake_llm_response = '{"scores": [1, 5, 10]}'

    with patch("app.reranker._call_llm_for_scores", return_value=[1, 5, 10]):
        result = rerank_with_llm("query di test", sources, top_k=3)

    # Il documento con score LLM più alto (idx=2) deve essere primo
    assert result[0]["id"] == "uuid-2", (
        f"Atteso uuid-2 primo, trovato {result[0]['id']}"
    )
    assert result[1]["id"] == "uuid-1"
    assert result[2]["id"] == "uuid-0"


def test_rerank_returns_top_k():
    """rerank_with_llm: ritorna esattamente top_k elementi."""
    sources = _make_sources(10)

    with patch("app.reranker._call_llm_for_scores", return_value=list(range(10))):
        result = rerank_with_llm("query", sources, top_k=3)

    assert len(result) == 3


def test_rerank_fallback_on_error():
    """rerank_with_llm: se LLM fallisce, ritorna sources originali invariate (top_k)."""
    sources = _make_sources(5)

    with patch("app.reranker._call_llm_for_scores", side_effect=Exception("LLM timeout")):
        result = rerank_with_llm("query", sources, top_k=3)

    # Fallback: top_k sources nell'ordine originale
    assert len(result) == 3
    assert result[0]["id"] == "uuid-0"


def test_rerank_empty_sources():
    """rerank_with_llm: lista vuota → lista vuota, nessun crash."""
    result = rerank_with_llm("query", [], top_k=5)
    assert result == []
