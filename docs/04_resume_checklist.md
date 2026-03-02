# Resume Checklist (Ripartire Domani)

**Date:** 2026-03-02  
**Status:** Ready to restart from M0-CC-05.2 baseline (repo pushed to GitHub)

---

## Morning Startup (10 min)

### 1. Check Environment
```powershell
cd C:\Users\D.Giro\280226_RAG_VE_Code
docker compose version
docker ps -a
```

### 2. Start Services
```powershell
docker compose up -d

# Wait for DB healthcheck (~30 sec)
Start-Sleep -Seconds 30

# Verify all running
docker compose ps
```

### 3. Test API Health
```powershell
curl http://localhost:8000/health
# Expected: {"status":"ok","database":"connected"}
```

---

## Ingest Workflow

### If adding new data:
```powershell
# 1. Place files in ./data/inbox/<namespace>/
#    (e.g., ./data/inbox/demo/ for demo KB)

# 2. Run ingest (worker profile)
docker compose --profile manual run --rm worker --kb demo --path /data/inbox/demo

# 3. Wait for JSON output (shows docs_new, chunks_inserted)
```

### If reingesting same KB (e.g., after fixing documents):
```powershell
# Worker deduplicates by content_hash, so re-running is safe
# (Identical files → skipped; changed files → new chunks inserted)

docker compose --profile manual run --rm worker --kb demo --path /data/inbox/demo
```

---

## Test Query

```powershell
# PowerShell syntax
$body = @{query = "search term"; top_k = 3} | ConvertTo-Json

curl -X POST http://localhost:8000/api/v1/query `
  -Headers @{"Content-Type" = "application/json"} `
  -Body $body
```

---

## Troubleshooting

### ❌ DB fails to start
```powershell
# Check logs
docker compose logs db

# Reset (WARNING: deletes all data)
docker compose down -v
docker compose up -d
```

### ❌ API 503 (service unavailable)
```powershell
# DB not healthy yet
docker compose logs api

# Wait 30+ seconds, restart api
docker compose restart api
```

### ❌ Worker fails with import error
```powershell
# Ensure docker-compose.yml has correct entrypoint:
# entrypoint: ["python", "-m", "app.ingest_fs"]

# Rebuild if docker-compose.yml changed:
docker compose up -d --build
```

### ❌ Ingest shows "0 files found"
```powershell
# Check file path:
# - Correct format: /data/inbox/<namespace>/
# - Files must be: .txt, .md, .csv, .json

# Verify from host (Windows path):
dir ".\data\inbox\demo"
```

### ❌ Host path not visible inside container
```powershell
# Windows absolute paths (C:\Users\...) are not mounted; worker looks under /data.
# Convert or move files into the mapped directory, e.g.:
#   C:\Users\...\project\data\inbox\demo -> /data/inbox/demo inside container
# Use Docker Desktop file sharing or ensure volume mount covers that location.
```

### ❌ Ingest encoding issue (BOM or mixed UTF-8)
```
# Worker handles this automatically:
# - Tries utf-8-sig (removes BOM)
# - Falls back to utf-8 with errors=ignore
# - Strips \ufeff explicitly

# If still failing: check file for NUL bytes or binary content
```

### ❌ Worker profile not recognized
```powershell
# Verify docker-compose.yml has:
# worker:
#   ...
#   profiles:
#     - manual

# Required syntax: --profile manual (not --profile=manual)
docker compose --profile manual run --rm worker --kb demo --path /data/inbox/demo
```

---

## Key Commands (Copy-Paste)

```powershell
# Full reset + restart
docker compose down -v
docker compose up -d
Start-Sleep -Seconds 30

# Ingest demo KB
docker compose --profile manual run --rm worker --kb demo --path /data/inbox/demo

# Query
curl -X POST http://localhost:8000/api/v1/query `
  -Headers @{"Content-Type" = "application/json"} `
  -Body '{"query":"bandi","top_k":3}'

# Stop
docker compose down
```

---

## What's Working

✅ DB init (pgvector, extensions, schema)  
✅ API endpoints (/health, /api/v1/query)  
✅ Filesystem ingest with encoding hardening  
✅ Vector search (pgvector + ORDER BY POSITION)  
✅ Deduplication by content_hash  
✅ Worker manual profile (on-demand only)  

## What's NOT Yet

❌ LLM synthesis (retrieval-only for now)  
❌ Multi-model embeddings  
❌ Auth/RBAC  
❌ Query caching
