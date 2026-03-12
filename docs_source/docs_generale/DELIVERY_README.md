# Delivery README - Runbook Operativo (M6-B Basic RBAC)

> [!NOTE]
> **Tipo Documento:** RUNBOOK / DELIVERY OPERATIONS
> **Stato:** ATTIVO (Post-M6-B)
> **Finalità:** Istruzioni operative reali per il deploy e l'avvio del sistema.
> **Versione:** 4.0 (Basic RBAC Ready)

## 1. Quick Start (Windows / Docker Desktop)
Questo documento contiene le istruzioni per eseguire il sistema localmente in modalità stabilizzata.

### Prerequisiti
- Docker Desktop attivo.
- Ollama installato (`pull nomic-embed-text` e `pull llama3.2`).

### Avvio Rapido
1. **Configura Ambiente:**
   ```powershell
   Copy-Item .env.example .env
   ```
2. **Avvia Infrastruttura:**
   ```powershell
   docker compose up -d db api
   ```
3. **Bootstrap Autenticazione:**
   ```powershell
   .\scripts\bootstrap_auth.ps1
   ```
4. **Verifica Salute:**
   ```powershell
   .\scripts\smoke_test.ps1
   ```

## 2. Operazioni Ingest
Il sistema supporta PDF, DOCX, TXT, MD, CSV, JSON.

### Ingest Manuale (CLI)
```powershell
docker compose --profile manual run --rm worker --kb <nome-kb> --path /data/inbox/<nome-kb>
```

### Ingest Automatico (Watcher)
Monitora la cartella `data/inbox/` per nuovi file:
```powershell
docker compose --profile watcher up -d watcher
```

## 3. Osservabilità & Audit (Novità M6-A)
Il sistema espone telemetria ed è pienamente auditabile:
- **Query Logging:** Tutte le query vengono salvate in `query_log` con tempi di latenza, identità utente (`user_id`) e UUID delle Knowledge Base coinvolte (`kb_ids`).
- **Metrics:** Endpoint `/metrics` protetto da API Key per monitoring operativo.
- **Health:** `/health/ready` ora valida l'integrità dello schema e il contenuto delle tabelle core.

## 4. Sicurezza & Handoff
- **Auth:** Basata su `X-API-Key`. Lo script `bootstrap_auth.ps1` gestisce la creazione della chiave per il frontend.
- **Configurazione:** In produzione, proteggere il file `.env` e non committare segreti reali.
- **Cleanup:** Per resettare completamente i dati: `docker compose down -v`.

## 5. Estensioni Future (Backlog M7+)
Le seguenti funzionalità **NON** sono incluse nella release attuale:
- **RBAC Granulare:** Gestione permessi specifica per singola Knowledge Base.
- **Cloud Connectors:** Integrazione nativa con SharePoint e OneDrive.
- **JWT/OIDC:** Integrazione con Identity Provider Enterprise esterni.

---
*Ultimo aggiornamento: 2026-03-12 — Post-M6-B Basic RBAC Completion.*
