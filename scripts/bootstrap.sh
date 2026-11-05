#!/usr/bin/env bash
# Prepara o ambiente (Linux/macOS/WSL): Python + Node. Idempotente.
# Não instala software do sistema. Use --force para reinstalar dependências.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FORCE=0
SKIP_FRONTEND=0
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    --skip-frontend) SKIP_FRONTEND=1 ;;
    *) echo "Opção desconhecida: $arg" >&2; exit 2 ;;
  esac
done

MIN_PYTHON="3.10"
MIN_NODE="20.11"
missing=()

version_ge() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]; }
step() { printf '\n==> %s\n' "$1"; }

step "Verificando requisitos"

PYTHON=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    v="$("$candidate" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
    if version_ge "$v" "$MIN_PYTHON"; then PYTHON="$candidate"; echo "Python $v OK"; break; fi
  fi
done
[ -n "$PYTHON" ] || missing+=("Python >= $MIN_PYTHON (Ubuntu: sudo apt install python3 python3-venv python3-pip)")
if [ -n "$PYTHON" ] && ! "$PYTHON" -c 'import venv, ensurepip' >/dev/null 2>&1; then
  missing+=("Módulo venv/ensurepip ausente (Ubuntu: sudo apt install python3-venv)")
fi

if command -v node >/dev/null 2>&1 && version_ge "$(node --version | sed 's/^v//')" "$MIN_NODE"; then
  echo "Node.js $(node --version) OK"
else
  missing+=("Node.js >= $MIN_NODE (https://nodejs.org/ ou nvm)")
fi
if command -v npm >/dev/null 2>&1; then echo "npm $(npm --version) OK"; else missing+=("npm (vem com o Node.js)"); fi

if [ "${#missing[@]}" -gt 0 ]; then
  echo
  echo "Requisitos ausentes:" >&2
  printf ' - %s\n' "${missing[@]}" >&2
  echo "Nada foi instalado. Instale os itens acima e execute o script novamente." >&2
  exit 1
fi

step "Criando diretórios de dados"
mkdir -p data/raw data/processed data/external data/models

step "Configurando .env"
if [ ! -f .env ]; then cp .env.example .env && echo ".env criado a partir de .env.example"; else echo ".env já existe (mantido)"; fi

step "Ambiente virtual Python (.venv)"
if [ ! -x .venv/bin/python ]; then "$PYTHON" -m venv .venv; else echo ".venv já existe"; fi

STAMP=".venv/.requirements.stamp"
HASH="$(cat requirements.txt backend/requirements.txt pipeline/requirements.txt ml/requirements.txt requirements-dev.txt | sha256sum | cut -d' ' -f1)"
if [ "$FORCE" = 1 ] || [ ! -f "$STAMP" ] || [ "$(cat "$STAMP")" != "$HASH" ]; then
  .venv/bin/python -m pip install --upgrade pip --quiet
  .venv/bin/python -m pip install -r requirements.txt
  printf '%s' "$HASH" > "$STAMP"
else
  echo "Dependências Python já instaladas"
fi

if [ "$SKIP_FRONTEND" = 0 ]; then
  step "Dependências do frontend"
  if [ "$FORCE" = 1 ] || [ ! -d frontend/node_modules ]; then
    (cd frontend && npm ci --no-audit --no-fund)
  else
    echo "node_modules já existe (use --force para reinstalar)"
  fi
fi

step "Validando instalação"
PYTHONPATH="$ROOT:$ROOT/backend" .venv/bin/python -c \
  "import fastapi, uvicorn, duckdb, pandas, sklearn; from app.main import app; print('Backend importável: OK')"
if [ "$SKIP_FRONTEND" = 0 ]; then (cd frontend && npx --no-install ng version | grep 'Angular CLI'); fi

echo
echo "Ambiente pronto. Execute: ./scripts/run.sh"
