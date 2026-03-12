-- M6-B RBAC: aggiunge colonna role ad api_keys per ambienti esistenti M3+
-- Idempotente: sicuro da rieseguire più volte senza errori

-- Aggiunge colonna role (DEFAULT 'user' → tutti i record esistenti diventano utenti standard)
ALTER TABLE api_keys
    ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'user';

-- Aggiunge vincolo CHECK tramite DO block (idempotente: verifica esistenza prima di creare)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_api_keys_role'
          AND conrelid = 'api_keys'::regclass
    ) THEN
        ALTER TABLE api_keys
            ADD CONSTRAINT chk_api_keys_role CHECK (role IN ('user', 'admin'));
    END IF;
END $$;
