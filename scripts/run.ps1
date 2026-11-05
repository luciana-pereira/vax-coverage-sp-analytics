<#
.SYNOPSIS
  Inicia o backend (FastAPI) e/ou frontend (Angular) em janelas separadas.

.PARAMETER Backend
  Inicia apenas o backend.

.PARAMETER Frontend
  Inicia apenas o frontend.
#>

[CmdletBinding()]
param(
    [switch]$Backend,
    [switch]$Frontend
)

$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $Root '.venv\Scripts\python.exe'
$frontendPath = Join-Path $Root 'frontend'

if (-not (Test-Path $venvPython)) {
    Write-Host 'Ambiente não preparado. Execute primeiro: .\scripts\bootstrap.ps1' -ForegroundColor Red
    exit 1
}

if (-not (Test-Path (Join-Path $frontendPath 'node_modules'))) {
    Write-Host 'Dependências do frontend ausentes. Execute primeiro: .\scripts\bootstrap.ps1' -ForegroundColor Red
    exit 1
}

function Get-EnvValue {
    param(
        [string]$Name,
        [string]$Default
    )

    $envFile = Join-Path $Root '.env'

    if (Test-Path $envFile) {
        $line = Get-Content $envFile |
            Where-Object { $_ -match "^\s*$Name\s*=" } |
            Select-Object -First 1

        if ($line) {
            return ($line -split '=', 2)[1].Trim()
        }
    }

    return $Default
}

# Sem parâmetro: inicia os dois.
$startBackend = (-not $Backend -and -not $Frontend) -or $Backend
$startFrontend = (-not $Backend -and -not $Frontend) -or $Frontend

if ($startBackend) {

    $hostName = Get-EnvValue 'API_HOST' '127.0.0.1'
    $port = Get-EnvValue 'API_PORT' '8000'

    $backendCommand = @"
`$env:PYTHONPATH='$Root;$Root\backend'
Set-Location '$Root'
& '$venvPython' -m uvicorn app.main:app --app-dir backend --reload --host $hostName --port $port
"@

    Start-Process `
        -FilePath 'powershell.exe' `
        -WorkingDirectory $Root `
        -ArgumentList @(
            '-NoExit',
            '-ExecutionPolicy',
            'Bypass',
            '-Command',
            $backendCommand
        )

    Write-Host "Backend iniciado: http://${hostName}:$port" -ForegroundColor Green
    Write-Host "Swagger: http://${hostName}:$port/docs" -ForegroundColor Green
}

if ($startFrontend) {

    $frontendCommand = @"
Set-Location '$frontendPath'
npm start
"@

    Start-Process `
        -FilePath 'powershell.exe' `
        -WorkingDirectory $frontendPath `
        -ArgumentList @(
            '-NoExit',
            '-ExecutionPolicy',
            'Bypass',
            '-Command',
            $frontendCommand
        )

    Write-Host 'Frontend iniciado: http://localhost:4200' -ForegroundColor Green
}

Write-Host ''
Write-Host 'Serviços iniciados em janelas separadas.' -ForegroundColor Cyan