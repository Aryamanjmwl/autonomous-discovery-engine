[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$FrontendRoot = Join-Path $RepoRoot "apps\studio\frontend"
$PackageFile = Join-Path $FrontendRoot "package.json"
$NodeModules = Join-Path $FrontendRoot "node_modules"

if (-not (Test-Path -LiteralPath $PackageFile -PathType Leaf)) {
    throw "ADE Studio frontend could not be resolved from $PSScriptRoot."
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Node.js is required. Install Node.js and make 'node' available."
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm is required. Install npm and make it available."
}
if (-not (Test-Path -LiteralPath $NodeModules -PathType Container)) {
    throw "Frontend dependencies are missing. Run 'npm install' in apps/studio/frontend."
}

Push-Location $FrontendRoot
try {
    Write-Host "Starting ADE Studio local frontend at http://localhost:3000"
    & npm run dev
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
