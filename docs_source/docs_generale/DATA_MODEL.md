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
  - created_at, updated_at

- Chunk
  - id (uuid)
  - document_id (uuid)
  - chunk_index (int)
  - testo (text)
  - start_offset, end_offset
  - embedding_id (uuid)
  - metadata (jsonb) — es. numero pagina, mime type

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
