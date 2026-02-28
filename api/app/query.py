# RAG VE API - Query logic
from typing import Optional, List, Dict, Any
from datetime import datetime

def build_query_sql(query_text: str, kb_namespace: Optional[str] = None, top_k: int = 5) -> str:
    """Build SQL query for text search on chunks table."""
    sql = """
        SELECT
            id::text,
            kb_namespace,
            document_id::text,
            testo as excerpt,
            metadata->>'source_path' as source_uri,
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

    sql += " ORDER BY chunk_index LIMIT %s"
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
            "source_uri": row.get("source_uri"),
            "excerpt": row["excerpt"]
        })
    return sources

def log_query(query_text: str, kb_namespace: Optional[str], sources: List[Dict], response_time_ms: int):
    """Log query to query_log table."""
    # Placeholder for future implementation
    pass
