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

Test con specifica KB:

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "programmi", "kb": "venezia", "top_k": 5}'
```

---

## 7. Reset (se necessario)

Per fermare e rimuovere tutto incluso il volume dati:

```bash
docker compose down -v
```

Per riavviare da zero:

```bash
docker compose up -d
```