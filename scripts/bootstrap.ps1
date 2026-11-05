<#
.SYNOPSIS
  Prepara o ambiente de desenvolvimento no Windows (Python + Node). Idempotente.
.DESCRIPTION
  Verifica Python/Node/npm, cria .venv, instala dependências Python e do frontend,
  cria diretórios de dados e .env. Não instala software do sistema.
  Docker não é exigido; se quiser usá-lo, rode-o no Ubuntu/WSL (-CheckDocker apenas informa).
.PARAMETER Force
  Reinstala as dependências mesmo que já existam.
.PARAMETER SkipFrontend
  Não instala as dependências do frontend.
.PARAMETER CheckDocker
  Informa se o Docker responde dentro do WSL.
#>
[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$SkipFrontend,
    [switch]$CheckDocker
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$MinPython = [version]'3.10'
$MinNode = [version]'20.11'
$Missing = New-Object System.Collections.Generic.List[string]

function Get-ToolVersion([string]$Command, [string[]]$Arguments, [string]$Pattern) {
    if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) { return $null }
    $output = & $Command @Arguments 2>&1 | Out-String
    if ($output -match $Pattern) { return [version]$Matches[1] }
    return $null
}

function Write-Step([string]$Message) { Write-Host "==> $Message" -ForegroundColor Cyan }

Write-Step 'Verificando requisitos'

$python = $null
foreach ($candidate in @('python', 'py')) {
    $arguments = if ($candidate -eq 'py') { @('-3', '--version') } else { @('--version') }
    $version = Get-ToolVersion $candidate $arguments 'Python (\d+\.\d+)'
    if ($version -and $version -ge $MinPython) { $python = @{ Command = $candidate; Version = $version }; break }
}
if ($python) { Write-Host "Python $($python.Version) OK" }
else { $Missing.Add("Python >= $MinPython não encontrado. Instale em https://www.python.org/downloads/ (marque 'Add to PATH').") }

$node = Get-ToolVersion 'node' @('--version') 'v(\d+\.\d+)'
if ($node -and $node -ge $MinNode) { Write-Host "Node.js $node OK" }
else { $Missing.Add("Node.js >= $MinNode não encontrado. Instale a versão LTS em https://nodejs.org/.") }

$npm = Get-ToolVersion 'npm' @('--version') '(\d+\.\d+)'
if ($npm) { Write-Host "npm $npm OK" }
else { $Missing.Add('npm não encontrado (vem com o Node.js).') }

if ($Missing.Count -gt 0) {
    Write-Host ''
    Write-Host 'Requisitos ausentes:' -ForegroundColor Red
    $Missing | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
    Write-Host 'Nada foi instalado. Instale os itens acima e execute o script novamente.'
    exit 1
}

Write-Step 'Criando diretórios de dados'
foreach ($dir in 'data/raw', 'data/processed', 'data/external', 'data/models') {
    New-Item -ItemType Directory -Force -Path (Join-Path $Root $dir) | Out-Null
}

Write-Step 'Configurando .env'
if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    Write-Host '.env criado a partir de .env.example'
}
else { Write-Host '.env já existe (mantido)' }

Write-Step 'Ambiente virtual Python (.venv)'
$venvPython = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    if ($python.Command -eq 'py') { & py -3 -m venv .venv } else { & $python.Command -m venv .venv }
}
else { Write-Host '.venv já existe' }

$marker = Join-Path $Root '.venv\.requirements.stamp'
$hash = (Get-FileHash -Algorithm SHA256 -Path 'requirements.txt', 'backend/requirements.txt', 'pipeline/requirements.txt', 'ml/requirements.txt', 'requirements-dev.txt' |
    ForEach-Object Hash) -join ''
if ($Force -or -not (Test-Path $marker) -or (Get-Content $marker -Raw) -ne $hash) {
    & $venvPython -m pip install --upgrade pip --quiet
    & $venvPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar as dependências Python.' }
    Set-Content -Path $marker -Value $hash -NoNewline
}
else { Write-Host 'Dependências Python já instaladas' }

if (-not $SkipFrontend) {
    Write-Step 'Dependências do frontend'
    Push-Location 'frontend'
    try {
        if ($Force -or -not (Test-Path 'node_modules')) {
            npm ci --no-audit --no-fund
            if ($LASTEXITCODE -ne 0) { throw 'Falha no npm ci.' }
        }
        else { Write-Host 'node_modules já existe (use -Force para reinstalar)' }
    }
    finally { Pop-Location }
}

Write-Step 'Validando instalação'
$env:PYTHONPATH = "$Root;$Root\backend"
& $venvPython -c "import fastapi, uvicorn, duckdb, pandas, sklearn; from app.main import app; print('Backend importável: OK')"
if ($LASTEXITCODE -ne 0) { throw 'Validação do backend falhou.' }
if (-not $SkipFrontend) {
    Push-Location 'frontend'
    try {
        npx --no-install ng version | Select-String 'Angular CLI'
        if ($LASTEXITCODE -ne 0) { throw 'Angular CLI não encontrado em frontend/node_modules.' }
    }
    finally { Pop-Location }
}

if ($CheckDocker) {
    Write-Step 'Docker (opcional, via WSL)'
    if (Get-Command wsl -ErrorAction SilentlyContinue) {
        wsl -e docker --version
        if ($LASTEXITCODE -ne 0) { Write-Host 'Docker não respondeu no WSL (opcional).' -ForegroundColor Yellow }
    }
    else { Write-Host 'WSL não encontrado (opcional).' -ForegroundColor Yellow }
}

Write-Host ''
Write-Host 'Ambiente pronto. Execute: .\scripts\run.ps1' -ForegroundColor Green
