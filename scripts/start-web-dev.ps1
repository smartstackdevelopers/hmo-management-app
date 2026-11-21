# Start Next.js with Auth0 from apps/web/.env.local (clears stale process overrides).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Web = Join-Path $Root "apps\web"

foreach ($name in @("AUTH0_DOMAIN", "AUTH0_ISSUER", "AUTH0_AUDIENCE", "AUTH0_CLIENT_ID", "AUTH0_CLIENT_SECRET", "AUTH0_SECRET")) {
    if (Test-Path "Env:$name") {
        Remove-Item "Env:$name" -ErrorAction SilentlyContinue
    }
}

Push-Location $Web
try {
    Write-Host "Starting HMore web on http://localhost:3000 (Auth0 from .env.local)" -ForegroundColor Cyan
    npm run dev
} finally {
    Pop-Location
}