# RAG VE API - Query logic
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from .embedding import embed_text
from .hybrid import fts_search, rrf_merge


def vector_to_str(vec: List[float]) -> str:
    """Convert Python list of floats to PostgreSQL vector format string.

    Args:
        vec: List of float values representing the embedding vector

    Returns:
        String in PostgreSQL vector format: "[0.12, -0.34, ...]"
    """
    return "[" + ",".join(str(v) for v in vec) + "]"


def build_query_sql(
    query_text: str,
    kb_namespace: Optional[str] = None,
    top_k: int = 5,
    query_vec: Optional[List[float]] = None
) -> Tuple[str, List]:
    """Build SQL query for vector similarity search on chunks table.

    Uses pgvector's <=> cosine distance operator for similarity search.
    Returns excerpt truncated to 800 chars.

    Args:
        query_text: The search query text (used to generate embedding if query_vec not provided)
        kb_namespace: Optional KB namespace to filter results
        top_k: Number of results to return (default: 5)
        query_vec: Optional pre-computed embedding vector as list of floats

    Returns:
        Tuple[str, List]: (sql_query, params_list)
    """
    # Generate embedding if not provided
    if query_vec is None:
        vec, model, dim = embed_text(query_text)
        query_vec_str = vector_to_str(vec)
    else:
        query_vec_str = vector_to_str(query_vec)

    sql = """
        SELECT
            id::text,
            kb_namespace,
            document_id::text,
            LEFT(testo, 800) as excerpt,
            metadata->>'source_path' as source_path,
            chunk_index,
            embedding <=> %s as distance
        FROM chunks
        WHERE embedding IS NOT NULL
    """
    params = [query_vec_str]

    if kb_namespace:
        sql += " AND kb_namespace = %s"
        params.append(kb_namespace)

    # Order by cosine distance (closest first)
    sql += " ORDER BY distance ASC LIMIT %s"
    params.append(top_k)

    return sql, params


def parse_results(rows) -> List[Dict[str, Any]]:
    """Parse query results into response format."""
    sources = []
    for row in rows:
        distance = float(row["distance"])
        score = max(0.0, 1.0 - distance)
        sources.append({
            "id": row["id"],
            "score": score,
            "kb_namespace": row["kb_namespace"],
            "source_path": row.get("source_path"),
            "excerpt": row["excerpt"]
        })
    return sources


def execute_search(
    query_text: str,
    cursor,
    kb_namespace: Optional[str] = None,
    top_k: int = 5,
    search_mode: str = "vector",
    query_vec: Optional[List[float]] = None,
) -> List[Dict[str, Any]]:
    """Esegue la ricerca in base al search_mode scelto.

    Modalità supportate:
    - "vector": solo cosine similarity (comportamento originale)
    - "fts": solo full-text search con tsvector
    - "hybrid": vector + FTS combinati con RRF k=60

    Args:
        query_text: testo della query
        cursor: cursore psycopg2 aperto (RealDictCursor)
        kb_namespace: namespace KB opzionale
        top_k: numero risultati finali
        search_mode: modalità di ricerca ("vector", "fts", "hybrid")
        query_vec: embedding precalcolato (opzionale, usato se mode != "fts")

    Returns:
        Lista di source dict con id, score, kb_namespace, source_path, excerpt
    """
    if search_mode == "fts":
        # Solo full-text search — nessun embedding necessario
        return fts_search(query_text, cursor, kb_namespace=kb_namespace, top_k=top_k)

    # Calcola embedding se non fornito (serve per vector e hybrid)
    if query_vec is None:
        vec, _model, _dim = embed_text(query_text)
    else:
        vec = query_vec

    if search_mode == "hybrid":
        # Recupera più candidati per il merge (top_k*3 da ciascuna lista)
        candidati = max(top_k * 3, 20)
        sql, params = build_query_sql(
            query_text=query_text,
            kb_namespace=kb_namespace,
            top_k=candidati,
            query_vec=vec,
        )
        cursor.execute(sql, params)
        vector_rows = cursor.fetchall()
        vector_sources = parse_results(vector_rows)

        fts_sources = fts_search(
            query_text, cursor, kb_namespace=kb_namespace, top_k=candidati
        )

        return rrf_merge(vector_sources, fts_sources, top_k=top_k)

    # Default: solo vector search
    sql, params = build_query_sql(
        query_text=query_text,
        kb_namespace=kb_namespace,
        top_k=top_k,
        query_vec=vec,
    )
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    return parse_results(rows)


def log_query(query_text: str, kb_namespace: Optional[str], sources: List[Dict], response_time_ms: int):
    """Log query to query_log table."""
    # Placeholder for future implementation
    pass
