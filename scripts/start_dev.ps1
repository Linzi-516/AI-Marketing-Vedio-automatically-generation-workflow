param(
    [switch]$InstallDeps
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$FrontendDir = Join-Path $Root "frontend"
$NodeDir = Join-Path $Root "tools\node"
$Npm = Join-Path $NodeDir "npm.cmd"

if (-not (Test-Path $Npm)) {
    Write-Host "Missing portable npm: $Npm" -ForegroundColor Red
    Write-Host "Please install Node.js first, or place portable Node under tools/node." -ForegroundColor Yellow
    exit 1
}

$env:PATH = "$NodeDir;$env:PATH"

if ($InstallDeps -or -not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
    Push-Location $FrontendDir
    & $Npm install
    Pop-Location
}

Write-Host ""
Write-Host "Starting backend:  http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Starting frontend: http://127.0.0.1:5173" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop this launcher. If child processes remain, close them from Task Manager." -ForegroundColor Yellow
Write-Host ""

$backend = Start-Job -Name "aigc-backend" -ScriptBlock {
    param($Root)
    Set-Location $Root
    python -m uvicorn api_server:app --host 127.0.0.1 --port 8000
} -ArgumentList $Root

$frontend = Start-Job -Name "aigc-frontend" -ScriptBlock {
    param($FrontendDir, $NodeDir, $Npm)
    Set-Location $FrontendDir
    $env:PATH = "$NodeDir;$env:PATH"
    & $Npm run dev -- --host 127.0.0.1
} -ArgumentList $FrontendDir, $NodeDir, $Npm

try {
    while ($true) {
        Receive-Job -Job $backend, $frontend -Keep
        Start-Sleep -Seconds 2
    }
}
finally {
    Write-Host "Stopping dev jobs..." -ForegroundColor Yellow
    Stop-Job -Job $backend, $frontend -ErrorAction SilentlyContinue
    Remove-Job -Job $backend, $frontend -Force -ErrorAction SilentlyContinue
}
