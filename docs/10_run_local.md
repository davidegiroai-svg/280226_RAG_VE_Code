# Avvio locale — RAG VE

Guida operativa per avviare il sistema su macchina Windows con Docker Desktop.
Valida per lo stato attuale: M3 completato (API, Frontend, Auth, Streaming).

---

## Prerequisiti

- Docker Desktop installato e in esecuzione
- Ollama installato e avviato con il modello embedding:
  ```powershell
  ollama pull nomic-embed-text
  ```
- (Opzionale, per risposte sintetiche) Ollama con modello LLM:
  ```powershell
  ollama pull llama3.2
  ```

---

## Passo 1 — Configura .env

```powershell
Copy-Item .env.example .env
```

Apri `.env` e verifica che `OLLAMA_BASE_URL` punti a Ollama sul tuo PC:

```
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

Non modificare altri valori a meno che tu non abbia motivi specifici.

---

## Passo 2 — Avvia DB e API

```powershell
docker compose up -d db api
```

Attendi circa 30 secondi per l'inizializzazione del database.

Verifica che i servizi siano attivi:

```powershell
docker compose ps
```

Dovresti vedere `db` e `api` con stato `running`.

Verifica che l'API risponda:

```powershell
Invoke-RestMethod -Uri 'http://localhost:8000/health'
```

Risposta attesa: `{"status":"ok","database":"connected"}`

---

## Passo 3 — Bootstrap autenticazione (prima volta)

Questo passo crea la chiave API per il frontend e aggiorna `.env` automaticamente.

```powershell
.\scripts\bootstrap_auth.ps1
```

Lo script:
1. Verifica che i container siano in esecuzione
2. Genera una API key per il frontend
3. Scrive `FRONTEND_API_KEY=<valore>` in `.env`
4. Riavvia il container frontend

Output atteso: tutti i passi con `[PASS]` e URL finale.

> **Nota:** eseguire UNA SOLA VOLTA. Se riesegui, viene creata una nuova chiave
> e quella vecchia resta valida (non viene revocata automaticamente).

---

## Passo 4 — Verifica il frontend

Apri il browser su: **http://localhost:3000**

Dovresti vedere l'interfaccia RAG VE con le pagine: Search, Upload, Documents, KBs.

---

## Passo 5 — Verifica base funzionamento

```powershell
# Stato DB e vector extension
Invoke-RestMethod -Uri 'http://localhost:8000/health/ready'
```

Risposta attesa: `{"status":"ok","database":"connected","vector":"ok"}`

---

## Comandi utili

### Ingest manuale documenti (worker CLI)

```powershell
# Metti i file in data\inbox\<nome-kb>\ poi esegui:
docker compose --profile manual run --rm worker --kb demo --path /data/inbox/demo
```

### Avviare il watcher automatico

Il watcher monitora `data/inbox/` e indicizza i nuovi file automaticamente.
Non si avvia con `docker compose up -d` standard — richiede il profilo dedicato:

```powershell
docker compose --profile watcher up -d watcher
```

Per fermarlo:

```powershell
docker compose --profile watcher stop watcher
```

### Listare le API key esistenti

```powershell
docker compose exec api python -m app.manage_keys list
```

### Reset completo (cancella tutti i dati)

```powershell
docker compose down -v
docker compose up -d db api
.\scripts\bootstrap_auth.ps1
```

---

## Troubleshooting

| Sintomo | Causa probabile | Soluzione |
|---|---|---|
| Frontend risponde 401 | `FRONTEND_API_KEY` vuota o mancante | Esegui `bootstrap_auth.ps1` |
| `/health` risponde 503 | DB non pronto | Attendi 30s e riprova |
| Embedding lento o assente | Ollama non in esecuzione | Avvia Ollama e verifica `ollama list` |
| Upload fallisce con 415 | Tipo file non supportato | Usa PDF, TXT, MD, CSV o JSON |
| Watcher non parte | Profilo non specificato | Usa `--profile watcher` |
