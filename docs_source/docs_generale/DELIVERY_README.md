Delivery README

This document contains the minimal copy-paste instructions to run the PoC locally and to hand off to the client's IT team (Comune di Venezia).

Prerequisites
- Docker and Docker Compose installed.
- PostgreSQL (or use the bundled Docker Compose service).

Run PoC (Docker Compose)
1. Copy environment template:
   - cp ve-multikb-agent/.env.example ve-multikb-agent/.env
2. Fill required variables in `ve-multikb-agent/.env` (database credentials, embedding model path).
3. Start services:
   - docker compose up --build -d

Initialize Database
1. Enter DB container or use psql client.
2. Run the complete DDL in `scripts/db_init.sql`; treat `docs/DATA_MODEL.md` as a logical description only.

Ingest sample data
1. Use the ingest CLI in `ve-multikb-agent` or upload sample documents via the API endpoint `/api/v1/ingest`.

Run local query demo
1. If a frontend UI is provided, start it according to its README.
2. Use the versioned API endpoint `/api/v1/query` to test retrieval and RAG flow.

Security & Handoff
- Replace the placeholder `REDACTED_REMOVE_AND_ROTATE` values with newly issued API keys.
- Rotate/invalidate any keys that were exposed prior to delivery.
- Share `ve-multikb-agent/.env.example` with client's IT and provide values securely (not via email).

Optional: Purge Git history
- If you need to remove secrets from Git history, use `git-filter-repo` or BFG. Coordinate with the client and take backups before running history-rewriting tools.

Contact
- For questions about the PoC, contact the engineering lead listed in `docs/04_handoff_notes.md`.


---

## Extended runbook (UI, upload, watcher, RAG modes, citations)

### Optional: Run Frontend Web UI
- Start the backend services first (API + DB + worker).
- Then run the UI dev server (implementation-dependent). Expected UI capabilities:
  - KB/namespace selector
  - query input + top_k + mode (roadmap)
  - sources list with expand/collapse
  - Documents page with upload + indexing status (optional)

### Upload documents via API
Example (curl):
- `curl -F "file=@./sample.pdf" "http://localhost:8000/api/v1/upload?kb=<kb_namespace>"`

Example (PowerShell):
- `Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/upload?kb=<kb_namespace>" -Form @{ file = Get-Item ".\sample.pdf" }`

Notes:
- The server must enforce max file size and allowed types (PDF/DOCX/TXT in MVP).
- Upload stores files into a per-KB inbox (PoC convention: `/data/inbox/<kb>/` volume).

### Run Watcher (auto-index + delete propagation)
- Start the watcher service (container or local process) with configurable polling:
  - `WATCHER_POLL_SECONDS` (e.g., 30)
  - `INBOX_ROOT` (e.g., `/data/inbox`)
- Watcher responsibilities:
  - detect new/updated files → enqueue ingest
  - detect deleted files → mark docs deleted + cleanup chunks

Troubleshooting:
- If running on Windows/Docker Desktop, prefer polling over filesystem events.
- Ensure the inbox volume is mounted read/write for the watcher and API.

### Query endpoints (retrieval vs full RAG)
Retrieval-only:
- `POST /api/v1/query` with `{ "kb":"<kb>", "query":"...", "top_k": 5 }`

Full RAG (answer synthesis):
- Option A: `POST /api/v1/answer`
- Option B: `POST /api/v1/query` with `synthesize=true`

### Output modes
- Use a `mode` parameter to request:
  - `summary`, `bullets`, `table`, `checklist`, `qa`, `extract-json`
- For `table` / `extract-json`, the API should return JSON validated by schema; UI renders the table.

### Page-level citations (PDF)
- Enable PDF page-aware ingestion to return citations with:
  - document title
  - page_start / page_end
  - section_title (if available)

### Security & TLS (production guidance)
- PoC may run without TLS on localhost.
- Production deployments MUST enable TLS, protect admin endpoints, and configure RBAC/ACL.
- Store secrets outside source control; prefer a secret manager when available.

### Observability
- Ensure `/health` and `/metrics` are reachable.
- Logs should include a `request_id` to correlate API, watcher and worker events.

### Evaluation harness (offline)
- Run evaluation scripts against a curated query dataset to compute:
  - Precision@K, MRR
  - (after answer synthesis) grounding/faithfulness metrics
- Store reports as versioned artifacts for regression tracking.

---

Updated: 2026-03-03
