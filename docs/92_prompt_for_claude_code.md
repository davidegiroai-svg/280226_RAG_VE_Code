Project root: C:/Users/D.Giro/280226_RAG_VE_Code

Summary (what exists):
- Repo initialized (.git/.gitignore)
- Audit: `_cc_status/*` and `docs/00_repo_audit.md` (initial audit)
- Compose + DB schema: `docker-compose.yml`, `scripts/db_init.sql`, `.env.example`
- Runbook: `docs/10_run_local.md` (start/verify/reset + API tests)
- API skeleton: `api/` with FastAPI endpoints `/health` and `/api/v1/query` (POST/GET). Latest commit: `a71bfbc` - CC-04.1 (input validation + query robustness)

Next actions to execute (priority):
1) Implement CC-05: create `worker/` to ingest filesystem -> chunk documents -> write into `chunks` table. Include `source_path` metadata and dedup by `content_hash`.
2) Add basic embedding pipeline (local or provider) and store embedding + model id in `chunks.embedding` fields.
3) Extend API query to perform vector search (pgvector) and return top-K with citations; replace placeholder scoring.

Rules for execution:
- Always start commands from project root. Prefix every command with: `cd "C:/Users/D.Giro/280226_RAG_VE_Code" && `
- Do not change audit/checkpoint files except to update checkpoint when task is DONE.
- After implementing CC-05, run audit script and update `_cc_status/checkpoint_status.md` with timestamp.

Immediate next CLI to run (example):
cd "C:/Users/D.Giro/280226_RAG_VE_Code" && git checkout -b feature/cc-05-ingest

Stop here and report back with a one-line checkpoint when CC-05 is implemented.
