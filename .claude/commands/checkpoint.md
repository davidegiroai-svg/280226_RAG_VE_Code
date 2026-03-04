\# /checkpoint — Aggiorna il log dei task completati



\## Come si usa

L'utente scrive: /checkpoint <nome del task completato>

Esempio: /checkpoint M2-PDF-ingest



\## Cosa fare



1\. Leggi il contenuto attuale di \_cc\_status/checkpoint\_status.md



2\. Aggiungi in fondo al file questo blocco (compilato con i dati reali della sessione):



---



\## TASK <NOME\_TASK> — <descrizione breve in italiano>

\*\*Status:\*\* DONE

\*\*Timestamp:\*\* <data e ora corrente>



\*\*File modificati in questa sessione:\*\*

\- <lista dei file toccati con una riga di descrizione>



\*\*Cosa è stato implementato:\*\*

<2-3 righe in italiano che spiegano cosa fa il codice aggiunto>



\*\*Comando di verifica:\*\*

```powershell

<comando PowerShell per testare che il task funzioni>

```



\*\*Output atteso:\*\*

<cosa deve apparire nel terminale se tutto funziona>



---



3\. Scrivi il file aggiornato



4\. Mostra all'utente solo il blocco appena aggiunto



5\. Ricorda all'utente di salvare con git:

```powershell

cd C:\\Users\\D.Giro\\280226\_RAG\_VE\_Code

git add -A

git commit -m "<nome\_task>: <descrizione breve>"

git push

```

Spiegazione: git add aggiunge tutti i file modificati,

git commit li salva con un messaggio descrittivo,

git push li carica su GitHub come backup.

