---
gsd_state_version: 1.0
milestone: M6-B
milestone_name: Basic RBAC on API Keys
status: DONE
last_updated: "2026-03-12T10:30:00Z"
---

# Project State - Operative Source of Truth

> [!NOTE]
> **Tipo Documento:** CURRENT STATE / OPERATIVE SOURCE OF TRUTH
> **Stato:** Attivo
> **Finalità:** Snapshot reale e verificabile dello stato di avanzamento.


## Current Milestone: M6-B – Basic RBAC on API Keys (DONE)
**Status:** Completed ✅

### Milestone Status
- **v1.0-v4.0 (Core & Stab):** [██████████] 100% DONE
- **v5.0 (Observability):** [██████████] 100% DONE
- v6.0-A (Auditability): [██████████] 100% DONE (user_id & kb_ids tracking)
- v6.0-B (Basic RBAC): [██████████] 100% DONE (admin/user roles)

## Technical Summary
- **Primary Auth:** API Key (X-API-Key) con hash SHA-256 su DB.
- **Frontend Pages:** Search, Upload, Documents, KBs.
- **Ingest Path:** `/data/inbox/<kb_name>`.
- **Search:** Vector, FTS, Hybrid (RRF).
- **Hardening:** Bootstrap unificato, Smoke Test suites, .env cleanup.
- Auditability: `query_log` valorizza `user_id` (nome API key) e `kb_ids` (UUID reali delle KB).
- RBAC: API Key con ruoli `admin` e `user`. Endpoint `/api/v1/upload` e `/metrics` ora admin-only.
- Observability: `/metrics` endpoint, `/health/ready` con schema check robusto.

## Key Decisions (Post-M6-A Alignment)
- **User Tracking:** `query_log.user_id` mappa il campo `name` della tabella `api_keys`. Risoluzione lato API.
- KB Tracking: `query_log.kb_ids` salva gli UUID reali (non i namespace) per persistenza audit.
- RBAC Design: Introdotta colonna `role` in `api_keys` con migration idempotente.
- Safety: Default `role='user'` per garantire il principio di least privilege.
- Legacy Tests: Riallineati i test DOCX alle specifiche di parsing M4.

## Pending Roadmap (Backlog)
1. Connettori Cloud Drive (SharePoint, OneDrive).
2. JWT/RBAC (Enterprise Identity).
3. Retention policy / GDPR per query_log.

---
*Updated 2026-03-12 after M6-B closure.*
