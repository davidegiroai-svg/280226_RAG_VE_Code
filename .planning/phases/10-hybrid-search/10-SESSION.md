# Phase 10: Hybrid Search — Session Log
**Started:** 2026-03-04 09:25:00
**Status:** PLANNING

## Goal
Implementazione della ricerca ibrida con tsvector (full-text) + vector similarity + Reciprocal Rank Fusion (RRF) per migliorare recall e precision.

## Requirements
- HYBR-01: Full-text search con tsvector + ts_rank su chunks.testo
- HYBR-02: Reciprocal Rank Fusion (RRF k=60) per combinare vector + FTS
- HYBR-03: Migration DB per indice tsvector su chunks.testo

## Tasks
- [x] Migration SQL per tsvector index su chunks.testo
- [x] Implementazione full-text search con ts_rank
- [x] Implementazione RRF per fusione ranking
- [x] Parametro search_mode in QueryRequest (vector/fts/hybrid)
- [x] Unit tests per hybrid search (23 test)
- [ ] Test di ranking: hybrid > solo vector per query keyword-heavy (post-MVP)
- [ ] E2E test con documenti reali (post-MVP)
- [ ] Performance test con dataset >100 chunks (post-MVP)

## Timeline
- [09:25] Sessione iniziata (Planning)
- [12:00] Implementazione completata (DONE)
  - scripts/migration_m2_hybrid.sql: testo_tsv TSVECTOR + GIN index + trigger
  - api/app/hybrid.py: fts_search() + rrf_merge(k=60)
  - api/app/query.py: execute_search() con search_mode
  - api/app/main.py: search_mode in QueryRequest + validazione
  - tests/test_hybrid_search.py: 23 test (78 totali, tutti PASSED)

## Status: DONE
