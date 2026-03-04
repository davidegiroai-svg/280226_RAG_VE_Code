Modello dei dati

Panoramica
Questo documento descrive il modello logico dei dati per il sistema RAG multi‑KB, con focus sulle entità necessarie per ingest, retrieval, provenienza e tracciamento dell'uso.

Entità principali
- KnowledgeBase (KB)
  - id (uuid)
  - nome (string)
  - descrizione (text)
  - proprietario (string)

- Documento
  - id (uuid)
  - kb_id (uuid) riferimento alla KB
  - source_uri (string)
  - titolo (string)
  - content_hash (string)
  - source_type (enum: filesystem|upload|connector)
  - file_name (string)
  - mime_type (string)
  - size_bytes (bigint)
  - version/source_revision (int/string, opz.)
  - ingest_status (enum: pending|indexed|failed|deleted)
  - last_seen_at (timestamptz, opz.)
  - is_deleted (bool) e deleted_at (timestamptz, opz.)
  - created_at, updated_at

- Chunk
  - id (uuid)
  - document_id (uuid)
  - chunk_index (int)
  - testo (text)
  - start_offset, end_offset
  - embedding_id (uuid)
  - metadata (jsonb) — es. numero pagina, intervallo pagine, sezione, mime type (page_start/page_end/section_title)

- Embedding / Vettore
  - id (uuid)
  - modello (string)
  - vettore (vector/pgvector)
  - dimensione (int)
  - created_at

- IngestJob
  - id (uuid)
  - kb_id (uuid)
  - connector_type (string)
  - status (enum)
  - started_at, finished_at
  - summary (jsonb)

- QueryLog
  - id (uuid)
  - user_id (nullable)
  - kb_ids (array)
  - query_text (text)
  - retrieved_chunks (jsonb)
  - model_used (string)
  - response_time_ms (int)
  - created_at

- AuditEvent (per compliance)
  - id (uuid)
  - request_id (string)
  - user_id (nullable)
  - event_type (enum)
  - kb_id (nullable)
  - document_id (nullable)
  - payload (jsonb)
  - created_at

Indici e considerazioni
  - Indici vettoriali sulla colonna `Embedding.vettore` usando pgvector (ivfflat o hnsw) in base alla scala.
  - Indici GIN su JSONB per i metadati se necessario.
  - Vincolo di unicità consigliato: UNIQUE(kb_id, content_hash) per evitare doppie ingestioni all'interno della stessa KB (lo stesso hash può apparire in KB differenti).

  Esempio SQL (Postgres + pgvector)
  ```sql
  CREATE TABLE knowledge_base (
    id uuid PRIMARY KEY,
    nome text,
    descrizione text
  );

  CREATE TABLE embedding (
    id uuid PRIMARY KEY,
    modello text,
    vettore vector(1536),
    dimensione int,
    created_at timestamptz
  );

  CREATE INDEX ON embedding USING ivfflat (vettore) WITH (lists = 100);
  ```

  Nota PoC
  - Il modello dati e gli esempi SQL sono pensati per supportare un PoC locale dimostrativo. Includere script di inizializzazione DB, dati di esempio e note di migrazione per il team IT del cliente.


---

## Estensioni modello dati (lifecycle file, citazioni pagina, ACL, audit)

Questa sezione estende il modello logico per supportare upload via API, watcher (auto-index + delete propagation), citazioni “serie”, connettori enterprise e compliance.

### Estensioni: Documento
Aggiungere campi consigliati:
- `source_type` (enum): `filesystem`, `upload`, `connector`
- `source_uri` (string): URI/path originale o endpoint esterno
- `file_name` (string)
- `mime_type` (string)
- `size_bytes` (bigint)
- `content_hash` (string) – già presente, usato per dedup/versioning
- `version` (int) o `source_revision` (string) per connettori esterni
- `ingest_status` (enum): `pending`, `indexed`, `failed`, `deleted`
- `last_seen_at` (timestamptz) – aggiornato dal watcher ad ogni scan
- `is_deleted` (bool) e `deleted_at` (timestamptz)
- `error_code`, `error_message` (nullable) per troubleshooting ingest
- `doc_title` (string) – titolo normalizzato (per citazioni)
- `page_count` (int, nullable) per PDF

**Vincoli consigliati**
- UNIQUE(`kb_id`, `content_hash`) per evitare duplicati nella stessa KB.
- Indice su (`kb_id`, `ingest_status`) per dashboard e watcher.

### Estensioni: Chunk (citazioni pagina/sezione)
Integrare metadata strutturati (colonne o JSONB):
- `page_start` (int, nullable)
- `page_end` (int, nullable)
- `section_title` (string, nullable)
- `chunk_hash` (string) per idempotenza
- (opz.) `layout_bbox` (jsonb) per coordinate OCR/vision

### Origine e connettori (enterprise)
Per supportare sync incrementale:
- `external_system` (string, nullable) es. `sharepoint`, `s3`, `drive`, `sap`, `salesforce`
- `external_id` (string, nullable) identificativo univoco nel sistema sorgente
- `external_acl` (jsonb, nullable) snapshot o mapping ACL

### Sicurezza: utenti, ruoli, permessi (RBAC/ACL)
Nuove entità (logiche):
- **User**
  - `id`, `email` (o subject), `display_name`, `is_active`, `created_at`
- **Role**
  - `id`, `name` (es. `admin`, `user`)
- **UserRole**
  - `user_id`, `role_id`
- **AccessControlEntry (ACE)** (opzionale per ACL fine-grain)
  - `id`, `principal_type` (`user`/`role`), `principal_id`
  - `resource_type` (`kb`/`document`), `resource_id`
  - `permission` (es. `read`, `write`, `admin`)

### Audit log (compliance)
Nuova entità:
- **AuditEvent**
  - `id` (uuid)
  - `request_id` (string)
  - `user_id` (nullable)
  - `event_type` (enum): `query`, `upload`, `ingest_start`, `ingest_finish`, `delete_detected`, `auth`, `admin_action`
  - `kb_id` (nullable), `document_id` (nullable)
  - `payload` (jsonb) – es. endpoint, parametri, esito
  - `created_at`

### Cache & query logs (opzionale)
- `QueryLog` già presente; estendere con:
  - `mode`, `synthesize`, `retrieval_params` (jsonb)
  - `citations` (jsonb)
- Tabelle cache (opzionale):
  - **EmbeddingCache** (key → vector)
  - **ResultCache** (query_hash + kb_scope → result payload)

---

Data aggiornamento: 2026-03-03
