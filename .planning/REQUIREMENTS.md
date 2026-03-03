# Requirements: RAG Multi-KB — Comune di Venezia

**Defined:** 2026-03-03
**Core Value:** Recupero accurato dei chunk piu rilevanti dai documenti della KB, con embedding locale (Ollama) e zero dipendenze cloud.

## v2 Requirements

Requirements for M2 milestone. Each maps to roadmap phases.

### PDF (PDF Ingest)

- [ ] **PDF-01**: User can ingest PDF files via the worker CLI (--path pointing to a folder containing PDFs)
- [ ] **PDF-02**: System extracts text per page using pymupdf4llm with page_chunks=True
- [ ] **PDF-03**: Each chunk stores page_start and page_end metadata in the chunks table
- [ ] **PDF-04**: PDF chunks are deduplicated like other file types (UNIQUE kb_id+content_hash)

### UPLD (Upload API)

- [ ] **UPLD-01**: User can upload one or more files via POST /api/v1/upload?kb=<namespace>
- [ ] **UPLD-02**: Upload endpoint accepts .pdf .txt .md .csv .json file types
- [ ] **UPLD-03**: Upload endpoint rejects files larger than MAX_UPLOAD_SIZE_MB with HTTP 413
- [ ] **UPLD-04**: Upload endpoint rejects unsupported file types with HTTP 415
- [ ] **UPLD-05**: Upload response includes upload_id, job_id, kb, and list of saved file paths

### LLM (LLM Synthesis)

- [ ] **LLM-01**: User can request a synthesized answer by adding synthesize=true to /api/v1/query
- [ ] **LLM-02**: System generates a natural-language answer using Ollama LLM from retrieved chunks
- [ ] **LLM-03**: Query falls back to retrieval-only answer if LLM unavailable or synthesize=false

### WTCH (File Watcher)

- [ ] **WTCH-01**: System automatically ingests new files added to /data/inbox/<kb>/ within WATCHER_POLL_SECONDS
- [ ] **WTCH-02**: System marks document as deleted and removes its chunks when source file is removed from inbox
- [ ] **WTCH-03**: Watcher runs as a persistent Docker service (restart: unless-stopped)
- [ ] **WTCH-04**: Watcher uses PollingObserver (not inotify) for Docker+Windows compatibility

### HYBR (Hybrid Search)

- [ ] **HYBR-01**: Query endpoint combines vector similarity and BM25 full-text scores via RRF (k=60)
- [ ] **HYBR-02**: Full-text search uses PostgreSQL tsvector index on chunks.testo
- [ ] **HYBR-03**: Results are ranked by combined RRF score, returned as sources with score field

### AUTH (Authentication)

- [ ] **AUTH-01**: System issues JWT tokens for admin and user roles
- [ ] **AUTH-02**: POST /api/v1/upload and ingest endpoints require admin role
- [ ] **AUTH-03**: POST /api/v1/query and GET /api/v1/kbs require user or admin role
- [ ] **AUTH-04**: GET /health remains public (no token required)

### API (Additional Endpoints)

- [ ] **API-01**: GET /api/v1/kbs returns list of knowledge bases with doc and chunk counts
- [ ] **API-02**: GET /health/ready returns 200 if DB connected and vector extension present, 503 otherwise

## v3 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Monitoring

- **MON-01**: GET /metrics exposes Prometheus-compatible query_count, ingest_count, error_count, avg_latency_ms
- **MON-02**: Audit log records every upload event (timestamp, file_name, kb, size)

### Advanced Embeddings

- **EMB-01**: Support SentenceTransformers provider as fallback when Ollama unavailable
- **EMB-02**: Support multiple embedding dimensions per KB (requires DB migration)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Cloud embedding providers (OpenAI, Cohere) | Dati PA — no cloud senza consenso esplicito GDPR |
| Mobile app | Web-first per PoC, risorse insufficienti |
| Real-time chat | Alta complessita, non nel core value RAG |
| Multi-tenant isolation avanzata | Namespace KB sufficiente per questo progetto |
| Modifica vector(768) | Richiede reset DB completo — nessun beneficio attuale |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PDF-01 | Phase 6 | Pending |
| PDF-02 | Phase 6 | Pending |
| PDF-03 | Phase 6 | Pending |
| PDF-04 | Phase 6 | Pending |
| UPLD-01 | Phase 7 | Pending |
| UPLD-02 | Phase 7 | Pending |
| UPLD-03 | Phase 7 | Pending |
| UPLD-04 | Phase 7 | Pending |
| UPLD-05 | Phase 7 | Pending |
| LLM-01 | Phase 8 | Pending |
| LLM-02 | Phase 8 | Pending |
| LLM-03 | Phase 8 | Pending |
| WTCH-01 | Phase 9 | Pending |
| WTCH-02 | Phase 9 | Pending |
| WTCH-03 | Phase 9 | Pending |
| WTCH-04 | Phase 9 | Pending |
| HYBR-01 | Phase 10 | Pending |
| HYBR-02 | Phase 10 | Pending |
| HYBR-03 | Phase 10 | Pending |
| AUTH-01 | Phase 11 | Pending |
| AUTH-02 | Phase 11 | Pending |
| AUTH-03 | Phase 11 | Pending |
| AUTH-04 | Phase 11 | Pending |
| API-01 | Phase 7 | Pending |
| API-02 | Phase 7 | Pending |

**Coverage:**
- v2 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0 (100% coverage)

---
*Requirements defined: 2026-03-03*
*Last updated: 2026-03-03 — traceability populated after roadmap v2.0 creation*
