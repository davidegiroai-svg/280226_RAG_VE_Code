# smoke_test.ps1 - Verifica funzionamento base RAG VE dopo fresh install
# Controlla: API raggiungibile, DB connesso, vector extension, autenticazione.
# Non modifica dati. Read-only.
#
# Uso:
#   cd C:\Users\D.Giro\280226_RAG_VE_Code
#   .\scripts\smoke_test.ps1
#
# Exit code: 0 = tutti i check passati | 1 = almeno un check fallito
#
# Endpoint testati:
#   GET /health                          - API raggiungibile + DB connesso (nessuna auth)
#   GET /health/ready                    - DB + estensione vector presente (nessuna auth)
#   GET /api/v1/kbs                      - Auth valida + DB query funzionante
#   GET /api/v1/graph/traverse           - GraphRAG traversal endpoint (M7)
#   GET /api/v1/graph/entities           - GraphRAG entities endpoint (M7)
#
# Nota: POST /api/v1/query NON incluso - richiede Ollama per embedding.

$BASE_URL  = "http://localhost:8000"
$ENV_FILE  = ".env"
$allPassed = $true

function Show-Result {
    param([bool]$ok, [string]$label, [string]$detail = "")
    if ($ok) {
        Write-Host "  [PASS] $label" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $label" -ForegroundColor Red
        if ($detail) {
            Write-Host "         $detail" -ForegroundColor DarkGray
        }
    }
}

function Invoke-Check {
    param([string]$url, [hashtable]$headers = @{})
    try {
        $resp = Invoke-RestMethod -Uri $url -Method GET -Headers $headers -ErrorAction Stop
        return @{ StatusCode = 200; Body = $resp; Error = $null }
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        if (-not $code) { $code = 0 }
        return @{ StatusCode = $code; Body = $null; Error = $_.Exception.Message }
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  RAG VE - Smoke Test" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Prerequisito: leggi FRONTEND_API_KEY da .env
Write-Host "Leggo la API key da $ENV_FILE..." -ForegroundColor Yellow

if (-not (Test-Path $ENV_FILE)) {
    Write-Host "  [FAIL] File $ENV_FILE non trovato." -ForegroundColor Red
    Write-Host "         Esegui prima: Copy-Item .env.example .env" -ForegroundColor DarkGray
    Write-Host "         Poi: .\scripts\bootstrap_auth.ps1" -ForegroundColor DarkGray
    exit 1
}

$apiKey = $null
foreach ($line in Get-Content $ENV_FILE) {
    if ($line -match "^FRONTEND_API_KEY=(.+)$") {
        $apiKey = $Matches[1].Trim()
        break
    }
}

if (-not $apiKey) {
    Write-Host "  [FAIL] FRONTEND_API_KEY non trovata o vuota in $ENV_FILE." -ForegroundColor Red
    Write-Host "         Esegui: .\scripts\bootstrap_auth.ps1" -ForegroundColor DarkGray
    exit 1
}
Write-Host "  [PASS] API key trovata in .env." -ForegroundColor Green
Write-Host ""

$authHeaders = @{ "X-API-Key" = $apiKey }

# CHECK 1: GET /health
Write-Host "Check 1/5 - /health (API + DB)"
$r = Invoke-Check "$BASE_URL/health"
if ($r.StatusCode -eq 200 -and $r.Body.status -eq "ok") {
    Show-Result $true "/health risponde 200 con status=ok"
} else {
    $detail = if ($r.Error) { $r.Error } else { "status=$($r.StatusCode)" }
    Show-Result $false "/health non risponde correttamente" $detail
    $allPassed = $false
}

# CHECK 2: GET /health/ready
Write-Host ""
Write-Host "Check 2/5 - /health/ready (DB + vector extension)"
$r = Invoke-Check "$BASE_URL/health/ready"
if ($r.StatusCode -eq 200 -and $r.Body.vector -eq "ok") {
    Show-Result $true "/health/ready risponde 200 con vector=ok"
} else {
    $detail = if ($r.Error) { $r.Error } else { "status=$($r.StatusCode)" }
    Show-Result $false "/health/ready non risponde correttamente" $detail
    $allPassed = $false
}

# CHECK 3: GET /api/v1/kbs (autenticato)
Write-Host ""
Write-Host "Check 3/5 - /api/v1/kbs (autenticazione + DB)"
$r = Invoke-Check "$BASE_URL/api/v1/kbs" $authHeaders
if ($r.StatusCode -eq 200 -and $null -ne $r.Body.kbs) {
    $n = $r.Body.kbs.Count
    Show-Result $true "/api/v1/kbs risponde 200 - KB trovate: $n"
} elseif ($r.StatusCode -eq 401) {
    Show-Result $false "Auth fallita: API key non accettata (401)" `
        "Verifica FRONTEND_API_KEY in .env. Riesegui bootstrap_auth.ps1."
    $allPassed = $false
} elseif ($r.StatusCode -eq 403) {
    Show-Result $false "Auth fallita: chiave revocata o scaduta (403)" `
        "Rigenera la chiave con: .\scripts\bootstrap_auth.ps1"
    $allPassed = $false
} else {
    $detail = if ($r.Error) { $r.Error } else { "status=$($r.StatusCode)" }
    Show-Result $false "/api/v1/kbs non risponde correttamente" $detail
    $allPassed = $false
}

# CHECK 4: GET /api/v1/graph/traverse (GraphRAG endpoint health)
Write-Host ""
Write-Host "Check 4/5 - /api/v1/graph/traverse (GraphRAG)"
$r4 = Invoke-Check "$BASE_URL/api/v1/graph/traverse?entity_name=FESR&depth=1" $authHeaders
if ($r4.StatusCode -eq 200 -and $null -ne $r4.Body.related_entities) {
    Show-Result $true "/api/v1/graph/traverse risponde 200"
} else {
    $detail = if ($r4.Error) { $r4.Error } else { "status=$($r4.StatusCode)" }
    Show-Result $false "/api/v1/graph/traverse non risponde correttamente" $detail
    $allPassed = $false
}

# CHECK 5: GET /api/v1/graph/entities con doc_id nullo → 200 lista vuota
Write-Host ""
Write-Host "Check 5/5 - /api/v1/graph/entities (GraphRAG)"
$r5 = Invoke-Check "$BASE_URL/api/v1/graph/entities?doc_id=00000000-0000-0000-0000-000000000000" $authHeaders
if ($r5.StatusCode -eq 200 -and $null -ne $r5.Body.entities) {
    Show-Result $true "/api/v1/graph/entities risponde 200"
} else {
    $detail = if ($r5.Error) { $r5.Error } else { "status=$($r5.StatusCode)" }
    Show-Result $false "/api/v1/graph/entities non risponde correttamente" $detail
    $allPassed = $false
}

# Riepilogo finale
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
if ($allPassed) {
    Write-Host "  RISULTATO: PASS (5/5) - sistema operativo" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Frontend disponibile su: http://localhost:3000" -ForegroundColor White
    Write-Host ""
    exit 0
} else {
    Write-Host "  RISULTATO: FAIL - uno o piu check falliti" -ForegroundColor Red
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Controlla i log con: docker compose logs api" -ForegroundColor White
    Write-Host "  Verifica lo stato con: docker compose ps" -ForegroundColor White
    Write-Host ""
    exit 1
}
