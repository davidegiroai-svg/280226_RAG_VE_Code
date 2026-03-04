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
- Frontend web minimale per query (KB/namespace, top_k, fonti) e gestione documenti (upload/stato).
- Upload documenti via UI/API con salvataggio in inbox per KB.
- Indicizzazione automatica (watcher/polling) e delete propagation (coerenza sorgente↔KB).
- Answer synthesis (RAG completa) e output modes (summary/table/checklist/extract-json).
- Citazioni pagina-livello per PDF (titolo/pagina/sezione).
- Observability (metriche/log/tracing) ed Evaluation harness (Precision@K, MRR, regressioni).
- Retrieval upgrades (rewrite, hybrid search, reranker, caching).
- Enterprise connectors (SharePoint/S3/Drive/SAP/Salesforce) con sync incrementale e ACL.
- Security & Compliance (auth, RBAC/ACL, audit log, TLS, retention).

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


---

## Appendix B – Roadmap funzionale estesa (feature epics)

Questa appendice formalizza le estensioni emerse e le colloca in una roadmap coerente. Le milestone sono indicative e possono essere riallineate in base a vincoli di budget e priorità del pilota.

### B.1 Feature: Frontend v1 (Web UI minimale)
**Descrizione**
- Web app minimale con:
  - selezione KB/namespace
  - box query + `top_k` + (roadmap) modalità output
  - risultati con fonti (expand/collapse)
  - pagina “Documenti” con upload e stato indicizzazione (opzionale)

**User stories**
- Come *utente*, voglio selezionare una KB e fare una query senza usare CLI.
- Come *utente*, voglio vedere le fonti e aprirle/espanderle per verificare.
- Come *admin*, voglio caricare documenti e vedere lo stato ingest/indicizzazione.

**Criteri di completamento (MVP UI)**
- UI funzionante su localhost; supporto a almeno 1 KB; query con `top_k`.
- Lista fonti con metadati minimi e toggle expand/collapse.
- Gestione errori (KB non selezionata, query vuota, timeout).

### B.2 Feature: Upload docs (UI/API)
**Descrizione**
- Endpoint upload (es. `POST /api/v1/upload?kb=...`) che salva file in una inbox per KB (es. `/data/inbox/<kb>/`) e avvia il flusso di ingest.

**User stories**
- Come *admin*, voglio caricare un PDF/DOCX via UI o curl.
- Come *admin*, voglio ricevere conferma (id file/job) e vedere lo stato.

### B.3 Feature: Auto-index + delete propagation (watcher)
**Descrizione**
- Servizio “watcher” che:
  - indicizza automaticamente file nuovi/modificati nell’inbox della KB
  - rimuove dal DB documenti/chunk quando i file vengono cancellati
  - è robusto su Windows/Docker: preferibile polling rispetto a soli eventi filesystem

**Note di prodotto**
- Principio “zero frizione”: non richiede un bottone “re-index”.
- Gestisce consistenza e conflitti (file sostituito, rename, duplicati).

### B.4 Feature: Answer synthesis (RAG completa)
**Descrizione**
- Aggiungere un livello di generazione che sintetizza i top chunk in una risposta breve, strutturata e non ridondante, con citazioni e fallback.

**Roadmap**
- M2: endpoint dedicato (`/api/v1/answer`) o flag su query (`synthesize=true`).
- M3: miglioramenti grounding (policy anti-hallucination, guardrails).

### B.5 Feature: Output modes (summary/table/checklist/extract)
**Descrizione**
- Stesso retrieval, output variabile in base a richiesta o parametro `mode`:
  - `summary`, `bullets`, `table`, `checklist`, `qa`, `extract-json`
- Consiglio: per `table` / `extract-json` l’LLM produce JSON strutturato validato da schema, la UI renderizza.

### B.6 Feature: Page-level citations (citazioni “serie”)
**Descrizione**
- Ingest PDF pagina-per-pagina o con mapping pagina→offset per supportare citazioni con:
  - titolo documento
  - pagina/e (start/end)
  - sezione (quando disponibile)

### B.7 Epic: Connectors enterprise
**Scope**
- Connettori (SharePoint, S3, Drive, SAP, Salesforce) con:
  - ingest/sync incrementale
  - gestione credenziali
  - mapping ACL

### B.8 Epic: Security & Compliance
**Scope**
- Autenticazione (token/session)
- RBAC/ACL per KB e documenti
- Audit log query/azioni
- TLS e encryption at rest (se richiesto)
- Retention log e policy GDPR

### B.9 Epic: Quality (Evaluation harness)
**Scope**
- Dataset query reali
- Metriche retrieval: Precision@K, MRR
- Regressioni automatiche (prima/dopo)
- Dopo answer synthesis: metriche grounding/faithfulness (es. punteggio di citazione/coverage)

### B.10 Epic: Retrieval quality upgrades
**Scope**
- Query rewriting / intent detection
- Hybrid search (BM25 + vector)
- Reranker (cross-encoder)
- Caching (embedding cache / result cache)

### B.11 Epic: Observability
**Scope**
- Metriche: latency ingest/query, error rate
- Log strutturati con `request_id`
- Dashboard (minima) + alert
- Health checks operativi

### B.12 Epic (opzionale): Multi-modal / Multi-agent
**Scope**
- Ingest tabelle/immagini (OCR/vision)
- Agenti specializzati + orchestratore (routing e tool calling)
- Policy e logging per routing

---

Data aggiornamento: 2026-03-03
