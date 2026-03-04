"""tests/test_hybrid_search.py — TDD Phase 10: Hybrid Search

Testa:
- fts_search(): query full-text con tsvector
- rrf_merge(): fusione dei ranking con Reciprocal Rank Fusion
- /api/v1/query con search_mode vector / fts / hybrid
- Casi limite: lista vuota, overlap, query invalida

RED:  fallenti prima dell'implementazione
GREEN: dopo implementazione in hybrid.py + query.py + main.py
"""
from unittest.mock import MagicMock, patch, call

import pytest
from fastapi.testclient import TestClient

from app.hybrid import fts_search, rrf_merge
from app.main import app

client = TestClient(app)


# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────

def _mock_cursor(rows=None):
    """Mock compatibile con 'with get_db_cursor() as cursor'."""
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = rows or []
    mock_cur.fetchone.return_value = None
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=mock_cur)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx, mock_cur


def _fts_row(id_="chunk-1", rank=0.5, kb="demo", path="/data/demo/doc.txt", excerpt="testo"):
    """Riga simulata per fts_search."""
    return {
        "id": id_,
        "rank": rank,
        "kb_namespace": kb,
        "source_path": path,
        "excerpt": excerpt,
    }


def _vector_source(id_="chunk-1", score=0.9, kb="demo", path="/data/demo/doc.txt", excerpt="testo"):
    """Sorgente simulata per vector search."""
    return {
        "id": id_,
        "score": score,
        "kb_namespace": kb,
        "source_path": path,
        "excerpt": excerpt,
    }


# ─────────────────────────────────────────────────────────
# Unit tests: fts_search()
# ─────────────────────────────────────────────────────────

class TestFtsSearch:

    def test_fts_search_ritorna_lista_vuota_se_nessun_match(self):
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = []

        risultati = fts_search("query inesistente", mock_cur)

        assert risultati == []

    def test_fts_search_ritorna_risultati_ordinati_per_rank(self):
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [
            _fts_row(id_="a", rank=0.8),
            _fts_row(id_="b", rank=0.3),
        ]

        risultati = fts_search("bando", mock_cur)

        assert len(risultati) == 2
        assert risultati[0]["id"] == "a"
        assert risultati[0]["score"] == pytest.approx(0.8)
        assert risultati[1]["score"] == pytest.approx(0.3)

    def test_fts_search_struttura_risultato(self):
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [
            _fts_row(id_="x", rank=0.6, kb="test_kb", path="/data/doc.pdf", excerpt="estratto testo")
        ]

        risultati = fts_search("bando", mock_cur)

        assert len(risultati) == 1
        r = risultati[0]
        assert r["id"] == "x"
        assert r["score"] == pytest.approx(0.6)
        assert r["kb_namespace"] == "test_kb"
        assert r["source_path"] == "/data/doc.pdf"
        assert r["excerpt"] == "estratto testo"

    def test_fts_search_con_kb_namespace_passa_parametro(self):
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = []

        fts_search("bando finanziamento", mock_cur, kb_namespace="demo_kb")

        # Verifica che execute sia stato chiamato con il namespace nella query
        call_args = mock_cur.execute.call_args
        assert call_args is not None
        sql, params = call_args[0]
        assert "demo_kb" in params

    def test_fts_search_senza_kb_namespace_non_filtra(self):
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = []

        fts_search("bando", mock_cur, kb_namespace=None)

        call_args = mock_cur.execute.call_args
        sql, params = call_args[0]
        # kb_namespace=None: il parametro non deve apparire nei params come stringa
        assert "demo_kb" not in params

    def test_fts_search_usa_plainto_tsquery_nel_sql(self):
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = []

        fts_search("progetto venezia", mock_cur)

        call_args = mock_cur.execute.call_args
        sql = call_args[0][0]
        assert "plainto_tsquery" in sql

    def test_fts_search_top_k_rispettato(self):
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = []

        fts_search("bando", mock_cur, top_k=7)

        call_args = mock_cur.execute.call_args
        sql, params = call_args[0]
        assert 7 in params


# ─────────────────────────────────────────────────────────
# Unit tests: rrf_merge()
# ─────────────────────────────────────────────────────────

class TestRrfMerge:

    def test_rrf_merge_liste_vuote_ritorna_vuoto(self):
        risultati = rrf_merge([], [], top_k=5)
        assert risultati == []

    def test_rrf_merge_solo_vector_results(self):
        vector = [_vector_source(id_="a"), _vector_source(id_="b")]

        risultati = rrf_merge(vector, [], top_k=2)

        assert len(risultati) == 2
        ids = [r["id"] for r in risultati]
        assert "a" in ids
        assert "b" in ids

    def test_rrf_merge_solo_fts_results(self):
        fts = [_vector_source(id_="c"), _vector_source(id_="d")]

        risultati = rrf_merge([], fts, top_k=2)

        assert len(risultati) == 2

    def test_rrf_merge_overlap_aumenta_score(self):
        """Documento presente in entrambe le liste deve avere score maggiore."""
        # doc "shared" appare primo in vector e primo in fts
        vector = [_vector_source(id_="shared"), _vector_source(id_="only_vector")]
        fts = [_vector_source(id_="shared"), _vector_source(id_="only_fts")]

        risultati = rrf_merge(vector, fts, top_k=3)

        ids = [r["id"] for r in risultati]
        assert ids[0] == "shared", f"'shared' dovrebbe essere primo, invece: {ids}"

    def test_rrf_merge_formula_rrf_corretta(self):
        """Verifica formula: score = 1/(k+1) + 1/(k+1) = 2/(k+1) per doc primo in entrambe."""
        k = 60
        vector = [_vector_source(id_="top")]
        fts = [_vector_source(id_="top")]

        risultati = rrf_merge(vector, fts, top_k=1, k=k)

        atteso = 2.0 / (k + 1)
        assert risultati[0]["score"] == pytest.approx(atteso)

    def test_rrf_merge_top_k_limita_risultati(self):
        vector = [_vector_source(id_=f"v{i}") for i in range(10)]
        fts = [_vector_source(id_=f"f{i}") for i in range(10)]

        risultati = rrf_merge(vector, fts, top_k=5)

        assert len(risultati) == 5

    def test_rrf_merge_ordinato_per_score_desc(self):
        # Verifica che i risultati siano ordinati per score RRF decrescente.
        # doc "top" appare primo in vector e secondo in fts
        # doc "mid" appare secondo in vector e primo in fts
        # doc "low" appare solo in vector al terzo posto
        k = 60
        vector = [
            _vector_source(id_="top"),
            _vector_source(id_="mid"),
            _vector_source(id_="low"),
        ]
        fts = [
            _vector_source(id_="mid"),
            _vector_source(id_="top"),
        ]

        risultati = rrf_merge(vector, fts, top_k=3, k=k)

        # "top": 1/(k+1) + 1/(k+2), "mid": 1/(k+2) + 1/(k+1) — pari (simmetria)
        # "low": solo 1/(k+3) — deve essere l'ultimo
        ids = [r["id"] for r in risultati]
        # "low" deve essere l'ultimo tra i 3 (score più basso)
        assert ids[-1] == "low", f"Atteso 'low' per ultimo, invece: {ids}"
        # "top" e "mid" hanno score identici per simmetria, entrambi prima di "low"
        assert "top" in ids[:2] and "mid" in ids[:2]

    def test_rrf_merge_score_nel_risultato(self):
        """Verifica che il campo score sia il valore RRF, non quello originale."""
        vector = [_vector_source(id_="x", score=0.99)]
        fts = []

        risultati = rrf_merge(vector, fts, top_k=1, k=60)

        atteso_rrf = 1.0 / (60 + 1)
        assert risultati[0]["score"] == pytest.approx(atteso_rrf)
        # NON deve essere il score originale 0.99
        assert risultati[0]["score"] != pytest.approx(0.99)


# ─────────────────────────────────────────────────────────
# Integration tests: /api/v1/query con search_mode
# ─────────────────────────────────────────────────────────

class TestQueryApiSearchMode:

    def test_query_default_mode_vector(self, monkeypatch):
        """search_mode assente → default 'vector', comportamento invariato."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
        mock_rows = [{
            "id": "uuid-1",
            "kb_namespace": "demo",
            "excerpt": "testo bando",
            "source_path": "/data/demo/doc.txt",
            "distance": 0.2,
        }]
        ctx, mock_cur = _mock_cursor(rows=mock_rows)

        with patch("app.main.get_db_cursor", return_value=ctx):
            with patch("app.main.embed_text", return_value=([0.0]*768, "dummy", 768)):
                resp = client.post("/api/v1/query", json={"query": "bando"})

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["sources"]) == 1
        assert data["sources"][0]["score"] == pytest.approx(0.8)

    def test_query_mode_fts_non_calcola_embedding(self, monkeypatch):
        """search_mode='fts' → embed_text NON deve essere chiamato."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
        mock_rows = [_fts_row(id_="x", rank=0.5)]
        ctx, mock_cur = _mock_cursor(rows=mock_rows)

        with patch("app.main.get_db_cursor", return_value=ctx):
            with patch("app.main.embed_text") as mock_embed:
                resp = client.post(
                    "/api/v1/query",
                    json={"query": "bando finanziamento", "search_mode": "fts"},
                )

        assert resp.status_code == 200
        mock_embed.assert_not_called()

    def test_query_mode_fts_ritorna_risultati(self, monkeypatch):
        """search_mode='fts' → risposta 200 con sources."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
        mock_rows = [_fts_row(id_="fts-1", rank=0.7, excerpt="estratto FTS")]
        ctx, mock_cur = _mock_cursor(rows=mock_rows)

        with patch("app.main.get_db_cursor", return_value=ctx):
            resp = client.post(
                "/api/v1/query",
                json={"query": "venezia bando", "search_mode": "fts"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["sources"]) == 1
        assert data["sources"][0]["id"] == "fts-1"

    def test_query_mode_hybrid_calcola_embedding(self, monkeypatch):
        """search_mode='hybrid' → embed_text DEVE essere chiamato."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
        ctx, mock_cur = _mock_cursor(rows=[])

        with patch("app.main.get_db_cursor", return_value=ctx):
            with patch("app.main.embed_text", return_value=([0.0]*768, "dummy", 768)) as mock_embed:
                resp = client.post(
                    "/api/v1/query",
                    json={"query": "bando", "search_mode": "hybrid"},
                )

        assert resp.status_code == 200
        mock_embed.assert_called_once()

    def test_query_mode_hybrid_lista_vuota_ok(self, monkeypatch):
        """search_mode='hybrid' con 0 risultati da entrambe le ricerche → answer fallback."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
        ctx, mock_cur = _mock_cursor(rows=[])

        with patch("app.main.get_db_cursor", return_value=ctx):
            with patch("app.main.embed_text", return_value=([0.0]*768, "dummy", 768)):
                resp = client.post(
                    "/api/v1/query",
                    json={"query": "termini inesistenti", "search_mode": "hybrid"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["sources"] == []
        assert "Nessun documento" in data["answer"]

    def test_query_search_mode_non_valido_ritorna_422(self, monkeypatch):
        """search_mode con valore non supportato → HTTP 422."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")

        with patch("app.main.embed_text", return_value=([0.0]*768, "dummy", 768)):
            resp = client.post(
                "/api/v1/query",
                json={"query": "bando", "search_mode": "fuzzy"},
            )

        assert resp.status_code == 422

    def test_query_mode_vector_ritorna_source_con_score_valido(self, monkeypatch):
        """search_mode='vector' → score tra 0 e 1."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
        mock_rows = [{
            "id": "v-1",
            "kb_namespace": "demo",
            "excerpt": "testo estratto",
            "source_path": None,
            "distance": 0.4,
        }]
        ctx, mock_cur = _mock_cursor(rows=mock_rows)

        with patch("app.main.get_db_cursor", return_value=ctx):
            with patch("app.main.embed_text", return_value=([0.0]*768, "dummy", 768)):
                resp = client.post(
                    "/api/v1/query",
                    json={"query": "bando", "search_mode": "vector"},
                )

        assert resp.status_code == 200
        sources = resp.json()["sources"]
        assert 0.0 <= sources[0]["score"] <= 1.0

    def test_query_search_mode_fts_lista_vuota_risposta_ok(self, monkeypatch):
        """search_mode='fts' senza risultati → sources=[], answer fallback."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
        ctx, mock_cur = _mock_cursor(rows=[])

        with patch("app.main.get_db_cursor", return_value=ctx):
            resp = client.post(
                "/api/v1/query",
                json={"query": "inesistente xyz", "search_mode": "fts"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["sources"] == []
        assert "Nessun documento" in data["answer"]
