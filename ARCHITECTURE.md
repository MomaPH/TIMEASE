# TIMEASE — Architecture

## Request Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Browser │───▶│ Next.js  │───▶│ FastAPI  │───▶│  Engine  │
│          │◀───│  :3000   │◀───│  :8000   │◀───│ (OR-Tools)│
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

- **Browser**: User interacts with React components
- **Next.js**: SSR, client-side state, API proxy to backend
- **FastAPI**: REST endpoints, AI chat SSE, session management
- **Engine**: CP-SAT solver, constraint application, timetable generation

## Module Responsibilities

### `timease/engine/`

Core solver logic. Contains data models (`models.py`), constraint handlers (`constraints.py`), and the CP-SAT solver wrapper (`solver.py`). Pure Python with OR-Tools, no I/O or network dependencies.

### `timease/io/`

Import/export handlers for Excel (`excel_import.py`, `excel_export.py`), PDF (`pdf_export.py`), and Word (`word_export.py`). Transforms between file formats and engine data structures.

### `timease/api/`

FastAPI application. `main.py` handles REST endpoints and session management. `ai_chat.py` implements the OpenAI-powered conversational setup with tool calling and SSE streaming.

### `frontend/`

Next.js 14 application. Multi-step wizard (`StepPanel.tsx`), chat interface, timetable visualization (`TimetableGrid.tsx`), and results export. TypeScript with Tailwind CSS.

## Data Lifecycle

```
Raw Input (JSON/Excel)
       │
       ▼
SchoolData.validate()  ← Structured errors with step_to_fix
       │
       ▼
    Solver  ← Constraint application, CP-SAT optimization
       │
       ▼
  Timetable  ← Scheduled sessions with rooms
       │
       ▼
  Exporters  ← PDF/Excel/Word output
```

## Session Strategy

In-memory dict keyed by `sid` (session ID). Sessions are ephemeral; no persistence layer. This is a known limitation, not a bug. Future: Redis or database-backed sessions.

```python
_sessions: dict[str, SchoolData] = {}
```

## Key Data Structures

### SchoolData

Root aggregate containing all school configuration:
- `school_info`: Name, year, location
- `timeslot_config`: Days, sessions, breaks
- `classes`: List of SchoolClass
- `teachers`: List of Teacher
- `rooms`: List of Room (optional)
- `curriculum`: List of CurriculumEntry (per-class)
- `teacher_assignments`: Manual teacher↔(class,subject) mappings
- `constraints`: Hard and soft constraints

### Timetable

Solver output containing scheduled sessions:
- `sessions`: List of ScheduledSession (class, subject, teacher, room, day, start, end)
- `warnings`: Soft constraint violations or substitutions

## Solver — Curriculum Splitting

The solver determines session splits from `CurriculumEntry.total_minutes_per_week`:

1. Enumerate valid `(sessions_per_week, minutes_per_session)` combinations
2. Filter by `min_session_minutes` / `max_session_minutes` if provided
3. Select the split closest to 60-minute sessions
4. Create decision variables for each resulting session

This keeps the data model simple (users specify hours, not session counts) while the solver handles the combinatorics.
