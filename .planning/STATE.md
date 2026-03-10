---
gsd_state_version: 1.0
milestone: M4
milestone_name: Stabilization & Release Hardening
status: IN PROGRESS
last_updated: "2026-03-10T11:13:00Z"
---

# Project State - Operative Source of Truth

> [!NOTE]
> **Tipo Documento:** CURRENT STATE / OPERATIVE SOURCE OF TRUTH
> **Stato:** Attivo
> **Finalità:** Snapshot reale e verificabile dello stato di avanzamento.


## Current Milestone: M4 – Stabilization & Release Hardening
**Status:** In Progress 🛠️

### Milestone Status
- **v1.0 (Core):** [██████████] 100% DONE
- **v2.0 (Advanced):** [██████████] 100% DONE (PDF, Upload, LLM, Watcher, Hybrid)
- **v3.0 (Frontend & Auth):** [██████████] 100% DONE (React UI, API Key Auth)
- **v4.0 (Stabilization):** [░░░░░░░░░░] 5% STARTED (Current focus)

## Technical Summary
- **Primary Auth:** API Key (X-API-Key) con hash SHA-256 su DB.
- **Frontend Pages:** Search, Upload, Documents, KBs.
- **Ingest Path:** `/data/inbox/<kb_name>`.
- **Search:** Vector, FTS, Hybrid (RRF).

## Key Decisions (Surgical Alignment)
- **Auth Reality:** JWT/RBAC non sono implementati. L'autenticazione corrente è basata su API Key.
- **File Support:** DOCX supportato solo via worker CLI; il watcher e l'upload UI sono limitati a PDF/TXT/MD/CSV/JSON.
- **Bootstrap:** Attualmente frammentato (SQL manuale richiesto).

## Pending for M4
1. Unificazione script SQL init.
2. Rimozione file `.env` e `.git` residui dai cleanup.
3. Attivazione logging query lato API.

---
*Updated 2026-03-10 after surgical documentation reform.*
