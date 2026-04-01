#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

# Build the React frontend
echo "Installing frontend dependencies…"
cd "$ROOT/frontend"
npm install

echo "Building frontend…"
npm run build

# Start the backend (serves frontend/dist/ as static files)
echo "Starting backend on port ${PORT:-8000}…"
cd "$ROOT/backend"
uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
