# Phase 6: PDF Ingest - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Estendere il worker CLI (`ingest_fs.py`) per ingestire file PDF. Ogni PDF viene elaborato pagina per pagina usando `pymupdf4llm`. I chunk prodotti includono metadata di paginazione (`page_start`, `page_end`). La deduplication e l'architettura del worker rimangono invariate. Watcher, upload API e altri formati non rientrano in questa fase.

</domain>

<decisions>
## Implementation Decisions

### Libreria PDF
- Usare `pymupdf4llm>=0.0.17` con `page_chunks=True` — una pagina = un chunk
- Aggiungere a `api/requirements.txt`

### Funzione di parsing PDF
- Aggiungere `read_pdf_chunks(p: Path) -> list[dict]` in `ingest_fs.py`
- NON modificare `read_text_file()` — resta invariata per TXT/MD/CSV/JSON
- Ogni dict nel risultato: `{"testo": str, "page_start": int, "page_end": int, "section_title": None}`

### Chunking
- Per PDF: un chunk per pagina (come restituito da pymupdf4llm) — NO re-chunking delle pagine
- Per TXT/MD/CSV/JSON: `chunk_text(1200, overlap=200)` — invariato
- Pagine con testo vuoto: scartare (non inserire chunk vuoti)

### Metadati chunk PDF
- `page_start` e `page_end`: numero pagina da `page["metadata"]["page"]`
- `section_title`: `None` (NULL) — pymupdf4llm non fornisce titoli di sezione affidabili per documenti istituzionali
- I campi `page_start`/`page_end`/`section_title` vengono anche salvati nel JSONB `metadata` oltre che nelle colonne dedicate

### Deduplication per PDF
- `content_hash`: sha256 della concatenazione di tutti i testi pagina (`"".join(p["testo"] for p in pages)`)
- Dedup a livello documento (stesso meccanismo TXT) — UNIQUE(kb_id, content_hash)

### Branch in insert_chunks()
- Aggiungere parametro `source_ext: str` a `insert_chunks()`
- Se `.pdf`: usare `read_pdf_chunks()` e passare page_start/page_end alla INSERT
- Altrimenti: comportamento attuale invariato

### Migration DB
- Creare `scripts/migration_m2_pdf.sql` con ALTER TABLE IF NOT EXISTS per `page_start`, `page_end`, `section_title`
- Aggiornare anche `scripts/db_init.sql` con le stesse colonne (per nuovi ambienti)
- La migration è **manuale** — l'utente esegue lo script prima di usare i PDF per la prima volta

### Estensioni list_files()
- Aggiungere `.pdf` agli ext supportati: `{".txt", ".md", ".csv", ".json", ".pdf"}`

### Gestione errori PDF
- PDF corrotto o criptato: loggare warning + skip del file (continua con i successivi)
- Il batch non fallisce per un singolo PDF problematico
- Compatibile con il comportamento del worker per file vuoti TXT (skip silenzioso)

### Output worker
- Output JSON finale invariato — aggiungere campo `pdfs_processed: int` nella summary
- Nessun progress per pagina durante l'elaborazione

### Claude's Discretion
- Esatto formato del messaggio di warning per PDF saltati
- Ordine di inserimento dei chunk PDF nel DB

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ensure_kb(cur, namespace)` — invariato, riusato per PDF
- `upsert_document(cur, kb_id, ...)` — invariato, hash del testo PDF concatenato
- `vector_to_str(vec)` — invariato
- `embed_texts(texts)` — batch embedding, già compatibile con liste di stringhe pagina
- `chunk_text()` — NON usato per PDF, solo per formati testo
- `sha256_text(text)` — riusato per content_hash PDF (testo concatenato)

### Established Patterns
- psycopg2 SYNC obbligatorio — no async, no asyncpg
- `RealDictCursor`: accesso con `row["colonna"]`
- `vector_to_str()`: sempre per liste Python → stringa pgvector
- `Json(meta)` per JSONB metadata — pattern già presente in `insert_chunks()`
- Dedup: ON CONFLICT DO NOTHING ovunque
- `conn.autocommit = False` + `conn.rollback()` su eccezione — pattern `main()`

### Integration Points
- `list_files()` → aggiungere `.pdf` agli ext
- `insert_chunks()` → branch su estensione file + nuove colonne page_start/page_end
- `scripts/db_init.sql` → aggiungere colonne chunks per nuovi ambienti
- `api/requirements.txt` → aggiungere pymupdf4llm
- `scripts/` → nuovo file `migration_m2_pdf.sql`

</code_context>

<specifics>
## Specific Ideas

- Il design della migration segue `db-rules.md`: script separato per ambienti esistenti + update di db_init.sql per nuovi
- L'utente userà il worker con lo stesso comando già noto: `docker compose --profile manual run --rm worker --kb demo --path /data/inbox/demo`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-pdf-ingest*
*Context gathered: 2026-03-03*
