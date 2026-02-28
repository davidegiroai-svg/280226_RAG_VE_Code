Panoramica dell'architettura

Scopo
Questo documento descrive l'architettura ad alto livello per il sistema RAG multi‑KB. Le descrizioni sono generiche e non fanno riferimento a directory o artefatti sperimentali specifici.

Componenti
- Worker di ingest: connettori che acquisiscono dati dalle sorgenti (filesystem, drive cloud, API), trasformano e chunkano i documenti, estraggono metadati e inviano chunk+embedding al vector store.

- Servizio di embedding: componente pluggabile che chiama modelli di embedding locali o remoti. Può essere co‑locato con i worker o eseguito come servizio separato.

- Vector store: store principale per il retrieval con indici di similarità vettoriale, supporto per namespace per più KB e colonne metadati per la provenienza (raccomandazione: PostgreSQL + pgvector o store compatibile).

- Orchestrator API: backend API (REST) che espone controllo ingest, endpoint di query, health e operazioni di gestione.

- Model Adapter: livello di astrazione che instrada le chiamate LLM a runtime locali (es. container modello) o a provider esterni; si occupa di assemblare i prompt, budgeting token e filtri di sicurezza.

- Admin UI: interfaccia web leggera per gestione KB, monitoraggio ingest e analytics di base.

- Scheduler / Job: gestisce schedulazione degli ingest, retry e job in background.

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
