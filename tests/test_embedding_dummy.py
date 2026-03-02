import os

from app.embedding import embed_text


def test_dummy_is_deterministic_and_dim_768(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBEDDING_DIM", "768")

    v1, m1, d1 = embed_text("ciao mondo")
    v2, m2, d2 = embed_text("ciao mondo")

    assert d1 == 768 and d2 == 768
    assert m1.startswith("dummy:") and m2.startswith("dummy:")
    assert len(v1) == 768 and len(v2) == 768
    assert v1 == v2  # determinismo