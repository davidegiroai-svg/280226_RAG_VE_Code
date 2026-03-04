-- migration_m2_auth.sql — Phase 11: API Key Authentication
-- Idempotente: usa IF NOT EXISTS ovunque

-- Tabella API keys (mai salvare la key raw, solo il hash SHA-256)
CREATE TABLE IF NOT EXISTS api_keys (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash    VARCHAR(128) NOT NULL UNIQUE,
    name        VARCHAR(100) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    expires_at  TIMESTAMPTZ NULL,
    revoked_at  TIMESTAMPTZ NULL,
    is_active   BOOLEAN DEFAULT TRUE
);

-- Indice per lookup veloce tramite hash (usato ad ogni richiesta autenticata)
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);

-- Indice per listing delle chiavi attive
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active) WHERE is_active = TRUE;
