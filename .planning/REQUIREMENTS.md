# Requirements Archive & Baseline - Target State

> [!NOTE]
> **Tipo Documento:** TARGET STATE / TO-BE REQUIREMENTS
> **Stato:** Baseline di Progetto
> **Finalità:** Archivio dei requisiti funzionali e non funzionali target.


## Implemented Requirements (M1-M3)

### Core (v1)
- **FR-01**: Ingest documenti MD/TXT/CSV/JSON via CLI.
- **FR-02**: Vector Search pgvector.
- **FR-03**: API /health e /query.

### Advanced (v2)
- **FR-04**: Ingest PDF (metadata pagina).
- **FR-05**: Streaming LLM SSE.
- **FR-06**: Ingest automatico (Watcher).
- **FR-07**: Upload API (POST /upload).
- **FR-08**: Ricerca Ibrida (Vector + FTS).

### Frontend & Auth (v3)
- **FR-09**: Interfaccia Web Search/Documents/KBs.
- **FR-10**: Autenticazione via Header X-API-Key.

## Real-Time Requirements (M4 Stabilization)
- **STAB-01**: Unificazione bootstrap DB.
- **STAB-02**: Coerenza formati (DOCX ovunque).
- **STAB-03**: Logging query persistente.

## Proposed / Future Requirements (Backlog)
- [ ] Supporto JWT/OIDC.
- [ ] RBAC granulare per KB.
- [ ] Connettori cloud drive reali.
- [ ] Output structuring (JSON templates).

---
*Last surgical correction: 2026-03-10. JWT/RBAC requirement moved to future/backlog.*
