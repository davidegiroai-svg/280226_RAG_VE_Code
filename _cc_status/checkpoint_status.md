# Checkpoint Status

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
