# State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-03)

**Core value:** Recupero accurato dei chunk più rilevanti dai documenti della KB, con embedding locale (Ollama) e zero dipendenze cloud.
**Current focus:** Milestone v2.0 — defining requirements

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-03 — Milestone v2.0 started

## Accumulated Context

### From M1 (v1.0)

- Embedding dim 768 è fisso: cambiarla richiede `docker compose down -v` + reinit DB completo
- psycopg2 SYNC obbligatorio — no asyncpg, no async def nelle route
- vector_to_str() sempre per liste Python → stringa pgvector senza spazi
- RealDictCursor: accedere con row["colonna"], mai row[0]
- Encoding: read_text_file() usa utf-8-sig — NON modificare
- Worker è profile:manual; il watcher sarà restart:unless-stopped
- Test: pytest SINCRONO, TestClient, mock DB con patch("api.app.db.get_db_cursor"), EMBEDDING_PROVIDER=dummy
- DB image: pgvector/pgvector:pg16 — NON aggiornare a pg17

### Pending todos from M1

- docs_source/ non ancora sincronizzate con stato reale (modifiche staged in git)
- ARCHITECTURE.md, BRD.md, DATA_MODEL.md, PRD.md, SRS.md hanno modifiche non committate
