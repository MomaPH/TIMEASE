# TIMEASE — Claude Code Reference

## Stack

- **Python 3.12** + FastAPI (`timease/api/`)
- **Next.js 14** + TypeScript (`frontend/`)
- **Google OR-Tools CP-SAT** (`timease/engine/`)
- **OpenAI GPT-4o** (`timease/api/ai_chat.py`)
- **openpyxl** / **reportlab** / **python-docx** for exports

**Not in the stack**: Reflex, Anthropic, Celery, Mypyc, Postgres, SQLAlchemy, SQLite.

## Run Commands

```bash
./start.sh              # Both services
uv run python run_api.py  # Backend only (:8000)
cd frontend && npm run dev  # Frontend only (:3000)
uv run pytest           # Run tests
cd frontend && npm run build  # Build frontend
```

## Key Files

| Purpose | Path |
|---------|------|
| FastAPI routes | `timease/api/main.py` |
| AI chat logic | `timease/api/ai_chat.py` |
| Solver | `timease/engine/solver.py` |
| Data models | `timease/engine/models.py` |
| Constraints | `timease/engine/constraints.py` |
| Excel import | `timease/io/excel_import.py` |
| Sample data | `timease/data/sample_school.json` |
| Frontend app | `frontend/app/` |
| Step wizard | `frontend/components/StepPanel.tsx` |
| Types | `frontend/lib/types.ts` |

## Conventions

- **UI text**: French
- **Code identifiers/docstrings/comments**: English
- **Type hints**: Required on every function
- **Logging**: Use `logging.getLogger(__name__)`, no `print()`
- **Errors**: French messages, reference field name
- **No silent fallbacks**: Wrong input raises with clear message

## The Unit of Truth

The **class** is the root aggregate. Curriculum, assignments, and hours are per-class. "Level" is display grouping only. Subjects are auto-derived from curriculum/assignments.

## Adding Dependencies

No new dependencies without justification in this file.

## Related Docs

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — system design and data flow
- [`AI_CONTRACT.md`](AI_CONTRACT.md) — AI layer specification
