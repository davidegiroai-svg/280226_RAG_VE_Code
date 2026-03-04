# Phase 8: LLM Synthesis — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Aggiungere synthesis LLM a POST /api/v1/query tramite il flag `synthesize=true`, con fallback retrieval-only se il modello non è disponibile.

**Architecture:** Nuovo modulo `api/app/llm.py` con funzione `generate_answer()` che usa il client OpenAI-compatible (sync) puntando a Ollama. `main.py` chiama `generate_answer()` solo se `synthesize=True`; qualsiasi eccezione attiva il fallback silenzioso. `QueryResponse` aggiunge campo `mode` per indicare `"synthesis"` o `"retrieval_only"`.

**Tech Stack:** FastAPI 0.115 (sync `def`), `openai>=1.0.0` (sync `OpenAI` client — NON `AsyncOpenAI`), Pydantic v2, pytest sincrono con `unittest.mock`.

---

## Contesto critico

- **SYNC obbligatorio**: le route FastAPI sono `def`, non `async def`. Usare `openai.OpenAI` (sync), mai `AsyncOpenAI`.
- **`OLLAMA_BASE_URL`** nel docker-compose vale `http://host.docker.internal:11434`. Il client OpenAI vuole il path `/v1` → il codice fa `os.environ.get("OLLAMA_BASE_URL") + "/v1"`.
- **Mock pattern**: `main.py` usa `from .llm import generate_answer` → il mock target è `app.main.generate_answer` (dove è importato, non dove è definito).
- **Fallback silenzioso**: qualsiasi `Exception` in `generate_answer()` → `mode="retrieval_only"`, non HTTP 500.
- **Env per-call**: leggere env dentro il body di `generate_answer()` per monkeypatch compatibility.

---

## Task 0 — Infrastruttura (nessun test)

### Task 0.1: Aggiungi `openai` a requirements.txt

**File:** `api/requirements.txt`

Aggiungi riga dopo `python-multipart`:
```
openai>=1.0.0
```

### Task 0.2: Aggiungi env vars a docker-compose.yml

**File:** `docker-compose.yml` — servizio `api`, sezione `environment`

Aggiungi dopo `MAX_UPLOAD_SIZE_MB`:
```yaml
      LLM_MODEL: "${LLM_MODEL:-mistral-nemo:12b}"
      LLM_TIMEOUT_S: "${LLM_TIMEOUT_S:-30}"
```

### Task 0.3: Rebuild container

```powershell
docker compose up -d --build
```

Atteso: `Successfully installed openai-...` nel log di build.

---

## Task 1 — Scrivi i test PRIMA (TDD: RED)

**File da creare:** `tests/test_llm_synthesis.py`

```powershell
# Dopo la creazione, verifica RED:
docker compose exec api pytest tests/test_llm_synthesis.py -v
# Atteso: tutti FAILED/ERROR (ImportError o 404 o AttributeError)
```

Contenuto completo:

```python
"""tests/test_llm_synthesis.py — TDD Phase 8: LLM Synthesis

RED:  fallenti prima dell'implementazione
GREEN: dopo llm.py + aggiornamento main.py
"""
import sys
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────

def _mock_cursor_with_rows(rows):
    """Mock compatibile con 'with get_db_cursor() as cursor'."""
    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = rows
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=mock_cur)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


_FAKE_ROWS = [
    {
        "id": "chunk-001",
        "kb_namespace": "demo",
        "excerpt": "I bandi del 2026 prevedono fondi per mobilità sostenibile.",
        "source_path": "/data/inbox/demo/bando.pdf",
        "distance": 0.15,
    }
]


# ─────────────────────────────────────────────────────────
# Unit test: generate_answer in llm.py
# ─────────────────────────────────────────────────────────

class TestGenerateAnswer:

    def test_generate_answer_chiama_openai_chat(self, monkeypatch):
        """generate_answer deve chiamare chat.completions.create e restituire il testo."""
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://fake-ollama:11434")
        monkeypatch.setenv("LLM_MODEL", "test-model")

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Risposta sintetica di test."

        with patch("app.llm.OpenAI") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.chat.completions.create.return_value = mock_response

            from app.llm import generate_answer
            result = generate_answer(
                query="Quali bandi ci sono?",
                chunks=[{"excerpt": "Testo del chunk."}],
            )

        assert result == "Risposta sintetica di test."
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "test-model"

    def test_generate_answer_usa_chunks_nel_prompt(self, monkeypatch):
        """Il prompt deve contenere il testo dei chunk forniti."""
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://fake-ollama:11434")

        captured_messages = []
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "ok"

        def capture_create(**kwargs):
            captured_messages.extend(kwargs.get("messages", []))
            return mock_response

        with patch("app.llm.OpenAI") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.chat.completions.create.side_effect = capture_create

            from app.llm import generate_answer
            generate_answer(
                query="Query di test",
                chunks=[{"excerpt": "Testo importante dal documento."}],
            )

        assert any("Testo importante dal documento." in m["content"] for m in captured_messages)

    def test_generate_answer_solleva_eccezione_se_openai_fallisce(self, monkeypatch):
        """Se OpenAI solleva un'eccezione, generate_answer deve propagarla."""
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://fake-ollama:11434")

        with patch("app.llm.OpenAI") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client
            mock_client.chat.completions.create.side_effect = Exception("connection refused")

            from app.llm import generate_answer
            with pytest.raises(Exception, match="connection refused"):
                generate_answer(query="test", chunks=[{"excerpt": "testo"}])


# ─────────────────────────────────────────────────────────
# Integration test: POST /api/v1/query con synthesize
# ─────────────────────────────────────────────────────────

class TestQuerySynthesis:

    def test_query_synthesize_false_non_chiama_llm(self, monkeypatch):
        """synthesize=False (default) → generate_answer NON viene chiamata."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
        ctx = _mock_cursor_with_rows(_FAKE_ROWS)

        with patch("app.main.get_db_cursor", return_value=ctx), \
             patch("app.main.embed_text", return_value=([0.0] * 768, "dummy", 768)), \
             patch("app.main.generate_answer") as mock_gen:

            resp = client.post("/api/v1/query", json={"query": "bandi", "top_k": 3})

        assert resp.status_code == 200
        mock_gen.assert_not_called()
        data = resp.json()
        assert data["mode"] == "retrieval_only"

    def test_query_synthesize_true_chiama_llm_e_ritorna_risposta(self, monkeypatch):
        """synthesize=True + LLM disponibile → answer da LLM, mode='synthesis'."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
        ctx = _mock_cursor_with_rows(_FAKE_ROWS)

        with patch("app.main.get_db_cursor", return_value=ctx), \
             patch("app.main.embed_text", return_value=([0.0] * 768, "dummy", 768)), \
             patch("app.main.generate_answer", return_value="Risposta LLM sintetica."):

            resp = client.post(
                "/api/v1/query",
                json={"query": "bandi 2026", "top_k": 3, "synthesize": True},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "Risposta LLM sintetica."
        assert data["mode"] == "synthesis"
        assert len(data["sources"]) == 1

    def test_query_synthesize_true_fallback_se_llm_non_disponibile(self, monkeypatch):
        """synthesize=True + LLM errore → fallback retrieval_only, NON HTTP 500."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
        ctx = _mock_cursor_with_rows(_FAKE_ROWS)

        with patch("app.main.get_db_cursor", return_value=ctx), \
             patch("app.main.embed_text", return_value=([0.0] * 768, "dummy", 768)), \
             patch("app.main.generate_answer", side_effect=Exception("LLM timeout")):

            resp = client.post(
                "/api/v1/query",
                json={"query": "bandi 2026", "top_k": 3, "synthesize": True},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "retrieval_only"
        assert len(data["sources"]) == 1

    def test_query_synthesize_true_nessun_chunk_non_chiama_llm(self, monkeypatch):
        """synthesize=True ma zero chunk → non chiama LLM, risposta 'nessun documento'."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
        ctx = _mock_cursor_with_rows([])  # nessun risultato

        with patch("app.main.get_db_cursor", return_value=ctx), \
             patch("app.main.embed_text", return_value=([0.0] * 768, "dummy", 768)), \
             patch("app.main.generate_answer") as mock_gen:

            resp = client.post(
                "/api/v1/query",
                json={"query": "query senza risultati", "top_k": 3, "synthesize": True},
            )

        assert resp.status_code == 200
        mock_gen.assert_not_called()
        data = resp.json()
        assert data["mode"] == "retrieval_only"

    def test_query_schema_accetta_synthesize_true(self):
        """Pydantic v2 deve accettare synthesize=true senza 422."""
        # Test validazione schema — non serve DB
        resp = client.post(
            "/api/v1/query",
            json={"query": "test", "synthesize": True},
        )
        # Può fallire con 500 (no DB) ma NON con 422 (validation error)
        assert resp.status_code != 422

    def test_query_risposta_include_mode_field(self, monkeypatch):
        """QueryResponse deve sempre includere il campo 'mode'."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
        ctx = _mock_cursor_with_rows(_FAKE_ROWS)

        with patch("app.main.get_db_cursor", return_value=ctx), \
             patch("app.main.embed_text", return_value=([0.0] * 768, "dummy", 768)):

            resp = client.post("/api/v1/query", json={"query": "bandi"})

        assert resp.status_code == 200
        assert "mode" in resp.json()
```

---

## Task 2 — Crea `api/app/llm.py`

**File da creare:** `api/app/llm.py`

```python
# api/app/llm.py — LLM synthesis module (Ollama-compatible via OpenAI SDK)
import os
from typing import List, Dict

from openai import OpenAI


def generate_answer(query: str, chunks: List[Dict], model: str = None) -> str:
    """Genera risposta sintetica usando LLM Ollama-compatible (sync).

    Args:
        query:  domanda originale dell'utente
        chunks: lista di dict con chiave 'excerpt' (testo del chunk)
        model:  override modello (None = usa LLM_MODEL env)

    Returns:
        Testo della risposta generata dall'LLM.

    Raises:
        Exception: qualsiasi errore di rete/timeout/API — il chiamante decide il fallback.
    """
    # Legge configurazione da env per-call (monkeypatch-compatible)
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434") + "/v1"
    llm_model = model or os.environ.get("LLM_MODEL", "mistral-nemo:12b")
    timeout = float(os.environ.get("LLM_TIMEOUT_S", "30"))

    client = OpenAI(base_url=base_url, api_key="ollama", timeout=timeout)

    # Assembla contesto dai chunk recuperati
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(f"[{i}] {chunk['excerpt']}")
    context = "\n\n".join(context_parts)

    prompt = (
        "Rispondi alla domanda seguente basandoti ESCLUSIVAMENTE sui documenti forniti.\n"
        "Se non trovi informazioni sufficienti, rispondi: "
        "'Non ho trovato informazioni sufficienti nei documenti.'\n\n"
        f"Documenti:\n{context}\n\n"
        f"Domanda: {query}\n\n"
        "Risposta:"
    )

    response = client.chat.completions.create(
        model=llm_model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()
```

---

## Task 3 — Aggiorna `api/app/main.py`

**File da modificare:** `api/app/main.py`

### Step 3.1: Aggiungi import di `generate_answer` in cima al file

Modifica la riga degli import esistenti (aggiunge solo `generate_answer`):

```python
from .llm import generate_answer
```

Posizionamento: dopo `from .embedding import embed_text`.

### Step 3.2: Aggiungi campo `synthesize` a `QueryRequest`

```python
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query text")
    kb: Optional[str] = Field(None, description="Optional KB namespace to filter")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Number of results to return (1-20)")
    synthesize: Optional[bool] = Field(False, description="Se True, genera risposta sintetica via LLM")
```

### Step 3.3: Aggiungi campo `mode` a `QueryResponse`

```python
class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]
    mode: str = "retrieval_only"
```

### Step 3.4: Aggiorna il body del route `/api/v1/query`

Sostituisci il blocco `# Build response` fino alla fine del try con:

```python
        sources = parse_results(rows)

        # Synthesis branch
        mode = "retrieval_only"
        if not sources:
            answer = "No matching documents found."
        elif request.synthesize:
            try:
                answer = generate_answer(query=request.query, chunks=sources)
                mode = "synthesis"
            except Exception:
                answer = "Retrieval-only response. LLM non disponibile."
        else:
            answer = "Retrieval-only response. No LLM synthesis yet."

        return QueryResponse(answer=answer, sources=sources, mode=mode)
```

Il file `main.py` completo dopo le modifiche diventa:

```python
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
from .llm import generate_answer

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
    synthesize: Optional[bool] = Field(False, description="Se True, genera risposta sintetica via LLM")

class Source(BaseModel):
    id: str
    score: float
    kb_namespace: str
    source_path: Optional[str] = None
    excerpt: str

class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]
    mode: str = "retrieval_only"

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
    Query API - returns retrieval results, opzionalmente con synthesis LLM.

    Accepts:
    - query: search text (required, min_length=1)
    - kb: optional KB namespace to filter
    - top_k: number of results to return (default: 5, range: 1-20)
    - synthesize: if True, calls LLM to generate a synthetic answer (default: False)

    Returns:
    - answer: risposta LLM se synthesize=True, placeholder altrimenti
    - sources: list of matching chunks with metadata
    - mode: "synthesis" | "retrieval_only"
    """
    try:
        query_vec, model_name, dim = embed_text(request.query)

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

        # Synthesis branch
        mode = "retrieval_only"
        if not sources:
            answer = "No matching documents found."
        elif request.synthesize:
            try:
                answer = generate_answer(query=request.query, chunks=sources)
                mode = "synthesis"
            except Exception:
                answer = "Retrieval-only response. LLM non disponibile."
        else:
            answer = "Retrieval-only response. No LLM synthesis yet."

        return QueryResponse(answer=answer, sources=sources, mode=mode)

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


@app.post("/api/v1/upload")
def upload_files(
    kb: Optional[str] = Query(None),
    files: List[UploadFile] = File(...),
):
    """Carica uno o piu' file nella knowledge base specificata."""
    if not kb or not kb.strip():
        raise HTTPException(
            status_code=400,
            detail="Parametro kb obbligatorio. Specificare il namespace della knowledge base."
        )
    kb = kb.strip()

    inbox_root = os.environ.get("INBOX_ROOT", "/data/inbox")
    max_mb = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "50"))
    max_bytes = max_mb * 1024 * 1024

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

    kb_dir = Path(inbox_root) / kb
    kb_dir.mkdir(parents=True, exist_ok=True)

    saved_names = []
    saved_sizes = []
    for filename, content in validated:
        (kb_dir / filename).write_bytes(content)
        saved_names.append(filename)
        saved_sizes.append(len(content))

    upload_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

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
        pass  # audit log best-effort

    return UploadResponse(
        upload_id=upload_id,
        job_id=job_id,
        kb=kb,
        files=saved_names,
    )
```

---

## Task 4 — Verifica RED

```powershell
docker compose exec api pytest tests/test_llm_synthesis.py -v
```

Atteso: **tutti FAILED** — `ImportError: cannot import name 'generate_answer'` o simile.

---

## Task 5 — Rebuild e verifica GREEN

```powershell
# Rebuild (necessario per openai in requirements.txt + nuovo llm.py)
docker compose up -d --build

# Test nuovi
docker compose exec api pytest tests/test_llm_synthesis.py -v
# Atteso: 9 passed

# Regressione completa
docker compose exec api pytest tests/ -v
# Atteso: 33 passed (9 nuovi + 16 phase7 + 8 phase6/embedding)
```

---

## Task 6 — Commit

```powershell
git add api/app/llm.py
git add api/app/main.py
git add api/requirements.txt
git add docker-compose.yml
git add tests/test_llm_synthesis.py
git commit -m "feat(phase8): LLM synthesis via Ollama — synthesize=true flag, fallback retrieval_only"
```

---

## Verifica end-to-end manuale (post-commit, Ollama deve girare)

```powershell
# 1. Query retrieval-only (default)
Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/query' -Method POST `
  -ContentType 'application/json' `
  -Body '{"query":"bandi","top_k":3}'
# Atteso: mode="retrieval_only"

# 2. Query con synthesis (richiede Ollama + modello scaricato)
Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/query' -Method POST `
  -ContentType 'application/json' `
  -Body '{"query":"bandi 2026","top_k":3,"synthesize":true}'
# Atteso: mode="synthesis", answer con testo generato

# 3. Fallback — se Ollama non gira: stesso atteso mode="retrieval_only" senza errore HTTP
```

---

## Riferimenti file critici

| File | Azione |
|------|--------|
| `api/app/llm.py` | Crea — `generate_answer()` con OpenAI sync client |
| `api/app/main.py` | Modifica — import + `synthesize` in QueryRequest + `mode` in QueryResponse + synthesis branch |
| `tests/test_llm_synthesis.py` | Crea — 9 test TDD (3 unit + 6 integration) |
| `api/requirements.txt` | Modifica — aggiungi `openai>=1.0.0` |
| `docker-compose.yml` | Modifica — aggiungi `LLM_MODEL` e `LLM_TIMEOUT_S` |

---

## Pitfall critici da ricordare

1. **`openai.OpenAI` non `AsyncOpenAI`** — le route sono `def` sync
2. **`api_key="ollama"`** — richiesto dal client ma ignorato da Ollama
3. **Mock target**: `patch("app.main.generate_answer")` non `patch("app.llm.generate_answer")`
4. **`OLLAMA_BASE_URL + "/v1"`** — Ollama espone OpenAI-compatible API su `/v1`
5. **`except Exception: pass`** nel fallback — silenzioso by design, non loggare la query
6. **Rebuild obbligatorio** dopo aggiunta `openai` a requirements.txt
