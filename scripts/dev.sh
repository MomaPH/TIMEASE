#!/usr/bin/env bash
# Start backend (FastAPI) and frontend (Next.js) in parallel.
# Usage: ./scripts/dev.sh
# Stop:  Ctrl-C kills both.

set -e
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

cleanup() { kill 0 2>/dev/null; }
trap cleanup EXIT

echo "Starting backend  → http://localhost:8000"
uv run uvicorn timease.api.main:app --reload --port 8000 &

echo "Starting frontend → http://localhost:3000"
cd "$ROOT/frontend" && npm run dev &

wait
