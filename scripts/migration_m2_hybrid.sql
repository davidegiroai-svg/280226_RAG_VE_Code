-- migration_m2_hybrid.sql — Phase 10: Hybrid Search (tsvector + BM25 + RRF)
-- Idempotente: usa IF NOT EXISTS ovunque

-- 1. Colonna tsvector precalcolata
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS testo_tsv TSVECTOR;

-- 2. Popola colonna per chunk esistenti (solo quelli non ancora valorizzati)
UPDATE chunks
SET testo_tsv = to_tsvector('italian', COALESCE(testo, ''))
WHERE testo_tsv IS NULL AND testo IS NOT NULL;

-- 3. Indice GIN per ricerca full-text rapida
CREATE INDEX IF NOT EXISTS idx_chunks_testo_tsv ON chunks USING GIN(testo_tsv);

-- 4. Trigger: aggiorna testo_tsv automaticamente su INSERT/UPDATE
CREATE OR REPLACE FUNCTION chunks_testo_tsv_update()
RETURNS TRIGGER AS $$
BEGIN
    NEW.testo_tsv := to_tsvector('italian', COALESCE(NEW.testo, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Rimuove il trigger se già esiste (idempotente), poi ricrea
DROP TRIGGER IF EXISTS trig_chunks_testo_tsv ON chunks;

CREATE TRIGGER trig_chunks_testo_tsv
BEFORE INSERT OR UPDATE OF testo ON chunks
FOR EACH ROW
EXECUTE FUNCTION chunks_testo_tsv_update();
