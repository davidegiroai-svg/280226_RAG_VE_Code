Documento dei Requisiti di Business (BRD)

Scopo
Questo BRD documenta la giustificazione di business, la proposta di valore, gli stakeholder e i requisiti di alto livello per il prodotto RAG multi‑KB descritto nel PRD.

Obiettivi di business
- Ridurre il tempo per reperire informazioni rilevanti all'interno di documenti e KB aziendali.
- Migliorare la qualità decisionale fornendo risposte fondate e citate.
- Offrire una soluzione portabile e a basso costo, eseguibile on‑premise o in cloud.

Clienti target e stakeholder
- Pubblica amministrazione e team locali che necessitano accesso consolidato a documenti di gare, finanziamenti e programmi.
- ONG e imprese di medie dimensioni con repository documentali distribuiti.
- Stakeholder interni: Product Manager, Lead Engineering, Responsabile Sicurezza, Operations.

Proposta di valore
- Risposte più rapide con provenienza riducono il costo di ricerca.
- Deploy riproducibile senza lock‑in riduce costi di fornitore e migliora il controllo dei dati.

Requisiti di business principali
- BR‑1: Il sistema deve indicizzare e cercare documenti da almeno tre tipi di sorgente (filesystem, cloud drive, pagine web) al lancio.  
  * Per il pilot di Venezia la copertura minima è filesystem locali e OneDrive/SharePoint; gli altri tipi sono previsti nel prodotto generico successivo.
- BR‑2: Il sistema deve fornire report di utilizzo e stime di costo per query quando si usano modelli cloud.
- BR‑3: Il sistema deve esporre una UI web (admin + query) per selezione KB/namespace, ricerca, visualizzazione fonti e monitoraggio ingest (incluso upload documenti dove previsto).
- BR‑4: Il sistema deve supportare caricamento documenti via UI/API per ridurre attrito operativo e velocizzare l’onboarding.
- BR‑5: Il sistema deve supportare indicizzazione automatica e propagazione delle cancellazioni (delete sync) per garantire coerenza tra sorgente e KB.
- BR‑6: Il sistema deve supportare auditabilità e compliance (citazioni, RBAC/ACL, audit log, retention) per contesti PA/enterprise.

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
- M0 (0–30 giorni): bonifica segreti, definizione schema DB e docker-compose spec, POC ingest.
- M1 (30–90 giorni): MVP deployabile su staging (ingest automatico, retrieval, admin UI minimale).
- M2 (90–180 giorni): ottimizzazione multi-model, test di resilienza, handoff cliente e training.

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

### B.3 Risposta “pronta” e output differenziati (RAG completa)
Oltre al retrieval di estratti, il valore percepito aumenta con:
- **Answer generation**: sintesi sopra i top chunk recuperati.
- **Output dinamico**: summary / bullets / table / checklist / extract-json, selezionabile da UI o parametro.

**Rischi & mitigazioni (business):**
- Rischio hallucination → mitigare con grounding, citazioni e fallback a “solo estratti”.
- Requisito di trasparenza → citazioni “serie” (titolo, pagina, sezione) dove possibile.

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
