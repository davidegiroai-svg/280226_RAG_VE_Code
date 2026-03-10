# bootstrap_auth.ps1 — Prima configurazione autenticazione RAG VE
# Da eseguire UNA VOLTA dopo il primo avvio di DB e API.
# Crea la API key per il frontend e aggiorna il file .env.
#
# Uso:
#   cd C:\Users\D.Giro\280226_RAG_VE_Code
#   .\scripts\bootstrap_auth.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  RAG VE — Bootstrap Autenticazione Frontend" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------------------------
# STEP 1/4 — Verifica prerequisiti
# ---------------------------------------------------------------------------
Write-Host "[1/4] Verifico che i container siano in esecuzione..." -ForegroundColor Yellow

$apiRunning = docker compose ps --status running --services 2>$null | Select-String "^api$"
if (-not $apiRunning) {
    Write-Host ""
    Write-Host "[FAIL] Il container 'api' non e' in esecuzione." -ForegroundColor Red
    Write-Host "       Avvia prima DB e API con:" -ForegroundColor White
    Write-Host "         docker compose up -d db api" -ForegroundColor White
    Write-Host "       Attendi 30 secondi, poi riesegui questo script." -ForegroundColor White
    exit 1
}
Write-Host "       [PASS] Container 'api' in esecuzione." -ForegroundColor Green

# Verifica che .env esista
if (-not (Test-Path ".env")) {
    Write-Host ""
    Write-Host "[FAIL] File .env non trovato." -ForegroundColor Red
    Write-Host "       Copia il template con:" -ForegroundColor White
    Write-Host "         Copy-Item .env.example .env" -ForegroundColor White
    Write-Host "       Poi riesegui questo script." -ForegroundColor White
    exit 1
}
Write-Host "       [PASS] File .env presente." -ForegroundColor Green

# ---------------------------------------------------------------------------
# STEP 2/4 — Genera API key
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "[2/4] Genero la API key per il frontend..." -ForegroundColor Yellow

$output = docker compose exec -T api python -m app.manage_keys create --name "frontend" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[FAIL] Impossibile generare la chiave. Output:" -ForegroundColor Red
    Write-Host $output -ForegroundColor Gray
    Write-Host "       Controlla i log con: docker compose logs api" -ForegroundColor White
    exit 1
}

# Estrae il valore dalla riga "X-API-Key:  <valore>"
$keyLine = $output | Select-String "X-API-Key:\s+(.+)"
if (-not $keyLine) {
    Write-Host ""
    Write-Host "[FAIL] Chiave generata ma non riconosciuta nell'output." -ForegroundColor Red
    Write-Host "       Output ricevuto:" -ForegroundColor Gray
    Write-Host $output -ForegroundColor Gray
    exit 1
}
$apiKey = $keyLine.Matches.Groups[1].Value.Trim()
Write-Host "       [PASS] Chiave generata." -ForegroundColor Green

# ---------------------------------------------------------------------------
# STEP 3/4 — Aggiorna .env
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "[3/4] Aggiorno FRONTEND_API_KEY in .env..." -ForegroundColor Yellow

$envContent = Get-Content ".env" -Raw
if ($envContent -match "FRONTEND_API_KEY=") {
    # Sostituisce la riga esistente
    $envContent = $envContent -replace "FRONTEND_API_KEY=.*", "FRONTEND_API_KEY=$apiKey"
} else {
    # Aggiunge la riga in fondo
    $envContent = $envContent.TrimEnd() + "`nFRONTEND_API_KEY=$apiKey`n"
}
Set-Content ".env" $envContent -NoNewline:$false
Write-Host "       [PASS] .env aggiornato." -ForegroundColor Green

# ---------------------------------------------------------------------------
# STEP 4/4 — Riavvia il frontend
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "[4/4] Riavvio il container frontend..." -ForegroundColor Yellow
docker compose up -d frontend 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "       [WARN] Riavvio frontend non riuscito. Prova manualmente:" -ForegroundColor DarkYellow
    Write-Host "         docker compose up -d frontend" -ForegroundColor White
} else {
    Write-Host "       [PASS] Frontend riavviato." -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# Riepilogo finale
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  CONFIGURAZIONE COMPLETATA" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Chiave creata e salvata in .env" -ForegroundColor White
Write-Host "  Frontend disponibile su: http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "  PROSSIMI PASSI:" -ForegroundColor Yellow
Write-Host "  1. Apri il browser su http://localhost:3000" -ForegroundColor White
Write-Host "  2. Per caricare documenti: usa l'interfaccia Upload del frontend" -ForegroundColor White
Write-Host "  3. Per verificare il sistema: esegui scripts\smoke_test.ps1" -ForegroundColor White
Write-Host ""
Write-Host "  NOTA: Conserva il valore di FRONTEND_API_KEY in .env." -ForegroundColor DarkYellow
Write-Host "        Non rigenerare la chiave senza aggiornare .env." -ForegroundColor DarkYellow
Write-Host ""
