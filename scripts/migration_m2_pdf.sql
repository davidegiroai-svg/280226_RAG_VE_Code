-- Migration M2 — PDF: aggiunge colonne paginazione alla tabella chunks
-- Sicuro da eseguire piu' volte (ADD COLUMN IF NOT EXISTS)

ALTER TABLE chunks ADD COLUMN IF NOT EXISTS page_start integer;
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS page_end integer;
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS section_title text;
