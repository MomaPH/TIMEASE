# TIMEASE — School Timetable Generator

## Project Overview
TIMEASE generates school timetables using Google OR-Tools CP-SAT solver.
Target: private schools in French-speaking Africa (SaaS).
Solo developer using Claude Code. This is my first app project.

## Tech Stack
- Python 3.12+ (only language in the project)
- Google OR-Tools CP-SAT (constraint solver — the C++ engine called from Python)
- Reflex (web framework — pure Python, compiles to React+FastAPI)
- SQLite (dev) → PostgreSQL (prod) via SQLAlchemy
- openpyxl (Excel), reportlab (PDF), python-docx (Word) for exports
- Anthropic Claude API (conversational AI setup feature)
- pytest for testing

## Architecture (CRITICAL — respect these boundaries)
- timease/engine/ — Solver engine. ZERO dependency on app/ or io/. Must be testable standalone.
- timease/io/ — File import/export. Depends on engine/ only.
- timease/app/ — Reflex web UI. Depends on engine/ and io/.
- tests/ — pytest. Run: uv run pytest
- scripts/ — CLI utilities.

## Rules
- All UI text and user-facing messages in French.
- Type hints on every function and method.
- Docstrings in English for code, French for user messages.
- Every new feature gets at least one test.
- Never use print() in library code — use logging module.
- timease/engine/ must NEVER import from timease/app/.
- Use dataclasses or Pydantic for data models.
- When creating Reflex components, keep them in single files.

## Commands
- Install deps: uv sync
- Run tests: uv run pytest
- Run app: cd timease/app && reflex run
- Run CLI solver: uv run python scripts/solve_from_json.py timease/data/sample_school.json

## Current status
Phase 0 — Foundation. Building data models and sample data.
