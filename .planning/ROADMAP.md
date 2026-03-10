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

## Future Roadmap (M6+ - Next Focus)
- [x] **Milestone 5: Enterprise Ready & Observability** (2026-03-10)
    - [x] **Task 5.1: Query Logging** - query_log attivo su /query e /query/stream.
    - [x] **Task 5.2: Monitoring** - GET /metrics con 5 contatori operativi (JSON semplice).
    - [x] **Task 5.3: Docx Testing** - 6 test in tests/test_docx.py, nessun bug trovato.
    - [x] **Task 5.4: Minor Hardening** - /health/ready verifica tabelle core schema.
- [ ] **Output Modes** (Summary/Table/Extract-JSON).
- [ ] **Cloud Drive Connectors** (SharePoint, OneDrive).
- [ ] **Enterprise Identity** (JWT, RBAC/ACL reali).

---
*Updated 2026-03-10. Historically accurate to the current CODE state.*
