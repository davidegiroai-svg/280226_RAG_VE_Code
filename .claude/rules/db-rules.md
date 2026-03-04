\# db-rules.md — Regole per DB schema e Docker Compose

---

paths:

&nbsp; - scripts/db\_init.sql

&nbsp; - docker-compose.yml

&nbsp; - scripts/\*.sql

---



\## Schema attuale (PostgreSQL 16 + pgvector)

Estensioni: vector (pgvector), pgcrypto (gen\_random\_uuid)



Tabella knowledge\_base:

&nbsp; id uuid PK DEFAULT gen\_random\_uuid()

&nbsp; namespace text UNIQUE NOT NULL

&nbsp; nome text | descrizione text | created\_at timestamptz



Tabella documents:

&nbsp; id uuid PK | kb\_id uuid FK → knowledge\_base CASCADE

&nbsp; source\_uri text | titolo text | content\_hash text

&nbsp; created\_at timestamptz | updated\_at timestamptz

&nbsp; UNIQUE(kb\_id, content\_hash)



Tabella chunks:

&nbsp; id uuid PK | document\_id uuid FK → documents CASCADE

&nbsp; kb\_id uuid FK → knowledge\_base CASCADE

&nbsp; kb\_namespace text NOT NULL | chunk\_index int NOT NULL

&nbsp; testo text NOT NULL | metadata jsonb DEFAULT '{}'

&nbsp; embedding vector(768) | embedding\_model text | embedding\_dim int

&nbsp; ingest\_date timestamptz



Tabelle accessorie: ingest\_job, query\_log



Indici esistenti:

&nbsp; idx\_chunks\_kb\_id, idx\_chunks\_kb\_namespace, idx\_chunks\_document\_id

&nbsp; idx\_chunks\_embedding\_ivfflat  (ivfflat cosine, lists=100)



\## Regole modifica schema (non derogabili)

\- NON modificare vector(768) senza docker compose down -v + reinit completo

\- Nuove colonne: ALTER TABLE ... ADD COLUMN IF NOT EXISTS (idempotente)

\- Nuovi indici: CREATE INDEX IF NOT EXISTS (idempotente)

\- Nuove tabelle: CREATE TABLE IF NOT EXISTS (idempotente)

\- Dopo ogni modifica a db\_init.sql: documentare in \_cc\_status/checkpoint\_status.md



\## Colonne da aggiungere in M2 per PDF (migration script separato)

Creare scripts/migration\_m2\_pdf.sql con:

&nbsp; ALTER TABLE chunks ADD COLUMN IF NOT EXISTS page\_start integer;

&nbsp; ALTER TABLE chunks ADD COLUMN IF NOT EXISTS page\_end integer;

&nbsp; ALTER TABLE chunks ADD COLUMN IF NOT EXISTS section\_title text;



Aggiungere anche in db\_init.sql per i nuovi ambienti.



\## Colonne da aggiungere in M2 per delete propagation (watcher)

Creare scripts/migration\_m2\_watcher.sql con:

&nbsp; ALTER TABLE documents ADD COLUMN IF NOT EXISTS is\_deleted boolean DEFAULT false;

&nbsp; ALTER TABLE documents ADD COLUMN IF NOT EXISTS deleted\_at timestamptz;

&nbsp; ALTER TABLE documents ADD COLUMN IF NOT EXISTS ingest\_status text DEFAULT 'indexed';

&nbsp; CREATE INDEX IF NOT EXISTS idx\_documents\_kb\_status ON documents(kb\_id, ingest\_status);



\## Docker Compose — servizi attuali

db:     pgvector/pgvector:pg16 | porta 5432 | healthcheck pg\_isready | volume pgdata

api:    build ./api | porta 8000 | depends\_on db condition service\_healthy

worker: build ./api | profile manual | volumes ./data:/data:ro | entrypoint ingest\_fs



\## Aggiungere servizio watcher in M2

watcher:

&nbsp; build: ./api

&nbsp; depends\_on:

&nbsp;   db:

&nbsp;     condition: service\_healthy

&nbsp; environment:

&nbsp;   DB\_HOST: db

&nbsp;   DB\_PORT: "5432"

&nbsp;   POSTGRES\_USER: "${POSTGRES\_USER:-rag}"

&nbsp;   POSTGRES\_PASSWORD: "${POSTGRES\_PASSWORD:-rag\_password\_change\_me}"

&nbsp;   POSTGRES\_DB: "${POSTGRES\_DB:-rag}"

&nbsp;   EMBEDDING\_PROVIDER: "${EMBEDDING\_PROVIDER:-ollama}"

&nbsp;   EMBEDDING\_MODEL: "${EMBEDDING\_MODEL:-nomic-embed-text}"

&nbsp;   EMBEDDING\_DIM: "${EMBEDDING\_DIM:-768}"

&nbsp;   OLLAMA\_BASE\_URL: "${OLLAMA\_BASE\_URL:-http://host.docker.internal:11434}"

&nbsp;   WATCHER\_POLL\_SECONDS: "${WATCHER\_POLL\_SECONDS:-30}"

&nbsp;   INBOX\_ROOT: /data/inbox

&nbsp; volumes:

&nbsp;   - ./data:/data:rw

&nbsp; entrypoint: \["python", "-m", "app.watcher"]

&nbsp; restart: unless-stopped



Nota: il volume watcher è :rw (read-write) — diverso dal worker che è :ro



\## Regole Docker Compose generali

\- Immagine DB: pgvector/pgvector:pg16 — NON aggiornare a pg17 senza test

\- restart: unless-stopped solo per servizi permanenti (db, api, watcher)

\- restart: "no" per worker (è manuale on-demand)

\- La porta 5432 del DB va rimossa in produzione (solo per sviluppo locale)

\- Env vars: sempre con fallback ${VAR:-default} per sicurezza

