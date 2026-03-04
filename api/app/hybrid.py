# RAG VE API - Hybrid search: FTS + RRF
"""Modulo hybrid search: full-text search con tsvector e Reciprocal Rank Fusion.

Fornisce:
- fts_search(): ricerca full-text con plainto_tsquery + ts_rank
- rrf_merge(): fusione dei ranking vector e FTS tramite RRF k=60
"""
from typing import Optional


def fts_search(
    query: str,
    cursor,
    kb_namespace: Optional[str] = None,
    top_k: int = 20,
) -> list[dict]:
    """Ricerca full-text tramite tsvector + ts_rank.

    Args:
        query: testo della query utente
        cursor: cursore psycopg2 già aperto (RealDictCursor)
        kb_namespace: namespace KB opzionale per filtrare i risultati
        top_k: numero massimo di risultati (per il merge RRF usa top_k*2)

    Returns:
        Lista di dict con chiavi: id, score, kb_namespace, source_path, excerpt
    """
    sql = """
        SELECT
            id::text,
            kb_namespace,
            LEFT(testo, 800) AS excerpt,
            metadata->>'source_path' AS source_path,
            ts_rank(testo_tsv, plainto_tsquery('italian', %s)) AS rank
        FROM chunks
        WHERE testo_tsv IS NOT NULL
          AND testo_tsv @@ plainto_tsquery('italian', %s)
    """
    params: list = [query, query]

    if kb_namespace:
        sql += " AND kb_namespace = %s"
        params.append(kb_namespace)

    sql += " ORDER BY rank DESC LIMIT %s"
    params.append(top_k)

    cursor.execute(sql, params)
    rows = cursor.fetchall()

    results = []
    for row in rows:
        results.append({
            "id": row["id"],
            "score": float(row["rank"]),
            "kb_namespace": row["kb_namespace"],
            "source_path": row.get("source_path"),
            "excerpt": row["excerpt"],
        })
    return results


def rrf_merge(
    vector_results: list[dict],
    fts_results: list[dict],
    top_k: int = 5,
    k: int = 60,
) -> list[dict]:
    """Reciprocal Rank Fusion: combina due ranking in un unico ranking finale.

    Formula: score_rrf(doc) = Σ 1/(k + rank_i) per ogni lista i
    Il rank è 1-based (primo risultato = rank 1).

    Args:
        vector_results: lista ordinata per score vector (migliore primo)
        fts_results: lista ordinata per score FTS (migliore primo)
        top_k: numero di risultati finali da restituire
        k: costante RRF (default 60, raccomandato in letteratura)

    Returns:
        Lista di dict con score_rrf, ordinata per score_rrf DESC, lunghezza top_k
    """
    # Accumula score RRF per ogni document id
    rrf_scores: dict[str, float] = {}
    doc_data: dict[str, dict] = {}

    for rank, doc in enumerate(vector_results, start=1):
        doc_id = doc["id"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank)
        doc_data[doc_id] = doc

    for rank, doc in enumerate(fts_results, start=1):
        doc_id = doc["id"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k + rank)
        # Aggiorna doc_data solo se non presente (il vector doc ha priorità per i campi)
        if doc_id not in doc_data:
            doc_data[doc_id] = doc

    # Ordina per score RRF decrescente
    ranked_ids = sorted(rrf_scores.keys(), key=lambda d: rrf_scores[d], reverse=True)

    results = []
    for doc_id in ranked_ids[:top_k]:
        entry = dict(doc_data[doc_id])
        entry["score"] = rrf_scores[doc_id]
        results.append(entry)

    return results
