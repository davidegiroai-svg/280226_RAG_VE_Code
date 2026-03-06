# Metadata Sidecar System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Arricchire ogni chunk con metadati strutturati (target, ambiti, tipo documento, fonte, ecc.) tramite file `.meta.json` sidecar letti all'ingest, propagati nella pipeline query, e visibili all'LLM nel contesto — migliorando drasticamente la precisione delle risposte RAG.

**Architecture:** Approccio A (sidecar JSON). Ogni documento ha un file `<nome>.meta.json` accanto a sé in `/data/inbox/<kb>/`. L'ingest lo legge e injetta i campi nel JSONB `chunks.metadata`. La pipeline query propaga il JSONB fino a `_build_context()`, che prefissa ogni chunk con un header TARGET/AMBITI leggibile dall'LLM. Per i nuovi upload, un nuovo modulo `metadata_extractor.py` usa l'LLM per generare il `.meta.json` automaticamente.

**Tech Stack:** Python 3.11, FastAPI sync, psycopg2, Ollama /api/chat, pytest sincrono

**Parallelizzazione agent teams:**
- **Agent A** (Tasks 1-3): pipeline code — ingest + query + context enrichment
- **Agent B** (Tasks 4-5): extractor code — metadata_extractor.py + upload integration
- **Agent C** (Task 6): contenuto — `.meta.json` per KB `programmi/`
- **Agent D** (Task 7): contenuto — `.meta.json` per KB `bandi/`
- **Agent E** (Task 8): contenuto — `.meta.json` per KB `progetti/`
- **Agent F** (Task 9, dopo tutti): re-ingest + test suite + checkpoint

---

## Schema `.meta.json` (riferimento per tutti gli agent)

```json
{
  "titolo": "...",
  "tipo_documento": "programma_operativo | avviso_bando | scheda_progetto | linee_guida | decreto | allegato | sintesi",
  "fonte_programma": "es. PN Inclusione, PN Metro+, PNRR, PR Veneto FESR, PR Veneto FSE+, CERV, AMIF",
  "fondo": "es. FSE+, FESR, AMIF, PNRR, Fondo Povertà, null",
  "ente_gestore": "es. Ministero del Lavoro, Regione Veneto, Comune di Venezia, ...",
  "anno": 2021,
  "lingua": "it | en",
  "targets": ["Minori", "Adulti", "Donne", "Anziani", "Famiglie", "ETS", "ATS/PA", "Cittadini", "Migranti"],
  "ambiti": [
    "Disabilità/Non autosufficienza",
    "Disagio socio-economico",
    "Disagio abitativo",
    "Grave emarginazione",
    "Occupabilità",
    "Socialità/Comunità",
    "Emergenza",
    "Discriminazione/Lotta alla violenza",
    "Rafforzamento capacità amministrativa",
    "Infrastrutture per l'inclusione sociale",
    "Child guarantee"
  ],
  "dotazione_finanziaria": "es. 1,18 miliardi € | null",
  "scadenza": "es. 2024-12-31 | null",
  "codice_avviso": "es. CERV-2024-CHILD | null",
  "note": "testo libero opzionale"
}
```

**Tassonomia completa targets (usa SOLO questi valori):**
`Minori` · `Adulti` · `Donne` · `Anziani` · `Famiglie` · `ETS` · `ATS/PA` · `Cittadini` · `Migranti`

**Tassonomia completa ambiti (usa SOLO questi valori):**
`Disabilità/Non autosufficienza` · `Disagio socio-economico` · `Disagio abitativo` · `Grave emarginazione` · `Occupabilità` · `Socialità/Comunità` · `Emergenza` · `Discriminazione/Lotta alla violenza` · `Rafforzamento capacità amministrativa` · `Infrastrutture per l'inclusione sociale` · `Child guarantee`

---

## Agent A — Task 1: `read_sidecar_meta()` + inject in `insert_chunks()`

**Files:**
- Modify: `api/app/ingest_fs.py`
- Test: `tests/test_ingest_pdf.py` (aggiungi in fondo)

### Step 1: Scrivi il test che fallisce

Aggiungi in `tests/test_ingest_pdf.py`:

```python
def test_read_sidecar_meta_legge_json_se_esiste(tmp_path):
    """read_sidecar_meta legge il .meta.json accanto al documento."""
    from app.ingest_fs import read_sidecar_meta
    doc = tmp_path / "doc.pdf"
    doc.write_bytes(b"%PDF-1.4")
    meta_file = tmp_path / "doc.meta.json"
    meta_file.write_text('{"titolo": "Test", "targets": ["Minori"]}', encoding="utf-8")

    result = read_sidecar_meta(doc)
    assert result["titolo"] == "Test"
    assert result["targets"] == ["Minori"]


def test_read_sidecar_meta_ritorna_dict_vuoto_se_assente(tmp_path):
    """read_sidecar_meta ritorna {} se il .meta.json non esiste."""
    from app.ingest_fs import read_sidecar_meta
    doc = tmp_path / "doc.pdf"
    doc.write_bytes(b"%PDF-1.4")

    result = read_sidecar_meta(doc)
    assert result == {}


def test_read_sidecar_meta_ritorna_dict_vuoto_se_json_malformato(tmp_path):
    """read_sidecar_meta ritorna {} se il .meta.json è malformato (no crash)."""
    from app.ingest_fs import read_sidecar_meta
    doc = tmp_path / "doc.pdf"
    doc.write_bytes(b"%PDF-1.4")
    (tmp_path / "doc.meta.json").write_text("{ INVALID JSON }", encoding="utf-8")

    result = read_sidecar_meta(doc)
    assert result == {}
```

### Step 2: Esegui per verificare FAIL

```powershell
docker compose exec api pytest tests/test_ingest_pdf.py::test_read_sidecar_meta_legge_json_se_esiste tests/test_ingest_pdf.py::test_read_sidecar_meta_ritorna_dict_vuoto_se_assente tests/test_ingest_pdf.py::test_read_sidecar_meta_ritorna_dict_vuoto_se_json_malformato -v
```

Atteso: `FAILED` — `read_sidecar_meta` non esiste.

### Step 3: Implementa `read_sidecar_meta()` in `api/app/ingest_fs.py`

Aggiungi dopo la funzione `read_text_file()` (circa riga 85):

```python
def read_sidecar_meta(doc_path: Path) -> dict:
    """Legge il file .meta.json sidecar accanto al documento se esiste.

    Cerca <nome_documento>.meta.json nella stessa directory del file.
    Ritorna il dict con i metadati, oppure {} se assente o malformato.

    Args:
        doc_path: Path del documento (es. /data/inbox/programmi/PNRR.pdf)

    Returns:
        Dict metadati (titolo, targets, ambiti, ecc.) o {} se non trovato.
    """
    meta_path = doc_path.with_suffix(".meta.json")
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
```

### Step 4: Inietta sidecar meta in `insert_chunks()`

In `insert_chunks()`, PRIMA del branch PDF (circa riga 162), aggiungi la lettura del sidecar:

```python
def insert_chunks(
    cur,
    kb_id: str,
    kb_namespace: str,
    doc_id: str,
    source_path: str,
    file_name: str,
    text: str,
    *,
    file_path: Path = None,
) -> int:
    # Leggi metadati sidecar se disponibili
    sidecar = read_sidecar_meta(file_path) if file_path is not None else {}
```

Poi nel branch PDF, sostituisci la costruzione di `meta` (riga ~177):

```python
        meta = {
            "source_path": source_path,
            "file_name": file_name,
            "chunk_index": chunk_index,
            "page_start": pc["page_start"],
            "page_end": pc["page_end"],
            **sidecar,   # sovrascrive con i campi sidecar se presenti
        }
```

E nel branch TXT/JSON (riga ~218):

```python
        meta = {
            "source_path": source_path,
            "file_name": file_name,
            "chunk_index": chunk_index,
            **sidecar,
        }
```

### Step 5: Esegui test

```powershell
docker compose exec api pytest tests/test_ingest_pdf.py -v
```

Atteso: tutti `PASSED`.

### Step 6: Commit

```bash
git add api/app/ingest_fs.py tests/test_ingest_pdf.py
git commit -m "feat(ingest): read_sidecar_meta() + inject doc metadata in chunks.metadata JSONB"
```

---

## Agent A — Task 2: Pipeline query propaga `doc_metadata`

**Files:**
- Modify: `api/app/query.py`
- Modify: `api/app/hybrid.py`
- Modify: `api/app/main.py` (solo modello `Source`)
- Test: aggiungi in `tests/test_query.py`

### Step 1: Scrivi test che fallisce

Aggiungi in `tests/test_query.py`:

```python
def test_parse_results_include_doc_metadata(monkeypatch):
    """parse_results deve includere doc_metadata dai chunk results."""
    from app.query import parse_results
    rows = [{
        "id": "uuid-1",
        "kb_namespace": "programmi",
        "excerpt": "Testo di prova.",
        "source_path": "/data/inbox/programmi/PNRR.pdf",
        "distance": 0.2,
        "doc_metadata": {"targets": ["Minori"], "ambiti": ["Child guarantee"]},
    }]
    results = parse_results(rows)
    assert results[0]["doc_metadata"] == {"targets": ["Minori"], "ambiti": ["Child guarantee"]}


def test_parse_results_doc_metadata_none_se_assente(monkeypatch):
    """parse_results restituisce doc_metadata={} se la colonna è NULL."""
    from app.query import parse_results
    rows = [{
        "id": "uuid-2",
        "kb_namespace": "programmi",
        "excerpt": "Testo.",
        "source_path": None,
        "distance": 0.3,
        "doc_metadata": None,
    }]
    results = parse_results(rows)
    assert results[0]["doc_metadata"] == {}
```

### Step 2: Verifica FAIL

```powershell
docker compose exec api pytest tests/test_query.py::test_parse_results_include_doc_metadata tests/test_query.py::test_parse_results_doc_metadata_none_se_assente -v
```

### Step 3: Aggiorna `build_query_sql()` in `query.py`

Aggiungi `metadata AS doc_metadata` alla SELECT (dopo `chunk_index`):

```python
    sql = """
        SELECT
            id::text,
            kb_namespace,
            document_id::text,
            testo as excerpt,
            metadata->>'source_path' as source_path,
            chunk_index,
            metadata AS doc_metadata,
            embedding <=> %s as distance
        FROM chunks
        WHERE embedding IS NOT NULL
    """
```

### Step 4: Aggiorna `parse_results()` in `query.py`

```python
def parse_results(rows) -> List[Dict[str, Any]]:
    """Parse query results into response format."""
    sources = []
    for row in rows:
        distance = float(row["distance"])
        score = max(0.0, 1.0 - distance)
        raw_meta = row.get("doc_metadata") or {}
        # psycopg2 RealDictCursor restituisce JSONB come dict Python
        if isinstance(raw_meta, str):
            import json as _json
            try:
                raw_meta = _json.loads(raw_meta)
            except Exception:
                raw_meta = {}
        sources.append({
            "id": row["id"],
            "score": score,
            "kb_namespace": row["kb_namespace"],
            "source_path": row.get("source_path"),
            "excerpt": row["excerpt"],
            "doc_metadata": raw_meta,
        })
    return sources
```

### Step 5: Aggiorna `fts_search()` in `hybrid.py`

Aggiungi `metadata AS doc_metadata` alla SELECT:

```python
    sql = """
        SELECT
            id::text,
            kb_namespace,
            LEFT(testo, 800) AS excerpt,
            metadata->>'source_path' AS source_path,
            metadata AS doc_metadata,
            ts_rank(testo_tsv, plainto_tsquery('italian', %s)) AS rank
        FROM chunks
        WHERE testo_tsv IS NOT NULL
          AND testo_tsv @@ plainto_tsquery('italian', %s)
    """
```

E nel builder risultati di `fts_search()`:

```python
    for row in rows:
        raw_meta = row.get("doc_metadata") or {}
        if isinstance(raw_meta, str):
            import json as _json
            try:
                raw_meta = _json.loads(raw_meta)
            except Exception:
                raw_meta = {}
        results.append({
            "id": row["id"],
            "score": float(row["rank"]),
            "kb_namespace": row["kb_namespace"],
            "source_path": row.get("source_path"),
            "excerpt": row["excerpt"],
            "doc_metadata": raw_meta,
        })
```

### Step 6: Esegui test

```powershell
docker compose exec api pytest tests/test_query.py -v
```

Atteso: tutti `PASSED`.

### Step 7: Commit

```bash
git add api/app/query.py api/app/hybrid.py tests/test_query.py
git commit -m "feat(query): propaga doc_metadata JSONB nella pipeline risultati"
```

---

## Agent A — Task 3: `_build_context()` con header metadati

**Files:**
- Modify: `api/app/llm.py`
- Test: `tests/test_llm.py`

### Step 1: Scrivi test che fallisce

Aggiungi in `tests/test_llm.py`:

```python
def test_build_context_include_header_metadata_se_presenti():
    """_build_context deve prefissare ogni chunk con TIPO/FONTE/TARGET/AMBITI se doc_metadata presente."""
    from app.llm import _build_context
    chunks = [{
        "excerpt": "Testo del programma.",
        "source_path": "/data/inbox/programmi/test.pdf",
        "kb_namespace": "programmi",
        "doc_metadata": {
            "tipo_documento": "programma_operativo",
            "fonte_programma": "PN Inclusione",
            "targets": ["Minori", "Famiglie"],
            "ambiti": ["Child guarantee", "Disagio socio-economico"],
        },
    }]
    ctx = _build_context(chunks)
    assert "TIPO: programma_operativo" in ctx
    assert "FONTE: PN Inclusione" in ctx
    assert "TARGET: Minori" in ctx
    assert "AMBITI: Child guarantee" in ctx


def test_build_context_no_header_se_metadata_assente():
    """_build_context non deve aggiungere header se doc_metadata è assente o vuoto."""
    from app.llm import _build_context
    chunks = [{"excerpt": "Testo.", "source_path": "/data/test.txt", "kb_namespace": "demo"}]
    ctx = _build_context(chunks)
    assert "TIPO:" not in ctx
    assert "TARGET:" not in ctx
    assert "--- INIZIO DOCUMENTO 1" in ctx
```

### Step 2: Verifica FAIL

```powershell
docker compose exec api pytest tests/test_llm.py::test_build_context_include_header_metadata_se_presenti tests/test_llm.py::test_build_context_no_header_se_metadata_assente -v
```

### Step 3: Aggiorna `_build_context()` in `api/app/llm.py`

```python
def _build_context(chunks: List[Dict[str, Any]]) -> str:
    """Costruisce la stringa contesto dai chunk recuperati.

    Ogni documento è avvolto da separatori INIZIO/FINE espliciti. Se il chunk
    ha doc_metadata (da sidecar .meta.json), aggiunge un header TARGET/AMBITI
    leggibile dall'LLM prima del testo.

    Formato per ogni chunk:
      --- INIZIO DOCUMENTO N (fonte: <path>) ---
      [TIPO: xxx | FONTE: xxx | TARGET: xxx · yyy | AMBITI: xxx · yyy]   ← se disponibile
      <excerpt>
      --- FINE DOCUMENTO N ---
    """
    if not chunks:
        return ""
    parti = []
    for i, chunk in enumerate(chunks, 1):
        excerpt = chunk.get("excerpt", "")
        fonte = chunk.get("source_path") or chunk.get("kb_namespace", "sconosciuta")
        meta = chunk.get("doc_metadata") or {}

        header_parts = []
        if meta.get("tipo_documento"):
            header_parts.append(f"TIPO: {meta['tipo_documento']}")
        if meta.get("fonte_programma"):
            header_parts.append(f"FONTE: {meta['fonte_programma']}")
        if meta.get("targets"):
            header_parts.append(f"TARGET: {' · '.join(meta['targets'])}")
        if meta.get("ambiti"):
            header_parts.append(f"AMBITI: {' · '.join(meta['ambiti'])}")

        meta_header = ""
        if header_parts:
            meta_header = "[" + " | ".join(header_parts) + "]\n"

        parti.append(
            f"--- INIZIO DOCUMENTO {i} (fonte: {fonte}) ---\n"
            f"{meta_header}"
            f"{excerpt}\n"
            f"--- FINE DOCUMENTO {i} ---"
        )
    return "\n\n".join(parti)
```

### Step 4: Esegui tutti i test llm

```powershell
docker compose exec api pytest tests/test_llm.py -v
```

Atteso: tutti 15 test `PASSED`.

### Step 5: Rebuild + regression completa

```powershell
docker compose up -d --build 2>&1 | tail -5
docker compose exec api pytest tests/ -q --tb=short 2>&1 | tail -5
```

Atteso: ≥ 132 test `PASSED`.

### Step 6: Commit

```bash
git add api/app/llm.py tests/test_llm.py
git commit -m "feat(llm): _build_context arricchito con header TARGET/AMBITI da doc_metadata sidecar"
```

---

## Agent B — Task 4: `metadata_extractor.py` (LLM extraction per nuovi documenti)

**Files:**
- Create: `api/app/metadata_extractor.py`
- Test: `tests/test_metadata_extractor.py`

### Step 1: Scrivi i test

Crea `tests/test_metadata_extractor.py`:

```python
"""tests/test_metadata_extractor.py — TDD per estrazione metadati LLM da documenti."""
import json
from unittest.mock import patch, MagicMock
from pathlib import Path


EXPECTED_SCHEMA_KEYS = {
    "titolo", "tipo_documento", "fonte_programma", "fondo", "ente_gestore",
    "anno", "lingua", "targets", "ambiti", "dotazione_finanziaria",
    "scadenza", "codice_avviso", "note",
}


def test_extract_metadata_ritorna_dict_con_schema_atteso(tmp_path):
    """extract_metadata_for_file deve ritornare dict con tutte le chiavi schema."""
    fake_response = MagicMock()
    fake_response.json.return_value = {
        "message": {"content": json.dumps({
            "titolo": "Test Doc",
            "tipo_documento": "avviso_bando",
            "fonte_programma": "PN Inclusione",
            "fondo": "FSE+",
            "ente_gestore": "Ministero",
            "anno": 2024,
            "lingua": "it",
            "targets": ["Minori"],
            "ambiti": ["Child guarantee"],
            "dotazione_finanziaria": "1M €",
            "scadenza": None,
            "codice_avviso": None,
            "note": None,
        })}
    }
    fake_response.raise_for_status.return_value = None

    doc = tmp_path / "test.pdf"
    doc.write_bytes(b"%PDF")

    with patch("requests.post", return_value=fake_response):
        from app.metadata_extractor import extract_metadata_for_file
        result = extract_metadata_for_file(doc, model="llama3.2", text_snippet="Testo test.")

    assert isinstance(result, dict)
    assert result["titolo"] == "Test Doc"
    assert result["targets"] == ["Minori"]


def test_extract_metadata_ritorna_fallback_su_errore_llm(tmp_path):
    """extract_metadata_for_file ritorna dict con valori null se LLM non risponde."""
    import requests as req
    doc = tmp_path / "test.pdf"
    doc.write_bytes(b"%PDF")

    with patch("requests.post", side_effect=req.ConnectionError("offline")):
        from app.metadata_extractor import extract_metadata_for_file
        result = extract_metadata_for_file(doc, model="llama3.2", text_snippet="Testo test.")

    assert isinstance(result, dict)
    assert "titolo" in result
    assert result["targets"] == []
    assert result["ambiti"] == []


def test_prompt_estrazione_contiene_tassonomia():
    """METADATA_EXTRACTION_PROMPT deve contenere la tassonomia targets e ambiti."""
    from app.metadata_extractor import METADATA_EXTRACTION_PROMPT
    p = METADATA_EXTRACTION_PROMPT
    for target in ["Minori", "Anziani", "Migranti", "ETS"]:
        assert target in p
    for ambito in ["Disabilità", "Occupabilità", "Child guarantee"]:
        assert ambito in p
```

### Step 2: Verifica FAIL

```powershell
docker compose exec api pytest tests/test_metadata_extractor.py -v
```

### Step 3: Crea `api/app/metadata_extractor.py`

```python
"""metadata_extractor.py — Estrazione metadati strutturati da documenti tramite LLM."""
import os
import json
import logging
import requests
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

METADATA_EXTRACTION_PROMPT = (
    "Sei un archivista esperto di documenti della Pubblica Amministrazione italiana, "
    "specializzato in fondi europei e programmazione sociale.\n\n"
    "Analizza il testo del documento fornito e restituisci SOLO un oggetto JSON valido "
    "(nessun testo aggiuntivo, nessun markdown, nessuna spiegazione) con questo schema:\n\n"
    '{"titolo": "...", '
    '"tipo_documento": "programma_operativo|avviso_bando|scheda_progetto|linee_guida|decreto|allegato|sintesi", '
    '"fonte_programma": "es. PN Inclusione, PN Metro+, PNRR, PR Veneto FESR, ...", '
    '"fondo": "FSE+|FESR|AMIF|PNRR|Fondo Povertà|null", '
    '"ente_gestore": "...", '
    '"anno": 2024, '
    '"lingua": "it|en", '
    '"targets": ["Minori","Adulti","Donne","Anziani","Famiglie","ETS","ATS/PA","Cittadini","Migranti"], '
    '"ambiti": ["Disabilità/Non autosufficienza","Disagio socio-economico","Disagio abitativo",'
    '"Grave emarginazione","Occupabilità","Socialità/Comunità","Emergenza",'
    '"Discriminazione/Lotta alla violenza","Rafforzamento capacità amministrativa",'
    '"Infrastrutture per l\'inclusione sociale","Child guarantee"], '
    '"dotazione_finanziaria": "...|null", '
    '"scadenza": "YYYY-MM-DD|null", '
    '"codice_avviso": "...|null", '
    '"note": "...|null"}\n\n'
    "ISTRUZIONI:\n"
    "- targets e ambiti: includi SOLO i valori dall'elenco sopra che sono effettivamente presenti nel documento\n"
    "- Se un campo non è presente nel documento, usa null\n"
    "- Rispondi ESCLUSIVAMENTE con il JSON, senza testo prima o dopo\n"
)

_FALLBACK = {
    "titolo": None, "tipo_documento": None, "fonte_programma": None,
    "fondo": None, "ente_gestore": None, "anno": None, "lingua": "it",
    "targets": [], "ambiti": [], "dotazione_finanziaria": None,
    "scadenza": None, "codice_avviso": None, "note": None,
}


def extract_metadata_for_file(
    file_path: Path,
    model: str,
    text_snippet: str,
    timeout: int = 120,
) -> dict:
    """Estrae metadati strutturati da un documento usando l'LLM Ollama.

    Args:
        file_path:    Path del documento (usato solo per il nome file come contesto).
        model:        Nome modello Ollama (es. llama3.2).
        text_snippet: Testo estratto dal documento (prime N pagine o chars).
        timeout:      Timeout HTTP in secondi.

    Returns:
        Dict con le chiavi dello schema metadati. In caso di errore: _FALLBACK.
    """
    ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")

    user_content = (
        f"Nome file: {file_path.name}\n\n"
        f"Testo documento:\n{text_snippet[:6000]}"
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": METADATA_EXTRACTION_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
    }

    try:
        resp = requests.post(f"{ollama_base_url}/api/chat", json=payload, timeout=timeout)
        resp.raise_for_status()
        content = resp.json()["message"]["content"].strip()
        # Rimuovi eventuali backtick markdown
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        logger.warning("extract_metadata_for_file: errore — %s", e)
        return dict(_FALLBACK)


def save_sidecar_meta(file_path: Path, meta: dict) -> Path:
    """Salva i metadati come file .meta.json accanto al documento.

    Args:
        file_path: Path del documento originale.
        meta:      Dict metadati da salvare.

    Returns:
        Path del file .meta.json creato.
    """
    meta_path = file_path.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta_path
```

### Step 4: Esegui test

```powershell
docker compose exec api pytest tests/test_metadata_extractor.py -v
```

### Step 5: Commit

```bash
git add api/app/metadata_extractor.py tests/test_metadata_extractor.py
git commit -m "feat(extractor): metadata_extractor.py — LLM extraction + save_sidecar_meta"
```

---

## Agent B — Task 5: Integrazione POST `/upload` con metadata extraction

**Files:**
- Modify: `api/app/main.py`
- Test: `tests/test_upload.py` (aggiungi casi)

### Step 1: Leggi il codice attuale dell'endpoint `/upload` in `api/app/main.py`

Leggi la sezione dell'endpoint upload (cerca `@app.post.*upload`).

### Step 2: Scrivi test che fallisce

Aggiungi in `tests/test_upload.py` (o crea il file se non esiste):

```python
def test_upload_genera_meta_json_se_llm_disponibile(monkeypatch, tmp_path):
    """POST /upload deve generare .meta.json accanto al file se Ollama risponde."""
    # Questo test verifica che save_sidecar_meta venga chiamata dopo l'upload
    monkeypatch.setenv("EMBEDDING_PROVIDER", "dummy")
    fake_meta = {"titolo": "Test", "targets": ["Minori"], "ambiti": ["Child guarantee"]}

    with patch("app.main.extract_metadata_for_file", return_value=fake_meta) as mock_extract, \
         patch("app.main.save_sidecar_meta") as mock_save:
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        # ... chiama upload con un file PDF di test
        # Verifica che mock_extract e mock_save siano stati chiamati
        pass  # Implementazione dettagliata da completare leggendo il codice upload attuale
```

**NOTA per l'agent:** Leggi il codice attuale di `main.py` (endpoint `/upload`) prima di scrivere il test completo. Il test deve:
1. Mockare `extract_metadata_for_file` (ritorna fake_meta)
2. Mockare `save_sidecar_meta`
3. Fare una POST /upload con un file .pdf
4. Verificare che entrambi i mock siano stati chiamati

### Step 3: Aggiungi import in `main.py`

```python
from .metadata_extractor import extract_metadata_for_file, save_sidecar_meta
```

### Step 4: Aggiungi metadata extraction nel body dell'endpoint `/upload`

Dopo aver salvato il file su disco, aggiungi (in background o sincrono):

```python
# Genera metadati sidecar via LLM (best-effort, non blocca upload se fallisce)
try:
    llm_model = os.environ.get("OLLAMA_LLM_MODEL", "llama3.2")
    # Estrai snippet di testo per il contesto
    text_snippet = _extract_text_snippet(saved_path)
    meta = extract_metadata_for_file(saved_path, model=llm_model, text_snippet=text_snippet)
    save_sidecar_meta(saved_path, meta)
except Exception as e:
    logger.warning("upload: metadata extraction fallita per %s — %s", saved_path.name, e)
```

Aggiungi anche la funzione helper `_extract_text_snippet()` in `main.py`:

```python
def _extract_text_snippet(file_path: Path, max_chars: int = 6000) -> str:
    """Estrae i primi max_chars caratteri di testo da un file per metadata extraction."""
    suffix = file_path.suffix.lower()
    try:
        if suffix == ".pdf":
            import pymupdf4llm
            return pymupdf4llm.to_markdown(str(file_path))[:max_chars]
        elif suffix in (".txt", ".md", ".csv", ".json"):
            return file_path.read_text(encoding="utf-8-sig", errors="ignore")[:max_chars]
        else:
            return f"File: {file_path.name}"
    except Exception:
        return f"File: {file_path.name}"
```

### Step 5: Rebuild + test

```powershell
docker compose up -d --build 2>&1 | tail -5
docker compose exec api pytest tests/ -q --tb=short 2>&1 | tail -5
```

### Step 6: Commit

```bash
git add api/app/main.py
git commit -m "feat(upload): genera .meta.json sidecar via LLM dopo ogni upload"
```

---

## Agent C — Task 6: Crea `.meta.json` per KB `programmi/`

**Percorso host:** `C:\Users\D.Giro\280226_RAG_VE_Code\data\inbox\programmi\`

**Per ogni documento, estrai testo con:**

```powershell
# PDF — estrai prime 80 pagine come testo
docker compose exec api python -c "
import pymupdf4llm, sys
text = pymupdf4llm.to_markdown(sys.argv[1])
print(text[:10000])
" /data/inbox/programmi/NOME_FILE.pdf

# Per vedere la struttura completa di un grosso PDF (es PNRR 300 pagine):
docker compose exec api python -c "
import pymupdf4llm
pages = pymupdf4llm.to_markdown('/data/inbox/programmi/PNRR.pdf', page_chunks=True)
# Mostra pagine con 'disabil' o 'lavoro' o 'minori' per verificare copertura tematica
for p in pages:
    if any(kw in p['text'].lower() for kw in ['disabil','lavoro','minori','migranti','anziani','famiglie']):
        print(f\"=== Pagina {p['metadata']['page']} ===\")
        print(p['text'][:500])
        print()
" 2>&1 | head -200
```

**Documenti da metadatare:**

1. `PNRR.pdf` → `PNRR.meta.json`
2. `IT - PN Inclusione e lotta alla povertà 2021-2027.pdf` → `IT - PN Inclusione e lotta alla povertà 2021-2027.meta.json`
3. `IT - PN Capacità per la coesione AT 2021-2027.pdf` → idem
4. `IT - PN METRO plus e città medie Sud 2021-2027.pdf` → idem
5. `IT - PR Veneto FESR 2021-2027.pdf` → idem
6. `IT - PR Veneto FSE+ 2021-2027.pdf` → idem
7. `IT - Programme Italy - AMIF.pdf` → idem
8. `Linee Guida per l'impiego della Quota Povertà Estrema del Fondo Povertà_2021-2023.pdf` → idem
9. `Linee Guida per l'impiego della Quota Servizi del Fondo Povertà_2022-2023.pdf` → idem
10. `Piano per la Non Auto Sufficienza_2022-2024.pdf` → idem

**Per ogni file, crea il `.meta.json` in `C:\Users\D.Giro\280226_RAG_VE_Code\data\inbox\programmi\`**

Usa la tassonomia ESATTA riportata in cima al piano. Leggi abbastanza testo da essere certi di coprire TUTTI i target e ambiti presenti nell'intero documento (non solo le prime pagine).

### Step finale: Verifica

```powershell
ls C:\Users\D.Giro\280226_RAG_VE_Code\data\inbox\programmi\*.meta.json
```

Atteso: 10 file `.meta.json`.

---

## Agent D — Task 7: Crea `.meta.json` per KB `bandi/`

**Percorso host:** `C:\Users\D.Giro\280226_RAG_VE_Code\data\inbox\bandi\`

**Per DOCX:**

```powershell
docker compose exec api python -c "
from docx import Document
doc = Document('/data/inbox/bandi/NOME_FILE.docx')
text = '\n'.join([p.text for p in doc.paragraphs if p.text.strip()])
print(text[:8000])
"
```

**Per PDF (come sopra).**

**Documenti da metadatare (crea `.meta.json` per ciascuno):**

PDF originali:
- `CERV_call-fiche_cerv-2024-child_en it.pdf`
- `CERV_call-fiche_cerv-2024-child_en.pdf`
- `Fondazione_CDP_Bando_A_Scuola_per_il_Futuro_seconda_edizione.pdf`
- `PerForma PA_avviso_linea_5_-_modifica_ai_sensi_art.24_-_7.11_signed.pdf`
- `PerForma PA_avviso_linea_5_formazione PA.pdf`
- `PN Governance_Allegato 1 - Definizioni.pdf`
- `PN Governance_Allegato 2 - Definizione dei Servizi e modalità di migrazione.pdf`
- `PN Governance_Allegato 3 - Domanda di partecipazione.pdf`
- `PN Governance_Allegato 4 - Istruzioni DNSH.pdf`
- `PN Governance_Allegato 5 - Domanda di erogazione.pdf`
- `PN Governance_Avviso 1.2 - Province e Città metropolitane.pdf`
- `PN Inclusione_DesTEENazioni_allegato_a_domanda_di_finanziamento_e_dichiarazioni.pdf`
- `PN Inclusione_DesTEENazioni_allegato_b_modello_proposta_progettuale_aaggornato_28032024.pdf`
- `PN Inclusione_DesTEENazioni_allegato_c_modello_piano_finanziario_aggiornato_28032024.pdf`
- `PN Inclusione_DesTEENazioni_allegato_d_privacy.pdf`
- `PN Inclusione_DesTEENazioni_avviso_desteenazione.pdf`
- `PN Inclusione_DesTEENazioni_decreto_prot_41_0000015_del_290124.pdf`
- `PN Inclusione_DesTEENazioni_nota_metodologica_spazio_multifunzionale.pdf`
- `PN Inclusione_DesTEENazioni_PANGI.pdf`
- `PN Inclusione_RSC_allegato_a_domanda_di_finanziamento_e_dichiarazioni.pdf`
- `PN Inclusione_RSC_allegato_d_privacy.pdf`
- `PN Inclusione_RSC_allegato_e_elenco_documenti_per_rendicontazione_spese.pdf`
- `Sintesi SCS_PN Governance_Avviso pubblico - ABILITAZIONE AL CLOUD PER LE PA LOCALI_rev.pdf`
- `Social Innovation Initiative_Approcci innovativi per affrontare la disoccupazione di lunga durata.pdf`
- `Social Innovation Initiative_Innovative Approaches Tackling Long-Term Unemployment.pdf`

DOCX:
- `Sintesi SCS_Avviso_CERV_DAPHNE.docx`
- `Sintesi SCS_Avviso_CERV_rights of the child and children's participation.docx`
- `Sintesi SCS_Avviso_PN Inclusione_DesTEENazioni.docx`
- `Sintesi SCS_ESFA_Innovative Approaches Tackling LongTerm Unemployment.docx`
- `Sintesi SCS_Fondazione_CDP_Avviso_A scuola per il futuro 2024.docx`
- `Sintesi SCS_PerForma PA.docx`
- `Sintesi SCS_PN Inclusione__Avviso_assunzione di personale.docx`
- `Sintesi SCS_PN Inclusione_Avviso pubblico "Manifestazione d'interesse finalizzata alla selezione di Enti del Terzo Settore per la co-progettazione.docx`
- `Sintesi SCS_PN Inclusione_Avviso pubblico "MANIFESTAZIONE DI INTERESSE per le azioni di incremento della capacità degli ATS .docx`
- `Sintesi SCS_PN Inclusione_Avviso_co-progettazione di interventi di empowerment.docx`
- `Sintesi SCS_PN Inclusione_RSC.docx`
- `Sintesi SCS_Social Innovation Initiative_Avviso_Innovative Approaches Tackling LongTerm Unemployment.docx`

**Nota:** `PN Inclusione_RSC_allegato_b_modello_proposta_progettuale.docx` e `PN Inclusione_RSC_allegato_c_modello_piano_finanziario.xlsx` sono template/moduli — per questi il meta va comunque compilato ma con `tipo_documento: "allegato"`.

### Step finale: Verifica

```powershell
ls C:\Users\D.Giro\280226_RAG_VE_Code\data\inbox\bandi\*.meta.json | Measure-Object
```

Atteso: ≥ 35 file `.meta.json`.

---

## Agent E — Task 8: Crea `.meta.json` per KB `progetti/`

**Percorso host:** `C:\Users\D.Giro\280226_RAG_VE_Code\data\inbox\progetti\`

**Per DOCX (stessa tecnica di Agent D). Per ODT:**

```powershell
# ODT — prova con python-docx (supporto parziale) o estrazione testo grezzo
docker compose exec api python -c "
from docx import Document
try:
    doc = Document('/data/inbox/progetti/NOME_FILE.odt')
    print('\n'.join([p.text for p in doc.paragraphs if p.text.strip()])[:5000])
except Exception as e:
    print(f'python-docx fallito: {e}')
    # Fallback: leggi come zip e cerca content.xml
    import zipfile, re
    with zipfile.ZipFile('/data/inbox/progetti/NOME_FILE.odt') as z:
        with z.open('content.xml') as f:
            xml = f.read().decode('utf-8')
            text = re.sub('<[^>]+>', ' ', xml)
            print(text[:5000])
"
```

**Documenti da metadatare:**

DOCX:
- `PN_Metro_plus_Scheda progetto nel PO_21_27_Azione 4.11.1_Adulti.docx`
- `PN_Metro_plus_Scheda progetto nel PO_21_27_Azione 4.8.1.docx`
- `PN_Metro_plus_Scheda progetto nel PO_21_27_Azione_4.11.1_Anziani e disabili.docx`
- `PN_Metro_plus_Scheda progetto nel PO_21_27_Azione_4.11.1_Minori e famiglie.docx`
- `PN_Metro_plus_Scheda progetto nel PO_21_27_Azione_4.11.2.docx`
- `PN_Metro_plus_Scheda progetto nel PO_21_27_Azione_4.12.1.docx`
- `PNRR_Linea_1.1.1.docx`
- `PNRR_Linea_1.1.2.docx`
- `PNRR_Linea_1.1.3.docx`
- `PNRR_Linea_1.1.4.docx`
- `PNRR_Linea_1.2.docx`
- `PNRR_Linea_1.3.1.docx`
- `PNRR_Linea_1.3.2.docx`

ODT:
- `PN_Metro_plus_Scheda progetto_Azione 4.11.1C_Adulti_13.09.23.odt`
- `PN_Metro_plus_Scheda progetto_Azione_4.11.1A_Anziani e disabili_13_09_2023odt.odt`

### Step finale: Verifica

```powershell
ls C:\Users\D.Giro\280226_RAG_VE_Code\data\inbox\progetti\*.meta.json | Measure-Object
```

Atteso: 15 file `.meta.json`.

---

## Agent F — Task 9: Re-ingest + Test suite + Checkpoint

**Da eseguire DOPO che tutti gli agent A-E hanno completato.**

### Step 1: Rebuild immagine (se non già fatto da A o B)

```powershell
docker compose up -d --build 2>&1 | tail -5
```

### Step 2: Re-ingest KB `programmi`

```powershell
docker compose --profile manual run --rm worker --kb programmi --path /data/inbox/programmi
```

Atteso: output con `chunks inserted` per ciascun documento, incluso il nuovo chunking sub-pagina.

### Step 3: Re-ingest KB `bandi`

```powershell
docker compose --profile manual run --rm worker --kb bandi --path /data/inbox/bandi
```

### Step 4: Re-ingest KB `progetti`

```powershell
docker compose --profile manual run --rm worker --kb progetti --path /data/inbox/progetti
```

### Step 5: Verifica metadati nel DB

```powershell
docker compose exec db psql -U rag -d rag -c "
SELECT kb_namespace, metadata->>'titolo' as titolo,
       metadata->>'targets' as targets,
       metadata->>'ambiti' as ambiti
FROM chunks
WHERE metadata->>'targets' IS NOT NULL
LIMIT 10;
"
```

Atteso: righe con `targets` e `ambiti` popolati dai `.meta.json`.

### Step 6: Test smoke E2E (con Ollama attivo)

```powershell
$body = @{
    query = "Quali interventi si possono realizzare per persone con disabilità riguardo all'inserimento lavorativo?";
    synthesize = $true;
    kb = "programmi";
    top_k = 5;
    search_mode = "hybrid"
} | ConvertTo-Json
Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/query' -Method Post -Body $body -ContentType 'application/json' -Headers @{"X-API-Key"="<YOUR_KEY>"}
```

Atteso: risposta che cita specifiche sezioni del PNRR/PN Inclusione/PR Veneto FSE+ relative a disabilità e occupabilità, con header `TARGET: Anziani · Adulti` e `AMBITI: Disabilità/Non autosufficienza · Occupabilità` visibili nel contesto.

### Step 7: Regression completa

```powershell
docker compose exec api pytest tests/ -q --tb=short 2>&1 | tail -5
```

Atteso: ≥ 135 test `PASSED`.

### Step 8: Aggiorna checkpoint

File `_cc_status/checkpoint_status.md` — aggiungi:

```markdown
## TASK FR-METADATA-SIDECAR — Metadata sidecar system + metadatazione documenti
**Status:** DONE
**Timestamp:** 2026-03-06
**File modificati:** api/app/ingest_fs.py, api/app/query.py, api/app/hybrid.py,
  api/app/llm.py, api/app/main.py, api/app/metadata_extractor.py (nuovo),
  tests/test_metadata_extractor.py (nuovo), data/inbox/**/*.meta.json (~60 file)
**Implementato:** Sidecar .meta.json per tutti i documenti esistenti (programmi/bandi/progetti).
  Pipeline ingest legge sidecar e injetta targets/ambiti/tipo nel JSONB chunks.metadata.
  Query pipeline propaga doc_metadata fino a _build_context() che aggiunge header TARGET/AMBITI.
  Nuovi upload generano .meta.json automaticamente via LLM.
```

### Step 9: Commit finale

```bash
git add -A
git commit -m "feat(metadata): sistema sidecar completo — .meta.json per 60 documenti + pipeline arricchita"
```
