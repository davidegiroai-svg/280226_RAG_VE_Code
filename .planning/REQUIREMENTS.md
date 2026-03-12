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

### Stabilization & Hardening (v4)
- **STAB-01**: Unificazione bootstrap DB (v4).
- **STAB-02**: Coerenza formati (DOCX end-to-end) (v4).
- **STAB-03**: Smoke Test Suite (v4).
- **STAB-04**: Repo Sanitization (.env.example tracking) (v4).

### Observability (v5)
- **OBS-01**: Query Logging persistente (`query_log`, best-effort, GDPR-safe) (v5).
- **OBS-02**: Endpoint `/metrics` con 5 contatori JSON, protetto da API key (v5).
- **OBS-03**: DOCX Testing — 6 test automatici (v5).
- **OBS-04**: `/health/ready` schema check su tabelle core (v5).

### Basic RBAC (v6-B)
- **RBAC-01**: Supporto ruoli `user` e `admin` su API Key (v6-B).
- **RBAC-02**: Endpoint amministrativi (`/upload`, `/metrics`) riservati a ruoli `admin` (v6-B).
- **RBAC-03**: CLI di gestione potenziata per supporto ruoli (v6-B).

## Proposed / Future Requirements (Backlog)
- [ ] Connettori cloud drive reali (SharePoint, OneDrive).
- [ ] Supporto JWT/OIDC.
- [ ] RBAC granulare per KB.
- [ ] Integrazione Identity Provider Enterprise (JWT/OIDC).
- [ ] Output structuring (JSON templates).

---
*Last surgical correction: 2026-03-12. M6-B Basic RBAC marked implemented.*
