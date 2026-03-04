# Milestones

## v1.0 — Core RAG Pipeline (COMPLETED 2026-03-03)

**Goal:** Bootstrap sistema RAG funzionante end-to-end: DB, API, embedding, ingest.

**Shipped:**
- Schema PostgreSQL 16 + pgvector vector(768) + indice ivfflat coseno
- FastAPI: GET /health, POST /api/v1/query con QueryResponse
- EmbeddingAdapter: Ollama (nomic-embed-text) + dummy deterministico
- Ingest worker CLI: TXT/MD/CSV/JSON, chunking 1200/200, dedup, encoding robusto
- Vector similarity search: cosine distance → score [0..1]
- Docker Compose: db, api, worker (manual profile)
- Runbook italiano + test pytest sincronizzati

**Last phase:** 5 (M1_TASK_05_Runbook+Hardening)

**Commits:** ef0dc9e (query vector search), 70e5983 (embeddings+ingest), bc9eed6 (DB schema), 14c7b91 (hardening)

---

## v2.0 — PDF + Upload + LLM + Watcher + Hybrid + Auth (COMPLETED 2026-03-04) 🏁

**Started:** 2026-03-03

**Goal:** Aggiungere ingest PDF, upload API, sintesi LLM, watcher automatico, ricerca ibrida e autenticazione base.

**Status:** Phase 6 COMPLETED (2026-03-03)
**Next:** Phase 7 — Upload API (IN PROGRESS)

### Phase 6: PDF Ingest (COMPLETED 2026-03-03)
- Integrazione `pymupdf4llm` per parsing PDF
- Metadata `page_start`, `page_end` salvati su DB
- Chunking intelligente per pagina (`page_chunks=True`)
- Test suite: `test_ingest_pdf.py` (8/8 passed)

---

## Phase 7 — Upload API (IN PROGRESS)

**Started:** 2026-03-03
**Goal:** Endpoint POST /upload per caricamento file tramite API + gestione KB.
**Status:** Phase 7 COMPLETED (2026-03-03)
**Next:** Phase 8 — LLM Synthesis (IN PROGRESS)

### Phase 7: Upload API (COMPLETED 2026-03-03)
- Endpoint `POST /upload` con validazione multipart, max size (413) e tipo (415)
- Endpoint `GET /kbs` per listing knowledge bases con conteggio documenti
- Endpoint `GET /health/ready` per monitoraggio dipendenze (DB)
- Error handling centralizzato e robusto
- Test suite: `test_upload_api.py` (24/24 passed)

---

## Phase 8 — LLM Synthesis (IN PROGRESS)

**Started:** 2026-03-03
**Goal:** Generazione risposte via LLM con parametro `synthesize=true` e fallback retrieval-only.
**Requirements:** LLM-01, LLM-02, LLM-03
**Status:** Phase 8 COMPLETED (2026-03-04)
**Next:** Phase 9 — Watcher (PLANNING)

### Phase 8: LLM Synthesis (COMPLETED 2026-03-04)
- Modulo `api/app/llm.py` con `synthesize_answer()` via Ollama `/api/chat`
- Parametro `synthesize=true` nel POST /api/v1/query
- Fallback graceful: se Ollama non disponibile → solo sources
- Env vars: `OLLAMA_LLM_MODEL`, `LLM_TIMEOUT_S`
- Test suite: `test_llm_synthesis.py` (10 test, 34 totali passed)

---

## Phase 9 — Watcher (PLANNING)

**Started:** 2026-03-04
**Goal:** Watcher automatico su filesystem per auto-ingest e delete propagation.
**Requirements:** WTCH-01, WTCH-02, WTCH-03, WTCH-04
**Status:** Phase 9 COMPLETED (2026-03-04)
**Next:** Phase 10 — Hybrid Search (PLANNING)

### Phase 9: Watcher (COMPLETED 2026-03-04)
- `api/app/watcher.py`: KBWatcher con `watchdog.PollingObserver` (polling 2s)
- Handler auto-ingest su file created + soft delete su file removed
- Migration SQL: colonne `is_deleted`, `deleted_at`, `ingest_status` su documents
- Endpoint `GET /api/v1/documents?kb=<ns>` per listing documenti con status
- Service Docker `watcher` (profilo separato, avvio manuale)
- Test suite: `test_watcher.py` (21 test, 55 totali passed)

---

## Phase 10 — Hybrid Search (PLANNING)

**Started:** 2026-03-04
**Goal:** Ricerca ibrida tsvector + BM25 + RRF per migliorare recall e precision.
**Requirements:** HYBR-01, HYBR-02, HYBR-03
**Status:** Phase 10 COMPLETED (2026-03-04)
**Next:** Phase 11 — Auth (PLANNING) — LAST PHASE!

### Phase 10: Hybrid Search (COMPLETED 2026-03-04)
- Migration SQL: `testo_tsv TSVECTOR` + GIN index + trigger auto-update
- Modulo `api/app/hybrid.py` con `fts_search()` + `rrf_merge()` (RRF k=60)
- Parametro `search_mode` in QueryRequest: vector (default), fts, hybrid
- Test suite: `test_hybrid_search.py` (23 test, 78 totali passed)

---

## Phase 11 — Auth (PLANNING) — ULTIMA FASE M2

**Started:** 2026-03-04
**Goal:** Autenticazione base con API key per proteggere tutti gli endpoint.
**Requirements:** AUTH-01, AUTH-02, AUTH-03, AUTH-04
**Status:** Phase 11 COMPLETED (2026-03-04) — M2 v2.0 DONE!

### Phase 11: Auth (COMPLETED 2026-03-04)
- Tabella `api_keys` con hash SHA-256, scadenza, revoca
- Middleware `require_api_key` su tutti gli endpoint `/api/v1/*`
- `/health` e `/health/ready` sempre pubblici
- CLI `manage_keys` per creare/revocare/listare API keys
- `AUTH_ENABLED` env var per disabilitare in dev
- Test suite: `test_auth.py` (24 test, **102 totali passed**)

---

## 🏆 Milestone v2.0 — RIEPILOGO FINALE

**Completata:** 2026-03-04
**Fasi:** 6/6 | **Requirements:** 25/25 | **Test:** 102 passed
**Tempo totale M2:** ~2 ore di implementazione effettiva

| Fase | Componente | Test |
|------|-----------|------|
| Phase 6 | PDF Ingest (pymupdf4llm) | 8 |
| Phase 7 | Upload API + KB management | 24 |
| Phase 8 | LLM Synthesis (Ollama) | 10 |
| Phase 9 | Watcher (auto-ingest + soft delete) | 21 |
| Phase 10 | Hybrid Search (tsvector + RRF) | 23 |
| Phase 11 | Auth (API key SHA-256) | 24 |
| **Totale** | | **102** |

---

## v3.0 — Frontend Web (COMPLETED 2026-03-04) 🏁

**Started:** 2026-03-04
**Completed:** 2026-03-04
**Commit:** a7dc621

**Goal:** Interfaccia web in italiano per utenti non tecnici: ricerca documenti, upload file, gestione Knowledge Base.

**Stack:** Vite 5 + React 18 + TypeScript + Tailwind CSS 3 + nginx (Docker multi-stage)

**Shipped:**
- 4 pagine: Ricerca, Upload, Documenti, Knowledge Base
- 8 componenti riutilizzabili (SearchBar, SearchResult, FileUpload, KBSelector, etc.)
- Proxy nginx con iniezione automatica API key
- Integrazione Docker: `docker compose up -d --build frontend` → http://localhost:3000
- 17 task completati, 29 file, 1319 righe di codice

---
