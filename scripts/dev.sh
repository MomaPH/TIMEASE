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

find_free_port() {
  local port="$1"
  while lsof -iTCP:"$port" -sTCP:LISTEN -Pn >/dev/null 2>&1; do
    port=$((port + 1))
  done
  printf '%s\n' "$port"
}

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

# Reset logs on every run for easier diagnostics.
find "$LOG_DIR" -maxdepth 1 -type f -name "*.log" -delete

# Clean logs older than 1 day
if [[ -f "$ROOT_DIR/scripts/clean_logs.sh" ]]; then
  "$ROOT_DIR/scripts/clean_logs.sh" >/dev/null 2>&1 || true
fi

BACKEND_OUT="$LOG_DIR/backend-${RUN_ID}.out.log"
BACKEND_ERR="$LOG_DIR/backend-${RUN_ID}.err.log"
FRONTEND_OUT="$LOG_DIR/frontend-${RUN_ID}.out.log"
FRONTEND_ERR="$LOG_DIR/frontend-${RUN_ID}.err.log"

BACKEND_PORT="${BACKEND_PORT:-$(find_free_port 8000)}"
FRONTEND_PORT="${FRONTEND_PORT:-$(find_free_port 3000)}"
BACKEND_INTERNAL_URL="${BACKEND_INTERNAL_URL:-http://127.0.0.1:${BACKEND_PORT}}"

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
  echo "Démarrage backend  → http://localhost:${BACKEND_PORT}"
  (
    cd "$ROOT_DIR"
    BACKEND_PORT="$BACKEND_PORT" FRONTEND_PORT="$FRONTEND_PORT" uv run uvicorn timease.api.main:app --port "$BACKEND_PORT"
  ) >"$BACKEND_OUT" 2>"$BACKEND_ERR" &
  BACKEND_PID="$!"

  if [[ ! -x "$FRONTEND_DIR/node_modules/.bin/next" ]]; then
    echo "Installation des dépendances frontend..."
    (
      cd "$FRONTEND_DIR"
      npm install
    ) >"$FRONTEND_OUT" 2>"$FRONTEND_ERR"
  fi

  echo "Build frontend..."
  (
    cd "$FRONTEND_DIR"
    npm run build
  ) >"$FRONTEND_OUT" 2>"$FRONTEND_ERR"

  echo "Démarrage frontend → http://localhost:${FRONTEND_PORT}"
  (
    cd "$FRONTEND_DIR"
    PORT="$FRONTEND_PORT" BACKEND_INTERNAL_URL="$BACKEND_INTERNAL_URL" npm run start
  ) >>"$FRONTEND_OUT" 2>>"$FRONTEND_ERR" &
  FRONTEND_PID="$!"
else
  echo "Mode: watch"
  echo "Démarrage backend  → http://localhost:${BACKEND_PORT}"
  (
    cd "$ROOT_DIR"
    BACKEND_PORT="$BACKEND_PORT" FRONTEND_PORT="$FRONTEND_PORT" uv run uvicorn timease.api.main:app --reload --port "$BACKEND_PORT"
  ) >"$BACKEND_OUT" 2>"$BACKEND_ERR" &
  BACKEND_PID="$!"

  if [[ ! -x "$FRONTEND_DIR/node_modules/.bin/next" ]]; then
    echo "Installation des dépendances frontend..."
    (
      cd "$FRONTEND_DIR"
      npm install
    ) >"$FRONTEND_OUT" 2>"$FRONTEND_ERR"
  fi

  echo "Démarrage frontend → http://localhost:${FRONTEND_PORT}"
  (
    cd "$FRONTEND_DIR"
    PORT="$FRONTEND_PORT" BACKEND_INTERNAL_URL="$BACKEND_INTERNAL_URL" npm run dev
  ) >"$FRONTEND_OUT" 2>"$FRONTEND_ERR" &
  FRONTEND_PID="$!"
fi

echo "Logs backend : $BACKEND_OUT / $BACKEND_ERR"
echo "Logs frontend: $FRONTEND_OUT / $FRONTEND_ERR"
echo "Port backend  : $BACKEND_PORT"
echo "Port frontend : $FRONTEND_PORT"
echo "Astuce: tail -f \"$BACKEND_ERR\" \"$FRONTEND_ERR\""

wait
