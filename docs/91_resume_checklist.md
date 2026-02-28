# Resume Checklist — RAG VE PoC (ripartenza)

## Comandi PowerShell (copiabili)

```powershell
# 1) Posizionati nella root del progetto
cd C:\Users\D.Giro\280226_RAG_VE_Code

# 2) Verifica file chiave
ls docker-compose.yml, .env.example, scripts\db_init.sql, api\Dockerfile

# 3) Controlla ultimo commit e log
git log -1 --oneline

# 4) Avvia servizi (DB + API)
docker compose up -d

# 5) Verifica health API
curl http://localhost:8000/health

# 6) Test rapido endpoint query (ritorna stub)
curl -X POST http://localhost:8000/api/v1/query -H "Content-Type: application/json" -d '{"query":"test","top_k":3}'
```

## Reset rapido

```powershell
# Fermare e rimuovere tutto incluso volume dati
docker compose down -v
```

## Dove guardare

- `_cc_status/checkpoint_status.md` — stato milestone e timestamp
- `docs/90_freeze_snapshot.md` — questo freeze snapshot
- `docs/10_run_local.md` — runbook operativo
- `api/` — codice skeleton API

## Primo task da riprendere

- Riprendere **CC-05**: implementare `worker/` per ingest filesystem + chunking + popolare `chunks`.  
Motivazione: senza dati reali, le API restano stub; CC-05 abilita test end-to-end e validazione successiva embedding/citation.
