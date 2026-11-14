# Run HMore identity bootstrap CLI (works when repo path contains spaces).
# Usage (from repo root):
#   .\scripts\bootstrap-identity.ps1 list-roles
#   .\scripts\bootstrap-identity.ps1 grant-super-admin --email you@example.com
#   .\scripts\bootstrap-identity.ps1 show-user --email you@example.com

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$BootstrapArgs
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Cli = Join-Path $Root "apps\api\scripts\bootstrap_identity.py"

if (-not (Test-Path $Python)) {
    Write-Error "Python venv not found. Run scripts\setup-local-windows.ps1 from: $Root"
}
if (-not (Test-Path $Cli)) {
    Write-Error "bootstrap_identity.py missing on this branch."
}

$env:PYTHONPATH = Join-Path $Root "apps\api"
Push-Location (Join-Path $Root "apps\api")
try {
    if ($BootstrapArgs.Count -eq 0) {
        & $Python $Cli --help
    } else {
        & $Python $Cli @BootstrapArgs
    }
    exit $LASTEXITCODE
} finally {
    Pop-Location
}