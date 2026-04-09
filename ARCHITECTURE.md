# TIMEASE — Architecture

## Request Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Browser │───▶│ Next.js  │───▶│ FastAPI  │───▶│  Engine  │
│          │◀───│  :3000   │◀───│  :8000   │◀───│ (OR-Tools)│
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

- **Browser**: User fills the step-by-step form wizard
- **Next.js**: SSR, client-side state, API calls to backend
- **FastAPI**: REST endpoints, session management
- **Engine**: CP-SAT solver, constraint application, timetable generation

## FastAPI Routes

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/session` | Create new session |
| GET | `/api/session/{sid}` | Get session state |
| POST | `/api/session/{sid}/restore` | Re-hydrate session from localStorage |
| PUT | `/api/session/{sid}/school_data` | Update school configuration |
| PUT | `/api/session/{sid}/assignments` | Update teacher assignments |
| POST | `/api/session/{sid}/upload` | Import Excel template |
| POST | `/api/session/{sid}/solve` | Run CP-SAT solver |
| GET | `/api/session/{sid}/export/{format}` | Export timetable (xlsx/pdf/docx/md) |

## Module Responsibilities

### `timease/engine/`

Core solver logic. Contains data models (`models.py`), constraint handlers (`constraints.py`), and the CP-SAT solver wrapper (`solver.py`). Pure Python with OR-Tools, no I/O or network dependencies.

### `timease/io/`

Import/export handlers for Excel (`excel_import.py`, `excel_export.py`), PDF (`pdf_export.py`), Word (`word_export.py`), and Markdown (`md_export.py`). Transforms between file formats and engine data structures.

### `timease/api/`

FastAPI application. `main.py` handles REST endpoints and session management.

### `frontend/`

Next.js 14 application. Multi-step form wizard (`StepPanel.tsx`), step navigation (`StepIndicator.tsx`), timetable visualization (`TimetableGrid.tsx`), and results export. TypeScript with Tailwind CSS.

## Data Lifecycle

```
Raw Input (Form / Excel)
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
  Exporters  ← PDF/Excel/Word/Markdown output
```

## Session Strategy

In-memory dict keyed by `sid` (session ID). Sessions are ephemeral; no persistence layer. The frontend persists session ID, school data, assignments, and timetable result in `localStorage` and re-hydrates on load. This is a known limitation, not a bug.

```python
_sessions: dict[str, dict] = {}
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
- `assignments`: List of scheduled sessions (class, subject, teacher, room, day, start, end)
- `unscheduled`: Sessions the solver could not place
- `warnings`: Soft constraint violations or substitutions

## Solver — Curriculum Splitting

The solver determines session splits from `CurriculumEntry.total_minutes_per_week`:

1. Enumerate valid `(sessions_per_week, minutes_per_session)` combinations
2. Filter by `min_session_minutes` / `max_session_minutes` if provided
3. Select the split closest to 60-minute sessions
4. Create decision variables for each resulting session

This keeps the data model simple (users specify hours, not session counts) while the solver handles the combinatorics.
