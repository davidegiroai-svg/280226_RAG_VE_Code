# RAG VE API - Query logic
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime


def build_query_sql(query_text: str, kb_namespace: Optional[str] = None, top_k: int = 5) -> Tuple[str, List]:
    """Build SQL query for text search on chunks table.

    Uses ILIKE for simple matching with ranking based on match position.
    Returns excerpt truncated to 800 chars.

    Returns:
        Tuple[str, List]: (sql_query, params_list)
    """
    sql = """
        SELECT
            id::text,
            kb_namespace,
            document_id::text,
            LEFT(testo, 800) as excerpt,
            metadata->>'source_path' as source_path,
            chunk_index
        FROM chunks
        WHERE 1=1
    """
    params = []

    if kb_namespace:
        sql += " AND kb_namespace = %s"
        params.append(kb_namespace)

    # Text search using ILIKE for simple matching
    sql += " AND LOWER(testo) LIKE LOWER(%s)"
    params.append(f"%{query_text}%")

    # Order by match position: exact match first, then position in text
    # Use POSITION to rank results by how early in the text the match appears
    sql += " ORDER BY POSITION(LOWER(%s) IN LOWER(testo)), chunk_index LIMIT %s"
    params.append(query_text)
    params.append(top_k)

    return sql, params


def parse_results(rows) -> List[Dict[str, Any]]:
    """Parse query results into response format."""
    sources = []
    for row in rows:
        sources.append({
            "id": row["id"],
            "score": 0.85,  # Placeholder - real score would need vector search
            "kb_namespace": row["kb_namespace"],
            "source_path": row.get("source_path"),
            "excerpt": row["excerpt"]
        })
    return sources


def log_query(query_text: str, kb_namespace: Optional[str], sources: List[Dict], response_time_ms: int):
    """Log query to query_log table."""
    # Placeholder for future implementation
    pass
