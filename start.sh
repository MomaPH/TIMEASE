#!/bin/bash
cd "$(dirname "$0")"
python run_api.py &
cd frontend && npm run dev &
wait
