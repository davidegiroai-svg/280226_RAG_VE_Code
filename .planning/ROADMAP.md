# Project Roadmap - Transition Strategy

> [!NOTE]
> **Tipo Documento:** IMPLEMENTATION STRATEGY / TRANSITION
> **Stato:** Attivo
> **Finalità:** Definire le tappe del passaggio dallo stato attuale a quello target.


## Completed Milestones
- [x] **v1.0 Core RAG Pipeline** (2026-03-03)
- [x] **v2.0 Advanced Features & Automation** (2026-03-06)
- [x] **v3.0 Frontend & Basic Security** (2026-03-10)
- [x] **v4.0 Stabilization & Release Hardening** (2026-03-10)

- [x] **v6.0-A Auditability Completion** (2026-03-11)
- [x] **v6.0-B Basic RBAC on API Keys** (2026-03-12)
    - [x] **role support:** colonna role in `api_keys`.
    - [x] **admin endpoints:** `/upload` e `/metrics` admin-only.
    - [x] **CLI update:** `manage_keys` con parametro `--role`.
    - [x] **user_id tracking:** identità della API Key in `query_log`.
    - [x] **kb_ids tracking:** UUID reali delle KB in `query_log`.
    - [x] **test alignment:** fix legacy DOCX expectations.

## Future Roadmap (M7+ - Next Focus)
- [ ] **Cloud Drive Connectors** (SharePoint, OneDrive).
- [ ] **Enterprise Identity** (JWT, RBAC/ACL granulari per KB).
- [ ] **Output Modes** (Summary/Table/Extract-JSON).

---
*Updated 2026-03-12. Accurate to the current CODE state.*
