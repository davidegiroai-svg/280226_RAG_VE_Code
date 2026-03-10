# Project Overview - Transition Strategy

> [!NOTE]
> **Tipo Documento:** IMPLEMENTATION STRATEGY / TRANSITION
> **Stato:** Attivo (In Evoluzione)
> **Finalità:** Definire lo stack tecnico e lo scope della transizione M4.
> **Fonte Primaria Verità:** Il Codice.

**Source of Truth: CODE**

## What This Is
Sistema RAG (Retrieval-Augmented Generation) Docker-first per il Comune di Venezia. Permette di interrogare documenti istituzionali (programmi, progetti, bandi) tramite API REST. L'utente invia una query testuale e riceve i chunk più rilevanti, ordinati per similarità coseno con pgvector.

## Core Value
Recupero accurato dei chunk più rilevanti dai documenti della KB, con embedding locale (Ollama) e zero dipendenze cloud.

## Requirements Baseline

### Validated & Implemented (M1-M3)
- ✓ Schema DB PostgreSQL 16 + pgvector — v1.0
- ✓ API REST FastAPI (v1) — v1.0
- ✓ Embedding adapter: Ollama (nomic-embed-text 768d) — v1.0
- ✓ Ingest worker CLI (manuale) — v1.0
- ✓ Ingest PDF (pymupdf4llm) — v2.0
- ✓ Upload API (POST /api/v1/upload) — v2.0
- ✓ LLM synthesis (SSE Streaming) — v2.0
- ✓ Watcher automatico (Polling) — v2.0
- ✓ Hybrid search (BM25 + RRF) — v2.0
- ✓ **Auth: API Key hashata** (X-API-Key header) — v3.0
- ✓ **Frontend Web (React/Vite)** — v3.0
- ✓ **M4 Stabilization & Hardening** (SQL Init, Smoke Test, DOCX end-to-end, Auth Bootstrap) — v4.0

### Milestone M4 — Stabilization & Release Hardening (DONE)
- ✓ **Bootstrap Consolidation:** Unificato script di init e migrazione.
- ✓ **Security Hardening:** Sanitizzazione repository e .env.example.
- ✓ **Document Logic Alignment:** Supporto DOCX esteso a watcher e UI.
- ✓ **Smoke Test Suite:** Validazione automatica post-deploy.

### Milestone M5 — Observability & Enterprise Readiness (DONE)
- ✓ **Query Logging:** Tracciamento persistente delle query in DB (`query_log`, `_write_query_log`).
- ✓ **Monitoring:** Endpoint `/metrics` con 5 contatori JSON (protetto da API key).
- ✓ **Docx Resilience:** 6 test in `tests/test_docx.py`, nessun bug trovato.
- ✓ **Health Hardening:** `/health/ready` verifica tabelle core dello schema.

### Out of Scope / Roadmap Future
- JWT/RBAC (Pianificato per Enterprise).
- OneDrive/SharePoint Connectors.

## Tech Stack
- **Backend:** FastAPI, psycopg2 (SYNC), uvicorn.
- **Database:** PostgreSQL 16 + pgvector (dim 768).
- **Core AI:** Ollama (Embedding + LLM).
- **Frontend:** React, Vite, Tailwind.
- **Security:** API Key hashata (SHA-256).

---
*Last updated: 2026-03-10 — M5 DONE (Query Logging, /metrics, DOCX Testing, /health/ready hardening).*
