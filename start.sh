#!/bin/bash
cd "$(dirname "$0")"
uv run python run_api.py &
cd frontend && npm run dev &
wait
