#!/usr/bin/env bash
# Inicia backend (FastAPI) e frontend (Angular). Ctrl+C encerra ambos.
# Uso: ./scripts/run.sh [--backend | --frontend]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="${1:-all}"

if [ ! -x .venv/bin/python ]; then
  echo "Ambiente não preparado. Execute primeiro: ./scripts/bootstrap.sh" >&2
  exit 1
fi

env_value() {
  local name="$1" default="$2" line
  if [ -f .env ]; then
    line="$(grep -E "^[[:space:]]*${name}[[:space:]]*=" .env | head -n1 || true)"
    if [ -n "$line" ]; then printf '%s' "${line#*=}" | tr -d '[:space:]'; return; fi
  fi
  printf '%s' "$default"
}

pids=()
cleanup() { for pid in "${pids[@]:-}"; do kill "$pid" 2>/dev/null || true; done; }
trap cleanup EXIT INT TERM

if [ "$MODE" = all ] || [ "$MODE" = --backend ]; then
  HOST="$(env_value API_HOST 127.0.0.1)"
  PORT="$(env_value API_PORT 8000)"
  PYTHONPATH="$ROOT:$ROOT/backend" .venv/bin/python -m uvicorn app.main:app \
    --app-dir backend --reload --host "$HOST" --port "$PORT" &
  pids+=("$!")
  echo "Backend: http://$HOST:$PORT (Swagger em /docs)"
fi

if [ "$MODE" = all ] || [ "$MODE" = --frontend ]; then
  if [ ! -d frontend/node_modules ]; then
    echo "Dependências do frontend ausentes. Execute ./scripts/bootstrap.sh" >&2
    exit 1
  fi
  echo "Frontend: http://localhost:4200"
  (cd frontend && npm start) &
  pids+=("$!")
fi

wait
