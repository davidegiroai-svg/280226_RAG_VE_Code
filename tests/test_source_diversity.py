"""
TDD — diversify_sources()
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

from app.query import diversify_sources


def _src(idx: int, doc: str, score: float = 0.9) -> dict:
    return {
        "id": f"uuid-{idx}",
        "score": score,
        "kb_namespace": "demo",
        "source_path": f"/data/inbox/demo/{doc}.pdf",
        "excerpt": f"Estratto {idx}",
    }


def test_diversity_limits_chunks_per_doc():
    """Max 2 chunk per documento: con 4 doc x 3 chunk ciascuno, top_k=8 → max 2 da docA."""
    # 4 documenti, 3 chunk each, ordinati per score
    sources = []
    for doc_idx, doc in enumerate(["docA", "docB", "docC", "docD"]):
        for chunk_idx in range(3):
            sources.append(_src(
                doc_idx * 3 + chunk_idx, doc,
                score=round(1.0 - (doc_idx * 3 + chunk_idx) * 0.05, 2)
            ))
    # top_k=8, max_per_doc=2 → max 2 da docA, restante da altri doc
    result = diversify_sources(sources, top_k=8, max_per_doc=2)
    paths = [r["source_path"] for r in result]
    assert paths.count("/data/inbox/demo/docA.pdf") <= 2, "docA non deve avere >2 chunk"
    assert len(result) == 8


def test_diversity_returns_top_k():
    """Ritorna esattamente top_k elementi."""
    sources = [_src(i, f"doc{i}", 1.0 - i * 0.05) for i in range(20)]
    result = diversify_sources(sources, top_k=5, max_per_doc=1)
    assert len(result) == 5


def test_diversity_single_source_fills_if_needed():
    """Se c'è un solo documento, ritorna comunque top_k chunk da esso."""
    sources = [_src(i, "soloDoc", 1.0 - i * 0.05) for i in range(10)]
    result = diversify_sources(sources, top_k=5, max_per_doc=2)
    assert len(result) == 5


def test_diversity_preserves_order():
    """L'ordine dei risultati deve rispettare lo score originale."""
    sources = [_src(i, f"doc{i}", 1.0 - i * 0.1) for i in range(6)]
    result = diversify_sources(sources, top_k=4, max_per_doc=1)
    scores = [r["score"] for r in result]
    assert scores == sorted(scores, reverse=True), "Score deve essere decrescente"
