# RAG VE API - Query logic
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from .embedding import embed_text


def vector_to_str(vec: List[float]) -> str:
    """Convert Python list of floats to PostgreSQL vector format string.

    Args:
        vec: List of float values representing the embedding vector

    Returns:
        String in PostgreSQL vector format: "[0.12, -0.34, ...]"
    """
    return "[" + ", ".join(str(v) for v in vec) + "]"


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
    sql += " ORDER BY embedding <=> %s LIMIT %s"
    params.append(query_vec_str)
    params.append(top_k)

    return sql, params


def parse_results(rows) -> List[Dict[str, Any]]:
    """Parse query results into response format."""
    sources = []
    for row in rows:
        distance = float(row["distance"])
        score = 1.0 - distance
        sources.append({
            "id": row["id"],
            "score": score,
            "kb_namespace": row["kb_namespace"],
            "source_path": row.get("source_path"),
            "excerpt": row["excerpt"]
        })
    return sources


def log_query(query_text: str, kb_namespace: Optional[str], sources: List[Dict], response_time_ms: int):
    """Log query to query_log table."""
    # Placeholder for future implementation
    pass
