-- Migration: contextual prepend — doc_title column + tsvector trigger arricchito
-- Eseguire con: docker compose exec db psql -U rag -d rag -f /docker-entrypoint-initdb.d/migration_contextual.sql

-- 1. Colonna doc_title per ricerca full-text arricchita
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS doc_title text;

-- 2. Backfill doc_title da documents.titolo per chunk esistenti
UPDATE chunks c
SET doc_title = d.titolo
FROM documents d
WHERE c.document_id = d.id
  AND c.doc_title IS NULL;

-- 3. Aggiorna trigger testo_tsv per includere doc_title
CREATE OR REPLACE FUNCTION chunks_testo_tsv_update()
RETURNS TRIGGER AS $$
BEGIN
    NEW.testo_tsv := to_tsvector('italian',
        COALESCE(NEW.doc_title, '') || ' ' || COALESCE(NEW.testo, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 4. Ricrea trigger con doc_title tra le colonne monitorate
DROP TRIGGER IF EXISTS trig_chunks_testo_tsv ON chunks;

CREATE TRIGGER trig_chunks_testo_tsv
BEFORE INSERT OR UPDATE OF testo, doc_title ON chunks
FOR EACH ROW
EXECUTE FUNCTION chunks_testo_tsv_update();

-- 5. Rigenera testo_tsv per tutti i chunk con il nuovo trigger
UPDATE chunks
SET testo_tsv = to_tsvector('italian',
    COALESCE(doc_title, '') || ' ' || COALESCE(testo, ''));
