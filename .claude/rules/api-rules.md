\# api-rules.md — Regole per API endpoints

---

paths:

&nbsp; - api/app/main.py

&nbsp; - api/app/query.py

&nbsp; - api/app/db.py

&nbsp; - tests/test\_query.py

&nbsp; - tests/test\_main.py

---



\## Stack SYNC (non cambiare)

\- Route FastAPI con def, NON async def

\- psycopg2 RealDictCursor: accedere con row\["nome\_colonna"], NON row\[0]

\- Context manager DB già implementato: with get\_db\_cursor() as cursor



\## Schemi Pydantic v2 esistenti in main.py (non ridefinire)

QueryRequest : query str min\_length=1 | kb Optional\[str] | top\_k Optional\[int] ge=1 le=20 default=5

Source       : id str | score float | kb\_namespace str | source\_path Optional\[str] | excerpt str

QueryResponse: answer str | sources List\[Source]



\## Estensioni schema Source da aggiungere in M2 (solo quando si implementa PDF)

page\_start    Optional\[int] = None

page\_end      Optional\[int] = None

section\_title Optional\[str] = None

doc\_title     Optional\[str] = None



\## Endpoint esistenti (non modificare comportamento senza test)

GET  /health           → {"status":"ok","database":"connected"} oppure HTTP 503

POST /api/v1/query     → QueryResponse con answer + sources ordinati per score desc



\## Nuovi endpoint da aggiungere in M2 (in ordine di priorità)

POST /api/v1/upload?kb=<namespace>

&nbsp; - multipart/form-data con uno o più file

&nbsp; - tipi supportati MVP: .pdf .txt .md .csv .json

&nbsp; - salva in /data/inbox/<kb>/<filename>

&nbsp; - ritorna: {"upload\_id": "uuid", "job\_id": "uuid", "kb": "namespace", "files": \[...]}

&nbsp; - errori: 413 se file > MAX\_UPLOAD\_SIZE\_MB | 415 per tipo non supportato | 400 se kb mancante



GET /api/v1/kbs

&nbsp; - ritorna lista KB dal DB con conteggio documenti e chunk

&nbsp; - {"kbs": \[{"namespace": str, "nome": str, "doc\_count": int, "chunk\_count": int}]}



GET /health/ready

&nbsp; - verifica DB connesso + estensione vector presente

&nbsp; - ritorna 200 se tutto ok, 503 con dettaglio se qualcosa manca



GET /metrics

&nbsp; - contatori: query\_count, ingest\_count, error\_count, avg\_latency\_ms

&nbsp; - formato testo Prometheus-compatible oppure JSON semplice per PoC



\## Gestione errori (detail sempre in italiano)

\- HTTP 413: "File troppo grande. Dimensione massima consentita: {MAX\_UPLOAD\_SIZE\_MB}MB"

\- HTTP 415: "Tipo file non supportato. Formati accettati: PDF, TXT, MD, CSV, JSON"

\- HTTP 400: "Parametro kb obbligatorio. Specificare il namespace della knowledge base."

\- HTTP 500: "Errore interno durante l'esecuzione della query: {dettaglio}"

\- HTTP 503: "Database non raggiungibile. Riprovare tra qualche secondo."



\## Parametro synthesize (da aggiungere in M2 con LLM)

POST /api/v1/query accetterà anche:

&nbsp; synthesize: Optional\[bool] = False

Se True e LLM disponibile → chiama api/app/llm.py per generare risposta sintetica

Se False o LLM non disponibile → answer = "Retrieval-only response." (comportamento attuale)

