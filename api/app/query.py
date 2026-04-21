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
    query_vec: Optional[List[float]] = None,
    file_type: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
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
            testo as excerpt,
            metadata->>'source_path' as source_path,
            chunk_index,
            metadata AS doc_metadata,
            doc_title,
            embedding <=> %s as distance
        FROM chunks
        WHERE embedding IS NOT NULL
    """
    params = [query_vec_str]

    if kb_namespace:
        sql += " AND kb_namespace = %s"
        params.append(kb_namespace)

    if file_type:
        sql += " AND metadata->>'file_type' = %s"
        params.append(file_type)

    if year_from is not None:
        sql += " AND EXTRACT(YEAR FROM ingest_date) >= %s"
        params.append(year_from)

    if year_to is not None:
        sql += " AND EXTRACT(YEAR FROM ingest_date) <= %s"
        params.append(year_to)

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
        raw_meta = row.get("doc_metadata") or {}
        # psycopg2 RealDictCursor restituisce JSONB come dict Python
        if isinstance(raw_meta, str):
            import json as _json
            try:
                raw_meta = _json.loads(raw_meta)
            except Exception:
                raw_meta = {}
        sources.append({
            "id": row["id"],
            "score": score,
            "kb_namespace": row["kb_namespace"],
            "source_path": row.get("source_path"),
            "excerpt": row["excerpt"],
            "doc_metadata": raw_meta,
            "doc_title": row.get("doc_title") or "",
        })
    return sources


def execute_search(
    query_text: str,
    cursor,
    kb_namespace: Optional[str] = None,
    top_k: int = 5,
    search_mode: str = "vector",
    query_vec: Optional[List[float]] = None,
    file_type: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    expanded_queries: Optional[List[str]] = None,
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
        return fts_search(
            query_text, cursor, kb_namespace=kb_namespace, top_k=top_k,
            file_type=file_type, year_from=year_from, year_to=year_to,
        )

    # Calcola embedding se non fornito (serve per vector e hybrid)
    if query_vec is None:
        vec, _model, _dim = embed_text(query_text)
    else:
        vec = query_vec

    if search_mode == "hybrid":
        # Recupera molti candidati per merge + diversity (top_k*5 min 50)
        candidati = max(top_k * 5, 50)

        # Multi-query expansion: se abbiamo piu' varianti, accumula risultati da tutte
        if expanded_queries and len(expanded_queries) > 1:
            all_vector = []
            all_fts = []
            for variant in expanded_queries:
                vec_i, _, _ = embed_text(variant)
                sql_i, params_i = build_query_sql(
                    query_text=variant,
                    kb_namespace=kb_namespace,
                    top_k=candidati,
                    query_vec=vec_i,
                    file_type=file_type,
                    year_from=year_from,
                    year_to=year_to,
                )
                cursor.execute(sql_i, params_i)
                vector_rows_i = cursor.fetchall()
                all_vector.extend(parse_results(vector_rows_i))

                fts_i = fts_search(
                    variant, cursor, kb_namespace=kb_namespace, top_k=candidati,
                    file_type=file_type, year_from=year_from, year_to=year_to,
                )
                all_fts.extend(fts_i)

            merged = rrf_merge(all_vector, all_fts, top_k=candidati)
            return diversify_sources(merged, top_k=top_k, max_per_doc=2)

        # Percorso standard: singola query
        sql, params = build_query_sql(
            query_text=query_text,
            kb_namespace=kb_namespace,
            top_k=candidati,
            query_vec=vec,
            file_type=file_type,
            year_from=year_from,
            year_to=year_to,
        )
        cursor.execute(sql, params)
        vector_rows = cursor.fetchall()
        vector_sources = parse_results(vector_rows)

        fts_sources = fts_search(
            query_text, cursor, kb_namespace=kb_namespace, top_k=candidati,
            file_type=file_type, year_from=year_from, year_to=year_to,
        )

        merged = rrf_merge(vector_sources, fts_sources, top_k=candidati)
        return diversify_sources(merged, top_k=top_k, max_per_doc=2)

    # Default: solo vector search (con diversification)
    candidati_vec = max(top_k * 3, 30)
    sql, params = build_query_sql(
        query_text=query_text,
        kb_namespace=kb_namespace,
        top_k=candidati_vec,
        query_vec=vec,
        file_type=file_type,
        year_from=year_from,
        year_to=year_to,
    )
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    return diversify_sources(parse_results(rows), top_k=top_k, max_per_doc=2)


def diversify_sources(sources: List[Dict], top_k: int, max_per_doc: int = 2) -> List[Dict]:
    """Source diversity: limita il numero di chunk per documento.

    Evita che un singolo documento domini i risultati restituendo troppi chunk.
    Scorre i risultati in ordine di score e accetta al massimo max_per_doc chunk
    per ogni source_path distinto, fino a top_k risultati totali.

    Args:
        sources: lista ordinata per score (migliore primo)
        top_k: numero massimo di risultati da restituire
        max_per_doc: massimo chunk per documento (default: 2)

    Returns:
        Lista diversificata di al massimo top_k elementi.
    """
    seen: Dict[str, int] = {}  # source_path → count
    result = []
    excluded = []
    for src in sources:
        sp = src.get("source_path") or src.get("kb_namespace", "unknown")
        count = seen.get(sp, 0)
        if count < max_per_doc:
            result.append(src)
            seen[sp] = count + 1
        else:
            excluded.append(src)
        if len(result) >= top_k:
            break
    # Fallback: se non si raggiunge top_k, aggiunge quelli esclusi in ordine di score
    # (violando max_per_doc solo se strettamente necessario)
    for src in excluded:
        if len(result) >= top_k:
            break
        result.append(src)
    return result


def log_query(query_text: str, kb_namespace: Optional[str], sources: List[Dict], response_time_ms: int):
    """Log query to query_log table."""
    # Placeholder for future implementation
    pass
