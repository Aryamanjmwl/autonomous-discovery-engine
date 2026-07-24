[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ProjectFile = Join-Path $RepoRoot "pyproject.toml"

if (-not (Test-Path -LiteralPath $ProjectFile -PathType Leaf)) {
    throw "ADE project root could not be resolved from $PSScriptRoot."
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python is required. Install Python 3.11 or newer and make 'python' available."
}

Push-Location $RepoRoot
try {
    & python -c "import ade.studio.api, fastapi, uvicorn"
    if ($LASTEXITCODE -ne 0) {
        throw 'Studio backend dependencies are missing. Run: pip install -e ".[studio]"'
    }
    Write-Host "Starting ADE Studio local backend at http://127.0.0.1:8765"
    Write-Host "Health endpoint: http://127.0.0.1:8765/health"
    & python -m ade.studio.api --host 127.0.0.1 --port 8765
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
