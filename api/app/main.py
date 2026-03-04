# RAG VE API - Main application
import os
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from pydantic import BaseModel, Field
from typing import Optional, List

from .db import test_connection, get_db_cursor
from .query import build_query_sql, parse_results
from .embedding import embed_text
from .llm import synthesize_answer

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
    synthesize: bool = Field(False, description="Se True, genera risposta sintetica via LLM")

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

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".csv", ".json"}


class HealthReadyResponse(BaseModel):
    status: str
    database: str
    vector: str


class KbInfo(BaseModel):
    namespace: str
    nome: Optional[str] = None
    doc_count: int
    chunk_count: int


class KbsResponse(BaseModel):
    kbs: List[KbInfo]


class UploadResponse(BaseModel):
    upload_id: str
    job_id: str
    kb: str
    files: List[str]


class DocumentInfo(BaseModel):
    id: str
    kb_namespace: str
    source_path: Optional[str] = None
    titolo: Optional[str] = None
    ingest_status: Optional[str] = None
    is_deleted: bool = False
    created_at: Optional[str] = None


class DocumentsResponse(BaseModel):
    documents: List[DocumentInfo]


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

        # Sintesi LLM opzionale (synthesize=True)
        answer = None
        if request.synthesize and sources:
            llm_model = os.environ.get("OLLAMA_LLM_MODEL", "llama3.2")
            answer = synthesize_answer(request.query, sources, llm_model)

        # Fallback se LLM non disponibile o synthesize=False
        if answer is None:
            if not sources:
                answer = "Nessun documento trovato per la query specificata."
            else:
                answer = "Retrieval-only response."

        return QueryResponse(answer=answer, sources=sources)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")


@app.get("/health/ready")
def health_ready():
    """Verifica DB connesso + estensione pgvector presente."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(
                    status_code=503,
                    detail="Estensione vector non trovata nel database."
                )
        return HealthReadyResponse(status="ready", database="connected", vector="ok")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database non raggiungibile: {str(e)}"
        )


@app.get("/api/v1/kbs")
def list_kbs():
    """Elenca le Knowledge Base con conteggio documenti e chunk."""
    try:
        sql = """
            SELECT
                kb.namespace,
                kb.nome,
                COUNT(DISTINCT d.id) AS doc_count,
                COUNT(c.id) AS chunk_count
            FROM knowledge_base kb
            LEFT JOIN documents d ON d.kb_id = kb.id
            LEFT JOIN chunks c ON c.kb_id = kb.id
            GROUP BY kb.namespace, kb.nome
            ORDER BY kb.namespace
        """
        with get_db_cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

        kbs = [
            KbInfo(
                namespace=row["namespace"],
                nome=row["nome"],
                doc_count=row["doc_count"],
                chunk_count=row["chunk_count"],
            )
            for row in rows
        ]
        return KbsResponse(kbs=kbs)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore interno durante il recupero delle KB: {str(e)}"
        )


@app.get("/api/v1/documents")
def list_documents(
    kb: Optional[str] = Query(None, description="Filtra per namespace KB"),
    status: Optional[str] = Query(None, description="Filtra per ingest_status (es. done, error)"),
    deleted: Optional[bool] = Query(None, description="Filtra per is_deleted (true/false)"),
):
    """Elenca i documenti indicizzati con stato ingest e soft-delete flag."""
    try:
        sql = """
            SELECT
                d.id::text,
                kb.namespace AS kb_namespace,
                d.source_uri AS source_path,
                d.titolo,
                d.ingest_status,
                COALESCE(d.is_deleted, FALSE) AS is_deleted,
                d.created_at::text
            FROM documents d
            JOIN knowledge_base kb ON kb.id = d.kb_id
            WHERE 1=1
        """
        params = []

        if kb:
            sql += " AND kb.namespace = %s"
            params.append(kb)
        if status is not None:
            sql += " AND d.ingest_status = %s"
            params.append(status)
        if deleted is not None:
            sql += " AND COALESCE(d.is_deleted, FALSE) = %s"
            params.append(deleted)

        sql += " ORDER BY d.created_at DESC"

        with get_db_cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        docs = [
            DocumentInfo(
                id=row["id"],
                kb_namespace=row["kb_namespace"],
                source_path=row.get("source_path"),
                titolo=row.get("titolo"),
                ingest_status=row.get("ingest_status"),
                is_deleted=bool(row.get("is_deleted", False)),
                created_at=row.get("created_at"),
            )
            for row in rows
        ]
        return DocumentsResponse(documents=docs)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore interno durante il recupero dei documenti: {str(e)}"
        )


@app.post("/api/v1/upload")
def upload_files(
    kb: Optional[str] = Query(None),
    files: List[UploadFile] = File(...),
):
    """Carica uno o piu' file nella knowledge base specificata."""
    # Validazione kb
    if not kb or not kb.strip():
        raise HTTPException(
            status_code=400,
            detail="Parametro kb obbligatorio. Specificare il namespace della knowledge base."
        )
    kb = kb.strip()

    # Legge configurazione da env (per-call: compatibile con monkeypatch)
    inbox_root = os.environ.get("INBOX_ROOT", "/data/inbox")
    max_mb = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "50"))
    max_bytes = max_mb * 1024 * 1024

    # Validazione tipo + lettura in memoria (una sola volta per file)
    validated = []
    for f in files:
        ext = Path(f.filename).suffix.lower() if f.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=415,
                detail="Tipo file non supportato. Formati accettati: PDF, TXT, MD, CSV, JSON"
            )
        content = f.file.read()
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File troppo grande. Dimensione massima consentita: {max_mb}MB"
            )
        validated.append((f.filename, content))

    # Crea directory e salva file su disco
    kb_dir = Path(inbox_root) / kb
    kb_dir.mkdir(parents=True, exist_ok=True)

    saved_names = []
    saved_sizes = []
    for filename, content in validated:
        (kb_dir / filename).write_bytes(content)
        saved_names.append(filename)
        saved_sizes.append(len(content))

    # Genera UUIDs
    upload_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    # Inserisce riga in upload_log (commit=True obbligatorio per scrittura)
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """
                INSERT INTO upload_log
                    (upload_id, job_id, kb_namespace, file_names, file_sizes_bytes)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (upload_id, job_id, kb, saved_names, saved_sizes),
            )
    except Exception:
        pass  # audit log best-effort: file già salvato su disco

    return UploadResponse(
        upload_id=upload_id,
        job_id=job_id,
        kb=kb,
        files=saved_names,
    )
