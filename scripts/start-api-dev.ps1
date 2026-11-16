# Start FastAPI with apps/api/.env (clears stale Auth0 placeholder overrides).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Api = Join-Path $Root "apps\api"
$EnvFile = Join-Path $Api ".env"

if (-not (Test-Path $EnvFile)) {
    Write-Host "Missing apps/api/.env — copy from .env.example and set DATABASE_URL + AUTH0_* (match apps/web/.env.local)." -ForegroundColor Red
    exit 1
}

foreach ($name in @("AUTH0_DOMAIN", "AUTH0_ISSUER", "AUTH0_AUDIENCE", "DATABASE_URL")) {
    if (Test-Path "Env:$name") {
        Remove-Item "Env:$name" -ErrorAction SilentlyContinue
    }
}

$Python = Join-Path $Root ".venv\Scripts\python.exe"
Push-Location $Api
try {
    Write-Host "Starting HMore API on http://127.0.0.1:8000 (LAN: http://192.168.x.x:8000)" -ForegroundColor Cyan
    Write-Host "Use --host 0.0.0.0 so phones on Wi-Fi can reach the API." -ForegroundColor DarkGray
    & $Python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
} finally {
    Pop-Location
}