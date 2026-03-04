# Checkpoint Status

**Checkpoint updated:** 2026-03-03T10:00:00 by M1_TASK_06_Final_Check

## TASK CC-01 — Bootstrap Repo + Audit Wrapper
**Status:** DONE
**Timestamp:** 2026-02-28T15:08:36
**Report:** docs/00_repo_audit.md
**Audit Directory:** _cc_status/audit/latest/

### Output Files Created:
- `_cc_status/audit/latest/repo_tree.txt`
- `_cc_status/audit/latest/git_status.txt`
- `_cc_status/audit/latest/risky_paths.txt`
- `_cc_status/audit/latest/audit_summary.json`

---

## TASK CC-02 — Initialize Git repo + .gitignore + first commit
**Status:** DONE
**Timestamp:** 2026-02-28T15:10:00
**Git:** initialized on branch master, commit 3ba729f
**Command:** `git init && git add . && git commit -m "M0 bootstrap: audit + docs baseline"`

---

## TASK CC-03 — Docker Compose (DB pgvector) + db_init.sql + env template + runbook
**Status:** DONE
**Timestamp:** 2026-02-28T15:48:00
**Files Created:**
- `docker-compose.yml` (service db with pgvector, volume, healthcheck, init mount)
- `scripts/db_init.sql` (estensioni: vector, pgcrypto; tabelle: knowledge_base, documents, chunks, ingest_job, query_log)
- `.env.example` (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT)
- `docs/10_run_local.md` (istruzioni per avvio locale)

**Schema DB:** 1536-dim vector per embedding

---

## TASK CC-03.1 — Hardening minimo Compose + Runbook
**Status:** DONE
**Timestamp:** 2026-02-28T16:00:00
**Changes:**
- Rimossa `POSTGRES_PORT` dall'environment del container
- Corretto commento fallback in docker-compose.yml
- Aggiunti comandi Windows/PowerShell in runbook
- Aggiunta nota su reset DB se cambiano credenziali

---

## TASK CC-04 — API skeleton (FastAPI) + DB connectivity + Query stub
**Status:** DONE
**Timestamp:** 2026-02-28T16:10:00
**Files Created:**
- `api/Dockerfile` (Python 3.11 slim, FastAPI, psycopg2-binary)
- `api/requirements.txt` (fastapi, uvicorn, psycopg2-binary, pydantic)
- `api/app/main.py` (endpoints /health, POST /api/v1/query)
- `api/app/db.py` (DB connection helpers)
- `api/app/query.py` (query logic and search)

**Changes to existing:**
- `docker-compose.yml` (aggiunto service api su porta 8000, depends_on db)
- `docs/10_run_local.md` (aggiunti comandi curl per test API)

---

## TASK CC-04.1 — Fix naming modules + query robustness
**Status:** DONE
**Timestamp:** 2026-02-28T16:15:00
**Changes:**
- `api/app/query.py`: type hint corretto `-> tuple[str, list]`, excerpt limitato a 800 chars
- `api/app/main.py`: pydantic validation per query (min_length=1), top_k (1-20)
- `api/Dockerfile`: già corretto (`app.main:app`)

**Nota:** Api endpoint endpoint sync (non async) per compatibilità con psycopg2

---

## TASK CC-04.2 — Align response schema to SRS + improve ranking + health semantics
**Status:** DONE
**Timestamp:** 2026-02-28T16:20:00
**Changes:**
- `api/app/main.py`: Source.source_uri → source_path, /health HTTP 503 quando db_ok=false
- `api/app/query.py`: source_uri → source_path, ORDER BY POSITION per ranking
- `docs/10_run_local.md`: aggiornato example output con source_path

---

## TASK M1_TASK_01_DB — pgvector schema per Vector Search
**Status:** DONE
**Timestamp:** 2026-03-02T13:57:00
**Changes:**
- `scripts/db_init.sql`: embedding changed from `vector(1536)` to `vector(768)`
- `scripts/db_init.sql`: aggiunto indice `idx_chunks_embedding_ivfflat` con `vector_cosine_ops`
- `docs/10_run_local.md`: aggiunta sezione "5. Embedding (vector search)"
- Verifica: DB re-init completato, schema verificato (`docker compose exec db psql ... \d chunks`)

---

## TASK CC-05.2 — Fix mojibake in ingest (UTF-8/Latin1 repair)
**Status:** DONE
**Timestamp:** 2026-03-02T11:00:00
**Changes:**
- `api/app/ingest_fs.py`: aggiunta heuristics repair per mojibake (`Ã`/`Â` -> caratteriaccentati)
- Verifica: query API restituisce "Questo è" invece di "Questo Ã¨"
- Commit: `610e100`, Push: OK su origin/master

---

## TASK CC-05.1 — Hardening ingest encoding + worker profile
**Status:** DONE
**Timestamp:** 2026-03-02T12:00:00
**Changes:**
- `api/app/ingest_fs.py`: gestione encoding robusta con `utf-8-sig` per rimuovere BOM
- `docker-compose.yml`: worker con `profiles: ["manual"]` per avvio solo su richiesta
- `docs/10_run_local.md`: sezione ingest con PowerShell examples + nota encoding/BOM

---

*Checkpoint updated by TASK CC-01*
*Checkpoint updated by TASK CC-02*
*Checkpoint updated by TASK CC-03*
*Checkpoint updated by TASK CC-03.1*
*Checkpoint updated by TASK CC-04*
*Checkpoint updated by TASK CC-04.1*
*Checkpoint updated by TASK CC-04.2*
*Checkpoint updated by TASK CC-05.1*
*Checkpoint updated by TASK CC-05.2*
*Checkpoint updated by TASK M1_TASK_01_DB*
*Checkpoint updated by TASK M1_TASK_02_EmbeddingAdapter*
*Checkpoint updated by TASK M1_TASK_03_Ingest_SaveEmbedding*
*Checkpoint updated by TASK M1_TASK_04_Query_VectorSearch*
*Checkpoint updated by TASK M1_TASK_05_Runbook+Hardening*
*Checkpoint updated by TASK M1_TASK_06_Final_Check*

---

## TASK M1_TASK_04_Query_VectorSearch — vector similarity search in API
**Status:** DONE
**Timestamp:** 2026-03-02T18:30:00
**Changes:**
- `api/app/query.py`: import `embed_text` from `.embedding`
- `api/app/query.py`: aggiunta funzione `vector_to_str()` per convertire liste Python in PostgreSQL vector string format
- `api/app/query.py`: modifica `build_query_sql()` per usare pgvector cosine similarity (`embedding <=> %s`)
- `api/app/query.py`: modifica `parse_results()` per calcolare `score = 1.0 - distance`
- `api/app/main.py`: import `embed_text`, calcolo embedding query in `query_api()`
- `docs/10_run_local.md`: aggiunta sezione "7. Vector Search Query API" con esempi PowerShell/CLI

**Verification:**
```powershell
# Windows/PowerShell
$response = Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/query' -Method POST -ContentType 'application/json' -Body '{"query": "bandi", "top_k": 3, "kb": "demo"}'
$response.sources | Select-Object id, score, source_path
```

**Esempio Output:**
```json
{
  "id": "c6350ed7-4617-48f2-816f-ed7892cbf223",
  "score": 0.413,
  "source_path": "/data/inbox/demo/test_mojibake.txt"
},
{
  "id": "627dcd6f-0b2a-4a2d-ad08-a6e1e66354c8",
  "score": 0.366,
  "source_path": "/data/inbox/demo/demo2.txt"
},
{
  "id": "c68a4fa2-4837-480d-a219-f800f2ce0196",
  "score": 0.365,
  "source_path": "/data/inbox/demo/demo.txt"
}
```

---

## TASK M1_TASK_05_Runbook+Hardening — Vector query hardening
**Status:** DONE
**Timestamp:** 2026-03-02T22:05:00
**Changes:**
- `api/app/query.py`: clamp score a [0..1] con `max(0.0, 1.0 - distance)`
- `api/app/query.py`: SQL semplificato con single vector parameter, ORDER BY distance ASC
- `api/app/query.py`: `vector_to_str()` senza spazi dopo virgola
- `docker-compose.yml`: aggiunte env vars embedding per api e worker
- `docs/10_run_local.md`: fix doppia numerazione "## 6"
- `docs/10_run_local.md`: fix mojibake chars (similarità, �� -> accented)
- `docs/10_run_local.md`: aggiunto snippet env vars embedding PowerShell

**Verification:**
```bash
docker compose up -d --build
docker compose run --rm worker --kb demo --path /data/inbox/demo
$response = Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/query' -Method POST -ContentType 'application/json' -Body '{"query": "bandi", "top_k": 3, "kb": "demo"}'
# Verify: score >= 0, sources ordered by score desc
```

---

## TASK M1_TASK_03_Ingest_SaveEmbedding — embedding vector storage in chunks
**Status:** DONE  
**Timestamp:** 2026-03-02

**Changes:**
- `api/app/ingest_fs.py`: batch embedding via `embed_texts()` (import da `app.embedding`)
- `api/app/ingest_fs.py`: insert su `chunks.embedding`, `chunks.embedding_model`, `chunks.embedding_dim`
- `api/app/ingest_fs.py`: conversione embedding list -> stringa pgvector con `vector_to_str()`

**Verification (example):**
- `docker compose run --rm worker --kb test_kb --path /data/inbox/demo`
- `SELECT COUNT(*) FROM chunks WHERE kb_namespace='test_kb' AND embedding IS NOT NULL;`  (expected > 0)
- `SELECT embedding_model, embedding_dim, COUNT(*) FROM chunks WHERE kb_namespace='test_kb' AND embedding IS NOT NULL GROUP BY 1,2;`

---

## TASK M1_TASK_05_Runbook+Hardening — Runbook updates + security hardening
**Status:** DONE
**Timestamp:** 2026-03-02T22:00:00

**Changes:**
- `docs/10_run_local.md`: aggiunta sezione "8. Security Hardening" con best practices
- `docs/10_run_local.md`: aggiunta sezione "9. Environment Variable Management" con spiegazione POSTGRES_* variabili
- `docker-compose.yml`: aggiunto commento esplicativo su variabili d'ambiente non esposte al container
- `docker-compose.yml`: aggiunta nota su ` profiles: ["manual"]` per worker service
- `api/.env.example`: rimossa `POSTGRES_PORT` (non necessaria per internal networking)
- `docs/10_run_local.md`: aggiornato esempio `.env` senza POSTGRES_PORT

---

## TASK M2_PHASE6_PDF_INGEST — PDF ingest implementation
**Status:** DONE
**Timestamp:** 2026-03-03

**Changes:**
- `api/requirements.txt`: aggiunto pymupdf4llm>=0.0.17, pytest>=8.0.0, httpx>=0.27.0
- `api/app/ingest_fs.py`: nuova funzione `read_pdf_chunks(p)` con pymupdf4llm page_chunks=True
- `api/app/ingest_fs.py`: `list_files()` esteso con estensione `.pdf`
- `api/app/ingest_fs.py`: `insert_chunks()` esteso con kwarg `file_path` — branch PDF salva page_start/page_end/section_title come colonne dedicate
- `api/app/ingest_fs.py`: `main()` aggiornato — hash binario per PDF, passa file_path a insert_chunks
- `docker-compose.yml`: aggiunto volume `./tests:/app/tests:ro` per eseguire pytest nel container
- `tests/conftest.py`: aggiunto per configurare sys.path in Docker
- `tests/test_ingest_pdf.py`: 7 test TDD (tutti PASSED)

**Verification:**
```bash
docker compose exec api pytest tests/ -v
# 8 passed in 0.44s
```

---

## TASK M1_TASK_06_Final_Check — M1 closure
**Status:** DONE
**Timestamp:** 2026-03-03

**Changes:**
- `api/app/query.py`: fix params bug (kb_namespace optional)
- `_cc_status/checkpoint_status.md`: cleanup duplicate M1_TASK_05, aggiunta M1_TASK_06

**Verification:**
```bash
# End-to-end test
docker compose up -d --build
docker compose --profile manual run --rm worker --kb demo --path /data/inbox/demo
docker compose exec db psql -U rag -d rag -c "SELECT COUNT(*) FROM chunks WHERE kb_namespace='demo' AND embedding IS NOT NULL;"
# Query API con KB
# Query API senza KB (kb=null)

---

## Phase 6 — PDF Ingest Completion
**Status:** DONE
**Timestamp:** 2026-03-03T22:55:00
**Milestone v2.0 Progress:** 1 of 6 phases completed
**Changes:**
- `api/app/ingest_fs.py`: aggiunta `read_pdf_chunks`
- `scripts/db_init.sql`: aggiunte colonne `page_start`, `page_end`
- `tests/test_ingest_pdf.py`: 8 test unitari completati
- `api/requirements.txt`: aggiunta `pymupdf4llm`

```
---

## Phase 9 — Watcher Completion
**Status:** DONE
**Timestamp:** 2026-03-04T10:30:00
**Milestone v2.0 Progress:** 4 of 6 phases completed (66%)
**Requirements Completed:** WTCH-01, WTCH-02, WTCH-03, WTCH-04
**Changes:**
- `scripts/migration_m2_watcher.sql`: ADD COLUMN IF NOT EXISTS is_deleted/deleted_at/ingest_status + indici
- `scripts/db_init.sql`: aggiornato con nuove colonne per fresh installs
- `api/requirements.txt`: aggiunto watchdog>=4.0.0
- `api/app/ingest_fs.py`: nuove funzioni `update_ingest_status()` e `ingest_single_file()`
- `api/app/watcher.py`: KBWatcher + InboxHandler + soft_delete_document() con PollingObserver
- `api/app/main.py`: nuovo endpoint GET /api/v1/documents con filtri kb/status/deleted
- `docker-compose.yml`: service watcher (profiles: watcher, restart: unless-stopped)
- `tests/test_watcher.py`: 21 test TDD (tutti PASSED) — 55 totali

**Verification:**
```bash
docker compose exec api pytest tests/ -v
# 55 passed in 5.61s
```

**Avvio watcher manuale:**
```powershell
docker compose --profile watcher up -d watcher
docker compose logs -f watcher
```

---

## Phase 11 — Auth Completion (M2 COMPLETE!)
**Status:** DONE
**Timestamp:** 2026-03-04T13:00:00
**Milestone v2.0 Progress:** 6/6 phases completed — M2 DONE!
**Requirements Completed:** AUTH-01, AUTH-02, AUTH-03, AUTH-04

**Changes:**
- `scripts/migration_m2_auth.sql`: CREATE TABLE api_keys (key_hash SHA-256, is_active, expires_at) + indici
- `api/app/auth.py`: hash_api_key() + verify_api_key() + require_api_key() Depends
- `api/app/main.py`: Depends(require_api_key) su tutti gli endpoint /api/v1/*
- `api/app/manage_keys.py`: CLI create/revoke/list API keys
- `docker-compose.yml`: env var AUTH_ENABLED al service api
- `.env.example`: aggiunta AUTH_ENABLED=true
- `tests/conftest.py`: autouse fixture disable_auth_by_default (AUTH_ENABLED=false per test)
- `tests/test_auth.py`: 24 test TDD (tutti PASSED) — 102 totali

**Verification:**
```bash
docker compose exec api pytest tests/ -v
# 102 passed in 2.41s
```

**Creare una API key:**
```powershell
docker compose exec api python -m app.manage_keys create --name "app-frontend"
# Output: X-API-Key: <uuid-raw> — salvare questo valore!
```

**Usare la API key:**
```powershell
$headers = @{"X-API-Key" = "<uuid-raw>"}
Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/query' -Method POST -ContentType 'application/json' -Headers $headers -Body '{"query": "bando"}'
```

---

## Milestone v2.0 — COMPLETATA
**Data:** 2026-03-04
**Fasi:** 6/6 completate (Phase 6-11)
**Requirements:** 25/25 completati (PDF-01..04, UPLD-01..07, API-01..02, LLM-01..03, WTCH-01..04, HYBR-01..03, AUTH-01..04)
**Test:** 102 test totali, tutti PASSED
**Componenti aggiunti:**
- PDF ingest (pymupdf4llm, page chunks)
- Upload API (POST /upload, GET /kbs, GET /health/ready)
- LLM synthesis (Ollama /api/chat, fallback graceful)
- Watcher (PollingObserver, auto-ingest, soft delete, GET /documents)
- Hybrid search (tsvector + RRF k=60, search_mode vector/fts/hybrid)
- Auth (API key X-API-Key, SHA-256 hash, manage_keys CLI)

---

## Phase 10 — Hybrid Search Completion
**Status:** DONE
**Timestamp:** 2026-03-04T12:00:00
**Milestone v2.0 Progress:** 5 of 6 phases completed (83%)
**Requirements Completed:** HYBR-01, HYBR-02, HYBR-03
**Changes:**
- `scripts/migration_m2_hybrid.sql`: ADD COLUMN testo_tsv TSVECTOR + GIN index + trigger auto-update
- `api/app/hybrid.py`: nuovo modulo con `fts_search()` + `rrf_merge()` (k=60)
- `api/app/query.py`: import fts_search/rrf_merge, nuova funzione `execute_search()` con search_mode
- `api/app/main.py`: campo `search_mode` in QueryRequest (vector/fts/hybrid), usa execute_search()
- `tests/test_hybrid_search.py`: 23 test TDD (tutti PASSED) — 78 totali

**Verification:**
```bash
docker compose exec api pytest tests/ -v
# 78 passed in 2.27s
```

**Uso con curl/PowerShell:**
```powershell
# Hybrid search
$body = '{"query": "bando venezia", "search_mode": "hybrid", "top_k": 5}'
Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/query' -Method POST -ContentType 'application/json' -Body $body

# Full-text search only
$body = '{"query": "bando venezia", "search_mode": "fts", "top_k": 5}'
Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/query' -Method POST -ContentType 'application/json' -Body $body
```

---

## Phase 8 — LLM Synthesis Completion
**Status:** DONE
**Timestamp:** 2026-03-04T09:30:00
**Milestone v2.0 Progress:** 3 of 6 phases completed (50%)
**Requirements Completed:** LLM-01, LLM-02, LLM-03
**Changes:**
- `api/app/llm.py`: nuova funzione `synthesize_answer(query, chunks, model)` via Ollama /api/chat
- `api/app/main.py`: parametro `synthesize: bool = False` in QueryRequest; chiama `synthesize_answer()` se True
- `docker-compose.yml`: env vars `OLLAMA_LLM_MODEL`, `LLM_TIMEOUT_S` aggiunte al service api
- `.env.example`: aggiunte `OLLAMA_LLM_MODEL=llama3.2`, `LLM_TIMEOUT_S=30`
- `tests/test_llm_synthesis.py`: 10 test TDD (5 unitari + 5 integrazione API), tutti PASSED

**Verification:**
```bash
docker compose exec api pytest tests/ -v
# 34 passed in 2.78s
```

**Esempio uso:**
```powershell
$body = '{"query": "bandi", "top_k": 3, "synthesize": true}'
Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/query' -Method POST -ContentType 'application/json' -Body $body
# Se Ollama disponibile con llama3.2: answer sintetica in italiano
# Se Ollama non disponibile: answer = "Retrieval-only response." + sources
```

---

## Phase 7 — Upload API Completion
**Status:** DONE
**Timestamp:** 2026-03-03T23:18:00
**Milestone v2.0 Progress:** 2 of 6 phases completed (33.33%)
**Requirements Completed:** 
- Phase 6: PDF-01, PDF-02, PDF-03, PDF-04
- Phase 7: UPLD-01, UPLD-02, UPLD-03, UPLD-04, UPLD-05, API-01, API-02
**Requirements Remaining:** 
- LLM-01, LLM-02, LLM-03 (Phase 8), WTCH-01, WTCH-02, WTCH-03, WTCH-04 (Phase 9), HYBR-01, HYBR-02, HYBR-03 (Phase 10), AUTH-01, AUTH-02, AUTH-03, AUTH-04 (Phase 11)
**Changes:**
- `api/app/main.py`: nuovi endpoint `/upload`, `/kbs`, `/health/ready`
- `api/app/schemas.py`: `UploadResponse`, `KBListResponse`
- `api/app/storage.py`: business logic per salvataggio file su disco
- `tests/test_upload_api.py`: 24 test unitari e di integrazione (tutti PASSED)
