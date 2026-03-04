# Learning Patterns & Best Practices

## PDF Parsing
- **Pattern:** Usare `pymupdf4llm` con parametro `page_chunks=True`.
- **Reason:** Permette di ottenere chunk che rispettano i confini della pagina, semplificando il mantenimento dei metadata `page_start` e `page_end`.

## Database Schema
- **Pattern:** Metadata `page_start` e `page_end` come colonne dedicate, `section_title` nullable.
- **Reason:** Facilita il recupero e la visualizzazione della provenienza esatta dei chunk nel frontend.

## Workflow TDD
- **Pattern:** Test RED → Implementazione → Test GREEN → Commit.
- **Reason:** Garantisce robustezza e documentazione automatica della logica durante lo sviluppo veloce.

## Dev Speed
- **Pattern:** Vanilla Claude Code.
- **Observation:** Risulta 2-3x più veloce rispetto a workflow pesanti come GSD/Superpowers per compiti di implementazione pura.

## Migrations
- **Pattern:** Script SQL separati con esecuzione manuale pre-ingest.
- **Reason:** Evita conflitti durante l'avvio dei container e permette un controllo granulare sullo schema.

## Upload API
- **Pattern:** Pydantic `FileStorage` e multipart validation rapida.
- **Pattern:** Gestione esplicita HTTP 413 (Entity Too Large) e 415 (Unsupported Media Type).
- **Pattern:** Storage organizzato `/data/inbox/<kb>/` per facilitare il watcher futuro.
- **Pattern:** Parametro `kb` obbligatorio negli endpoint di gestione per isolamento logico.

## Testing & Workflow
- **Pattern:** Mocking dei path di sistema nei test multipart tramite `httpx.MultipartEncoder`.
- **Pattern:** Vanilla Claude adoption (senza GSD) garantisce 2x velocità di implementazione e minore token overhead.

## LLM Integration
- **Pattern:** Uso di `requests` per chiamare direttamente l'API di Ollama invece di librerie esterne (es. `openai`).
- **Reason:** Riduce il numero di dipendenze e sfrutta librerie già presenti e verificate (requirements.txt).
- **Pattern:** Prompt di sistema RAG in italiano con istruzione "rispondi SOLO basandoti sui documenti forniti".
- **Pattern:** Timeout configurabile via env var `LLM_TIMEOUT_S` (default 30s) con fallback silenzioso.
- **Pattern:** Fallback = `answer: "Retrieval-only response."` + sources normali (mai errore 500 per LLM assente).
- **Pattern:** Modello LLM configurabile via env var `OLLAMA_LLM_MODEL` (default llama3.2).

## Watcher
- **Pattern:** `watchdog.PollingObserver` obbligatorio su Docker+Windows (inotify non funziona).
- **Pattern:** Soft delete: `is_deleted=TRUE, deleted_at=NOW()` — mai cancellazione fisica dal DB.
- **Pattern:** `ingest_status` con stati: pending → processing → done/error per tracciamento completo.
- **Pattern:** Service Docker con profilo separato (`profiles: ["watcher"]`) per avvio manuale.
- **Pattern:** `ingest_single_file()` come entry point atomico per il watcher (separato dal batch ingest).

## Hybrid Search
- **Pattern:** `tsvector` con lingua `'italian'` per stemming corretto dei documenti italiani.
- **Pattern:** GIN index su `testo_tsv` per performance FTS su grandi dataset.
- **Pattern:** Trigger SQL auto-update su INSERT/UPDATE per mantenere `testo_tsv` sincronizzato.
- **Pattern:** RRF k=60 (Reciprocal Rank Fusion) — standard in letteratura IR per fusione ranking.
- **Pattern:** Tre modalità `search_mode`: "vector" (default), "fts", "hybrid" — retrocompatibile.
- **Pattern:** `plainto_tsquery('italian', query)` per query utente naturali (no sintassi speciale).

## Auth
- **Pattern:** API key hash con SHA-256 (mai raw nel DB).
- **Pattern:** `AUTH_ENABLED` env var per disabilitare auth in dev/test (default True in prod).
- **Pattern:** `/health` e `/health/ready` sempre pubblici — mai protetti da auth.
- **Pattern:** `conftest.py` autouse fixture per disabilitare auth nei test automaticamente.
- **Pattern:** CLI `manage_keys` per operazioni admin (create, revoke, list) — psycopg2 sync.

## Frontend
- **Pattern:** Vite + React 18 + TypeScript + Tailwind CSS 3 per frontend leggeri e veloci.
- **Pattern:** Docker multi-stage: `node:20-alpine` per build → `nginx:alpine` per serve (immagine finale ~20MB).
- **Pattern:** nginx `proxy_pass` per `/api/*` con iniezione `X-API-Key` via `envsubst` nel template.
- **Pattern:** `FRONTEND_API_KEY` env var iniettata in nginx — l'utente non la vede mai nel browser.
- **Pattern:** Tab navigation responsive con sticky header — 4 pagine: Ricerca, Upload, Documenti, KB.
- **Pattern:** Componenti riutilizzabili: Spinner e ErrorMessage come building blocks condivisi.
