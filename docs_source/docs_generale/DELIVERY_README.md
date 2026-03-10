# Delivery README - Runbook Operativo (M4 Release Hardened)

> [!NOTE]
> **Tipo Documento:** RUNBOOK / DELIVERY OPERATIONS
> **Stato:** ATTIVO (Post-M4)
> **Finalità:** Istruzioni operative reali per il deploy e l'avvio del sistema.
> **Versione:** 2.0 (Stabilized)

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

## 3. Sicurezza & Handoff
- **Auth:** Basata su `X-API-Key`. Lo script `bootstrap_auth.ps1` gestisce la creazione della chiave per il frontend.
- **Configurazione:** In produzione, proteggere il file `.env` e non committare segreti reali.
- **Cleanup:** Per resettare completamente i dati: `docker compose down -v`.

## 4. Estensioni Future (Roadmap M5+)
Le seguenti funzionalità **NON** sono incluse nella release M4 ma sono pianificate:
- **Query Logging:** Tracciamento persistente delle query in database.
- **Monitoring:** Endpoint `/metrics` per integrazione con Prometheus/Grafana.
- **RBAC:** Gestione permessi granulare per Knowledge Base.
- **Cloud Connectors:** Integrazione con SharePoint e OneDrive.

---
*Ultimo aggiornamento: 2026-03-10 — Post-M4 Release Hardening.*
