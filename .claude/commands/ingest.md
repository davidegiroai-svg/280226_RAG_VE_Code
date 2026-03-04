\# /ingest — Guida per indicizzare documenti



\## Come si usa

L'utente scrive: /ingest

Oppure: /ingest <nome-kb>



\## Cosa fare



1\. Se il nome KB non è stato specificato, chiedi:

&nbsp;  "Come vuoi chiamare questa knowledge base?

&nbsp;  Esempi: bandi, programmi, progetti, delibere"



2\. Spiega in italiano semplice:

&nbsp;  "I tuoi documenti devono stare nella cartella:

&nbsp;  C:\\Users\\D.Giro\\280226\_RAG\_VE\_Code\\data\\inbox\\<nome-kb>\\

&nbsp;  Prima di procedere, assicurati di aver copiato i file lì."



3\. Fornisci i comandi nell'ordine esatto:

```powershell

\# Passo 1: crea la cartella se non esiste

New-Item -ItemType Directory -Force -Path "C:\\Users\\D.Giro\\280226\_RAG\_VE\_Code\\data\\inbox\\<nome-kb>"



\# Passo 2: copia i tuoi documenti nella cartella

\# (modifica il percorso con quello dei tuoi file)

Copy-Item "C:\\percorso\\tuoi\\documenti\\\*" -Destination "C:\\Users\\D.Giro\\280226\_RAG\_VE\_Code\\data\\inbox\\<nome-kb>\\" -Recurse



\# Passo 3: avvia l'indicizzazione

docker compose --profile manual run --rm worker --kb <nome-kb> --path /data/inbox/<nome-kb>

```



4\. Spiega l'output atteso:

&nbsp;  Se funziona vedrai:

&nbsp;  "OK ingest completed"

&nbsp;  seguito da un riepilogo tipo:

&nbsp;  {

&nbsp;    "kb": "<nome-kb>",

&nbsp;    "files\_found": 5,

&nbsp;    "documents\_new": 5,

&nbsp;    "documents\_skipped\_existing": 0,

&nbsp;    "chunks\_inserted": 47

&nbsp;  }



&nbsp;  documents\_skipped\_existing > 0 è normale:

&nbsp;  significa che quei file erano già stati indicizzati in precedenza.



5\. Dopo l'ingest, suggerisci un test:

```powershell

Invoke-RestMethod `

&nbsp; -Uri 'http://localhost:8000/api/v1/query' `

&nbsp; -Method POST `

&nbsp; -ContentType 'application/json' `

&nbsp; -Body '{"query":"<scrivi qui una parola chiave dei tuoi documenti>","top\_k":3,"kb":"<nome-kb>"}'

```



6\. Se l'utente vede "files\_found: 0", spiega:

&nbsp;  "Nessun file trovato. Verifica che:

&nbsp;  - I file siano in data\\inbox\\<nome-kb>\\ (non in sottocartelle diverse)

&nbsp;  - I file abbiano estensione .txt .md .csv o .json

&nbsp;  - Il nome del percorso non abbia spazi o caratteri speciali"

