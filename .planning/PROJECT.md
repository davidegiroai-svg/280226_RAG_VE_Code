# RAG Multi-KB — Comune di Venezia

## What This Is

Sistema RAG (Retrieval-Augmented Generation) Docker-first per il Comune di Venezia. Permette di interrogare documenti istituzionali (programmi, progetti, bandi) tramite API REST. L'utente invia una query testuale e riceve i chunk più rilevanti, ordinati per similarità coseno con pgvector.

## Core Value

Recupero accurato dei chunk più rilevanti dai documenti della KB, con embedding locale (Ollama) e zero dipendenze cloud.

## Requirements

### Validated

<!-- Shipped in M1 (v1.0) — 2026-03-03 -->

- ✓ Schema DB PostgreSQL 16 + pgvector con vector(768) e indice ivfflat coseno — v1.0
- ✓ API GET /health e POST /api/v1/query con risposta QueryResponse (answer + sources) — v1.0
- ✓ Embedding adapter: Ollama (nomic-embed-text 768d) + dummy deterministico per test — v1.0
- ✓ Ingest worker CLI per TXT/MD/CSV/JSON con chunking (1200 chars, overlap 200) — v1.0
- ✓ Deduplication UNIQUE(kb_id, content_hash) ON CONFLICT DO NOTHING — v1.0
- ✓ Encoding robusto: utf-8-sig + repair mojibake — v1.0
- ✓ Docker Compose: db (pgvector/pg16), api :8000, worker (profile manual) — v1.0
- ✓ Vector similarity search: cosine distance → score clamped [0..1] — v1.0

### Active

<!-- Current scope — M2 v2.0 -->

- [ ] Ingest PDF con pymupdf4llm (page_chunks=True, page_start/end metadata)
- [ ] Upload API: POST /api/v1/upload?kb=<namespace> salva file in /data/inbox/<kb>/
- [ ] LLM synthesis: api/app/llm.py + parametro synthesize=true in query
- [ ] File watcher: watchdog.PollingObserver su /data/inbox/ con delete propagation
- [ ] Hybrid search: tsvector + BM25 + RRF k=60
- [ ] Auth: RBAC base (admin/user) con JWT

### Out of Scope

- Provider cloud embeddings (OpenAI, Cohere) — dati della PA, no cloud senza consenso esplicito
- App mobile — web-first per PoC
- Real-time notifications — complessità non giustificata per il volume attuale
- Multi-tenant isolation avanzata — namespace KB sufficiente per ora

## Context

- Stack fisso: FastAPI + psycopg2 SYNC + PostgreSQL 16 pgvector + Ollama locale
- Embedding dim 768 fisso — cambiarla richiede docker compose down -v + reinit DB
- psycopg2 sync obbligatorio: route FastAPI def non async, RealDictCursor
- Windows host: tutti i comandi via Docker, mai python diretto su host
- Ingest worker è manuale (profile manual), il watcher sarà automatico (restart: unless-stopped)

## Constraints

- **Tech stack**: Python 3.11, FastAPI 0.115, psycopg2-binary SYNC, pgvector/pgvector:pg16 — non aggiornare senza test
- **Embedding dim**: 768 fisso per nomic-embed-text — cambio richiede reset completo DB
- **Docker-first**: mai pip/python diretto su Windows host
- **Secrets**: solo in .env (gitignore), .env.example con placeholder
- **Sync**: psycopg2 sync ovunque, no asyncpg, no async def nelle route API

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| psycopg2 SYNC invece di asyncpg | Semplicità, nessun loop event conflict con FastAPI sync | ✓ Good |
| pgvector ivfflat cosine (lists=100) | Bilanciamento velocità/accuratezza per dataset medio | ✓ Good |
| Ollama locale per embedding | Dati PA, no cloud, privacy by design | ✓ Good |
| vector(768) fisso | nomic-embed-text 768d, deciso in M1_TASK_01 | ✓ Good |
| Chunking 1200 chars overlap 200 | Compromesso contesto/granularità per testi istituzionali | — Pending |
| watchdog.PollingObserver per watcher | inotify non funziona su Docker+Windows | — Pending |

## Current Milestone: v2.0 PDF+API+LLM+Watcher+Hybrid+Auth

**Goal:** Aggiungere ingest PDF, upload API, sintesi LLM, watcher automatico, ricerca ibrida e autenticazione base.

**Target features:**
- PDF ingest con page metadata
- Upload API REST per file
- Sintesi LLM con Ollama (synthesize=true)
- Watcher automatico su inbox
- Hybrid search (BM25 + vector + RRF)
- Auth JWT base (admin/user)

---
*Last updated: 2026-03-03 after M1 completion — M2 v2.0 started*
