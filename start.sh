#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv"
STAMP="$VENV/.backend-deps-installed"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ ! -d "$VENV" ]; then
  echo "Creating Python virtual environment…"
  "$PYTHON_BIN" -m venv "$VENV"
fi

if [ ! -x "$VENV/bin/pip" ]; then
  echo "Virtual environment is missing pip. Delete .venv and rerun."
  exit 1
fi

if [ ! -f "$STAMP" ] || [ "$ROOT/backend/requirements.txt" -nt "$STAMP" ]; then
  echo "Installing backend dependencies…"
  "$VENV/bin/pip" install -r "$ROOT/backend/requirements.txt"
  touch "$STAMP"
fi

if [ ! -f "$ROOT/.env" ] && [ ! -f "$ROOT/env" ]; then
  echo "Creating .env from .env.example…"
  cp "$ROOT/.env.example" "$ROOT/.env"
fi

echo "Installing frontend dependencies…"
cd "$ROOT/frontend"
npm install

echo "Building frontend…"
npm run build

# Start the backend (serves frontend/dist/ as static files)
echo "Starting backend on port ${PORT:-8000}…"
cd "$ROOT/backend"
exec "$VENV/bin/uvicorn" main:app --host 0.0.0.0 --port "${PORT:-8000}"
