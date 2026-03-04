\# security.md — Regole sicurezza per tutto il progetto RAG VE

\# (caricato sempre da Claude Code, senza paths: — la sicurezza è trasversale)



\## Secrets e credenziali (non derogabile)

\- MAI inserire password, token, API key o connessioni DB nel codice Python o SQL

\- Tutte le credenziali vivono SOLO in .env (già in .gitignore)

\- .env.example committato con valori placeholder: rag\_password\_change\_me

\- Se si aggiunge una nuova variabile sensibile: aggiungerla in .env.example con valore fittizio

\- Prima di ogni git commit: verificare che .env non sia in staging (git status)



\## Variabili d'ambiente obbligatorie (già in .env.example)

POSTGRES\_USER, POSTGRES\_PASSWORD, POSTGRES\_DB, POSTGRES\_PORT

EMBEDDING\_PROVIDER, EMBEDDING\_MODEL, EMBEDDING\_DIM

OLLAMA\_BASE\_URL, EMBEDDING\_TIMEOUT\_S



\## Nuove variabili da aggiungere in M2

MAX\_UPLOAD\_SIZE\_MB   (per upload API — default consigliato: 50)

SECRET\_KEY           (per auth JWT quando si implementa RBAC)



\## Dati personali e GDPR

\- query\_log.query\_text contiene testo utente: trattarlo come dato personale

\- Non loggare mai il testo delle query nei log applicativi (solo query\_id e latency\_ms)

\- Embedding dei documenti: non inviare testo a provider esterni senza consenso

&nbsp; (il provider "ollama" è locale: OK; "openai" invia a cloud: richede valutazione)



\## Endpoint da proteggere in M2 (quando si aggiunge auth)

\- POST /api/v1/upload   → solo ruolo admin

\- POST /api/v1/ingest   → solo ruolo admin

\- GET  /api/v1/kbs      → ruolo user o admin

\- POST /api/v1/query    → ruolo user o admin

\- GET  /health          → pubblico

\- GET  /metrics         → solo rete interna (non esporre pubblicamente)



\## Docker e rete

\- La porta 5432 del DB NON deve essere esposta pubblicamente in produzione

&nbsp; (in docker-compose.yml: ports solo per sviluppo locale, rimuovere in produzione)

\- Il container DB non deve avere accesso alla rete esterna (solo rete interna Docker)



\## Audit log (da implementare in M2)

\- Ogni query deve produrre una riga in query\_log con: user\_id (nullable), kb\_ids, response\_time\_ms

\- NON salvare query\_text in chiaro nei log applicativi (solo nel DB con retention policy)

\- Ogni upload deve produrre un evento in audit\_log con: timestamp, file\_name, kb, dimensione

