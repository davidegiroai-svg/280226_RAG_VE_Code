-- M7 GraphRAG: entities + entity_relations tables
-- Idempotente: CREATE TABLE IF NOT EXISTS, CREATE INDEX IF NOT EXISTS

-- ─────────────────────────────────
-- Tabella: entities
-- ─────────────────────────────────
CREATE TABLE IF NOT EXISTS entities (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    kb_id        uuid NOT NULL REFERENCES knowledge_base(id) ON DELETE CASCADE,
    doc_id       uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    entity_type  text NOT NULL,   -- fonte|programma|asse|bando|progetto|beneficiario|scadenza|importo
    canonical    text NOT NULL,   -- lowercased/stripped (chiave dedup)
    display_name text NOT NULL,   -- testo originale estratto
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

-- ─────────────────────────────────
-- Tabella: entity_relations
-- ─────────────────────────────────
CREATE TABLE IF NOT EXISTS entity_relations (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id     uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    from_id    uuid NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    to_id      uuid NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relation   text NOT NULL,   -- finanziato_da|appartiene_a|asse|risponde_a|gestito_da
    weight     real DEFAULT 1.0,
    created_at timestamptz DEFAULT now(),
    UNIQUE (doc_id, from_id, to_id, relation)
);

CREATE INDEX IF NOT EXISTS idx_entity_relations_from ON entity_relations(from_id);
CREATE INDEX IF NOT EXISTS idx_entity_relations_to   ON entity_relations(to_id);
CREATE INDEX IF NOT EXISTS idx_entity_relations_doc  ON entity_relations(doc_id);
