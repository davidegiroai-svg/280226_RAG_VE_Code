# Business Requirements Document (BRD) - Target State

> [!NOTE]
> **Tipo Documento:** TARGET STATE / TO-BE VISION
> **Stato:** Visione di Prodotto a Regime
> **Finalità:** Definire il valore di business complessivo e il perimetro del prodotto finale.
> **Ambito Temporale:** Progetto complessivo (Post-M4).
> 
> **ATTENZIONE:** Questo documento descrive lo stato target del progetto e non deve essere interpretato come conferma che tutte le capacità qui indicate (es. connettori cloud, RBAC enterprise) siano già implementate. Per lo stato reale consultare `.planning/STATE.md`.

## 1. Stato Implementato Attuale (Short-Term: M1-M3)
- Sistema RAG funzionante con core pipeline Docker-first.
- Ingest: Filesystem locale (PDF, TXT, MD, CSV, JSON, DOCX).
- Search: Vector, FTS e Hybrid Search (RRF).
- UI: Frontend React/Vite completo.
- Security: Autenticazione via API Key (X-API-Key Header).
- AI: Integrazione Ollama per Embedding e LLM Synthesis (Streaming SSE).

## 2. Gap Analysis vs Target Vision
- **Conformità Enterprise:** Attualmente manca RBAC/ACL granulare (implementata solo API Key).
- **Integrazioni Cloud:** I connettori SharePoint/OneDrive sono in roadmap (target BR-1).
- **Analisi Avanzata:** Reportistica costi e query logging avanzato sono target M5+.

## 3. Requisiti di Business Principali (Target)
- BR‑1: [ROADMAP] Il sistema deve indicizzare e cercare documenti da almeno tre tipi di sorgente (filesystem, cloud drive, pagine web).
- BR‑2: [FUTURE] Il sistema deve fornire report di utilizzo e stime di costo per query modelli cloud.
- BR‑3: [DONE] Il sistema deve esporre una UI web (admin + query).
- BR‑4: [DONE] Il sistema deve supportare caricamento documenti via UI/API.
- BR‑5: [DONE] Il sistema deve supportare indicizzazione automatica e propagazione delle cancellazioni (Watcher).
- BR‑6: [PARTIAL] Il sistema deve supportare auditabilità e compliance (API Key attiva, RBAC target).


Criteri di successo
- Completare il primo pilota con il cliente target entro X settimane e ottenere soddisfazione utente ≥ target.

Rischi
- Requisiti di privacy e compliance per documenti sensibili.
- Costi legati a API di modelli gestiti in caso di uso intensivo.

Vincoli
- Documentare l'hardware minimo richiesto per un deployment on‑premise iniziale.

PoC e consegna
- Il piano operativo prevede lo sviluppo di un PoC eseguibile localmente per demo al Comune di Venezia; i deliverable devono includere artefatti esportabili (configurazioni Docker Compose/k8s, script DB, esempi di config e runbook) per il passaggio al team IT del cliente.
PoC and Handoff Intent
- The immediate plan is to build a runnable PoC on the local workstation suitable for client demos (Comune di Venezia). Deliverables must include exportable configuration and deployment artifacts so the client's IT teams can reproduce and operate the service within their infrastructure.
# Business Requirements Document (BRD)

Data: 2026-02-26

## Appendix A – RAG per Venezia

1. Sintesi esecutiva
- Il progetto fornisce alla governance locale uno strumento che trasforma la raccolta documentale in conoscenza immediatamente utilizzabile, riducendo attriti operativi e migliorando decisioni e compliance.

2. Bisogni aziendali
- Velocizzare accesso alle informazioni critiche (bandi, progetti, programmi).
- Migliorare qualità delle risposte a quesiti tecnici e amministrativi.
- Ridurre errori di interpretazione documentale e supportare auditabilità.

3. Benefici attesi / ROI (indicativo)
- Efficienza operativa: riduzione del tempo speso in ricerca documentale (risparmio ore/uomo).
- Riduzione ritardi amministrativi dovuti a informazioni mancanti o disperse.
- Valore intangibile: miglioramento della trasparenza e servizio al cittadino.
- ROI: dipende dal volume di richieste e dal costo del personale; obiettivo di break-even operativo entro 6–12 mesi su utilizzo moderato.

4. Processo attuale e gap
- Processo attuale: ricerca manuale in cartelle e PDF, comunicazioni via email, versioning limitato.
- Gap: nessuna indicizzazione semantica, mancanza di tracciatura centralizzata, tempi di risposta elevati.

5. Impatti organizzativi
- Ruoli e responsabilità: nominare un owner per ingestion/categorizzazione, responsabile IT per deploy e sicurezza, referente legale per compliance.
- Formazione: breve training (1 sessione 60–90min) per utenti chiave e admin.
- Process change: introdurre routine di caricamento documenti e validazione metadata.

6. Requisiti business vincolanti
- I dati sensibili non devono essere committati al repository.
- Soluzione preferibilmente Docker-first e portable su macchine cliente.
- Possibilità di eseguire interamente on‑premise per dati sensibili.

Richieste operative aggiuntive (security/hand‑off)
- Autenticazione/RBAC per accesso API e UI (ruoli admin vs user).
- Policy di retention per i log delle query; il campo testo viene trattato come dato personale e va anonimizzato/cancellato.
- Criteri di redazione/anonymization per estratti citati.
- Distinzione PoC vs produzione: PoC locale può funzionare senza TLS, la versione di produzione deve obbligatoriamente usare TLS e chiavi rotative.

7. KPI e metrica di business
- Tempo medio per reperire informazione (baseline → target)
- Percentuale di richieste risolte senza escalation
- Numero di documenti ingestati per settimana
- Adozione: numero di utenti attivi mensili

8. Roadmap di alto livello e milestone commerciali
- M3 (Completata): Implementazione UI Completa, Streaming SSE, Ingest worker (PDF/DOCX), Watcher, API Key Auth.
- M4 (Completata): Stabilization & Release Hardening (consolidamento bootstrap, cleanup repo, DOCX end-to-end, Smoke Test).
- M5 (Pianificata): Observability & Advanced Query Logging.

9. Rischi business
- Rischio di mancata adozione → mitigare con formazione e POC con utenti reali.
- Rischio legato a privacy/consenso → mitigare con policy e storage locale.
- Rischio costo HW per modelli locali → mitigare con opzione hybrid provider.

10. Decisioni finanziarie e approvazioni richieste
- Confermare scelta zero-budget/open-source o budget per servizi esterni (se necessario).
- Approvare team operativo e assetto per rotazione chiavi e pulizia storia Git.

Fine BRD.


---

## Appendix B – Estensioni emerse (UI, ingest, qualità, security)

Questa appendice integra i requisiti business con le estensioni emerse durante l’allineamento tecnico-funzionale. Le voci sono organizzate per macro‑tema e possono essere incrementali (MVP → roadmap).

### B.1 User journey: Frontend Web (UI semplice e intuitiva)
**Scenario tipico (utente non tecnico / funzionario):**
1. Seleziona la Knowledge Base (KB) o un namespace dal menu.
2. Inserisce la domanda nel box query, imposta `top_k` e (in roadmap) la modalità di output.
3. Ottiene risultati con risposta/sintesi e **fonti** consultabili (expand/collapse).
4. (Opzionale) Apre la pagina “Documenti” per caricare file e verificare lo stato di indicizzazione.

**Benefici business attesi:**
- Adozione più rapida (riduzione barriera d’ingresso rispetto a CLI).
- Riduzione tempo di ricerca e di “caccia al PDF giusto”.
- Migliore tracciabilità: l’utente vede e riapre le fonti.

### B.2 Obiettivo operativo “zero frizione”: upload + indicizzazione automatica
Per ridurre manualità e rischi operativi, l’esperienza desiderata è:
- Caricamento documenti via UI/API (senza uso di Esplora Risorse come prerequisito).
- Indicizzazione automatica (watcher) su cartelle di inbox per KB.
- Propagazione delete: se un file viene rimosso dalla sorgente, il sistema rimuove (o marca come eliminati) documenti/chunk nel DB, senza bottone dedicato.

**Benefici business attesi:**
- Continuità operativa: meno passaggi manuali, meno errori.
- Coerenza tra repository sorgente e KB indicizzata.
- Maggior frequenza di aggiornamento del corpus (più “freshness” → più fiducia).

### B.3 Risposta "Reasoning RAG" e Sintesi Esperta (stile NotebookLM)
Il sistema non deve limitarsi a recuperare estratti, ma deve fungere da assistente intelligente:
- **Analisi e Ragionamento**: L'assistente analizza il contesto di più documenti per fornire una risposta "ragionata", che connetta punti diversi (es. legare un bando a un programma di finanziamento).
- **Risposta Discorsiva**: L'output deve essere fluido, istituzionale ma colloquiale, evitando lo stile "copia-incolla" e preferendo una spiegazione logicamente strutturata.
- **Drill-down Cognitivo**: Supporto alla conversazione per esplorare dettagli citati nella risposta precedente, con l'IA capace di mantenere il filo del discorso specialistico.

**Rischi & mitigazioni (business):**
- Rischio di eccessiva creatività → Mitigazione: Grounding rigoroso e obbligo di citazione per ogni affermazione chiave.
- Precisione delle fonti → Mitigazione: Citazione dinamica [Fonte X] integrata nel testo discorsivo.

### B.4 Auditabilità, security & compliance (Enterprise RAG)
Per contesti PA/enterprise sono necessari:
- Autenticazione e controllo accessi (RBAC/ACL) su KB e documenti.
- Audit log (chi ha chiesto cosa e quando) con retention.
- Cifratura in transito (TLS) e, se richiesto, at‑rest.
- Policy di trattamento dei log (query text come dato potenzialmente personale).

### B.5 Evoluzioni enterprise: connettori, qualità retrieval, osservabilità
Roadmap tipica:
- Connettori (SharePoint / S3 / Drive / SAP / Salesforce) con sync incrementale e gestione credenziali/ACL.
- Retrieval upgrades: rewrite/intent, hybrid search, reranker, caching.
- Evaluation harness: dataset query reali, metriche (Precision@K, MRR), regressioni automatiche.
- Osservabilità: metriche ingest/query, tracing con `request_id`, dashboard e alert.
- (Opzionale) Multimodale e multi‑agent: ingest tabelle/immagini (OCR/vision) e agenti specializzati.

---

Data aggiornamento: 2026-03-03
