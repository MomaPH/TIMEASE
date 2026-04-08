# TIMEASE

TIMEASE generates school timetables for private schools in French-speaking Africa. The school describes *what* it needs; the solver decides *how*. Built with Google OR-Tools CP-SAT for constraint satisfaction, an ergonomic-first frontend, and an AI-assisted conversational setup layer powered by OpenAI GPT-4o.

## Stack

- **Python 3.12** + FastAPI (`timease/api/`)
- **Next.js 14** + TypeScript (`frontend/`)
- **Google OR-Tools CP-SAT** (`timease/engine/`)
- **OpenAI GPT-4o** (`timease/api/ai_chat.py`)
- **openpyxl** / **reportlab** / **python-docx** for Excel/PDF/Word exports

## Prerequisites

- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv) package manager
- Node.js 20+
- `OPENAI_API_KEY` in `.env`

## Install

```bash
uv sync
cd frontend && npm install
```

## Run

```bash
./start.sh
```

- Backend: http://localhost:8000
- Frontend: http://localhost:3000

## Test

```bash
uv run pytest
cd frontend && npm run build
```

## Project Layout

```
timease/
├── api/          # FastAPI routes and AI chat
├── engine/       # CP-SAT solver, models, constraints
├── io/           # Excel/PDF/Word import/export
└── data/         # Sample data and templates
frontend/         # Next.js 14 TypeScript app
scripts/          # CLI utilities
tests/            # pytest suite
```

## Documentation

- [`CLAUDE.md`](CLAUDE.md) — conventions and key file map
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — system design and data flow
- [`AI_CONTRACT.md`](AI_CONTRACT.md) — AI layer specification
