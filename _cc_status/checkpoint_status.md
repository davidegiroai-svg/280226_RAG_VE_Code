# Checkpoint Status

**Checkpoint updated:** 2026-04-21 by POST-M7-ACTIVATION

## TASK POST-M7-ACTIVATION — Attivazione produzione feature RAG quality
**Status:** DONE
**Timestamp:** 2026-04-21
**Commit:** 677773c

**Operazioni eseguite:**
- Migration DB: `scripts/migration_contextual.sql` applicata — colonna `doc_title` aggiunta a chunks, trigger tsvector arricchito con titolo documento, backfill 7706 chunk
- Backfill embeddings: tutti i 7706 chunk re-embeddati con prefisso contestuale `[kb|titolo|tipo]`
- Backfill metadata: 7 documenti auto-classificati (2 skip demo, 1 err test file)
- Fix volume worker: `docker-compose.yml` worker volume `:ro` → `:rw` per scrittura `.meta.json`
- Feature flags attivati in `.env`: `AUTO_CLASSIFY_ENABLED=true`, `MULTIQUERY_ENABLED=true`

**Verifiche:**
- Multi-query expansion: 4 varianti generate per query test
- FTS con doc_title: match su testo titolo documento via tsvector
- Test suite: 245 passed

**Prossimo sviluppo:** Document Management UI (delete/re-ingest/preview da frontend)

---

**Checkpoint updated:** 2026-04-19 by POST-M7-GRAPHRAG

## TASK POST-M7 — Backfill entità, Frontend GraphRAG, Smoke test 5/5
**Status:** DONE
**Timestamp:** 2026-04-19

**File creati:**
- `api/app/backfill_entities.py` — script CLI per estrarre entità dai documenti già ingestiti (pre-M7)
- `tests/test_backfill_entities.py` — 3 test TDD per il backfill

**File modificati:**
- `frontend/src/types.ts` — aggiunto `graph_enabled?: boolean` a QueryRequest; nuove interfacce `RelatedEntity` e `RelatedDoc`; `related_entities` e `related_docs` in Source
- `frontend/src/pages/SearchPage.tsx` — stato `graphEnabled`, toggle checkbox GraphRAG nella barra impostazioni, display entità (badge viola) e doc correlati per ogni source
- `scripts/smoke_test.ps1` — aggiornato da 3/3 a 5/5 check: aggiunti Check 4 (graph/traverse) e Check 5 (graph/entities)

**Cosa è stato implementato:**
- `backfill_entities.py`: legge tutti i documenti non eliminati dal DB, ricostruisce il testo dai chunk esistenti (`chunks.testo ORDER BY chunk_index`) e chiama `extract_and_save` (idempotente, ON CONFLICT DO NOTHING). Supporta flag `--kb <namespace>` per processare un singolo KB.
- Frontend: toggle "GraphRAG" nella barra ricerca; se attivo invia `graph_enabled: true` nell'API call e mostra entità correlate come pill colorati e doc correlati come testo sotto ogni fonte.
- Smoke test aggiornato: verifica 5 endpoint chiave inclusi i due endpoint grafo M7.

**Conteggio test:**
- Prima: 203 test (M7-GraphRAG)
- Dopo: **206 test** (+3 test_backfill_entities)

**Comando di verifica:**
```powershell
# Test suite
docker compose exec api pytest tests/ -v
# Backfill entità
docker compose exec api python -m app.backfill_entities
# Smoke test
.\scripts\smoke_test.ps1
```

**Output atteso:**
- `206 passed` nella suite pytest
- Log backfill: `Backfill: N documenti da processare` → `[namespace] doc_id — OK` per ogni doc
- Smoke test: `RISULTATO: PASS (5/5) - sistema operativo`

---

**Checkpoint updated:** 2026-04-18 by M7-GRAPHRAG

## TASK M7-GraphRAG — Graph Entity Relationship Layer
**Status:** DONE
**Timestamp:** 2026-04-18
**File creati:**
- `scripts/migration_m7_graph.sql` — DDL: tabelle `entities` + `entity_relations`, indici GIN/btree, trigger tsvector
- `api/app/entity_extractor.py` — estrazione entità via Ollama LLM, normalizzazione, persistenza su DB (best-effort, mai raise)
- `api/app/graph_query.py` — traversal grafo via recursive CTE PostgreSQL, `enrich_sources()` per arricchimento risultati query
- `tests/test_entity_extractor.py` — 27 test TDD
- `tests/test_graph_query.py` — 12 test TDD
- `tests/test_graph_api.py` — 12 test TDD

**File modificati:**
- `scripts/db_init.sql` — DDL M7 aggiunto in fondo (fresh install)
- `api/app/ingest_fs.py` — hook `_graph_extract_and_save` in `ingest_single_file()` e `main()` (dentro `with conn.cursor()`)
- `api/app/main.py` — `QueryRequest.graph_enabled`, `Source.related_entities/related_docs`, endpoint `/api/v1/graph/entities` e `/api/v1/graph/traverse`, import `enrich_sources` a livello modulo
- `api/app/llm.py` — `_build_context()` aggiunge header `ENTITÀ:` per GraphRAG context
- `docker-compose.yml` — env vars `ENTITY_EXTRACTION_ENABLED` + `ENTITY_EXTRACTION_TIMEOUT_S` per api e worker
- `.env.example` — 2 nuove variabili

**Implementato:**
- Tabella `entities`: tipo, canonical (normalizzato), display_name, metadata jsonb, full-text search tsvector GIN
- Tabella `entity_relations`: from/to con peso, UNIQUE per (doc_id, from, to, relation)
- Tipi entità: fonte, programma, asse, bando, progetto, beneficiario, scadenza, importo
- Relazioni: finanziato_da, appartiene_a, asse, risponde_a, gestito_da
- Estrazione best-effort durante ingest (Ollama JSON structured output, gate ENTITY_EXTRACTION_ENABLED)
- Graph traversal via recursive CTE, depth cap=5, forward+backward traversal
- `graph_enabled=true` in POST /query arricchisce ogni source con related_entities e related_docs
- Header ENTITÀ nel context LLM per grounding migliorato
- Graceful degradation completa: extraction/enrichment failure mai propaga

**Conteggio test:**
- Prima: 141 test (M6-B)
- Dopo: **203 test** (+62 nuovi)

**DB verificato:**
```sql
\dt entities        -- tabella presente
\dt entity_relations -- tabella presente
```

---

**Checkpoint updated:** 2026-03-06 by FR-METADATA-SIDECAR

## TASK FR-METADATA-SIDECAR — Metadata sidecar system + metadatazione documenti
**Status:** DONE
**Timestamp:** 2026-03-06
**File modificati:**
- `api/app/ingest_fs.py` — `read_sidecar_meta()` + inject in `insert_chunks()` + esclusione `.meta.json` da `list_files()`
- `api/app/query.py` — `build_query_sql()` + `parse_results()` con `doc_metadata`
- `api/app/hybrid.py` — `fts_search()` con `doc_metadata`
- `api/app/llm.py` — `_build_context()` con header TARGET/AMBITI
- `api/app/main.py` — `Source.doc_metadata`, upload integration con `extract_metadata_for_file` + `save_sidecar_meta`
- `api/app/metadata_extractor.py` (NUOVO) — LLM extraction + save_sidecar_meta
- `tests/test_metadata_extractor.py` (NUOVO) — 3 test TDD
- `tests/test_ingest_pdf.py` — 3 nuovi test (test_read_sidecar_meta_*)
- `tests/test_query.py` — 2 nuovi test (doc_metadata)
- `tests/test_llm.py` — 2 nuovi test (build_context metadata header)
- `tests/test_upload_api.py` — 1 nuovo test (test_upload_genera_meta_json_se_llm_disponibile)
- `data/inbox/programmi/*.meta.json` (10 file)
- `data/inbox/bandi/*.meta.json` (40 file)
- `data/inbox/progetti/*.meta.json` (15 file)

**Implementato:**
- Sidecar `.meta.json` per tutti i documenti esistenti (programmi/bandi/progetti)
- Pipeline ingest legge sidecar e injetta targets/ambiti/tipo nel JSONB `chunks.metadata`
- `list_files()` esclude `.meta.json` per evitare ingest accidentale dei file sidecar
- Query pipeline propaga `doc_metadata` fino a `_build_context()` che aggiunge header TARGET/AMBITI
- Nuovi upload generano `.meta.json` automaticamente via LLM (best-effort, non blocca upload)
- `metadata_extractor.py`: estrazione strutturata con METADATA_EXTRACTION_PROMPT + tassonomia obbligatoria

**Conteggio test:**
- Prima: 128 test
- Dopo: **141 test** (+13 nuovi)

**Fix extra:** `list_files()` esclude `.meta.json` per evitare che i file sidecar vengano
trattati come documenti JSON da ingestire.

**DB verificato:**
```sql
SELECT kb_namespace, metadata->>'titolo', metadata->>'targets', metadata->>'ambiti'
FROM chunks WHERE metadata->>'targets' IS NOT NULL LIMIT 5;
-- Risultati con targets/ambiti popolati da .meta.json
```

**Stato KB dopo re-ingest:**
- programmi: 10 docs, 5359 chunks (tutti con sidecar metadata)
- bandi: 35 docs, 2184 chunks (35/38 con sidecar, 3 falliti silenziosamente)
- progetti: 13 docs, 38 chunks (tutti con sidecar metadata)

---

**Checkpoint updated:** 2026-03-06 by M3_FR7_FR8_WatcherStability_ReasoningRAG

## TASK M3-FR7 — Watcher Stability (on_modified + namespace validation + DB health check)
**Status:** DONE
**Timestamp:** 2026-03-06
**Files Modified:** `api/app/watcher.py`, `tests/test_watcher.py`

### Difetti corretti:
- **W1** `on_modified()` implementato via `_validate_and_ingest()` condiviso con `on_created`
- **W2** Validazione profondità namespace: file in `/inbox/kb/sub/file.txt` ignorati (solo profondità 2 accettata)
- **W3** `_check_db_connection()` aggiunto, chiamato in `main()` al bootstrap con log warning se offline
- **L3** `_validate_and_ingest()` elimina duplicazione tra `on_created` e `on_modified`

### Test aggiunti:
- `TestInboxHandlerOnModified` (3 test): on_modified rilancia ingest, ignora directory, ignora sub-dir
- `TestWatcherMain` (2 test): warning DB offline, info DB online

---

## TASK M3-FR8b — Anti-Allucinazione Tabellare + Tassonomia Obbligatoria
**Status:** DONE
**Timestamp:** 2026-03-06

**File modificati in questa sessione:**
- `api/app/llm.py` — PROMPT_SISTEMA v3 + `_build_context()` v2 con delimitatori INIZIO/FINE
- `tests/test_llm.py` — 2 test aggiornati + 6 nuovi test (13 totali nel file)

**Cosa è stato implementato:**
`PROMPT_SISTEMA` è stato riscritto in versione v3 con tassonomia hardcoded dei TARGET (Minori, Anziani, Famiglie, Migranti, ETS...) e AMBITI (Disabilità, Occupabilità, Child guarantee, Grave emarginazione...), regola di esclusione esplicita per frammenti fuori target (`IGNORA COMPLETAMENTE`), fallback elegante quando nessun documento è pertinente (`non ho trovato / altri target o altri ambiti`), e divieto di dumping tabellare (`È VIETATO il copia-incolla pedissequo`). `_build_context()` produce ora delimitatori `--- INIZIO DOCUMENTO N / FINE DOCUMENTO N ---` per prevenire la fusione cross-documento da parte dell'LLM.

**Conteggio test:**
- Prima: 122 test
- Dopo: **128 test** (+6 nuovi)

**Comando di verifica:**
```powershell
docker compose exec api pytest tests/test_llm.py -v
docker compose exec api pytest tests/ -q --tb=no 2>&1 | tail -3
```

**Output atteso:**
```
13 passed in 0.25s
128 passed, 1 warning in 2.48s
```

---

## TASK M3-FR8 — Reasoning RAG (PROMPT_SISTEMA v2 + _build_context condiviso)
**Status:** DONE
**Timestamp:** 2026-03-06
**Files Modified:** `api/app/llm.py`, `tests/test_llm.py` (creato)

### Miglioramenti:
- **L1** PROMPT_SISTEMA riscritta con grounding assoluto ("esclusivamente") — no allucinazioni
- **L2** Chain-of-thought implicito: regola 5 richiede ragionamento breve prima della risposta
- **L3** `_build_context()` funzione condivisa, elimina duplicazione tra `synthesize_answer` e `synthesize_stream`
- Citazioni inline `[Documento N]` ora richieste esplicitamente dopo ogni affermazione

### Test creati (tests/test_llm.py):
- 7 test: `_build_context` con chunks, vuoto, namespace fallback; PROMPT_SISTEMA keywords; integrazione synthesize_answer

### Conteggio test:
- Prima: 110 test
- Dopo: **122 test** (12 nuovi)

---

**Checkpoint updated:** 2026-03-03T10:00:00 by M1_TASK_06_Final_Check

## TASK CC-01 — Bootstrap Repo + Audit Wrapper
**Status:** DONE
**Timestamp:** 2026-02-28T15:08:36
**Report:** docs/00_repo_audit.md
**Audit Directory:** _cc_status/audit/latest/

### Output Files Created:
- `_cc_status/audit/latest/repo_tree.txt`
- `_cc_status/audit/latest/git_status.txt`
- `_cc_status/audit/latest/risky_paths.txt`
- `_cc_status/audit/latest/audit_summary.json`

---

## TASK CC-02 — Initialize Git repo + .gitignore + first commit
**Status:** DONE
**Timestamp:** 2026-02-28T15:10:00
**Git:** initialized on branch master, commit 3ba729f
**Command:** `git init && git add . && git commit -m "M0 bootstrap: audit + docs baseline"`

---

## TASK CC-03 — Docker Compose (DB pgvector) + db_init.sql + env template + runbook
**Status:** DONE
**Timestamp:** 2026-02-28T15:48:00
**Files Created:**
- `docker-compose.yml` (service db with pgvector, volume, healthcheck, init mount)
- `scripts/db_init.sql` (estensioni: vector, pgcrypto; tabelle: knowledge_base, documents, chunks, ingest_job, query_log)
- `.env.example` (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT)
- `docs/10_run_local.md` (istruzioni per avvio locale)

**Schema DB:** 1536-dim vector per embedding

---

## TASK CC-03.1 — Hardening minimo Compose + Runbook
**Status:** DONE
**Timestamp:** 2026-02-28T16:00:00
**Changes:**
- Rimossa `POSTGRES_PORT` dall'environment del container
- Corretto commento fallback in docker-compose.yml
- Aggiunti comandi Windows/PowerShell in runbook
- Aggiunta nota su reset DB se cambiano credenziali

---

## TASK CC-04 — API skeleton (FastAPI) + DB connectivity + Query stub
**Status:** DONE
**Timestamp:** 2026-02-28T16:10:00
**Files Created:**
- `api/Dockerfile` (Python 3.11 slim, FastAPI, psycopg2-binary)
- `api/requirements.txt` (fastapi, uvicorn, psycopg2-binary, pydantic)
- `api/app/main.py` (endpoints /health, POST /api/v1/query)
- `api/app/db.py` (DB connection helpers)
- `api/app/query.py` (query logic and search)

**Changes to existing:**
- `docker-compose.yml` (aggiunto service api su porta 8000, depends_on db)
- `docs/10_run_local.md` (aggiunti comandi curl per test API)

---

## TASK CC-04.1 — Fix naming modules + query robustness
**Status:** DONE
**Timestamp:** 2026-02-28T16:15:00
**Changes:**
- `api/app/query.py`: type hint corretto `-> tuple[str, list]`, excerpt limitato a 800 chars
- `api/app/main.py`: pydantic validation per query (min_length=1), top_k (1-20)
- `api/Dockerfile`: già corretto (`app.main:app`)

**Nota:** Api endpoint endpoint sync (non async) per compatibilità con psycopg2

---

## TASK CC-04.2 — Align response schema to SRS + improve ranking + health semantics
**Status:** DONE
**Timestamp:** 2026-02-28T16:20:00
**Changes:**
- `api/app/main.py`: Source.source_uri → source_path, /health HTTP 503 quando db_ok=false
- `api/app/query.py`: source_uri → source_path, ORDER BY POSITION per ranking
- `docs/10_run_local.md`: aggiornato example output con source_path

---

## TASK M1_TASK_01_DB — pgvector schema per Vector Search
**Status:** DONE
**Timestamp:** 2026-03-02T13:57:00
**Changes:**
- `scripts/db_init.sql`: embedding changed from `vector(1536)` to `vector(768)`
- `scripts/db_init.sql`: aggiunto indice `idx_chunks_embedding_ivfflat` con `vector_cosine_ops`
- `docs/10_run_local.md`: aggiunta sezione "5. Embedding (vector search)"
- Verifica: DB re-init completato, schema verificato (`docker compose exec db psql ... \d chunks`)

---

## TASK CC-05.2 — Fix mojibake in ingest (UTF-8/Latin1 repair)
**Status:** DONE
**Timestamp:** 2026-03-02T11:00:00
**Changes:**
- `api/app/ingest_fs.py`: aggiunta heuristics repair per mojibake (`Ã`/`Â` -> caratteriaccentati)
- Verifica: query API restituisce "Questo è" invece di "Questo Ã¨"
- Commit: `610e100`, Push: OK su origin/master

---

## TASK CC-05.1 — Hardening ingest encoding + worker profile
**Status:** DONE
**Timestamp:** 2026-03-02T12:00:00
**Changes:**
- `api/app/ingest_fs.py`: gestione encoding robusta con `utf-8-sig` per rimuovere BOM
- `docker-compose.yml`: worker con `profiles: ["manual"]` per avvio solo su richiesta
- `docs/10_run_local.md`: sezione ingest con PowerShell examples + nota encoding/BOM

---

*Checkpoint updated by TASK CC-01*
*Checkpoint updated by TASK CC-02*
*Checkpoint updated by TASK CC-03*
*Checkpoint updated by TASK CC-03.1*
*Checkpoint updated by TASK CC-04*
*Checkpoint updated by TASK CC-04.1*
*Checkpoint updated by TASK CC-04.2*
*Checkpoint updated by TASK CC-05.1*
*Checkpoint updated by TASK CC-05.2*
*Checkpoint updated by TASK M1_TASK_01_DB*
*Checkpoint updated by TASK M1_TASK_02_EmbeddingAdapter*
*Checkpoint updated by TASK M1_TASK_03_Ingest_SaveEmbedding*
*Checkpoint updated by TASK M1_TASK_04_Query_VectorSearch*
*Checkpoint updated by TASK M1_TASK_05_Runbook+Hardening*
*Checkpoint updated by TASK M1_TASK_06_Final_Check*

---

## TASK M1_TASK_04_Query_VectorSearch — vector similarity search in API
**Status:** DONE
**Timestamp:** 2026-03-02T18:30:00
**Changes:**
- `api/app/query.py`: import `embed_text` from `.embedding`
- `api/app/query.py`: aggiunta funzione `vector_to_str()` per convertire liste Python in PostgreSQL vector string format
- `api/app/query.py`: modifica `build_query_sql()` per usare pgvector cosine similarity (`embedding <=> %s`)
- `api/app/query.py`: modifica `parse_results()` per calcolare `score = 1.0 - distance`
- `api/app/main.py`: import `embed_text`, calcolo embedding query in `query_api()`
- `docs/10_run_local.md`: aggiunta sezione "7. Vector Search Query API" con esempi PowerShell/CLI

**Verification:**
```powershell
# Windows/PowerShell
$response = Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/query' -Method POST -ContentType 'application/json' -Body '{"query": "bandi", "top_k": 3, "kb": "demo"}'
$response.sources | Select-Object id, score, source_path
```

**Esempio Output:**
```json
{
  "id": "c6350ed7-4617-48f2-816f-ed7892cbf223",
  "score": 0.413,
  "source_path": "/data/inbox/demo/test_mojibake.txt"
},
{
  "id": "627dcd6f-0b2a-4a2d-ad08-a6e1e66354c8",
  "score": 0.366,
  "source_path": "/data/inbox/demo/demo2.txt"
},
{
  "id": "c68a4fa2-4837-480d-a219-f800f2ce0196",
  "score": 0.365,
  "source_path": "/data/inbox/demo/demo.txt"
}
```

---

## TASK M1_TASK_05_Runbook+Hardening — Vector query hardening
**Status:** DONE
**Timestamp:** 2026-03-02T22:05:00
**Changes:**
- `api/app/query.py`: clamp score a [0..1] con `max(0.0, 1.0 - distance)`
- `api/app/query.py`: SQL semplificato con single vector parameter, ORDER BY distance ASC
- `api/app/query.py`: `vector_to_str()` senza spazi dopo virgola
- `docker-compose.yml`: aggiunte env vars embedding per api e worker
- `docs/10_run_local.md`: fix doppia numerazione "## 6"
- `docs/10_run_local.md`: fix mojibake chars (similarità, �� -> accented)
- `docs/10_run_local.md`: aggiunto snippet env vars embedding PowerShell

**Verification:**
```bash
docker compose up -d --build
docker compose run --rm worker --kb demo --path /data/inbox/demo
$response = Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/query' -Method POST -ContentType 'application/json' -Body '{"query": "bandi", "top_k": 3, "kb": "demo"}'
# Verify: score >= 0, sources ordered by score desc
```

---

## TASK M1_TASK_03_Ingest_SaveEmbedding — embedding vector storage in chunks
**Status:** DONE  
**Timestamp:** 2026-03-02

**Changes:**
- `api/app/ingest_fs.py`: batch embedding via `embed_texts()` (import da `app.embedding`)
- `api/app/ingest_fs.py`: insert su `chunks.embedding`, `chunks.embedding_model`, `chunks.embedding_dim`
- `api/app/ingest_fs.py`: conversione embedding list -> stringa pgvector con `vector_to_str()`

**Verification (example):**
- `docker compose run --rm worker --kb test_kb --path /data/inbox/demo`
- `SELECT COUNT(*) FROM chunks WHERE kb_namespace='test_kb' AND embedding IS NOT NULL;`  (expected > 0)
- `SELECT embedding_model, embedding_dim, COUNT(*) FROM chunks WHERE kb_namespace='test_kb' AND embedding IS NOT NULL GROUP BY 1,2;`

---

## TASK M1_TASK_05_Runbook+Hardening — Runbook updates + security hardening
**Status:** DONE
**Timestamp:** 2026-03-02T22:00:00

**Changes:**
- `docs/10_run_local.md`: aggiunta sezione "8. Security Hardening" con best practices
- `docs/10_run_local.md`: aggiunta sezione "9. Environment Variable Management" con spiegazione POSTGRES_* variabili
- `docker-compose.yml`: aggiunto commento esplicativo su variabili d'ambiente non esposte al container
- `docker-compose.yml`: aggiunta nota su ` profiles: ["manual"]` per worker service
- `api/.env.example`: rimossa `POSTGRES_PORT` (non necessaria per internal networking)
- `docs/10_run_local.md`: aggiornato esempio `.env` senza POSTGRES_PORT

---

## TASK M2_PHASE6_PDF_INGEST — PDF ingest implementation
**Status:** DONE
**Timestamp:** 2026-03-03

**Changes:**
- `api/requirements.txt`: aggiunto pymupdf4llm>=0.0.17, pytest>=8.0.0, httpx>=0.27.0
- `api/app/ingest_fs.py`: nuova funzione `read_pdf_chunks(p)` con pymupdf4llm page_chunks=True
- `api/app/ingest_fs.py`: `list_files()` esteso con estensione `.pdf`
- `api/app/ingest_fs.py`: `insert_chunks()` esteso con kwarg `file_path` — branch PDF salva page_start/page_end/section_title come colonne dedicate
- `api/app/ingest_fs.py`: `main()` aggiornato — hash binario per PDF, passa file_path a insert_chunks
- `docker-compose.yml`: aggiunto volume `./tests:/app/tests:ro` per eseguire pytest nel container
- `tests/conftest.py`: aggiunto per configurare sys.path in Docker
- `tests/test_ingest_pdf.py`: 7 test TDD (tutti PASSED)

**Verification:**
```bash
docker compose exec api pytest tests/ -v
# 8 passed in 0.44s
```

---

## TASK M1_TASK_06_Final_Check — M1 closure
**Status:** DONE
**Timestamp:** 2026-03-03

**Changes:**
- `api/app/query.py`: fix params bug (kb_namespace optional)
- `_cc_status/checkpoint_status.md`: cleanup duplicate M1_TASK_05, aggiunta M1_TASK_06

**Verification:**
```bash
# End-to-end test
docker compose up -d --build
docker compose --profile manual run --rm worker --kb demo --path /data/inbox/demo
docker compose exec db psql -U rag -d rag -c "SELECT COUNT(*) FROM chunks WHERE kb_namespace='demo' AND embedding IS NOT NULL;"
# Query API con KB
# Query API senza KB (kb=null)

---

## Phase 6 — PDF Ingest Completion
**Status:** DONE
**Timestamp:** 2026-03-03T22:55:00
**Milestone v2.0 Progress:** 1 of 6 phases completed
**Changes:**
- `api/app/ingest_fs.py`: aggiunta `read_pdf_chunks`
- `scripts/db_init.sql`: aggiunte colonne `page_start`, `page_end`
- `tests/test_ingest_pdf.py`: 8 test unitari completati
- `api/requirements.txt`: aggiunta `pymupdf4llm`

```
---

## Phase 9 — Watcher Completion
**Status:** DONE
**Timestamp:** 2026-03-04T10:30:00
**Milestone v2.0 Progress:** 4 of 6 phases completed (66%)
**Requirements Completed:** WTCH-01, WTCH-02, WTCH-03, WTCH-04
**Changes:**
- `scripts/migration_m2_watcher.sql`: ADD COLUMN IF NOT EXISTS is_deleted/deleted_at/ingest_status + indici
- `scripts/db_init.sql`: aggiornato con nuove colonne per fresh installs
- `api/requirements.txt`: aggiunto watchdog>=4.0.0
- `api/app/ingest_fs.py`: nuove funzioni `update_ingest_status()` e `ingest_single_file()`
- `api/app/watcher.py`: KBWatcher + InboxHandler + soft_delete_document() con PollingObserver
- `api/app/main.py`: nuovo endpoint GET /api/v1/documents con filtri kb/status/deleted
- `docker-compose.yml`: service watcher (profiles: watcher, restart: unless-stopped)
- `tests/test_watcher.py`: 21 test TDD (tutti PASSED) — 55 totali

**Verification:**
```bash
docker compose exec api pytest tests/ -v
# 55 passed in 5.61s
```

**Avvio watcher manuale:**
```powershell
docker compose --profile watcher up -d watcher
docker compose logs -f watcher
```

---

## Phase 11 — Auth Completion (M2 COMPLETE!)
**Status:** DONE
**Timestamp:** 2026-03-04T13:00:00
**Milestone v2.0 Progress:** 6/6 phases completed — M2 DONE!
**Requirements Completed:** AUTH-01, AUTH-02, AUTH-03, AUTH-04

**Changes:**
- `scripts/migration_m2_auth.sql`: CREATE TABLE api_keys (key_hash SHA-256, is_active, expires_at) + indici
- `api/app/auth.py`: hash_api_key() + verify_api_key() + require_api_key() Depends
- `api/app/main.py`: Depends(require_api_key) su tutti gli endpoint /api/v1/*
- `api/app/manage_keys.py`: CLI create/revoke/list API keys
- `docker-compose.yml`: env var AUTH_ENABLED al service api
- `.env.example`: aggiunta AUTH_ENABLED=true
- `tests/conftest.py`: autouse fixture disable_auth_by_default (AUTH_ENABLED=false per test)
- `tests/test_auth.py`: 24 test TDD (tutti PASSED) — 102 totali

**Verification:**
```bash
docker compose exec api pytest tests/ -v
# 102 passed in 2.41s
```

**Creare una API key:**
```powershell
docker compose exec api python -m app.manage_keys create --name "app-frontend"
# Output: X-API-Key: <uuid-raw> — salvare questo valore!
```

**Usare la API key:**
```powershell
$headers = @{"X-API-Key" = "<uuid-raw>"}
Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/query' -Method POST -ContentType 'application/json' -Headers $headers -Body '{"query": "bando"}'
```

---

## Phase 12 — Frontend Web M3
**Status:** DONE
**Timestamp:** 2026-03-04
**Milestone:** M3 — Frontend Web RAG Venezia

**Componenti creati:**
- `frontend/` — nuova directory con stack Vite + React 18 + TypeScript + Tailwind CSS 3
- `frontend/Dockerfile` — multi-stage: node:20-alpine build → nginx:alpine serve
- `frontend/nginx.conf.template` — proxy `/api/*` e `/health*` con envsubst per FRONTEND_API_KEY
- `frontend/src/types.ts` — interfacce TypeScript da API (QueryRequest, Source, QueryResponse, KbInfo, DocumentInfo, UploadResponse)
- `frontend/src/api.ts` — client API tipato: searchQuery, listKbs, listDocuments, uploadFiles
- `frontend/src/App.tsx` — tab navigation responsive (Ricerca/Upload/Documenti/KB)
- `frontend/src/pages/SearchPage.tsx` — ricerca con KB selector, settings collassabili, risultati con score badge, risposta LLM
- `frontend/src/pages/UploadPage.tsx` — drag & drop upload con validazione tipo/dimensione
- `frontend/src/pages/DocumentsPage.tsx` — tabella documenti con status badge e filtro KB
- `frontend/src/pages/KBsPage.tsx` — griglia cards KB con statistiche
- `frontend/src/components/` — SearchBar, SearchResult, SearchSettings, FileUpload, KBSelector, DocumentList, Spinner, ErrorMessage

**Docker Compose:**
- Aggiunto servizio `frontend` in `docker-compose.yml` (porta `${FRONTEND_PORT:-3000}:80`)
- Aggiunto `FRONTEND_PORT` e `FRONTEND_API_KEY` in `.env.example`

**Primo avvio:**
```powershell
# 1. Creare API key per il frontend
docker compose exec api python -m app.manage_keys create --name "frontend"
# → Copiare il valore come FRONTEND_API_KEY in .env

# 2. Avviare il frontend
docker compose up -d --build frontend

# 3. Aprire http://localhost:3000
```

---

## Milestone v2.0 — COMPLETATA
**Data:** 2026-03-04
**Fasi:** 6/6 completate (Phase 6-11)
**Requirements:** 25/25 completati (PDF-01..04, UPLD-01..07, API-01..02, LLM-01..03, WTCH-01..04, HYBR-01..03, AUTH-01..04)
**Test:** 102 test totali, tutti PASSED
**Componenti aggiunti:**
- PDF ingest (pymupdf4llm, page chunks)
- Upload API (POST /upload, GET /kbs, GET /health/ready)
- LLM synthesis (Ollama /api/chat, fallback graceful)
- Watcher (PollingObserver, auto-ingest, soft delete, GET /documents)
- Hybrid search (tsvector + RRF k=60, search_mode vector/fts/hybrid)
- Auth (API key X-API-Key, SHA-256 hash, manage_keys CLI)

---

## Phase 10 — Hybrid Search Completion
**Status:** DONE
**Timestamp:** 2026-03-04T12:00:00
**Milestone v2.0 Progress:** 5 of 6 phases completed (83%)
**Requirements Completed:** HYBR-01, HYBR-02, HYBR-03
**Changes:**
- `scripts/migration_m2_hybrid.sql`: ADD COLUMN testo_tsv TSVECTOR + GIN index + trigger auto-update
- `api/app/hybrid.py`: nuovo modulo con `fts_search()` + `rrf_merge()` (k=60)
- `api/app/query.py`: import fts_search/rrf_merge, nuova funzione `execute_search()` con search_mode
- `api/app/main.py`: campo `search_mode` in QueryRequest (vector/fts/hybrid), usa execute_search()
- `tests/test_hybrid_search.py`: 23 test TDD (tutti PASSED) — 78 totali

**Verification:**
```bash
docker compose exec api pytest tests/ -v
# 78 passed in 2.27s
```

**Uso con curl/PowerShell:**
```powershell
# Hybrid search
$body = '{"query": "bando venezia", "search_mode": "hybrid", "top_k": 5}'
Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/query' -Method POST -ContentType 'application/json' -Body $body

# Full-text search only
$body = '{"query": "bando venezia", "search_mode": "fts", "top_k": 5}'
Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/query' -Method POST -ContentType 'application/json' -Body $body
```

---

## Phase 8 — LLM Synthesis Completion
**Status:** DONE
**Timestamp:** 2026-03-04T09:30:00
**Milestone v2.0 Progress:** 3 of 6 phases completed (50%)
**Requirements Completed:** LLM-01, LLM-02, LLM-03
**Changes:**
- `api/app/llm.py`: nuova funzione `synthesize_answer(query, chunks, model)` via Ollama /api/chat
- `api/app/main.py`: parametro `synthesize: bool = False` in QueryRequest; chiama `synthesize_answer()` se True
- `docker-compose.yml`: env vars `OLLAMA_LLM_MODEL`, `LLM_TIMEOUT_S` aggiunte al service api
- `.env.example`: aggiunte `OLLAMA_LLM_MODEL=llama3.2`, `LLM_TIMEOUT_S=30`
- `tests/test_llm_synthesis.py`: 10 test TDD (5 unitari + 5 integrazione API), tutti PASSED

**Verification:**
```bash
docker compose exec api pytest tests/ -v
# 34 passed in 2.78s
```

**Esempio uso:**
```powershell
$body = '{"query": "bandi", "top_k": 3, "synthesize": true}'
Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/query' -Method POST -ContentType 'application/json' -Body $body
# Se Ollama disponibile con llama3.2: answer sintetica in italiano
# Se Ollama non disponibile: answer = "Retrieval-only response." + sources
```

---

## Phase 7 — Upload API Completion
**Status:** DONE
**Timestamp:** 2026-03-03T23:18:00
**Milestone v2.0 Progress:** 2 of 6 phases completed (33.33%)
**Requirements Completed:** 
- Phase 6: PDF-01, PDF-02, PDF-03, PDF-04
- Phase 7: UPLD-01, UPLD-02, UPLD-03, UPLD-04, UPLD-05, API-01, API-02
**Requirements Remaining:** 
- LLM-01, LLM-02, LLM-03 (Phase 8), WTCH-01, WTCH-02, WTCH-03, WTCH-04 (Phase 9), HYBR-01, HYBR-02, HYBR-03 (Phase 10), AUTH-01, AUTH-02, AUTH-03, AUTH-04 (Phase 11)
**Changes:**
- `api/app/main.py`: nuovi endpoint `/upload`, `/kbs`, `/health/ready`
- `api/app/schemas.py`: `UploadResponse`, `KBListResponse`
- `api/app/storage.py`: business logic per salvataggio file su disco
- `tests/test_upload_api.py`: 24 test unitari e di integrazione (tutti PASSED)
---

## TASK M2_MAINTENANCE_01 — DB Cleanup & KB Initialization
**Status:** DONE
**Timestamp:** 2026-03-04T16:00:00
**Changes:**
- Rimozione KB legacy (`demo`, `test_kb`, `final_test`) e relativi documenti/chunk.
- Inserimento KB definitive (`bandi`, `progetti`, `programmi`) nella tabella `knowledge_base`.
- Verifica allineamento cartelle filesystem e records database.

**Verification:**
- Endpoint `GET /api/v1/kbs` restituisce correttamente le nuove categorie.

---

## TASK M2_EVOLUTION_01 — Conversational RAG Planning & Docs
**Status:** DONE
**Timestamp:** 2026-03-04T18:45:00
**Milestone:** M4 — Conversational RAG (NotebookLM-style)
**Changes:**
- Aggiornamento documentazione sorgente: `BRD.md`, `PRD.md`, `SRS.md`, `ARCHITECTURE.md` aggiornati con requisiti per chat history e risposte strutturate.
- Definizione schema API per supporto `history` nel backend.
- Progettazione interfaccia React per visualizzazione a "bolle di chat" invece di solo elenco risultati.

---

## TASK M3_CONVERSATIONAL_01 — RAG Conversazionale (NotebookLM-style)
**Status:** DONE
**Timestamp:** 2026-03-04T19:30:00
**Milestone:** M3/M4 — Conversational RAG

**Changes:**
- `api/app/llm.py`: `synthesize_answer()` accetta `history: Optional[List[Dict]]`; messaggi inseriti tra system prompt e user message; PROMPT_SISTEMA aggiornato con istruzioni Markdown e contesto conversazionale.
- `api/app/main.py`: aggiunto `ChatMessage` model Pydantic; `QueryRequest` ha nuovo campo `history: Optional[List[ChatMessage]]`; chiamata a `synthesize_answer()` passa history convertita.
- `frontend/package.json`: aggiunto `react-markdown ^9.0.1` e `remark-gfm ^4.0.0`.
- `frontend/src/types.ts`: aggiunto `ChatMessage`, `UIChatMessage`, `history` in `QueryRequest`.
- `frontend/src/pages/SearchPage.tsx`: trasformata in chat UI — stato `messages[]` locale, bolle utente/assistente, ReactMarkdown con classi arbitrary Tailwind, fonti collassabili (▸/▾), auto-scroll, Invio per inviare.
- `tests/test_llm_synthesis.py`: +5 test TDD — `TestSynthesizeAnswerConHistory` (3 test) + `TestQueryApiConHistory` (2 test).

**Test count:** 106 passed (+ pre-existing failure in test_ingest_pdf non correlata)
**Commits:** 713a8c8, 6786a1d, 838d3f4, 2681842

---

## TASK M3_STREAMING_SSE — Streaming SSE (fix Gateway Timeout)
**Status:** DONE
**Timestamp:** 2026-03-04T21:00:00
**Milestone:** M3 — Streaming per prevenire HTTP 504 su LLM lento

**Problema risolto:** nginx `proxy_read_timeout 120s` causava 504 con LLM su CPU (90-130s).
Con `stream: True` in Ollama il primo token arriva in 1-3s, nginx resetta il timeout ad ogni chunk.

**Changes:**
- `api/app/llm.py`: aggiunto `import json`, `Generator` typing; nuova funzione `synthesize_stream()` generator con streaming NDJSON da Ollama `/api/chat` (stream=True).
- `api/app/main.py`: aggiunto `import json`, `StreamingResponse`; nuovo endpoint `POST /api/v1/query/stream` — invia fonti + token LLM come eventi SSE (`data: {"type":...}`).
- `frontend/nginx.conf.template`: aggiunto `proxy_buffering off` + `proxy_cache off` nel blocco `/api/` per passare i chunk SSE senza buffering.
- `frontend/src/api.ts`: importato `Source`; aggiunto `StreamCallbacks` interface + `searchQueryStream()` con ReadableStream reader.
- `frontend/src/pages/SearchPage.tsx`: `handleSend` usa `searchQueryStream()` — messaggio assistente aggiunto vuoto subito, aggiornato token per token (typing effect), `onDone`/`onError` gestiscono setLoading.
- `tests/test_stream.py`: 3 nuovi test SSE (retrieval-only, sources vuote, streaming LLM mockato).

**Test count:** 110 passed
**Formato SSE:**
```
data: {"type": "sources", "sources": [...]}
data: {"type": "token", "content": "..."}   ← ripetuto per ogni token
data: [DONE]
```

---

## TASK M3_LLM_DIAGNOSTICS — Fix logging LLM synthesis pipeline
**Status:** DONE
**Timestamp:** 2026-03-05T10:00:00
**Milestone:** M3 — Diagnostica e fix robustezza pipeline LLM

**Problema investigato:**
Il frontend mostrava il messaggio di fallback LLM ("Il servizio di elaborazione è temporaneamente
non disponibile…") nonostante il vector search funzionasse correttamente.

**Root cause identificata:**
- Il modello `llama3.2` è presente in Ollama (confermato via `/api/tags`)
- La pipeline SSE funziona: i token vengono generati correttamente (confermato con curl 180s)
- Il fallback era causato dal **cold start** del modello (60-120s alla prima chiamata)
- Le eccezioni in `synthesize_answer` e `synthesize_stream` venivano catturate silenziosamente
  senza logging — qualsiasi errore futuro sarebbe invisibile

**File modificati:**
- `api/app/llm.py`:
  - Aggiunto `import logging` e `logger = logging.getLogger(__name__)`
  - `synthesize_answer`: default timeout `"30"` → `"120"` (allineato a `synthesize_stream`)
  - `synthesize_answer`: `except (ConnectionError, Timeout)` e `except Exception` ora loggano il messaggio dell'eccezione con `logger.warning()`
  - `synthesize_stream`: `except Exception` ora logga il messaggio dell'eccezione con `logger.warning()`

**Verifica:**
```powershell
# Test suite — 110 passed
docker compose exec api pytest tests/ -v

# Log API: se LLM ha errori, ora appariranno come WARNING con dettaglio
docker compose logs api --tail=50

# Test streaming diretto (attendere 60-120s per cold start)
curl -s -X POST http://localhost:8000/api/v1/query/stream `
  -H "Content-Type: application/json" `
  -H "X-API-Key: 284c95e3-369c-40a2-b5b1-298190ee561b" `
  -d "{\"query\":\"cos e il PNRR?\",\"synthesize\":true,\"top_k\":2}" `
  --max-time 180
```

**Output atteso:**
```
data: {"type": "sources", "sources": [...]}
data: {"type": "thinking"}
data: {"type": "token", "content": "..."}
... (molti token)
data: [DONE]
```

---

## TASK M3_FR8_RAG_REASONING_FIX  Refactoring Tassonomico e Anti-Hallucination
**Status:** DONE
**Timestamp:** 2026-03-07T09:44:06
**Milestone:** M3/M4  Reasoning RAG robusto
**Changes:**
- `api/app/llm.py`: PROMPT_SISTEMA strutturato con TARGET e AMBITI obbligatori (FR-8).
- `api/app/llm.py`: Aggiunta direttiva anti-dumping per evitare copia/incolla formattato di tabelle FESR inutili.
- `frontend/src/pages/SearchPage.tsx`: Fix UI stream token parsing.
- Test regression suite aggiornata (129 test totali, 0 fail).

**Verification:**
\\\ash
docker compose exec api pytest tests/ -v
\\\`n
