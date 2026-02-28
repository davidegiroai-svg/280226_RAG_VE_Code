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

## 5. Reset (se necessario)

Per fermare e rimuovere tutto incluso il volume dati:

```bash
docker compose down -v
```

Per riavviare da zero:

```bash
docker compose up -d
```
