# Phase 10: Hybrid Search — Session Log
**Started:** 2026-03-04 09:25:00
**Ended:** 2026-03-04 09:35:00
**Status:** COMPLETED

## Goal
Implementazione della ricerca ibrida con tsvector (full-text) + vector similarity + Reciprocal Rank Fusion (RRF) per migliorare recall e precision.

## Requirements
- ✅ HYBR-01: Full-text search con tsvector + ts_rank su chunks.testo
- ✅ HYBR-02: Reciprocal Rank Fusion (RRF k=60) per combinare vector + FTS
- ✅ HYBR-03: Migration DB per indice tsvector su chunks.testo

## Tasks
- [x] Migration SQL per tsvector index su chunks.testo
- [x] Implementazione full-text search con ts_rank
- [x] Implementazione RRF per fusione ranking
- [x] Parametro search_mode in QueryRequest (vector/fts/hybrid)
- [x] Unit tests per hybrid search
- [x] Test di ranking
- [x] E2E test con documenti reali

## Files Modified
- ✨ scripts/migration_m2_hybrid.sql (tsvector + GIN index + trigger auto-update)
- ✨ api/app/hybrid.py (`fts_search()` + `rrf_merge()` k=60)
- ✏️ api/app/query.py (`execute_search()` con search_mode)
- ✏️ api/app/main.py (campo `search_mode` in QueryRequest)
- ✨ tests/test_hybrid_search.py (23 test)

## Test Status
- ✅ 78 test totali passed (23 nuovi hybrid + 55 precedenti)

## Key Decisions
- tsvector con lingua 'italian' per stemming corretto
- GIN index per performance FTS su grandi dataset
- Trigger auto-update su INSERT/UPDATE per mantenere testo_tsv sincronizzato
- RRF k=60 (standard in letteratura IR)
- Tre modalità: vector (default), fts, hybrid
