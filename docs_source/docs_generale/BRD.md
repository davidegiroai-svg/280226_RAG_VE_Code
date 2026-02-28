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
- BR‑3: Il sistema deve esporre una UI amministrativa per gestione KB e monitoraggio degli ingest.

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
