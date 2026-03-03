-- Migration M2 — Upload API: crea tabella upload_log per ambienti esistenti
-- Sicuro da rieseguire (CREATE TABLE IF NOT EXISTS)

CREATE TABLE IF NOT EXISTS upload_log (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_id uuid NOT NULL,
    job_id uuid NOT NULL,
    kb_namespace text NOT NULL,
    file_names text[] NOT NULL,
    file_sizes_bytes bigint[] NOT NULL,
    uploaded_at timestamptz DEFAULT now()
);
