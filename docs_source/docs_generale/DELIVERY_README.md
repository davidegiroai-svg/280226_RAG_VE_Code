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
