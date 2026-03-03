---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: PDF + Upload + LLM + Watcher + Hybrid + Auth
status: planning
stopped_at: Phase 6 context gathered
last_updated: "2026-03-03T18:59:43.622Z"
last_activity: 2026-03-03 — Roadmap v2.0 created (phases 6-11, 25 requirements mapped)
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-03)

**Core value:** Recupero accurato dei chunk piu rilevanti dai documenti della KB, con embedding locale (Ollama) e zero dipendenze cloud.
**Current focus:** Phase 6 — PDF Ingest (first phase of v2.0)

## Current Position

Phase: 6 of 11 (PDF Ingest)
Plan: 0 of ? in current phase
Status: Ready to plan
Last activity: 2026-03-03 — Roadmap v2.0 created (phases 6-11, 25 requirements mapped)

Progress: [░░░░░░░░░░] 0% (v2.0 — 0/6 phases complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 0 (v2.0)
- Average duration: — min
- Total execution time: — hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:** No data yet.

*Updated after each plan completion*

## Accumulated Context

### Decisions from M1 (carry forward)

- Embedding dim 768 fisso: cambiarla richiede `docker compose down -v` + reinit DB completo
- psycopg2 SYNC obbligatorio — no asyncpg, no async def nelle route
- vector_to_str() sempre per liste Python → stringa pgvector senza spazi
- RealDictCursor: accedere con row["colonna"], mai row[0]
- watchdog.PollingObserver per watcher (inotify non funziona su Docker+Windows)
- DB image: pgvector/pgvector:pg16 — NON aggiornare a pg17

### M2 Key Dependencies

- Phase 6 (PDF): richiede migration columns page_start/page_end/section_title su chunks
- Phase 9 (Watcher): richiede migration columns is_deleted/deleted_at/ingest_status su documents
- Phase 10 (Hybrid): richiede tsvector index su chunks.testo
- Phase 11 (Auth): da implementare per ultima — wrappa tutti gli endpoint esistenti

### Pending Todos

- docs_source/ non ancora sincronizzate con stato reale (modifiche staged in git)
- ARCHITECTURE.md, BRD.md, DATA_MODEL.md, PRD.md, SRS.md hanno modifiche non committate

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-03-03T18:59:43.575Z
Stopped at: Phase 6 context gathered
Resume file: .planning/phases/06-pdf-ingest/06-CONTEXT.md
