# Resume Checklist — RAG VE PoC

> Se riavvio domani, ecco cosa faccio subito per orientarmi e partire.

## 1. Eseguire comandi di verifica

```powershell
# 1.1 Posizionarsi nella root del progetto
cd C:\Users\D.Giro\280226_RAG_VE_Code

# 1.2 Controllare presenza file critici
ls docker-compose.yml, README.md, scripts\db_init.sql

# 1.3 Guardare audit summary
Get-Content _cc_status\audit\latest\audit_summary.json | ConvertFrom-Json | Format-List

# 1.4 Visualizzare checkpoint status
Get-Content _cc_status\checkpoint_status.md

# 1.5 Controllare lo stato Git
git status --short
git log --oneline -1

# 1.5 Elencare struttura repo veloce
(Get-ChildItem -Recurse -Depth 2).FullName
```

(max 5 comandi per mantenere checklist snella)

## 2. Dove guardare per capire cosa è già stato fatto

- `docs/00_repo_audit.md`: audit completo con lista file, gap e suggerimenti.
- `_cc_status/checkpoint_status.md`: indica lo stato dell’ultimo task completato.
- `_cc_status/audit/latest/*` (soprattutto `repo_tree.txt` e `git_status.txt`).
- Cartella `scripts/` per eventuale script utility (`repo_audit.py`).

## 3. Primo task consigliato (CC-03)

**Task successivo:** aggiungere il file `docker-compose.yml` di base con un servizio Postgres/pgvector e un backend placeholder.  
Con Git inizializzato, ogni cambiamento sarà tracciato.

## 4. Nota operativa

Dopo git init, aggiornare `docs/03_project_status_snapshot.md` e `docs/04_resume_checklist.md` con eventuali nuove evidenze e continuare a usare lo script di audit per generare checkpoint.
