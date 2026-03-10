---
gsd_state_version: 1.0
milestone: M5
milestone_name: Enterprise Ready & Observability
status: DONE
last_updated: "2026-03-10T16:00:00Z"
---

# Project State - Operative Source of Truth

> [!NOTE]
> **Tipo Documento:** CURRENT STATE / OPERATIVE SOURCE OF TRUTH
> **Stato:** Attivo
> **Finalità:** Snapshot reale e verificabile dello stato di avanzamento.


## Current Milestone: M5 – Enterprise Ready & Observability (DONE)
**Status:** Completed ✅

### Milestone Status
- **v1.0 (Core):** [██████████] 100% DONE
- **v2.0 (Advanced):** [██████████] 100% DONE (PDF, Upload, LLM, Watcher, Hybrid)
- **v3.0 (Frontend & Auth):** [██████████] 100% DONE (React UI, API Key Auth)
- **v4.0 (Stabilization):** [██████████] 100% DONE (Bootstrap, Security, Smoke Test, DOCX)
- **v5.0 (Observability):** [██████████] 100% DONE (Query Logging, /metrics, DOCX Tests, /health/ready)

## Technical Summary
- **Primary Auth:** API Key (X-API-Key) con hash SHA-256 su DB.
- **Frontend Pages:** Search, Upload, Documents, KBs.
- **Ingest Path:** `/data/inbox/<kb_name>`.
- **Search:** Vector, FTS, Hybrid (RRF).
- **Hardening:** Bootstrap unificato, Smoke Test suites, .env cleanup.
- **Observability:** query_log attivo, /metrics endpoint, /health/ready schema check.

## Key Decisions (Post-M5 Alignment)
- **Query Logging:** Attivo su /query e /query/stream. user_id=NULL (accettato), retrieved_chunks come JSONB {id,score}.
- **Metrics:** GET /metrics protetto da API key. JSON semplice, no Prometheus dependency.
- **DOCX Testing:** 6 test in test_docx.py. Nessun bug trovato nel parser esistente.
- **/health/ready:** Ora verifica anche tabelle core (knowledge_base, documents, chunks).

## Pending for M6
1. user_id reale in query_log (richiede JOIN su api_keys).
2. JWT/RBAC (Enterprise Identity).
3. Cloud Drive Connectors (SharePoint, OneDrive).

---
*Updated 2026-03-10 after M5 closure.*
