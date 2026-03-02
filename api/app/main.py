# RAG VE API - Main application
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

from .db import test_connection, get_db_cursor
from .query import build_query_sql, parse_results
from .embedding import embed_text

app = FastAPI(
    title="RAG VE API",
    description="API for RAG multi-KB system",
    version="1.0.0"
)

# Request/Response models
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query text")
    kb: Optional[str] = Field(None, description="Optional KB namespace to filter")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Number of results to return (1-20)")

class Source(BaseModel):
    id: str
    score: float
    kb_namespace: str
    source_path: Optional[str] = None
    excerpt: str

class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]

class HealthResponse(BaseModel):
    status: str
    database: str

@app.get("/health")
def health_check():
    """Health check endpoint with DB connection test."""
    try:
        db_ok = test_connection()
        if not db_ok:
            raise HTTPException(status_code=503, detail="Database connection failed")
        return HealthResponse(status="ok", database="connected")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

@app.post("/api/v1/query")
def query_api(request: QueryRequest):
    """
    Query API - returns retrieval results.

    Accepts:
    - query: search text (required, min_length=1)
    - kb: optional KB namespace to filter
    - top_k: number of results to return (default: 5, range: 1-20)

    Returns:
    - answer: placeholder (retrieval-only for now)
    - sources: list of matching chunks with metadata
    """
    try:
        # Calculate embedding for the query
        query_vec, model_name, dim = embed_text(request.query)

        # Build and execute query
        sql, params = build_query_sql(
            query_text=request.query,
            kb_namespace=request.kb,
            top_k=request.top_k,
            query_vec=query_vec
        )

        with get_db_cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        sources = parse_results(rows)

        # Build response
        answer = "Retrieval-only response. No LLM synthesis yet."
        if not sources:
            answer = "No matching documents found."

        return QueryResponse(answer=answer, sources=sources)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")
