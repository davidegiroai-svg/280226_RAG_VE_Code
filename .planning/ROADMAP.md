# Roadmap: RAG Multi-KB — Comune di Venezia

## Milestones

- [x] **v1.0 Core RAG Pipeline** - Phases 1-5 (shipped 2026-03-03)
- [ ] **v2.0 PDF + Upload + LLM + Watcher + Hybrid + Auth** - Phases 6-11 (in progress)

## Phases

<details>
<summary>v1.0 Core RAG Pipeline (Phases 1-5) — SHIPPED 2026-03-03</summary>

Phases 1-5 delivered the end-to-end RAG pipeline: PostgreSQL+pgvector schema, FastAPI /health + /query, Ollama embedding adapter, ingest worker for TXT/MD/CSV/JSON, vector similarity search, Docker Compose stack, and runbook.

</details>

### v2.0 PDF + Upload + LLM + Watcher + Hybrid + Auth (In Progress)

**Milestone Goal:** Aggiungere ingest PDF, upload API, sintesi LLM, watcher automatico, ricerca ibrida e autenticazione base.

- [ ] **Phase 6: PDF Ingest** - Worker CLI esteso per ingest PDF con metadata pagina
- [ ] **Phase 7: Upload API + Endpoint Aggiuntivi** - POST /upload, GET /kbs, GET /health/ready
- [ ] **Phase 8: LLM Synthesis** - Risposta sintetica via Ollama con parametro synthesize=true
- [ ] **Phase 9: File Watcher** - Servizio Docker persistente che monitora inbox e propaga le eliminazioni
- [ ] **Phase 10: Hybrid Search** - Ricerca ibrida BM25 + vettoriale con RRF
- [ ] **Phase 11: Authentication** - JWT RBAC base (admin/user) applicato agli endpoint

## Phase Details

### Phase 6: PDF Ingest
**Goal**: Il worker CLI ingerisce file PDF estraendo testo per pagina con metadata di paginazione
**Depends on**: Phase 5 (M1 complete)
**Requirements**: PDF-01, PDF-02, PDF-03, PDF-04
**Success Criteria** (what must be TRUE):
  1. User can run the worker CLI with --path pointing to a folder containing PDF files and chunks are stored in DB
  2. Each PDF chunk in the DB has page_start and page_end values matching the source page number
  3. Ingesting the same PDF twice produces no duplicate chunks (UNIQUE kb_id+content_hash enforced)
  4. Worker processes PDFs and TXT/MD/CSV/JSON in the same run without errors
**Plans**: TBD

### Phase 7: Upload API + Endpoint Aggiuntivi
**Goal**: Gli utenti possono caricare file via REST e consultare la lista delle knowledge base e lo stato del DB
**Depends on**: Phase 6
**Requirements**: UPLD-01, UPLD-02, UPLD-03, UPLD-04, UPLD-05, API-01, API-02
**Success Criteria** (what must be TRUE):
  1. User can POST one or more files to /api/v1/upload?kb=<namespace> and receive upload_id, job_id, kb, and file paths in response
  2. Upload endpoint accepts .pdf .txt .md .csv .json and rejects all other types with HTTP 415
  3. Upload endpoint rejects files exceeding MAX_UPLOAD_SIZE_MB with HTTP 413
  4. GET /api/v1/kbs returns a list of knowledge bases with doc_count and chunk_count for each
  5. GET /health/ready returns 200 when DB is connected and vector extension is present, 503 with detail otherwise
**Plans**: TBD

### Phase 8: LLM Synthesis
**Goal**: Le query possono produrre risposte in linguaggio naturale generate da Ollama a partire dai chunk recuperati
**Depends on**: Phase 7
**Requirements**: LLM-01, LLM-02, LLM-03
**Success Criteria** (what must be TRUE):
  1. User can send POST /api/v1/query with synthesize=true and receive a natural-language answer field in the response
  2. When Ollama LLM is available, the answer field contains a synthesized response based on the retrieved chunks
  3. When synthesize=false or Ollama LLM is unavailable, the query returns the retrieval-only answer without error
**Plans**: TBD

### Phase 9: File Watcher
**Goal**: Il sistema ingesta automaticamente i file nuovi e propaga le eliminazioni senza intervento manuale
**Depends on**: Phase 6
**Requirements**: WTCH-01, WTCH-02, WTCH-03, WTCH-04
**Success Criteria** (what must be TRUE):
  1. A new file dropped into /data/inbox/<kb>/ is automatically ingested within WATCHER_POLL_SECONDS without any manual command
  2. When a file is removed from /data/inbox/<kb>/, its document is marked as deleted in the DB and its chunks are removed
  3. The watcher service restarts automatically after Docker daemon restart (restart: unless-stopped)
  4. The watcher operates correctly on Docker+Windows using PollingObserver (no inotify dependency)
**Plans**: TBD

### Phase 10: Hybrid Search
**Goal**: Le query combinano similarita vettoriale e ricerca full-text BM25 per risultati piu accurati
**Depends on**: Phase 9
**Requirements**: HYBR-01, HYBR-02, HYBR-03
**Success Criteria** (what must be TRUE):
  1. POST /api/v1/query returns results ranked by a combined RRF score (k=60) that blends vector similarity and BM25
  2. The chunks table has a tsvector index on the testo column that powers full-text search queries
  3. Sources in the query response carry a score field reflecting the combined RRF rank, returned in descending order
**Plans**: TBD

### Phase 11: Authentication
**Goal**: Gli endpoint API sono protetti da JWT RBAC con ruoli admin e user
**Depends on**: Phase 10
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04
**Success Criteria** (what must be TRUE):
  1. System issues a JWT token for admin or user role upon login, and the token is accepted for subsequent requests
  2. POST /api/v1/upload returns 401/403 when called without a valid admin token
  3. POST /api/v1/query and GET /api/v1/kbs return 401/403 when called without a valid user or admin token
  4. GET /health remains accessible without any token (public endpoint)
**Plans**: TBD

## Progress

**Execution Order:** 6 → 7 → 8 → 9 → 10 → 11
(Note: Phase 9 depends on Phase 6 only — could run parallel to 7/8, but sequential is simpler for solo dev)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 6. PDF Ingest | v2.0 | 0/? | Not started | - |
| 7. Upload API + Endpoint Aggiuntivi | v2.0 | 0/? | Not started | - |
| 8. LLM Synthesis | v2.0 | 0/? | Not started | - |
| 9. File Watcher | v2.0 | 0/? | Not started | - |
| 10. Hybrid Search | v2.0 | 0/? | Not started | - |
| 11. Authentication | v2.0 | 0/? | Not started | - |
