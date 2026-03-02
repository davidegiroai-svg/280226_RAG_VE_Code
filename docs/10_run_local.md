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

## 5. Windows/PowerShell

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

## 6. Verifica API

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

## 7. Ingest da filesystem

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

## 8. Windows/PowerShell

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

## 9. Query demo

Dopo l'ingest, query i documenti:

```bash
# Test POST /api/v1/query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "bandi", "top_k": 3}'
```

---

## 10. Reset (se necessario)

Per fermare e rimuovere tutto incluso il volume dati:

```bash
docker compose down -v
```

Per riavviare da zero:

```bash
docker compose up -d
```