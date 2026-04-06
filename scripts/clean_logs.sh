#!/usr/bin/env bash
# Clean development logs older than 1 day
# Run this daily via cron or manually
# Usage: ./scripts/clean_logs.sh

set -euo pipefail

LOG_DIR="$(cd "$(dirname "$0")/.." && pwd)/logs/dev"
RETENTION_DAYS=1

if [[ ! -d "$LOG_DIR" ]]; then
    echo "Log directory not found: $LOG_DIR"
    exit 0
fi

echo "Cleaning logs older than ${RETENTION_DAYS} day(s) in: $LOG_DIR"

# Find and delete log files older than RETENTION_DAYS
DELETED=$(find "$LOG_DIR" -name "*.log" -type f -mtime +${RETENTION_DAYS} -delete -print | wc -l)

echo "✓ Deleted $DELETED old log file(s)"

# Keep directory structure
touch "$LOG_DIR/.gitkeep" 2>/dev/null || true

exit 0
