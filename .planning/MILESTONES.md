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

## v2.0 — PDF + Upload + LLM + Watcher + Hybrid + Auth (IN PROGRESS)

**Started:** 2026-03-03

**Goal:** Aggiungere ingest PDF, upload API, sintesi LLM, watcher automatico, ricerca ibrida e autenticazione base.

**Status:** Defining requirements → Roadmap

---
