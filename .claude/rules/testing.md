\# testing.md — Regole test per tutto il progetto RAG VE

\# (caricato sempre da Claude Code, senza paths: — le regole di test sono trasversali)



\## Stack test (obbligatorio)

\- pytest SINCRONO — NON usare pytest-asyncio (il progetto usa psycopg2 sync)

\- TestClient da fastapi.testclient (sincrono, no httpx async)

\- Mock DB: unittest.mock.patch("api.app.db.get\_db\_cursor")

\- Mock embedding: monkeypatch.setenv("EMBEDDING\_PROVIDER", "dummy")

\- File: tests/test\_<modulo>.py con funzioni test\_<caso>()



\## Regola TDD (non derogabile)

Scrivere PRIMA il test che fallisce, POI l'implementazione.

Mai scrivere codice senza un test corrispondente.

Se viene chiesto di implementare una feature, il primo artefatto è sempre il test.



\## Template test API (copia e adatta per ogni nuova feature)

```python

from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from api.app.main import app



client = TestClient(app)



def test\_query\_ritorna\_sources\_con\_score\_valido(monkeypatch):

&nbsp;   monkeypatch.setenv("EMBEDDING\_PROVIDER", "dummy")

&nbsp;   mock\_rows = \[{

&nbsp;       "id": "test-uuid-123",

&nbsp;       "kb\_namespace": "demo",

&nbsp;       "excerpt": "testo di esempio sul bando",

&nbsp;       "source\_path": "/data/inbox/demo/file.txt",

&nbsp;       "distance": 0.3

&nbsp;   }]

&nbsp;   with patch("api.app.db.get\_db\_cursor") as mock\_cur:

&nbsp;       mock\_cur.return\_value.\_\_enter\_\_.return\_value.fetchall.return\_value = mock\_rows

&nbsp;       with patch("api.app.main.embed\_text", return\_value=(\[0.0]\*768, "dummy", 768)):

&nbsp;           resp = client.post("/api/v1/query", json={"query": "bandi", "top\_k": 3})

&nbsp;   assert resp.status\_code == 200, f"Atteso 200, ricevuto {resp.status\_code}"

&nbsp;   data = resp.json()

&nbsp;   assert len(data\["sources"]) == 1

&nbsp;   assert 0.0 <= data\["sources"]\[0]\["score"] <= 1.0

```



\## Casi di test da coprire per ogni nuova feature

\- Happy path: input valido → risposta 200 con struttura corretta

\- Input invalido: query vuota → 422; top\_k fuori range (0 o 21) → 422

\- DB non disponibile: mock che lancia Exception → 500 o 503

\- KB inesistente: sources lista vuota, NON un errore



\## Eseguire i test (comandi PowerShell)

```powershell

\# Tutti i test

docker compose exec api pytest tests/ -v



\# Solo un file

docker compose exec api pytest tests/test\_query.py -v



\# Solo un test specifico

docker compose exec api pytest tests/ -v -k "test\_query\_ritorna"

```

Output atteso se tutto passa: righe verdi con "PASSED", ultima riga "X passed in Y.Ys"

