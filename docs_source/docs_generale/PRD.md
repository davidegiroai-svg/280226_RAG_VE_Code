Documento dei Requisiti di Prodotto (PRD)

Panoramica
Questo documento descrive i requisiti di prodotto per un sistema RAG (Retrieval-Augmented Generation) "Docker-first", agnostico rispetto ai fornitori, che supporta più knowledge base (multi-KB), connettori di ingest flessibili e backend modello sia locali che cloud. Il contenuto è neutro rispetto a layout o artefatti di sviluppo sperimentali.

Obiettivi
- Fornire risposte accurate e spiegabili combinando ricerca vettoriale su più KB e sintesi tramite LLM.
- Supportare deployment on‑premise e cloud con runbook operativi chiari.
- Abilitare ingestione sicura da fonti aziendali comuni (condivisioni file, OneDrive/SharePoint, Google Drive, S3, PDF, DOCX).
  * *Nota MVP Venezia*: la priorità iniziale è su filesystem locali e OneDrive/SharePoint; gli altri connettori (S3, crawling web) rientrano nella roadmap del prodotto generico.
- Permettere la selezione di provider modello (runtime locale o API provider) tramite un "Model Adapter" pluggabile.

Caratteristiche principali
- Gestione multi‑KB con namespacing.
- Connettori di ingest con sincronizzazione incrementale e monitoraggio.
- Pipeline di chunking + embedding con parametri configurabili.
- Archiviazione vettoriale con metadati di provenienza, versioning e politiche di pruning.
- Orchestrazione query e prompt con grounding delle fonti e citazioni.
- Interfaccia amministrativa per upload, mappatura cartelle e revisione log di ingest.
- Monitoraggio, logging e report di costo/uso.

Metriche di successo
- MRR (Mean Reciprocal Rank) sulle porzioni recuperate ≥ baseline target (da definire).
- Punteggio di soddisfazione utente ≥ target dopo la prima release.
- Tempo di ingest per 1GB di corpus < 30 minuti sull'hardware raccomandato.

Vincoli e assunzioni
- Stack target: servizio API backend, vector store (Postgres+pgvector o equivalente), modelli di embedding (locali o gestiti) e UI opzionale.
- Nessun lock‑in su vector store o provider di modelli.
- I segreti non devono essere commessi nel controllo versione; usare variabili d'ambiente o secret manager.

Fuori dallo scope
- Costruire un database vettoriale proprietario e chiuso.
- Integrazioni che richiedono accesso a internals di piattaforme terze a pagamento oltre le API standard.

Nota PoC ed esportabilità
- Obiettivo immediato: sviluppare un Proof of Concept (PoC) eseguibile sulla macchina di sviluppo per demo al cliente (Comune di Venezia). Il PoC deve essere auto‑contenuto, "Docker‑first" e facilmente esportabile: includere manifest Docker Compose o k8s, script di inizializzazione DB, file di configurazione di esempio e un breve runbook per la migrazione nell'ambiente IT del cliente.
Note: PoC and Export Path
- The immediate objective is to develop a Proof of Concept (PoC) on the local development machine to demonstrate functionality to the client (Comune di Venezia). The PoC should be self-contained, Docker-first, and easily exportable so that delivered artifacts (configuration, Docker Compose or k8s manifests, DB schema, and runbook) can be migrated into the client's IT environment for production onboarding.

# Appendix A – Product requirements for the Venezia pilot (MVP)

Data: 2026-02-26

1. Scopo
- Fornire a enti e operatori locali uno strumento di ricerca conversazionale (RAG) che renda interrogabili in modo rapido, verificabile e tracciabile i documenti relativi alla programmazione (Europea, Nazionale e Regionale) i bandi e i progetti.

2. Problema da risolvere
- Dati e documenti critici sono sparsi in cartelle, PDF e sistemi diversi; l'accesso è lento, dispersivo e non facilmente riutilizzabile per supportare risposte operative e decisioni.

3. Obiettivi di business
- Rendere interrogabili i contenuti principali (programmi, progetti, bandi) con risposte contestualizzate e riferimenti alle fonti.
- Ridurre il tempo medio di reperimento informazione da ore a minuti.
- Fornire un canale sicuro e auditabile per la consultazione interna ed esterna.

4. Utenti e stakeholder
- Utenti primari: operatori di progetto, funzionari amministrativi, responsabili di bandi, staff tecnico locale.
- Stakeholder: direzione progetto, team IT del cliente, team legale/qualità, stakeholder esterni (partner, consulenti).

5. Casi d'uso principali
- Ricerca rapida: un operatore chiede informazioni su un bando e riceve risposta sintetica con link/estratti del documento.
- Verifica normativa: controllo di clausole specifiche in documenti PDF di gara o normativa locale.
- Ingest automatico: nuovi documenti inseriti nelle cartelle `programmi/`, `progetti/`, `bandi/` vengono automaticamente indicizzati.
- Audit e tracciamento: log delle query e delle fonti consultate per verifica e compliance.

6. Priorità (MVP)
- Alta: ingest automatico da cartelle locali/OneDrive/SharePoint.
- Media: supporto multi-modello (adapter per provider locali e cloud), testing A/B qualità risposte.
- Bassa: integrazioni avanzate (n8n), dashboard analitiche complesse.  
(Nota: la versione pilota è pensata a zero budget e si concentra su sorgenti locali e OneDrive/SharePoint; supporto a S3 e crawling web è previsto solo nelle fasi successive del prodotto generico.)

7. Metriche di successo
- Riduzione del tempo medio per reperire informazioni del 70% su dataset campione.
- Precision@K dei documenti recuperati ≥ 80% su test di validazione (campione).
- Tempo medio di risposta (end-to-end) < 2s per retrieval; generazione LLM dipendente dal provider.

8. Vincoli
- Zero-budget preferenziale: soluzioni open-source e locali per il PoC.
- Nessun secret nel repository; deployment Docker-first.
- Privacy e compliance con regolamenti locali (GDPR) per i dati sensibili.

9. Assunzioni
- Cliente fornisce accesso a documenti principali (cartelle locali o OneDrive/SharePoint).
- Hardware di staging sufficiente per embeddings locali o possibilità di usare provider esterni.

10. Deliverables MVP
- Documentazione A-D aggiornata, `docker-compose` spec, ingest worker POC, backend API minimale, Admin UI POC, test dataset e checklist di quality-check.

Fine Appendice.
