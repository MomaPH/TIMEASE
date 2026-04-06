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



## Rules
- All UI text and user-facing messages in French.
- Type hints on every function and method.
- Docstrings in English for code, French for user messages.
- Every new feature gets at least one test.
- Never use print() in library code — use logging module.


## Current status
Phase 0 — Foundation. Building data models and sample data.
Phase 1 — Constraints implementation, export/imports, conflict reporting and analyzer, AI layer.
Phase 2 (Active) — Stripping Greedy logic, Mypyc compliation, Celery async solving, Postgres RLS, and Premium AI UX scaling.

## Phase 2 Rules
- Assume 100% human-in-the-loop manual assignments. No algorithmic teacher routing (Auto mode deprecated).
- Never break Celery worker queues or Next.js SSE streams when updating the solver route.
- All new Python heavy logic loops must be strictly typed to support `mypyc` compilation.
- Do not let the UI ping Anthropic APIs for basic structural mathematical errors.

## Session Continuity
- **Read `CONTEXT.md` first** when resuming work — it contains current state and next steps.
- **Update `CONTEXT.md`** at end of each session with progress, blockers, and next actions.
- **Check `task.md`** for Phase 2 checklist status.
