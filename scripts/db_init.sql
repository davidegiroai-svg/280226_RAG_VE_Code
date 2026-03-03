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
    ingest_date timestamptz DEFAULT now()
);

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
