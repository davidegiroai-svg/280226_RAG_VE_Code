# Product Requirements Document (PRD) - Target State

> [!NOTE]
> **Tipo Documento:** TARGET STATE / TO-BE PRODUCT VISION
> **Stato:** Requisiti di Prodotto a Regime
> **Finalità:** Dettagliare le funzionalità desiderate per il sistema RAG.
> **Fonte Primaria Verità:** Il codice per lo stato attuale, questo documento per le feature roadmap.
> 
> **Nota Esplicita:** Questo documento rappresenta il perimetro finale del prodotto. Alcune epiche (es. Connettori Enterprise, Security RBAC) sono attualmente in fase di sviluppo o roadmap futura.

## 1. Feature Status Matrix (Stato Attuale vs Target)

| Feature | Stato | Nota |
| :--- | :--- | :--- |
| **Multi-KB Management** | IMPLEMENTATO | Namespacing via DB attivo. |
| **Ingest Pipeline** | IMPLEMENTATO | Supporto PDF/TXT/MD/CSV/JSON/DOCX. |
| **Watcher (Auto-index)**| IMPLEMENTATO | Polling robusto su Docker/Windows. |
| **RAG Answer Synthesis** | IMPLEMENTATO | SSE Streaming via Ollama attivo. |
| **Auth (API Key)** | IMPLEMENTATO | Header X-API-Key hashata. |
| **Hybrid Search (FTS)** | IMPLEMENTATO | RRF (BM25 + Vector) attivo. |
| **Output Modes** | PIANIFICATO | Summary/Table/JSON (Roadmap M5). |
| **RBAC / ACL Granulari** | ROADMAP | Target per versione Enterprise. |
| **Connettori Cloud** | ROADMAP | SharePoint/OneDrive in roadmap. |
| **Observability (/metrics)**| ROADMAP | Endpoint Prometheus (Pianificato M5). |

## 2. Panoramica Target
Questo documento descrive i requisiti di prodotto per un sistema RAG (Retrieval-Augmented Generation) "Docker-first", agnostico rispetto ai fornitori, che supporta più knowledge base (multi-KB), connettori di ingest flessibili e backend modello sia locali che cloud.


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
- Alta: ingest automatico da cartelle locali, streaming SSE.
- Media: supporto multi-modello, testing A/B qualità risposte.
- Bassa: connettori cloud (SharePoint/S3), output modes avanzati.  
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

### B.4 Feature: Reasoning Answer Synthesis (RAG Avanzato)
**Descrizione**
- Implementare una logica di generazione che non sia una mera sintesi, ma un'analisi ragionata. L'assistente deve:
  - Confrontare informazioni tra diversi documenti.
  - Dedurre risposte a domande complesse (es. "quali interventi per i disabili...") partendo dai dati tecnici.
  - Supportare la `history` per permettere un'analisi iterativa e approfondimenti (drill-down) senza perdita di contesto.
- Il tono deve essere quello di un consulente della Pubblica Amministrazione: preciso, esaustivo e basato su evidenze.

**Roadmap**
- M2: Ottimizzazione del Prompt di Sistema per incoraggiare il ragionamento analitico (Chain of Thought implicito).
- M3: Gestione di risposte multi-pagina e tabelle comparative generate dinamicamente.

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
