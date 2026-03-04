-- Migration M2: colonne watcher per la tabella documents
-- Idempotente: usa ADD COLUMN IF NOT EXISTS

ALTER TABLE documents ADD COLUMN IF NOT EXISTS is_deleted boolean DEFAULT false;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS deleted_at timestamptz;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS ingest_status text DEFAULT 'indexed';

-- Indici per filtrare per status e deleted flag
CREATE INDEX IF NOT EXISTS idx_documents_kb_status ON documents(kb_id, ingest_status);
CREATE INDEX IF NOT EXISTS idx_documents_kb_deleted ON documents(kb_id, is_deleted);
