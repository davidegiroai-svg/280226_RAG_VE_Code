# Project Status Snapshot (post CC-05.2)

**Date:** 2026-03-02  
**Last Commit:** `610e100` — M0: CC-05.2 fix mojibake in ingest  
**Baseline:** M0 (multi-KB filesystem ingest → chunks → retrieval API; encoding + mojibake handling)

**Repository:** pushed to GitHub at `https://github.com/davidegiroai-svg/280226_RAG_VE_Code.git` (remote `origin`).

---

## Runnable Components

### ✅ Database (PostgreSQL + pgvector)
- **Status:** Initialized and healthy
- **Startup:** Automatic with `docker compose up -d`
- **Schema:** knowledge_base, documents, chunks, ingest_job, query_log
- **Embedding dim:** 1536 (pgvector)
- **Persistence:** Volume `pgdata` (survives recreate)

### ✅ API (FastAPI)
- **Status:** Live on `http://localhost:8000`
- **Startup:** Automatic with `docker compose up -d`
- **Endpoints:**
  - `GET /health` — DB connection health check (returns 503 if DB down)
  - `POST /api/v1/query` — Vector search & retrieval
    - Request: `{"query": "...", "kb": "...", "top_k": 5}`
    - Response: `{"answer": "...", "sources": [...]}`

### ⚙️ Worker (Filesystem Ingest)
- **Status:** On-demand only (profile: `manual`)
- **Startup:** NOT automatic (must explicitly request)
- **Encoding:**
  - Robust UTF-8 handling (utf-8-sig for BOM removal)
  - Fallback to utf-8 with errors=ignore
  - Safe for mixed-encoding text files
- **Supported formats:** .txt, .md, .csv, .json

---

## How to Run Locally

### Prerequisites
```powershell
# Required: Docker Desktop running
docker compose version
```

### 1. Initial Setup
```powershell
cp .env.example .env
# Edit .env if needed (default credentials: rag:rag_password_change_me)

docker compose up -d

# Wait ~30 seconds for DB initialization
Start-Sleep -Seconds 30

docker compose ps
```

### 2. Ingest Data (Manual Profile)
```powershell
# Ingest from /data/inbox/demo (namespace: "demo")
docker compose --profile manual run --rm worker --kb demo --path /data/inbox/demo

# Or custom path/namespace:
# docker compose --profile manual run --rm worker --kb my_kb --path /data/inbox/custom_folder
```

Expected output:
```json
{
  "kb": "demo",
  "path": "/data/inbox/demo",
  "files_found": N,
  "files_read": N,
  "documents_new": M,
  "documents_skipped_existing": K,
  "chunks_inserted": Z
}
```

### 3. Test Query (PowerShell)
```powershell
# Health check
curl http://localhost:8000/health

# Search query
$body = @{query = "bandi"; top_k = 3} | ConvertTo-Json
curl -X POST http://localhost:8000/api/v1/query `
  -Headers @{"Content-Type" = "application/json"} `
  -Body $body
```

### 4. Cleanup
```powershell
# Stop all services (keep volumes)
docker compose down

# Stop and remove all data
docker compose down -v
```

---

## Stato M0

- All components required for the minimal MVP are in place and runnable with a single `docker compose up -d` followed by a manual worker run.
- Encoding robustness now includes BOM stripping and heuristic mojibake repair (see ingest_fs.py).
- Worker remains under `manual` profile; it will not start with the default `up` command.
- Repository has been initialized and pushed to GitHub (`origin` remote).

---

## Notes

- **No full rebuild needed:** If only code changes (not schema), restart API:
  ```powershell
  docker compose restart api
  ```

- **DB reset if schema changes:**
  ```powershell
  docker compose down -v
  docker compose up -d
  ```

- **Worker encoding fallback:** Files with BOM or mixed encoding are handled gracefully

- **API is retrieval-only:** No LLM synthesis; responses are raw chunk excerpts + metadata
