# Run RAG VE PoC Localmente

## Prerequisiti

- Docker Desktop installato e in esecuzione
- Docker Compose disponibile (`docker compose version`)

---

## 1. Configurazione

Copia il file di esempio e aggiorna le credenziali:

```bash
cp .env.example .env
# Modificare .env con le credenziali desiderate
```

**Nota:** Se cambi `POSTGRES_USER`, `POSTGRES_PASSWORD` o `POSTGRES_DB`, devi ricostruire il container:
```powershell
docker compose down -v
docker compose up -d
```

---

## 2. Avvio

```bash
docker compose up -d
```

Attendere ~30 secondi per l'inizializzazione del database.

---

## 3. Verifica

```bash
# Controllare stato servizi
docker compose ps

# Verificare healthcheck
docker compose logs db
```

---

## 4. Verifica tabelle DB

Accedere al container Postgres:

```bash
docker compose exec db psql -U rag -d rag -c "\dt"
```

Dovresti vedere:
- knowledge_base
- documents
- chunks
- ingest_job
- query_log

---

## 5. Embedding (vector search)

**Dimensione embedding vincolante: 768**

Il sistema usa `vector(768)` per compatibilità con il modello locale **Ollama `nomic-embed-text`** (default per M1).

Se hai dati con vector(1536) da una precedente installazione, devi re-inizializzare il DB:

```powershell
# PowerShell - Comando per re-init DB (cancella tutti i dati!)
docker compose down -v
docker compose up -d
```

**Nota:** Il re-init cancella permanentemente tutti i dati nel DB. Fai backup prima di eseguire se necessario.

Per configurare le variabili di ambiente per l'embedding (opzionale), usa i seguenti comandi PowerShell:

```powershell
# Configurazione embedding (se necessario)
$env:EMBEDDING_PROVIDER="ollama"
$env:OLLAMA_MODEL="nomic-embed-text"
$env:OLLAMA_BASE_URL="http://host.docker.internal:11434"
```

---

## 6. Windows/PowerShell

Se usi PowerShell su Windows, i comandi sono identici. Esempi:

```powershell
# Copia .env
Copy-Item .env.example .env

# Avvio
docker compose up -d

# Verifica
docker compose ps
```

---

## 7. Verifica API

Dopo l'avvio dei servizi, testare l'endpoint health:

```bash
# Test endpoint /health
curl http://localhost:8000/health
```

Testare l'endpoint query:

```bash
# Test POST /api/v1/query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "bandi", "top_k": 3}'
```

Esempio di risposta:

```json
{
  "answer": "Retrieval-only response. No LLM synthesis yet.",
  "sources": [
    {
      "id": "uuid",
      "score": 0.85,
      "kb_namespace": "venezia",
      "source_path": "/path/to/file.pdf",
      "excerpt": "estratto del documento..."
    }
  ]
}
```

---

## 8. Vector Search Query API

Dopo l'ingest, puoi query i documenti usando la ricerca vettoriale (cosine similarity):

### Windows/PowerShell

```powershell
# Test POST /api/v1/query con vector search
$response = Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/query' -Method POST -ContentType 'application/json' -Body '{"query": "bandi", "top_k": 3, "kb": "demo"}'
$response | ConvertTo-Json -Depth 10
```

### Linux/macOS

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "bandi", "top_k": 3, "kb": "demo"}'
```

Esempio di risposta (con 3 risultati ordinati per score):

```json
{
  "answer": "Retrieval-only response. No LLM synthesis yet.",
  "sources": [
    {
      "id": "c6350ed7-4617-48f2-816f-ed7892cbf223",
      "score": 0.413,
      "kb_namespace": "demo",
      "source_path": "/data/inbox/demo/test_mojibake.txt",
      "excerpt": "Questo è un file di test con caratteri accentati..."
    },
    {
      "id": "627dcd6f-0b2a-4a2d-ad08-a6e1e66354c8",
      "score": 0.366,
      "kb_namespace": "demo",
      "source_path": "/data/inbox/demo/demo2.txt",
      "excerpt": "Questo è un secondo file di test..."
    },
    {
      "id": "c68a4fa2-4837-480d-a219-f800f2ce0196",
      "score": 0.365,
      "kb_namespace": "demo",
      "source_path": "/data/inbox/demo/demo.txt",
      "excerpt": "Questo è un file di test per il PoC RAG VE..."
    }
  ]
}
```

**Note:**
- `score`: misura della similarità cosine (1.0 = perfetta, 0.0 = nessuna somiglianza)
- I risultati sono ordinati per score decrescente
- Il filtro `kb` è opzionale: se omesso, cerca in tutte le KB

---

## 9. Ingest da filesystem

Per inserire documenti dal filesystem (es. `./data/inbox/<kb>/`):

```bash
# Eseguire l'ingest su una specifica KB e cartella
docker compose --profile manual run --rm worker --kb demo --path /data/inbox/demo
```

**Nota Windows/Git Bash:** Se usi Git Bash/MSYS su Windows, i path tipo `/data/...` potrebbero essere convertiti in `C:/Program Files/Git/...`. In questo caso:
- Usa `MSYS_NO_PATHCONV=1` prima del comando, oppure
- Esegui i comandi da PowerShell

Esempio con `MSYS_NO_PATHCONV=1`:

```bash
MSYS_NO_PATHCONV=1 docker compose --profile manual run --rm worker --kb demo --path /data/inbox/demo
```

Il worker processa solo file `.txt`, `.md`, `.csv`, `.json` (UTF-8) e:
- crea la KB se non esiste
- inserisce documenti con deduplicazione
- chunka il testo in pezzi da 1200 caratteri con 200 di overlap
- inserisce chunks con metadata

---

## 10. Windows/PowerShell

Se usi PowerShell su Windows, i comandi sono identici. Esempi:

```powershell
# Copia .env
Copy-Item .env.example .env

# Avvio
docker compose up -d

# Verifica
docker compose ps

# Esegui ingest
docker compose --profile manual run --rm worker --kb demo --path /data/inbox/demo
```

**Nota encoding/BOM:** Se vedi caratteri strani (es. `ï»¿` o `Ã¨`) negli estratti, rigenera i file in UTF-8 **senza BOM**, oppure lascia che sia `ingest_fs.py` a gestirli automaticamente (usa `utf-8-sig` per rimuovere BOM).

---

## 11. Query demo

Dopo l'ingest, query i documenti:

```bash
# Test POST /api/v1/query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "bandi", "top_k": 3}'
```

---

## 12. Reset (se necessario)

Per fermare e rimuovere tutto incluso il volume dati:

```bash
docker compose down -v
```

Per riavviare da zero:

```bash
docker compose up -d
```