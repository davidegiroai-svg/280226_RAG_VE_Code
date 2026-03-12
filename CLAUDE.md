\# Project Rules & Rules (CLAUDE.md)

> [!NOTE]
> **Tipo Documento:** OPERATIVE SOURCE OF TRUTH
> **Stato:** Attivo
> **Finalità:** Punto di ingresso per sessioni Claude Code e regole di sviluppo.



\## Progetto

RAG Docker-first per il Comune di Venezia: interrogazione documenti (programmi, progetti, bandi).

Stack: FastAPI + PostgreSQL 16 + pgvector + Ollama (nomic-embed-text, 768d).

Percorso Windows: C:\Users\D.Giro\280226_RAG_VE_Code



## Stato milestone

- M3 DONE (2026-03-10): UI Completa, Streaming SSE, Ingest worker, Watcher, API Key Auth.
- M4 DONE (2026-03-10): Stabilization & Release Hardening (Bootstrap, Repo cleanup, Smoke Test, DOCX end-to-end).
- M5 DONE (2026-03-10): Observability & Enterprise Expansion (Query Logging, /metrics, DOCX Testing, /health/ready hardening).
- M6-A DONE (2026-03-11): Auditability Completion (user_id/kb_ids in query_log, legacy tests alignment).
- M6-B DONE (2026-03-12): Basic RBAC on API Keys (role column, require_admin_key, /upload & /metrics admin-only).
- M7 TODO: Cloud Drive Connectors (SharePoint/OneDrive) or Enterprise Identity.

- Dettaglio checkpoint: _cc_status/checkpoint_status.md



## Struttura reale del progetto

```

api/app/main.py        FastAPI: /health + POST /api/v1/query

api/app/db.py          psycopg2 sync connection

api/app/embedding.py   Adapter: ollama + dummy deterministico

api/app/ingest\_fs.py   Worker CLI ingest filesystem

api/app/query.py       vector\_to\_str + build\_query\_sql + parse\_results

scripts/db\_init.sql    Schema: knowledge\_base, documents, chunks + ivfflat(768)

docker-compose.yml     services: db (pg16), api :8000, worker (profile:manual)

tests/                 pytest sincrono

\_cc\_status/            Checkpoint log — NON modificare a mano

```



\## Comandi Windows/PowerShell (SEMPRE Docker)

```powershell

docker compose up -d

docker compose up -d --build

docker compose --profile manual run --rm worker --kb demo --path /data/inbox/demo

Invoke-RestMethod -Uri 'http://localhost:8000/health'

docker compose logs -f api

docker compose down -v && docker compose up -d

.\scripts\smoke_test.ps1

docker compose exec api python -m app.manage_keys list

docker compose exec api python -m app.manage_keys create --name "admin-key" --role admin

```



## Regole non derogabili

1\. Docker-first: mai python/pip direttamente su Windows

2\. No secrets nel codice: solo in .env (gitignore); template = .env.example

3\. psycopg2 SYNC: route FastAPI con def, NON async def

4\. vector\_to\_str(): sempre per lista Python -> stringa pgvector \[x,y,...]

5\. Encoding: read\_text\_file() usa utf-8-sig — NON modificare

6\. Dedup: UNIQUE(kb\_id, content\_hash) ON CONFLICT DO NOTHING ovunque

7\. Checkpoint: aggiornare \_cc\_status/checkpoint\_status.md dopo ogni task

8\. Lingua: commenti in italiano; nomi funzioni/variabili/API in inglese



\## Convenzioni stack

\- Python 3.11, Pydantic v2, psycopg2-binary SYNC, FastAPI 0.115, uvicorn

\- DB image: pgvector/pgvector:pg16 (NON pg17)

\- Embedding dim 768 fisso — cambiarla richiede docker compose down -v + reinit



\## Regole dettagliate (file separati)

\- Testing (sempre attivo)   → .claude/rules/testing.md

\- Sicurezza (sempre attivo) → .claude/rules/security.md

\- API endpoints             → .claude/rules/api-rules.md    (auto: api/app/main.py, query.py, db.py)

\- Ingest + Embedding        → .claude/rules/ingest-rules.md (auto: api/app/ingest\_fs.py, embedding.py)

\- DB + Docker Compose       → .claude/rules/db-rules.md     (auto: scripts/, docker-compose.yml)



## Strumenti installati

### Superpowers (plugin Claude Code)
Installato via plugin marketplace. Si attiva automaticamente ad ogni sessione.
Aggiunge: brainstorming prima del codice, TDD enforcement, code review automatica.
Comandi disponibili: /superpowers:brainstorm, /superpowers:write-plan, /superpowers:execute-plan
NOTA: le regole in .claude/rules/testing.md hanno priorità sul TDD generico di Superpowers
perché contengono i pattern specifici per psycopg2 sync e i mock corretti per questo progetto.

### GSD — Get Shit Done (locale al progetto)
Installato in .claude/commands/gsd/ e .claude/get-shit-done/
Comandi principali:
- /gsd:new-milestone  → usa questo per iniziare M2 (NON /gsd:new-project — il progetto esiste già)
- /gsd:plan-phase     → pianifica una fase con subagenti
- /gsd:execute-phase  → esegue la fase pianificata
- /gsd:health         → controlla lo stato GSD
NOTA: GSD gestisce il suo stato in .claude/get-shit-done/STATE.md
Il nostro checkpoint log rimane in _cc_status/checkpoint_status.md (non rimuovere)



\## Utente senza competenze di codice

Per ogni azione fornire SEMPRE:

\- Comando PowerShell esatto da copiare

\- Spiegazione in italiano semplice

\- Output atteso

\- Troubleshooting in italiano se c'è errore

