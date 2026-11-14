# Local HMore setup (Windows). Run from repo root in PowerShell:
#   Set-ExecutionPolicy -Scope Process Bypass; .\scripts\setup-local-windows.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

function Refresh-Path {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
        [System.Environment]::GetEnvironmentVariable("Path", "User")
}

function Test-DockerCli {
    Refresh-Path
    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $docker) { return $false }
    $out = docker ps 2>&1
    return $LASTEXITCODE -eq 0
}

Write-Host "== HMore local setup ==" -ForegroundColor Cyan

if (-not (Test-Path "$Root\.venv\Scripts\python.exe")) {
    Write-Host "Creating Python venv..."
    python -m venv "$Root\.venv"
}

Write-Host "Installing API Python dependencies..."
& "$Root\.venv\Scripts\python.exe" -m pip install -q -r "$Root\apps\api\requirements.txt"

if (-not (Test-Path "$Root\apps\api\.env")) {
    Copy-Item "$Root\apps\api\.env.example" "$Root\apps\api\.env"
    Write-Host "Created apps/api/.env — review DATABASE_URL and AUTH0_*"
}

if (-not (Test-DockerCli)) {
    Write-Host ""
    Write-Host "Docker is not running yet." -ForegroundColor Yellow
    Write-Host "1. Install Docker Desktop (or finish install + restart PC)."
    Write-Host "2. Open Docker Desktop and wait until it says Running."
    Write-Host "3. Re-run this script."
    exit 2
}

Write-Host "Starting PostgreSQL (pgvector)..."
docker compose -f "$Root\infra\docker\docker-compose.yml" up -d postgres

$deadline = (Get-Date).AddMinutes(3)
do {
    $ready = docker compose -f "$Root\infra\docker\docker-compose.yml" ps --format json 2>$null |
        ConvertFrom-Json |
        Where-Object { $_.Service -eq "postgres" -and $_.Health -eq "healthy" }
    if ($ready) { break }
    Start-Sleep -Seconds 3
} while ((Get-Date) -lt $deadline)

Write-Host "Running Alembic migrations..."
Push-Location "$Root\apps\api"
& "$Root\.venv\Scripts\alembic.exe" upgrade head
if (-not $?) { Pop-Location; exit 1 }

Write-Host "Checking database connection..."
& "$Root\.venv\Scripts\python.exe" -c "from app.db.session import check_database_connection, reset_engine_cache; reset_engine_cache(); print('DB OK:', check_database_connection())"
Pop-Location

Write-Host ""
Write-Host "Done. Start API: cd apps\api; ..\..\.venv\Scripts\uvicorn app.main:app --reload --port 8000" -ForegroundColor Green
Write-Host "Bootstrap roles: python scripts\bootstrap_identity.py list-roles" -ForegroundColor Green