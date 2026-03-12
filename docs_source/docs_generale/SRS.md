# Software Requirements Specification (SRS) - Target State

> [!NOTE]
> **Tipo Documento:** TARGET STATE / TO-BE TECHNICAL SPEC
> **Stato:** Requisiti Tecnici a Regime
> **Finalità:** Definire le specifiche funzionali e non funzionali del sistema.
> **Ambito Temporale:** Progetto complessivo.
> 
> **Nota Esplicita:** Alcuni requisiti (es. FR-1 cloud connectors, FR-11 RBAC) sono target futuri e non presenti nella release M4 corrente.

## 1. Stato dei Requisiti Funzionali

| ID | Requisito | Stato | Nota |
| :--- | :--- | :--- | :--- |
| **FR-1** | Ingest Multi-fonte | PARZIALE | Filesystem OK, Cloud/Web ROADMAP. |
| **FR-2** | Embedding & Vectorization | IMPLEMENTATO | Ollama 768d attivo. |
| **FR-3** | Query API & SSE Streaming| IMPLEMENTATO | Endpoint `/api/v1/query/stream` attivo. |
| **FR-9** | Output Modes Advanced | PIANIFICATO | Roadmap M7+. |
| **FR-11**| Security Auth (Basic RBAC)| IMPLEMENTATO | Ruoli `admin`/`user` (M6-B). |
| **FR-11.1**| Audit Logging | IMPLEMENTATO | user_id/kb_ids tracking (M6-A). |
| **FR-12**| Observability | IMPLEMENTATO | Health & Metrics operative. |

---
Data aggiornamento: 2026-03-10
## 2. Introduction
This SRS specifies functional and non-functional requirements for the RAG multi-KB system.

3. Non-Functional Requirements
- NFR-1: Security
  - All secrets stored outside source control; use env vars or secret manager.
  - Data in transit must use TLS; sensitive data at rest should be encrypted when required.
  - Authentication & RBAC (admin vs user) required for sensitive endpoints.
  - Query logs contain text; retention policy and anonymization rules must be defined.
  - PoC may run without TLS on localhost; production deployments mandate TLS.

- NFR-2: Performance
  - Typical query latency (vector search + optional LLM synth) target: < 2s for search, + model latency.

- NFR-3: Scalability
  - System must scale horizontally for ingestion workers and API instances.

4. APIs (example)
- POST /api/v1/ingest - start ingestion job (body: connector config, KB id)
- GET /api/v1/ingest/{jobId} - job status and logs
- POST /api/v1/query - {kb_ids:[], query: string, model_options:{}}
- GET /api/v1/kbs - list KBs and metadata

5. Acceptance Criteria
- Ingest a representative corpus (1GB) with no unrecoverable failures and complete metadata extraction.
- Query results must include at least one correct, source-cited passage for 80% of benchmark queries.

---

## Appendix A – Requirements for the Venezia pilot (MVP)

Data: 2026-02-26

1. Scopo
- Specificare requisiti funzionali e non funzionali per il sistema RAG che indicizza e rende interrogabili documenti di `programmi/`, `progetti/`, `bandi/` per la Città di Venezia.

2. Visione generale del sistema
- Componenti principali: ingest worker, embedding service (adapter), vector store (Postgres+pgvector), backend (FastAPI), model adapter (LLM provider), frontend admin/UI, deployment Docker Compose.

3. Requisiti funzionali (FR)
- FR-1 Ingest automatico: il sistema deve scaricare/monitorare cartelle locali o OneDrive/SharePoint e avviare pipeline di conversione + chunking.
- FR-2 Chunking e metadati: ogni documento deve essere suddiviso in segmenti con metadata `source_path`, `page`, `kb_namespace`, `ingest_date`.
- FR-3 Embedding: il sistema deve calcolare embedding per ogni chunk tramite `EmbeddingAdapter` (supportare SentenceTransformers e provider remoto).
- FR-4 Upsert in vector store: vettori e metadati devono essere memorizzati in Postgres con colonna `kb_namespace` per isolare KB; l'uso di `kb_id` derivato da namespace è accettabile.
- FR-5 Query API: esporre endpoint `/api/v1/query` che riceve query testuale e opzioni (KB target, top_k) e ritorna risposta sintetica + lista dei chunk fonte ordinale.
- FR-6 Routing multi-KB: il backend deve decidere la KB target via regole metadata-based e fallback embedding-based.
- FR-7 Model selection: l'`ModelAdapter` deve poter selezionare provider runtime basato su env/feature flag e policy fallback.
- FR-8 Admin UI: mapping cartelle → KB, stato ingest, log errori, selezione provider LLM, upload manuale drag&drop.
- FR-9 Health & monitoring: endpoint `/health`, `/metrics`, log di errori e metriche base.

4. Requisiti non funzionali
- (ereditati dall’appendice principale; stesso NFR di sicurezza, performance e scalabilità)

5. Criteri di accettazione
- Ingestione e query come per il prodotto generico, limitata a sorgenti locali e OneDrive/SharePoint.

---

6. Interfacce minime
- POST `/api/v1/query` {"query":string, "kb":string?, "top_k":int?} -> {"answer":string, "sources":[{id,score,source_path,excerpt}]}

7. Modello dati sintetico
- Tabella `knowledge_base` con campi: kb_id(uuid PK), namespace(text unique), created_at(timestamp)
- Tabella `kb_documents` con campi: id(uuid), kb_id(uuid FK), kb_namespace(text) denormalizzato, source_path(text), chunk_text(text), content_hash(text), metadata(jsonb), embedding(vector), ingest_date(timestamp)
  - vincolo unico consigliato: UNIQUE(kb_id, content_hash) per evitare duplicati all'interno della stessa KB.

8. Deployment e test
- Deployment consigliato per PoC: `docker-compose` con Postgres+pgvector, backend, worker e servizio modello opzionale.
- Test di accettazione: ingest E2E, query E2E e controlli di sicurezza su segreti.

9. Sicurezza e operazioni
- API admin protette; auditing di operazioni critiche; politica di gestione segreti documentata.

10. Obiettivo PoC
- Lo scopo immediato è ottenere un PoC eseguibile localmente per dimostrare la soluzione al Comune di Venezia. Fornire manifesti di deployment (Docker Compose o k8s), script di init DB, esempi di configurazione e un breve runbook per consentire al team IT del cliente di riprodurre e mettere in produzione la soluzione.

Fine SRS


---

## 11. Addendum – Extended Requirements (UI, Upload, Watcher, RAG, Enterprise)

This addendum captures newly agreed requirements and makes them testable. It is implementation-agnostic, but defines interfaces and expected behaviors.

### FR-5: Frontend Web UI (Conversational RAG)
- Provide a web UI that acts as an advanced conversational assistant (NotebookLM-style):
  - KB / namespace selection.
  - Chat interface supporting continuous message exchange and follow-up queries.
  - LLM answers formatted with advanced Markdown (tables, lists).
  - Explicit rendering of citations and context sources dynamically expandable below each AI message.
  - optional “Documents” page with upload and indexing status.
- UI must handle and display errors: empty query, KB not selected, API unavailable, timeout.

### FR-6: Upload API (UI/API)
- Provide an upload endpoint, e.g. `POST /api/v1/upload?kb=<kb_namespace|id>`.
- Payload: `multipart/form-data` with one or multiple files.
- Supported file types (MVP): PDF, DOCX, TXT (extendable).
- Limits: configurable max size per file and per request; return 413 on limit exceeded.
- Behavior:
  - store the file into a per-KB inbox area (PoC convention: `/data/inbox/<kb>/`)
  - return a response with `upload_id` and/or `ingest_job_id`
  - trigger ingestion (immediate or via watcher queue)

### FR-7: Watcher service (auto-index + delete propagation)
- Provide a “watcher” process that:
  - periodically scans inbox folders for each KB (polling preferred for Windows/Docker robustness)
  - ingests new or modified files (based on hash/version)
  - propagates deletions: if a previously known file is removed from the inbox, the system marks the document as deleted and removes or deactivates related chunks in the vector store
- Polling frequency is configurable (e.g., seconds/minutes). Default must balance freshness and load.
- Consistency rules:
  - No duplicates inside a KB (content hash + KB uniqueness).
  - Renames must not create duplicate docs if the content is identical.
  - If a file changes, old chunks must be replaced (versioned) deterministically.

### FR-8: Answer generation (“Conversational Full RAG”)
- Query flow may optionally synthesize an answer using an LLM in a multi-turn conversation:
  - Option A: `POST /api/v1/answer` (including `history`)
  - Option B: `POST /api/v1/query` with flag `synthesize=true` and an optional `history` array of `{role, content}`.
- The synthesized response must:
  - be grounded in retrieved chunks
  - reduce redundancy and follow a consistent structure
  - provide citations (at least chunk-level; page-level when available)
- Fallback:
  - if synthesis fails, return retrieval-only results (sources/excerpts) with an explicit `mode="retrieval_only"` marker.

### FR-9: Output modes
- Support a `mode` parameter that controls response format:
  - `summary`, `bullets`, `table`, `checklist`, `qa`, `extract-json`
- For `table` and `extract-json`:
  - the system must return JSON structured output validated against a JSON Schema.
  - if schema validation fails, retry with a safe prompt or fall back to `bullets`.

### FR-10: Page-level citations
- For PDF ingestion, the system must support page-aware metadata:
  - ingest page-by-page or maintain a mapping of chunk offsets to page numbers
  - store `doc_title`, `page_start`, `page_end`, and (if available) `section_title`
- Query/answer responses must be able to return structured citations:
  - `{doc_id, doc_title, page_start, page_end, section_title?, excerpt, source_uri}`

### FR-11: Security & access control
- Authentication is required via X-API-Key header (SHA-256 hashed in DB).
- Authorization model:
  - API Key valid/active check.
  - Basic RBAC: ruoli `admin` e `user` supportati (M6-B).
  - No ACL granulari per KB nella versione attuale.
- Audit log:
  - store who requested what (user_id), when, target KB(s), and request_id.
- Retention and anonymization policies must be configurable.

### FR-12: Observability interfaces
- Provide:
  - `GET /health`
  - `GET /health/ready`
  - `GET /metrics`
- Structured logs MUST include: timestamp, level, request_id, endpoint, latency_ms, error_code (when applicable).

### FR-13: Evaluation harness (offline)
- Provide an offline evaluation suite that:
  - runs a dataset of representative queries
  - computes retrieval metrics (Precision@K, MRR)
  - produces a versioned report artifact
- After answer synthesis is introduced, add grounding/faithfulness metrics as defined in PRD.

### FR-14: Retrieval upgrades (enterprise)
- Support optional components in the query pipeline:
  - query rewriting / intent detection
  - hybrid retrieval (BM25 + vector)
  - reranking (cross-encoder)
  - caching (embedding cache and/or results cache)
- Parameters must be configurable and testable.

### FR-15: Enterprise connectors (roadmap)
- Define connector interfaces for SharePoint / S3 / Drive / SAP / Salesforce with:
  - incremental sync
  - credential management
  - ACL mapping (where supported)

### FR-16: Multi-modal & multi-agent (optional)
- Multi-modal ingestion (tables/images) via OCR/vision pipelines.
- Agent routing: specialized agents (e.g., legal, table, summarizer, extractor) and an orchestrator to select tools/modes.
- All routing decisions must be logged with request_id and traceable.

### NFR addendum
- Accessibility (UI): meet baseline WCAG-friendly patterns (keyboard navigation, contrast, ARIA labels).
- Performance: UI interactions should not block; API timeouts and retries should be bounded and documented.

---

Updated: 2026-03-12 (Post-M6-B)
