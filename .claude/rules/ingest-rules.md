\# ingest-rules.md — Regole per ingest e embedding

---

paths:

&nbsp; - api/app/ingest\_fs.py

&nbsp; - api/app/embedding.py

&nbsp; - tests/test\_ingest.py

&nbsp; - tests/test\_embedding.py

---



\## Funzioni esistenti in ingest\_fs.py (NON riscrivere, solo estendere)

ensure\_kb(cur, namespace)              → crea o recupera KB dal DB, ritorna kb\_id

upsert\_document(cur, kb\_id, ...)       → insert con ON CONFLICT DO NOTHING, ritorna (doc\_id, is\_new)

insert\_chunks(cur, kb\_id, ...)         → batch embedding + insert chunks, ritorna count

chunk\_text(text, size=1200, overlap=200) → generatore di (index, testo)

read\_text\_file(p)                      → legge con utf-8-sig + repair mojibake — NON TOCCARE

vector\_to\_str(vec)                     → "\[x1,x2,...,xN]" senza spazi — usare sempre



\## Aggiunta PDF (task M2-1 — come implementare)

1\. Aggiungere a api/requirements.txt:

&nbsp;  pymupdf4llm>=0.0.17



2\. In list\_files(): aggiungere ".pdf" agli ext supportati

&nbsp;  exts = {".txt", ".md", ".csv", ".json", ".pdf"}



3\. Aggiungere nuova funzione (NON modificare read\_text\_file):

&nbsp;  def read\_pdf\_chunks(p: Path) -> list\[dict]:

&nbsp;    import pymupdf4llm

&nbsp;    pages = pymupdf4llm.to\_markdown(str(p), page\_chunks=True)

&nbsp;    result = \[]

&nbsp;    for page in pages:

&nbsp;      result.append({

&nbsp;        "testo": page\["text"],

&nbsp;        "page\_start": page\["metadata"]\["page"],

&nbsp;        "page\_end": page\["metadata"]\["page"],

&nbsp;        "section\_title": None

&nbsp;      })

&nbsp;    return result



4\. In insert\_chunks(): branch su estensione file

&nbsp;  - Se .pdf: usare read\_pdf\_chunks(), salvare page\_start/page\_end in metadata JSONB

&nbsp;  - Se altro: comportamento attuale invariato



5\. Colonne DB da aggiungere in scripts/db\_init.sql (vedere db-rules.md):

&nbsp;  page\_start integer NULL

&nbsp;  page\_end   integer NULL

&nbsp;  section\_title text NULL



\## EmbeddingAdapter in embedding.py (NON modificare interfaccia pubblica)

embed\_text(text: str)        → Tuple\[List\[float], str, int]   # singolo

embed\_texts(texts: List\[str]) → Tuple\[List\[List\[float]], str, int]  # batch



Provider "dummy":  deterministico sha256 — usare SEMPRE nei test, zero dipendenze

Provider "ollama": chiama /api/embed (batch), fallback /api/embeddings (legacy per-item)

EMBEDDING\_DIM deve matchare il modello: 768 per nomic-embed-text



\## Aggiunta provider SentenceTransformers (roadmap — solo se Ollama non disponibile)

Nuovo provider "sentence-transformers" in embedding.py:

\- model: intfloat/multilingual-e5-large (1024d) oppure nomic-embed-text locale

\- aggiungere a requirements.txt: sentence-transformers>=2.7

\- Se si cambia dim da 768 a 1024: docker compose down -v obbligatorio + reinit DB



\## Watcher service (task M2-4 — come implementare)

\- Usare watchdog.PollingObserver, NON Observer (inotify non funziona su Docker+Windows)

\- Polling interval: env WATCHER\_POLL\_SECONDS (default 30)

\- Debouncing: aspettare che il file non cambi dimensione per 2 poll prima di ingestire

\- Delete propagation:

&nbsp;   file sparisce da inbox → UPDATE documents SET is\_deleted=True, deleted\_at=now()

&nbsp;   → DELETE FROM chunks WHERE document\_id = <id>

&nbsp;   → inserire riga in audit\_log

\- Aggiungere a docker-compose.yml come nuovo service (vedere db-rules.md)



\## Chunking attuale (non cambiare per TXT/MD/CSV/JSON)

chunk\_text(text, size=1200, overlap=200): caratteri non token, step = size - overlap = 1000

Per PDF usare pymupdf4llm che gestisce già il chunking per pagina

