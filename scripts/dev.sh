#!/usr/bin/env bash
# Start backend (FastAPI) and frontend (Next.js) in parallel.
# Usage:
#   ./scripts/dev.sh          # watch mode (default)
#   ./scripts/dev.sh --once   # one-time mode (no watchers)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
LOG_DIR="$ROOT_DIR/logs/dev"
RUN_ID="$(date +%Y%m%d-%H%M%S)"
MODE="watch"

for arg in "$@"; do
  case "$arg" in
    --once)
      MODE="once"
      ;;
    --watch)
      MODE="watch"
      ;;
    -h|--help)
      echo "Usage: ./scripts/dev.sh [--once|--watch]"
      exit 0
      ;;
    *)
      echo "Option inconnue: $arg"
      echo "Usage: ./scripts/dev.sh [--once|--watch]"
      exit 2
      ;;
  esac
done

mkdir -p "$LOG_DIR"

# Clean logs older than 1 day
if [[ -f "$ROOT_DIR/scripts/clean_logs.sh" ]]; then
  "$ROOT_DIR/scripts/clean_logs.sh" >/dev/null 2>&1 || true
fi

BACKEND_OUT="$LOG_DIR/backend-${RUN_ID}.out.log"
BACKEND_ERR="$LOG_DIR/backend-${RUN_ID}.err.log"
FRONTEND_OUT="$LOG_DIR/frontend-${RUN_ID}.out.log"
FRONTEND_ERR="$LOG_DIR/frontend-${RUN_ID}.err.log"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [[ -n "${FRONTEND_PID:-}" ]]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if [[ "$MODE" == "once" ]]; then
  echo "Mode: one-shot (sans watchers)"
  echo "Démarrage backend  → http://localhost:8000"
  (
    cd "$ROOT_DIR"
    uv run uvicorn timease.api.main:app --port 8000
  ) >"$BACKEND_OUT" 2>"$BACKEND_ERR" &
  BACKEND_PID="$!"

  echo "Build frontend..."
  (
    cd "$FRONTEND_DIR"
    npm run build
  ) >"$FRONTEND_OUT" 2>"$FRONTEND_ERR"

  echo "Démarrage frontend → http://localhost:3000"
  (
    cd "$FRONTEND_DIR"
    npm run start
  ) >>"$FRONTEND_OUT" 2>>"$FRONTEND_ERR" &
  FRONTEND_PID="$!"
else
  echo "Mode: watch"
  echo "Démarrage backend  → http://localhost:8000"
  (
    cd "$ROOT_DIR"
    uv run uvicorn timease.api.main:app --reload --port 8000
  ) >"$BACKEND_OUT" 2>"$BACKEND_ERR" &
  BACKEND_PID="$!"

  echo "Démarrage frontend → http://localhost:3000"
  (
    cd "$FRONTEND_DIR"
    npm run dev
  ) >"$FRONTEND_OUT" 2>"$FRONTEND_ERR" &
  FRONTEND_PID="$!"
fi

echo "Logs backend : $BACKEND_OUT / $BACKEND_ERR"
echo "Logs frontend: $FRONTEND_OUT / $FRONTEND_ERR"
echo "Astuce: tail -f \"$BACKEND_ERR\" \"$FRONTEND_ERR\""

wait
