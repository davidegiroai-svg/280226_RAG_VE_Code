# Architecture Design - Target State

> [!NOTE]
> **Tipo Documento:** TARGET STATE / TO-BE ARCHITECTURE
> **Stato:** Design Architetturale a Regime
> **Finalità:** Descrivere la struttura dei componenti e i flussi del sistema.
> 
> **Nota Esplicita:** I componenti marcati come [ROADMAP] (es. Connector Services Enterprise) non sono inclusi nell'architettura operativa corrente M4.

## 1. Component Status (As-Is vs To-Be)

- **Vector Store (PG + pgvector):** IMPLEMENTATO.
- **Orchestrator API (FastAPI):** IMPLEMENTATO.
- **Auth Middleware (API Key Hash):** IMPLEMENTATO.
- **Watcher / Indexer Service:** IMPLEMENTATO (Polling, supporta PDF/DOCX/TXT/MD/CSV/JSON).
- **Frontend Web (React/Vite):** IMPLEMENTATO.
- **Connector Services (Cloud/S3):** [ROADMAP].
- **Observability (/metrics):** [ROADMAP M5].

## 2. Panoramica dell'architettura
Questo documento descrive l'architettura ad alto livello per il sistema RAG multi‑KB.

Flusso dei dati
1. I connettori sorgente individuano i documenti e li inviano ai Worker di ingest.
2. I worker chunkano i documenti, estraggono metadati, calcolano embedding via il Servizio di embedding e upsertano i chunk nel Vector Store sotto il namespace della KB.
3. Query utente -> Orchestrator API -> ricerca vettoriale (per KB) -> top‑N chunk con metadati -> opzionale Model Adapter sintetizza la risposta finale usando i chunk recuperati.

Deployment
- Manifest Docker Compose o Kubernetes per deployment di produzione.
- Configurazione tramite variabili d'ambiente e injection dei segreti tramite secret manager.

Decisioni di design
- Separare embedding e logica LLM tramite adapter per rimanere agnostici rispetto ai provider.
- Usare un DB relazionale con estensione vettoriale per semplificare operazioni e backup.
- Conservare la provenienza a livello di chunk per garantire citazioni trasparenti e auditabilità.

Note operative
- Registrare output ed errori dei job di ingest; fornire audit trail per ogni KB.
- Documentare rotazione chiavi e gestione segreti nel runbook.

PoC ed esportabilità
- L'architettura privilegia la possibilità di costruire un PoC locale dimostrabile al cliente (Comune di Venezia). I deliverable del PoC devono includere servizi containerizzati (Docker Compose o manifest k8s), script di inizializzazione DB, configurazioni di esempio e un runbook per permettere al team IT del cliente di riprodurre e mettere in produzione la soluzione.


---

## Estensioni architetturali (UI, watcher, RAG, enterprise)

Questa sezione integra la panoramica con i componenti e i flussi necessari per le estensioni emerse (MVP → roadmap).

### Componenti aggiuntivi
- **Frontend Web (UI)**: web app minimale per selezione KB/namespace, query, visualizzazione fonti (expand/collapse) e (opzionale) pagina Documenti con upload e stato indicizzazione.
- **Upload API**: endpoint di backend per ricevere file via UI/API e salvarli in una inbox per KB (convenzione PoC: volume `/data/inbox/<kb>/`).
- **Watcher / Indexer Service**: servizio separato che effettua polling sulle inbox per KB, avvia ingest su nuovi/modificati e propaga delete (cleanup) quando i file spariscono dalla sorgente.
- **LLM Generator**: componente per answer synthesis (RAG completa) sopra al retrieval; usa prompt orchestration e policy di grounding.
- **Response Router / Templates**: layer che seleziona template e schema di output (`summary`, `table`, `checklist`, `extract-json`) e valida JSON quando richiesto.
- **PDF Page Parser**: pipeline di parsing che preserva metadata pagina/sezione per citazioni “serie”.
- **Auth Middleware**: Autenticazione tramite Header `X-API-Key` con validazione hash su DB.
- **Observability stack**: logging strutturato, metriche e tracing con `request_id`.
- **Evaluation harness (offline)**: pipeline separata per eseguire benchmark e regressioni su retrieval/RAG.
- **Connector services (roadmap)**: moduli con scheduler/queue per ingest e sync incrementale da SharePoint/S3/Drive/SAP/Salesforce.
- **Agent framework (opzionale)**: orchestratore + agenti specializzati per routing multi‑modal e tool calling.

### Flussi chiave (sequenze)
**1) Query via UI (Reasoning RAG + conversational synthesis)**
1. UI → Orchestrator API: `POST /api/v1/query` (kb, top_k, mode, synthesize, `history`)
2. Orchestrator → Retrieval pipeline: hybrid retrieve (FTS + Vector) → top chunks
3. Orchestrator → LLM Generator: Esegue il "Reasoning Step". L'IA analizza i chunk, cerca correlazioni e genera una risposta discorsiva esaustiva basandosi anche sulla `history`.
4. Orchestrator → Response Router: Formatta l'output (Markdown, tabelle) per una lettura ottimale.
5. API → UI: Messaggio assistente (ragionato) + Citazioni puntuali + Fonti espandibili.

**2) Upload documenti via UI/API**
1. UI/curl → Upload API: `POST /api/v1/upload?kb=...` (multipart)
2. Backend salva file in inbox per KB e restituisce `upload_id`/`job_id`
3. Watcher rileva file nuovo/modificato → avvia ingest worker
4. Ingest worker chunking + embedding + upsert nel vector store

**3) Delete propagation (senza bottone)**
1. Watcher (polling) rileva che un file noto non è più presente in inbox
2. Backend/worker marca Documento come `is_deleted=true` (o rimuove fisicamente) e:
   - elimina/disattiva i chunk correlati nel vector store
   - registra evento in audit log

**4) Citazioni pagina-livello (PDF)**
1. PDF Page Parser estrae testo pagina-per-pagina e produce chunk con `page_start/page_end` e `doc_title`
2. Query/answer includono citations strutturate con pagina e (se disponibile) sezione

### Considerazioni di deployment
- In PoC: UI e API possono essere co‑locate; watcher come servizio separato (container).
- In produzione: separazione più netta (API stateless + worker/watcher scalabili), policy engine centralizzato, TLS obbligatorio e segreti in secret manager.

---

Data aggiornamento: 2026-03-03
