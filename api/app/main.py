# RAG VE API - Main application
import os
import uuid
import json
import time
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List

from .db import test_connection, get_db_cursor
from .query import build_query_sql, parse_results, execute_search
from .embedding import embed_text
from .llm import synthesize_answer
from .auth import require_api_key, require_admin_key
from .metadata_extractor import extract_metadata_for_file, save_sidecar_meta
from .graph_query import enrich_sources
from .reranker import rerank_with_llm

logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG VE API",
    description="API for RAG multi-KB system",
    version="1.0.0"
)


def _write_query_log(query_text: str, sources: list, model_used: str, response_time_ms: int, user_id: str = None) -> None:
    """Scrive una riga in query_log. Best-effort: non propaga eccezioni."""
    try:
        chunks_json = json.dumps([
            {
                "id": s["id"] if isinstance(s, dict) else s.id,
                "score": s["score"] if isinstance(s, dict) else s.score,
            }
            for s in (sources or [])
        ])
        # Estrae i namespace distinti presenti nelle sources
        namespaces = list({
            (s["kb_namespace"] if isinstance(s, dict) else s.kb_namespace)
            for s in (sources or [])
            if (s["kb_namespace"] if isinstance(s, dict) else s.kb_namespace)
        })
        with get_db_cursor(commit=True) as cursor:
            # Risolve namespace → UUID reali della knowledge_base
            kb_ids_pg = None
            if namespaces:
                cursor.execute(
                    "SELECT id::text FROM knowledge_base WHERE namespace = ANY(%s)",
                    (namespaces,),
                )
                rows = cursor.fetchall()
                if rows:
                    kb_ids_pg = "{" + ",".join(r["id"] for r in rows) + "}"
            cursor.execute(
                """
                INSERT INTO query_log (user_id, kb_ids, query_text, retrieved_chunks, model_used, response_time_ms)
                VALUES (%s, %s::uuid[], %s, %s::jsonb, %s, %s)
                """,
                (user_id, kb_ids_pg, query_text, chunks_json, model_used, response_time_ms),
            )
    except Exception as e:
        logger.warning("query_log write failed: %s", e)

# Request/Response models
VALID_SEARCH_MODES = {"vector", "fts", "hybrid"}


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' o 'assistant'")
    content: str = Field(..., description="Testo del messaggio")


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query text")
    kb: Optional[str] = Field(None, description="Optional KB namespace to filter")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Number of results to return (1-20)")
    synthesize: bool = Field(False, description="Se True, genera risposta sintetica via LLM")
    search_mode: str = Field("vector", description="Modalità ricerca: vector, fts, hybrid")
    history: Optional[List[ChatMessage]] = Field(None, description="Storia della conversazione precedente")
    graph_enabled: Optional[bool] = Field(False, description="Se True, arricchisce i risultati con il grafo entità")
    file_type: Optional[str] = Field(None, description="Filtra per tipo file: pdf, docx, txt, md, csv, json")
    year_from: Optional[int] = Field(None, description="Filtra chunk con ingest_date >= anno specificato")
    year_to: Optional[int] = Field(None, description="Filtra chunk con ingest_date <= anno specificato")
    rerank: Optional[bool] = Field(False, description="Se True, usa LLM per re-ranking post-retrieval")

class Source(BaseModel):
    id: str
    score: float
    kb_namespace: str
    source_path: Optional[str] = None
    excerpt: str
    doc_metadata: Optional[dict] = None
    related_entities: Optional[list] = None
    related_docs: Optional[list] = None

class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]

class HealthResponse(BaseModel):
    status: str
    database: str

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".csv", ".json", ".docx"}


class HealthReadyResponse(BaseModel):
    status: str
    database: str
    vector: str
    schema: str


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


class MetricsResponse(BaseModel):
    query_count: int
    avg_latency_ms: int
    upload_count: int
    doc_count: int
    chunk_count: int


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
def query_api(request: QueryRequest, _auth=Depends(require_api_key)):
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
        # Valida search_mode
        if request.search_mode not in VALID_SEARCH_MODES:
            raise HTTPException(
                status_code=422,
                detail=f"search_mode non valido. Valori accettati: {', '.join(sorted(VALID_SEARCH_MODES))}"
            )

        # Timing: misurato da qui fino a prima del return (embedding + retrieval + sintesi)
        t0 = time.perf_counter()

        # Calcola embedding (non serve per search_mode="fts")
        query_vec = None
        if request.search_mode != "fts":
            query_vec, _model_name, _dim = embed_text(request.query)

        # Se rerank: recupera top_k*3 candidati per poi ri-classificare
        retrieval_k = request.top_k * 3 if request.rerank else request.top_k

        with get_db_cursor() as cursor:
            sources = execute_search(
                query_text=request.query,
                cursor=cursor,
                kb_namespace=request.kb,
                top_k=retrieval_k,
                search_mode=request.search_mode,
                query_vec=query_vec,
                file_type=request.file_type,
                year_from=request.year_from,
                year_to=request.year_to,
            )

        # Re-ranking LLM opzionale
        if request.rerank and sources:
            try:
                sources = rerank_with_llm(request.query, sources, top_k=request.top_k)
            except Exception as e:
                logger.warning("rerank failed, using original order: %s", e)
                sources = sources[:request.top_k]

        # M7 GraphRAG: arricchimento opzionale con grafo entità
        if request.graph_enabled and sources:
            try:
                with get_db_cursor() as graph_cursor:
                    sources = enrich_sources(graph_cursor, sources, depth=2)
            except Exception as e:
                logger.warning("graph enrichment failed: %s", e)

        # Sintesi LLM opzionale (synthesize=True)
        answer = None
        if request.synthesize and sources:
            llm_model = os.environ.get("OLLAMA_LLM_MODEL", "llama3.2")
            history_dicts = (
                [{"role": m.role, "content": m.content} for m in request.history]
                if request.history else None
            )
            answer = synthesize_answer(request.query, sources, llm_model, history=history_dicts)

        # Fallback se LLM non disponibile o synthesize=False
        if answer is None:
            if not sources:
                answer = "Nessun documento trovato per la query specificata."
            elif request.synthesize:
                # LLM chiamato ma non disponibile: messaggio amichevole con nomi file
                visti: set = set()
                nomi = []
                for s in sources:
                    fname = (s.get("source_path") or "").split("/")[-1] or s.get("kb_namespace", "?")
                    if fname not in visti:
                        nomi.append(f"- {fname}")
                        visti.add(fname)
                elenco = "\n".join(nomi[:5])
                n = len(sources)
                answer = (
                    "Mi dispiace, il servizio di elaborazione è temporaneamente non disponibile. "
                    f"Ho trovato {n} estratt{'i' if n != 1 else 'o'} nei seguenti documenti "
                    "che potrebbero rispondere alla tua domanda:\n\n"
                    f"{elenco}\n\n"
                    "Ti invito a consultare le fonti qui sotto per i dettagli."
                )
            else:
                answer = "Retrieval-only response."

        response_time_ms = int((time.perf_counter() - t0) * 1000)
        model_used = (
            os.environ.get("OLLAMA_LLM_MODEL", "llama3.2")
            if request.synthesize
            else os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")
        )
        _write_query_log(request.query, sources, model_used, response_time_ms, user_id=_auth)

        return QueryResponse(answer=answer, sources=sources)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")


@app.post("/api/v1/query/stream")
def query_stream(request: QueryRequest, _auth=Depends(require_api_key)):
    """Endpoint SSE: invia fonti + token LLM in streaming.
    Formato eventi:
      data: {"type": "sources", "sources": [...]}
      data: {"type": "token", "content": "..."}
      data: [DONE]
    """
    from .llm import synthesize_stream as _synthesize_stream

    try:
        if request.search_mode not in VALID_SEARCH_MODES:
            raise HTTPException(status_code=422, detail="search_mode non valido")

        # Timing: solo retrieval (embedding + ricerca) — lo stream LLM è non-deterministico
        t0 = time.perf_counter()

        query_vec = None
        if request.search_mode != "fts":
            query_vec, _m, _d = embed_text(request.query)

        retrieval_k = request.top_k * 3 if request.rerank else request.top_k

        with get_db_cursor() as cursor:
            sources = execute_search(
                query_text=request.query,
                cursor=cursor,
                kb_namespace=request.kb,
                top_k=retrieval_k,
                search_mode=request.search_mode,
                query_vec=query_vec,
                file_type=request.file_type,
                year_from=request.year_from,
                year_to=request.year_to,
            )

        # Re-ranking LLM opzionale
        if request.rerank and sources:
            try:
                sources = rerank_with_llm(request.query, sources, top_k=request.top_k)
            except Exception as e:
                logger.warning("rerank (stream) failed: %s", e)
                sources = sources[:request.top_k]

        # M7 GraphRAG: arricchimento opzionale con grafo entità
        if request.graph_enabled and sources:
            try:
                with get_db_cursor() as graph_cursor:
                    sources = enrich_sources(graph_cursor, sources, depth=2)
            except Exception as e:
                logger.warning("graph enrichment (stream) failed: %s", e)

        retrieval_ms = int((time.perf_counter() - t0) * 1000)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")

    stream_model_used = (
        os.environ.get("OLLAMA_LLM_MODEL", "llama3.2")
        if request.synthesize
        else "retrieval-only"
    )
    _write_query_log(request.query, sources, stream_model_used, retrieval_ms, user_id=_auth)

    # Serializza sources come lista di dict (compatibile con Source pydantic)
    sources_data = [
        {
            "id": s["id"] if isinstance(s, dict) else s.id,
            "score": s["score"] if isinstance(s, dict) else s.score,
            "kb_namespace": s["kb_namespace"] if isinstance(s, dict) else s.kb_namespace,
            "source_path": s.get("source_path") if isinstance(s, dict) else s.source_path,
            "excerpt": s["excerpt"] if isinstance(s, dict) else s.excerpt,
        }
        for s in sources
    ]

    llm_model = os.environ.get("OLLAMA_LLM_MODEL", "llama3.2")
    history_dicts = (
        [{"role": m.role, "content": m.content} for m in request.history]
        if request.history else None
    )

    def event_generator():
        # Evento 1: fonti (arriva subito, prima che LLM generi)
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources_data})}\n\n"

        if not sources or not request.synthesize:
            msg = (
                "Nessun documento trovato per la query specificata."
                if not sources
                else "Retrieval-only response."
            )
            yield f"data: {json.dumps({'type': 'token', 'content': msg})}\n\n"
        else:
            # Evento 2: segnale "thinking" — il frontend lo mostra come placeholder
            yield f"data: {json.dumps({'type': 'thinking'})}\n\n"

            token_count = 0
            for token in _synthesize_stream(request.query, sources, llm_model, history=history_dicts):
                token_count += 1
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            # Fallback se LLM non ha risposto (Ollama down / timeout)
            if token_count == 0:
                visti: set = set()
                nomi = []
                for s in sources:
                    fname = (s.get("source_path") or "").split("/")[-1] or s.get("kb_namespace", "?")
                    if fname not in visti:
                        nomi.append(f"- {fname}")
                        visti.add(fname)
                elenco = "\n".join(nomi[:5])
                n = len(sources)
                msg = (
                    "Il servizio di elaborazione è temporaneamente non disponibile. "
                    f"Ho trovato {n} estratt{'i' if n != 1 else 'o'} nei seguenti documenti:\n\n"
                    f"{elenco}\n\n"
                    "Consulta le fonti qui sotto per i dettagli."
                )
                yield f"data: {json.dumps({'type': 'token', 'content': msg})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/health/ready")
def health_ready():
    """Verifica DB connesso + estensione pgvector + tabelle core dello schema."""
    try:
        with get_db_cursor() as cursor:
            # Check 1: estensione pgvector
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            if cursor.fetchone() is None:
                raise HTTPException(
                    status_code=503,
                    detail="Estensione vector non trovata nel database."
                )
            # Check 2: tabelle core dello schema (knowledge_base, documents, chunks)
            cursor.execute(
                """
                SELECT COUNT(*)::int AS count FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('knowledge_base', 'documents', 'chunks')
                """
            )
            table_count = cursor.fetchone()["count"]
            if table_count < 3:
                raise HTTPException(
                    status_code=503,
                    detail=f"Schema DB incompleto: attese 3 tabelle core, trovate {table_count}."
                )
        return HealthReadyResponse(status="ready", database="connected", vector="ok", schema="ok")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database non raggiungibile: {str(e)}"
        )


@app.get("/api/v1/kbs")
def list_kbs(_auth=Depends(require_api_key)):
    """Elenca le Knowledge Base con conteggio documenti e chunk."""
    try:
        sql = """
            SELECT
                kb.namespace,
                kb.nome,
                COUNT(DISTINCT d.id) AS doc_count,
                COUNT(DISTINCT c.id) AS chunk_count
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
    _auth=Depends(require_api_key),
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
    _auth=Depends(require_admin_key),
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
    llm_model = os.environ.get("LLM_MODEL", "llama3.2")
    for filename, content in validated:
        file_path = kb_dir / filename
        file_path.write_bytes(content)
        saved_names.append(filename)
        saved_sizes.append(len(content))
        # Genera sidecar .meta.json via LLM (best-effort, non blocca l'upload)
        try:
            text_snippet = content.decode("utf-8", errors="replace")
            meta = extract_metadata_for_file(file_path, llm_model, text_snippet)
            save_sidecar_meta(file_path, meta)
        except Exception:
            pass  # best-effort: metadata extraction non blocca l'upload

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


@app.get("/metrics")
def get_metrics(_auth=Depends(require_admin_key)):
    """Metriche operative essenziali. Lettura da tabelle esistenti, nessuna dipendenza esterna."""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM query_log)::int                                                   AS query_count,
                    COALESCE((SELECT ROUND(AVG(response_time_ms))::int FROM query_log), 0)                  AS avg_latency_ms,
                    (SELECT COUNT(*) FROM upload_log)::int                                                  AS upload_count,
                    (SELECT COUNT(*) FROM documents WHERE COALESCE(is_deleted, FALSE) = FALSE)::int         AS doc_count,
                    (SELECT COUNT(*) FROM chunks)::int                                                      AS chunk_count
                """
            )
            row = cursor.fetchone()
        return MetricsResponse(
            query_count=row["query_count"],
            avg_latency_ms=row["avg_latency_ms"],
            upload_count=row["upload_count"],
            doc_count=row["doc_count"],
            chunk_count=row["chunk_count"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore interno durante il recupero delle metriche: {str(e)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# M7 GraphRAG — endpoint grafo entità
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/v1/graph/entities")
def graph_entities(
    doc_id: str = Query(..., description="UUID del documento"),
    _auth=Depends(require_api_key),
):
    """Ritorna tutte le entità estratte per un documento.

    Args:
        doc_id: UUID del documento (recuperabile da GET /api/v1/documents)

    Returns:
        {"doc_id": "...", "entities": [{id, entity_type, canonical, display_name, ...}]}
    """
    try:
        from .graph_query import get_document_entities  # già importato a livello modulo via enrich_sources
        with get_db_cursor() as cursor:
            entities = get_document_entities(cursor, [doc_id])
        return {"doc_id": doc_id, "entities": entities}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore interno durante il recupero delle entità: {str(e)}"
        )


@app.get("/api/v1/graph/traverse")
def graph_traverse(
    entity_name: str = Query(..., description="Nome entità da cui partire (ricerca ILIKE)"),
    depth: int = Query(2, ge=1, le=5, description="Profondità traversal (1-5)"),
    _auth=Depends(require_api_key),
):
    """Traversa il grafo entità da un'entità nominata.

    Cerca l'entità per nome (case-insensitive ILIKE su canonical),
    poi attraversa il grafo fino a `depth` hop.

    Returns:
        {"seed_entity": {...}, "related_entities": [...], "depth": N}
    """
    try:
        from .graph_query import traverse_related  # già importato via enrich_sources
        with get_db_cursor() as cursor:
            # Risolvi nome → entity_id(s)
            cursor.execute(
                """
                SELECT id::text, entity_type, canonical, display_name
                FROM entities
                WHERE canonical ILIKE %s
                LIMIT 10
                """,
                (f"%{entity_name.strip().lower()}%",),
            )
            seeds = cursor.fetchall()
            if not seeds:
                return {"seed_entity": None, "related_entities": [], "depth": depth}

            # seeds può essere RealDictCursor o tuple
            if hasattr(seeds[0], "keys"):
                seeds = [dict(s) for s in seeds]
            else:
                cols = ["id", "entity_type", "canonical", "display_name"]
                seeds = [dict(zip(cols, s)) for s in seeds]

            seed_ids = [s["id"] for s in seeds]
            related = traverse_related(cursor, seed_ids, depth=depth)

        return {
            "seed_entity": seeds[0],
            "related_entities": related,
            "depth": depth,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore interno durante il traversal del grafo: {str(e)}"
        )
