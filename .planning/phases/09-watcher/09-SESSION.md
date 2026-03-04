# Phase 9: Watcher — Session Log
**Started:** 2026-03-04 09:09:00
**Ended:** 2026-03-04 09:25:00
**Status:** COMPLETED

## Goal
Implementazione di un watcher automatico per monitorare il filesystem e auto-ingestire nuovi documenti, con propagazione delle cancellazioni.

## Requirements
- ✅ WTCH-01: Monitoraggio automatico di /data/inbox/<kb>/ per nuovi file
- ✅ WTCH-02: Auto-ingest di file aggiunti (TXT, MD, CSV, JSON, PDF)
- ✅ WTCH-03: Propagazione delete (soft delete su DB quando file rimosso)
- ✅ WTCH-04: Migration DB per colonne is_deleted, deleted_at, ingest_status su documents

## Tasks
- [x] Migration SQL per colonne watcher su documents
- [x] Implementazione watcher con watchdog.PollingObserver
- [x] Handler per evento "file created" → auto-ingest
- [x] Handler per evento "file deleted" → soft delete su DB
- [x] Gestione ingest_status (pending/processing/done/error)
- [x] Unit tests per watcher handlers
- [x] Test di integrazione con filesystem mock
- [x] E2E test con Docker

## Files Modified
- ✨ api/app/watcher.py (nuovo — KBWatcher con PollingObserver)
- ✨ scripts/migration_m2_watcher.sql (nuovo — ALTER TABLE documents)
- ✏️ api/app/ingest_fs.py (aggiunta `ingest_single_file()`)
- ✏️ api/app/main.py (endpoint GET /api/v1/documents)
- ✏️ docker-compose.yml (service watcher con profilo "watcher")
- ✨ tests/test_watcher.py (21 test)

## Test Status
- ✅ 55 test totali passed (21 nuovi watcher + 34 precedenti)

## Timeline
- [09:09] Sessione iniziata (Planning)
- [09:15] Implementazione migration SQL e watcher.py
- [09:20] Test TDD completati, tutti green
- [09:25] Sessione completata

## Key Decisions
- watchdog.PollingObserver con polling_interval=2s (inotify non funziona su Docker+Windows)
- Soft delete: `is_deleted=TRUE, deleted_at=NOW()` (mai cancellazione fisica dal DB)
- Service watcher con profilo separato per avvio manuale
