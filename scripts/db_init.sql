-- RAG VE - Database initialization script
-- Esegue all'avvio del container Postgres (docker-entrypoint-initdb.d)

-- Estensioni richieste
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Tabella knowledge_base
CREATE TABLE knowledge_base (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace text UNIQUE NOT NULL,
    nome text,
    descrizione text,
    created_at timestamptz DEFAULT now()
);

-- Tabella documents
CREATE TABLE documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    kb_id uuid NOT NULL REFERENCES knowledge_base(id) ON DELETE CASCADE,
    source_uri text,
    titolo text,
    content_hash text,
    is_deleted boolean DEFAULT false,
    deleted_at timestamptz,
    ingest_status text DEFAULT 'indexed',
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    UNIQUE(kb_id, content_hash)
);

-- Tabella chunks
CREATE TABLE chunks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    kb_id uuid NOT NULL REFERENCES knowledge_base(id) ON DELETE CASCADE,
    kb_namespace text NOT NULL,
    chunk_index int NOT NULL,
    testo text NOT NULL,
    start_offset int,
    end_offset int,
    metadata jsonb DEFAULT '{}'::jsonb,
    embedding_model text,
    embedding_dim int,
    embedding vector(768),
    page_start integer,
    page_end integer,
    section_title text,
    doc_title text,
    ingest_date timestamptz DEFAULT now()
);

-- Indici per documents
CREATE INDEX idx_documents_kb_status ON documents(kb_id, ingest_status);
CREATE INDEX idx_documents_kb_deleted ON documents(kb_id, is_deleted);

-- Indici per chunks
CREATE INDEX idx_chunks_kb_id ON chunks(kb_id);
CREATE INDEX idx_chunks_kb_namespace ON chunks(kb_namespace);
CREATE INDEX idx_chunks_document_id ON chunks(document_id);

-- Indice vettoriale per cosine similarity (ivfflat con opclass vector_cosine_ops)
-- Dimensione 768 per compatibilita' con modello Ollama (nomic-embed-text)
CREATE INDEX idx_chunks_embedding_ivfflat ON chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Tabella ingest_job
CREATE TABLE ingest_job (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    kb_id uuid REFERENCES knowledge_base(id) ON DELETE CASCADE,
    connector_type text NOT NULL,
    status text NOT NULL,
    started_at timestamptz,
    finished_at timestamptz,
    summary jsonb DEFAULT '{}'::jsonb
);

-- Tabella query_log
CREATE TABLE query_log (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id text,
    kb_ids uuid[],
    query_text text,
    retrieved_chunks jsonb,
    model_used text,
    response_time_ms int,
    created_at timestamptz DEFAULT now()
);

-- Tabella upload_log
CREATE TABLE IF NOT EXISTS upload_log (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_id uuid NOT NULL,
    job_id uuid NOT NULL,
    kb_namespace text NOT NULL,
    file_names text[] NOT NULL,
    file_sizes_bytes bigint[] NOT NULL,
    uploaded_at timestamptz DEFAULT now()
);

-- Tabella api_keys (auth M3 — hash SHA-256, mai salvare la key raw)
-- M6-B: aggiunta colonna role (user/admin) con DEFAULT 'user'
CREATE TABLE IF NOT EXISTS api_keys (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash    VARCHAR(128) NOT NULL UNIQUE,
    name        VARCHAR(100) NOT NULL,
    role        VARCHAR(20)  NOT NULL DEFAULT 'user',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    expires_at  TIMESTAMPTZ NULL,
    revoked_at  TIMESTAMPTZ NULL,
    is_active   BOOLEAN DEFAULT TRUE,
    CONSTRAINT chk_api_keys_role CHECK (role IN ('user', 'admin'))
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active) WHERE is_active = TRUE;

-- Hybrid search: colonna tsvector precalcolata + indice GIN + trigger (M3)
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS testo_tsv TSVECTOR;
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS doc_title text;

-- Popola per chunk gia' esistenti (no-op su fresh install)
UPDATE chunks
SET testo_tsv = to_tsvector('italian', COALESCE(doc_title, '') || ' ' || COALESCE(testo, ''))
WHERE testo_tsv IS NULL AND testo IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_chunks_testo_tsv ON chunks USING GIN(testo_tsv);

CREATE OR REPLACE FUNCTION chunks_testo_tsv_update()
RETURNS TRIGGER AS $$
BEGIN
    NEW.testo_tsv := to_tsvector('italian',
        COALESCE(NEW.doc_title, '') || ' ' || COALESCE(NEW.testo, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trig_chunks_testo_tsv ON chunks;

CREATE TRIGGER trig_chunks_testo_tsv
BEFORE INSERT OR UPDATE OF testo, doc_title ON chunks
FOR EACH ROW
EXECUTE FUNCTION chunks_testo_tsv_update();

-- ─────────────────────────────────────────────────────────────────────────────
-- M7 GraphRAG: entities + entity_relations
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS entities (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    kb_id        uuid NOT NULL REFERENCES knowledge_base(id) ON DELETE CASCADE,
    doc_id       uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    entity_type  text NOT NULL,
    canonical    text NOT NULL,
    display_name text NOT NULL,
    raw_value    text,
    metadata     jsonb DEFAULT '{}'::jsonb,
    name_tsv     tsvector,
    created_at   timestamptz DEFAULT now(),
    UNIQUE (doc_id, entity_type, canonical)
);

CREATE INDEX IF NOT EXISTS idx_entities_name_tsv  ON entities USING GIN(name_tsv);
CREATE INDEX IF NOT EXISTS idx_entities_doc_id    ON entities(doc_id);
CREATE INDEX IF NOT EXISTS idx_entities_kb_type   ON entities(kb_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_canonical ON entities(canonical, entity_type);

CREATE OR REPLACE FUNCTION entities_name_tsv_update()
RETURNS TRIGGER AS $$
BEGIN
    NEW.name_tsv := to_tsvector('italian',
        COALESCE(NEW.display_name, '') || ' ' || COALESCE(NEW.canonical, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trig_entities_name_tsv ON entities;
CREATE TRIGGER trig_entities_name_tsv
BEFORE INSERT OR UPDATE OF display_name, canonical ON entities
FOR EACH ROW EXECUTE FUNCTION entities_name_tsv_update();

CREATE TABLE IF NOT EXISTS entity_relations (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id     uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    from_id    uuid NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    to_id      uuid NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relation   text NOT NULL,
    weight     real DEFAULT 1.0,
    created_at timestamptz DEFAULT now(),
    UNIQUE (doc_id, from_id, to_id, relation)
);

CREATE INDEX IF NOT EXISTS idx_entity_relations_from ON entity_relations(from_id);
CREATE INDEX IF NOT EXISTS idx_entity_relations_to   ON entity_relations(to_id);
CREATE INDEX IF NOT EXISTS idx_entity_relations_doc  ON entity_relations(doc_id);
