# RAG VE API - Main application
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Any

from .db import test_connection, get_db_cursor
from .query import build_query_sql, parse_results, log_query

app = FastAPI(
    title="RAG VE API",
    description="API for RAG multi-KB system",
    version="1.0.0"
)


# Request/Response models
class QueryRequest(BaseModel):
    query: str
    kb: Optional[str] = None
    top_k: Optional[int] = 5


class Source(BaseModel):
    id: str
    score: float
    kb_namespace: str
    source_uri: Optional[str] = None
    excerpt: str


class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]


class HealthResponse(BaseModel):
    status: str
    database: str


@app.get("/health")
async def health_check():
    """Health check endpoint with DB connection test."""
    try:
        db_ok = test_connection()
        return HealthResponse(
            status="ok",
            database="connected" if db_ok else "disconnected"
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")


@app.post("/api/v1/query")
async def query_api(request: QueryRequest):
    """
    Query API - returns retrieval results.

    Accepts:
    - query: search text
    - kb: optional KB namespace to filter
    - top_k: number of results to return (default: 5)

    Returns:
    - answer: placeholder (retrieval-only for now)
    - sources: list of matching chunks with metadata
    """
    try:
        # Build and execute query
        sql, params = build_query_sql(
            query_text=request.query,
            kb_namespace=request.kb,
            top_k=request.top_k
        )

        with get_db_cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        sources = parse_results(rows)

        # Build response
        answer = "Retrieval-only response. No LLM synthesis yet."
        if not sources:
            answer = "No matching documents found."

        return QueryResponse(
            answer=answer,
            sources=sources
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")


@app.get("/api/v1/query")
async def query_get(query: str, kb: Optional[str] = None, top_k: Optional[int] = 5):
    """
    GET version of query API (for testing).
    Same parameters as POST /api/v1/query
    """
    return await query_api(QueryRequest(query=query, kb=kb, top_k=top_k))
