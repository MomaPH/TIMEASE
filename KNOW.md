# TIMEASE — Technical Knowledge Base

State as of 2026-04-06. Transitioning to Phase 2 (Human-in-the-Loop optimizations).

---

## 1. Architecture

```
TIMEASE/
├── timease/
│   ├── engine/          # Solver engine — zero web dependency
│   │   ├── models.py    # All data models (dataclasses)
│   │   ├── solver.py    # CP-SAT timetable solver
│   │   ├── constraints.py  # Hard constraint builder (H1–H11)
│   │   ├── analysis.py  # Soft constraint analyzer (post-solve)
│   │   ├── conflicts.py # Infeasibility diagnosis (ConflictAnalyzer)
│   │   └── plans.py     # Session planning helpers
│   ├── io/              # File import/export
│   │   ├── file_parser.py   # Text extraction: xlsx, csv, docx, txt, pdf, json, md, yaml
│   │   ├── excel_import.py  # Structured Excel template import
│   │   ├── excel_export.py  # Excel timetable export
│   │   ├── pdf_export.py    # PDF timetable export
│   │   ├── word_export.py   # Premium Word export (cover page, headers/footers)
│   │   └── md_export.py     # Premium Markdown export (YAML frontmatter, stats block)
│   ├── api/
│   │   ├── main.py      # FastAPI backend — REST API + SSE streaming
│   │   └── ai_chat.py   # Anthropic AI chat handler (streaming + agentic loop)
│   └── data/
│       ├── sample_school.json           # Lycée Excellence de Dakar (test data)
│       ├── real_school_dakar.json       # Institut Islamique de Dakar
│       ├── real_school_dakar_LOCKED.json  # Locked reference snapshot
│       └── template.xlsx               # Excel import template
├── frontend/            # Next.js 16 app (App Router, React 19, Tailwind v4)
│   ├── app/
│   │   ├── page.tsx             # Landing / home
│   │   ├── workspace/page.tsx   # Main UI: AI chat + wizard form side-by-side
│   │   ├── results/page.tsx     # Timetable viewer + export buttons
│   │   ├── collaboration/page.tsx  # Teacher invitation links
│   │   └── collab/[token]/page.tsx # Teacher availability portal (public)
│   ├── components/
│   │   ├── ChatMessage.tsx      # Markdown rendering, copy button, option chips
│   │   ├── StepIndicator.tsx    # 9-step horizontal wizard bar
│   │   ├── StepPanel.tsx        # Editable form for each wizard step
│   │   ├── FileImportModal.tsx  # Post-upload import summary
│   │   ├── TimetableGrid.tsx    # Timetable table with subject color fills
│   │   ├── ClientLayout.tsx     # Root client layout wrapper
│   │   ├── Sidebar.tsx          # Navigation sidebar
│   │   └── Toast.tsx            # Toast notification system
│   ├── hooks/
│   │   └── useSession.ts        # Session state + localStorage persistence
│   └── lib/
│       ├── api.ts               # All fetch calls to backend (incl. SSE stream)
│       └── types.ts             # TypeScript types (ChatMessage, SchoolData, Steps…)
├── scripts/
│   ├── solve_from_json.py   # CLI solver with ANSI grid display
│   ├── solve_from_excel.py  # CLI solver from Excel template
│   └── generate_sample.py   # Generate sample school data
├── tests/               # pytest suite
│   ├── test_models.py
│   ├── test_validation.py
│   ├── test_conflicts.py
│   ├── test_solver.py
│   ├── test_analysis.py
│   ├── test_plans.py
│   └── test_io.py
├── run_api.py           # Entry point: uvicorn timease.api.main:app
├── start.sh             # Starts both backend (port 8000) and frontend (port 3000)
├── pyproject.toml       # uv project config
├── CLAUDE.md            # Dev instructions for Claude Code
└── KNOW.md              # This file
```

**Dependency rule**: `engine/` imports nothing from `api/` or `io/`. `io/` may import `engine/`. `api/` may import both. This boundary is enforced and tested.

---

## 2. Running the App

```bash
# Install Python + Node deps
uv sync
cd frontend && npm install && cd ..

# Start everything (backend on :8000, frontend on :3000)
./start.sh

# OR start separately
uv run python run_api.py          # backend
cd frontend && npm run dev         # frontend

# Run tests
uv run pytest

# CLI solver
uv run python scripts/solve_from_json.py timease/data/sample_school.json
```

---

## 3. API Overview

Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/session` | Create new session → `{session_id}` |
| GET | `/api/session/{sid}` | Get session state |
| POST | `/api/session/{sid}/restore` | Re-hydrate session from localStorage data |
| PUT | `/api/session/{sid}/school_data` | Replace school data |
| PUT | `/api/session/{sid}/assignments` | Replace teacher assignments |
| POST | `/api/session/{sid}/chat` | Non-streaming AI chat turn |
| POST | `/api/session/{sid}/chat/stream` | SSE streaming AI chat turn |
| POST | `/api/session/{sid}/upload` | Upload file (xlsx/csv/docx/pdf/json/md/yaml) |
| POST | `/api/session/{sid}/solve` | Run CP-SAT solver |
| GET | `/api/session/{sid}/export/{format}` | Export timetable (xlsx/pdf/docx/md) |
| POST | `/api/session/{sid}/collab/generate` | Generate teacher invitation tokens |
| GET | `/api/collab/{token}` | Get collab token data |
| POST | `/api/collab/{token}/availability` | Teacher submits availability |

### SSE streaming event format
Events sent as `data: {json}\n\n`:
- `{"type": "delta", "text": "..."}` — streamed text token
- `{"type": "tool_start", "name": "..."}` — tool call starting
- `{"type": "done", "data_saved": bool, "trigger_generation": bool, "options": [...], "set_step": int|null, "saved_types": [...], "ai_history": [...]}` — final event

### Session state shape
```python
{
  "school_data": {
    "name": str, "city": str, "academic_year": str,
    "days": list[str], "sessions": list[dict], "base_unit_minutes": int,
    "classes": list[dict], "teachers": list[dict], "rooms": list[dict],
    "subjects": list[dict], "curriculum": list[dict], "constraints": list[dict]
  },
  "teacher_assignments": list[{"teacher": str, "subject": str, "school_class": str}],
  "timetable_result": dict | None,
  "ai_history": list[dict],
  "collab_links": list[dict]
}
```

---

## 4. Data Model

All models are Python dataclasses in `timease/engine/models.py`.

### CurriculumEntry
| Field | Type | Notes |
|-------|------|-------|
| `level` | str | e.g. "6ème", "3ème" |
| `subject` | str | e.g. "Mathématiques" |
| `total_minutes_per_week` | int | Weekly teaching time |
| `mode` | str | `"manual"` or `"auto"` |
| `sessions_per_week` | int | How many sessions |
| `minutes_per_session` | int | Duration each session |
| `teacher` | str \| None | If set, bypasses greedy assignment |

### Teacher
| Field | Type | Notes |
|-------|------|-------|
| `name` | str | |
| `subjects` | list[str] | What they can teach |
| `max_hours_per_week` | float | Hard cap |
| `unavailable_slots` | list[...] | Day/session pairs |

### TimetableResult
| Field | Type | Notes |
|-------|------|-------|
| `assignments` | list[Assignment] | Scheduled sessions |
| `solved` | bool | True = full solution found |
| `partial` | bool | True = some sessions skipped |
| `unscheduled_sessions` | list[dict] | Sessions that couldn't be placed |
| `conflicts` | list[dict] | Conflict reports |
| `soft_constraint_details` | list[dict] | S1–S5 satisfaction data |
| `warnings` | list[str] | Non-fatal validation warnings |
| `solve_time_seconds` | float | |

---

## 5. Solver Architecture

Defined in `timease/engine/solver.py`.

### Variable model
Each session gets **one IntVar** on a global timeline:
```
slot_value = day_idx × n_slots_per_day + slot_within_day
```
For a 196-session school: ~1,204 variables (vs ~97,000 for a naive BoolVar grid).

### Build pipeline (in order)
1. **Greedy teacher pre-assignment** — scores teachers on `(n_other_subjects, current_assigned_count, -remaining_capacity)`. Explicit `CurriculumEntry.teacher` bypasses greedy.
2. **Domain pre-filtering** — applies H1, H3, H5, H6, H7 + teacher unavailability to shrink each session's valid slot set. Empty-domain sessions are skipped → `partial=True`.
3. **CP-SAT model build** — `add_no_overlap` per class, per teacher, per room.
4. **Room assignment** — `BoolVar` per `(session, eligible_room)` with `add_exactly_one`.
5. **Solve** — feasibility only (no objective function).
6. **Post-solve analysis** — soft constraints S1–S5 evaluated in Python against the solution.

### Performance
- `sample_school.json`: 196 sessions, 8 classes, 14 teachers → ~15 seconds
- `real_school_dakar.json`: 97 sessions, 4 classes, 14 teachers → ~60 seconds (tight constraints)

---

## 6. Hard Constraints (H1–H11)

| ID | Category | Mechanism | What it enforces |
|----|----------|-----------|-----------------|
| H1 | `start_time` | Domain filter | Minimum start hour |
| H2 | `one_teacher_per_subject_per_class` | Greedy | One teacher per (class, subject) |
| H3 | `day_off` | Domain filter | Block a full day or AM/PM half |
| H4 | `max_consecutive` | CP-SAT | Max consecutive hours per class |
| H5 | `subject_on_days` | Domain filter | Subject only on listed days |
| H6 | `subject_not_on_days` | Domain filter | Subject excluded from listed days |
| H7 | `subject_not_last_slot` | Domain filter | Subject can't be last slot of day |
| H8 | `teacher_day_off` | CP-SAT | Teacher unavailable on day/session |
| H9 | `fixed_assignment` | CP-SAT | Pin session to exact day + time |
| H10 | (auto) | Pre-assignment | Satisfied by greedy |
| H11 | `min_sessions_per_day` | CP-SAT | Min sessions per class on days |

---

## 7. Soft Constraints (S1–S5)

Post-solve Python analysis only — no CP-SAT objective. Scores are percentages.

| ID | Category | What it measures |
|----|----------|-----------------|
| S1 | `teacher_time_preference` | Sessions in teacher's preferred period |
| S3 | `balanced_daily_load` | Daily hour variance per class |
| S4 | `subject_spread` | Subject sessions spread across days |
| S5 | `heavy_subjects_morning` | Heavy subjects scheduled in morning |

**Known S1/S5 conflict**: teacher prefers afternoon (S1) but teaches a heavy subject (S5 wants morning). Detected by `validate_warnings()`.

---

## 8. ConflictAnalyzer

Runs automatically on INFEASIBLE result. Three-step diagnosis:
1. **Quick checks** — missing teacher, missing room type, overloaded teacher, insufficient week slots.
2. **Constraint relaxation** — removes each hard constraint one at a time, re-solves (5s timeout). If feasible without C → C is flagged.
3. **Fix suggestions** — each report has French `FixOption` objects with `ease` score (1 = easy config change, 3 = requires hiring).

---

## 9. AI Chat System

Defined in `timease/api/ai_chat.py`. Model: `claude-sonnet-4-6`.

### Tools
| Tool | Trigger |
|------|---------|
| `save_school_info` | After user confirms school info |
| `save_teachers` | After user confirms teacher list |
| `save_classes` | After user confirms class list |
| `save_rooms` | After user confirms room list |
| `save_subjects` | After user confirms subject list |
| `save_assignments` | After user confirms teacher-subject-class assignments |
| `save_curriculum` | After user confirms weekly hours |
| `save_constraints` | After user confirms constraints |
| `propose_options` | On every question with choices (rendered as chips in UI) |
| `trigger_generation` | When all data ready + user requests generation |
| `set_current_step` | After saving, to advance the wizard panel (0–8) |

### Conflict diagnosis flow
When `POST /api/session/{sid}/solve` returns INFEASIBLE:
1. `ConflictAnalyzer` runs and produces `ConflictReport` list — each report has `step_to_fix: int` (wizard step index), `severity`, and ranked `FixOption` objects.
2. Structured reports are stored as `last_conflict_reports` in the session.
3. On the next AI chat turn, `_build_system_prompt` injects the conflict reports as a `RÉSULTAT DU DERNIER ESSAI` block, guiding the AI to explain each conflict and call `set_current_step` to navigate the user to the right fix step.
4. `unscheduled_sessions` are also grouped by inferred cause (`missing_teacher`, `room_unavailable`, `no_valid_slot`, `constraint_conflict`) and returned as `unscheduled_groups` in the solve response.

### Agentic loop
`stream_chat()` runs up to 4 API turns per user message. After each data save, the tool result instructs the AI to: (1) show a recap table, (2) call `set_current_step`, (3) call `propose_options`. Forces proactive follow-up.

### Validation flow
All save tool descriptions require user confirmation before calling. AI shows summary table + `[✅ Confirmer] [✏️ Modifier]` chips first.

---

## 10. Frontend Architecture

**Tech**: Next.js 16, React 19, Tailwind CSS v4, TypeScript.

### localStorage persistence
| Key | Content |
|-----|---------|
| `timease_session` | Session ID |
| `timease_timetable_{sid}` | Last timetable result (survives backend restart) |
| `timease_messages_{sid}` | Chat message history |
| `timease_aihistory_{sid}` | AI conversation history (Anthropic format) |

`useSession` restores all state on mount. Re-hydration via `POST /restore` is called before exports.

### Wizard steps (0–8)
`0` École → `1` Classes → `2` Enseignants → `3` Salles → `4` Matières → `5` Affectations → `6` Programme → `7` Contraintes → `8` Résumé/Générer

### Streaming
`sendChatStream()` in `api.ts` uses `fetch` + `ReadableStream` to parse SSE. Tokens are appended to a placeholder message in real-time. `done` event finalizes with options/step/saved metadata.

---

## 11. Export Formats

| Format | Notes |
|--------|-------|
| Excel (.xlsx) | openpyxl, one sheet per class/teacher |
| PDF (.pdf) | reportlab, landscape A4 |
| Word (.docx) | Premium: cover page (school name 28pt, accent band), Georgia headings, teal header rows with white text, lightened subject color fills, alternating row shading, per-page header + footer (page X/Y) |
| Markdown (.md) | Premium: YAML frontmatter, stats blockquote table, emoji section dividers, subject legend, right-aligned time column |

---

## 12. Known Limitations

| # | Area | Description |
|---|------|-------------|
| 1 | Soft constraint optimization | S1–S5 measured post-solve but not CP-SAT objectives. Solver doesn't optimize them. |
| 2 | Partial solution completeness | Mutual-exclusion INFEASIBLE (non-empty domains but conflicting sessions) returns empty assignments. Requires optional-interval model rewrite. |
| 3 | Teacher granularity | `CurriculumEntry.teacher` is level-scoped. Can't assign different teachers to 6ème A vs 6ème B for same subject without separate entries. |
| 4 | Greedy irreversibility | CP-SAT can't reassign after greedy phase. Suboptimal greedy choice can't be corrected by solver. |
| 5 | In-memory sessions | Backend sessions lost on restart. Phase 2 introduces Postgres RLS. |
| 6 | Collaboration | Teacher availability portal pending Admin Approval staging flow (Phase 2). |

---

## 13. Phase 2 Roadmap & Architectural Shifts

> [!IMPORTANT]
> The overriding philosophy of Phase 2 is **Absolute Human Authority**. Algorithmic abstractions must not override human administration.

### A. Deprecating Greedy / Auto Assignment
In real schools, teachers negotiate classes during contract phases. Therefore, `CurriculumEntry.mode="auto"` and the Python Greedy Pre-Assignment engine are deprecated. The engine assumes 100% rigid manual assignments, dropping the computationally heavy routing loop and simply plotting human choices against time slots natively.

### B. Scaled Asynchronous Solving (Celery & Render PaaS)
Large models exceed HTTP 60s timeouts.
- **Worker Queues:** CP-SAT tasks are decoupled using Celery and Redis (`@celery.task`).
- **Cloud Split:** Because serverless environments (Vercel) kill background workers, Next.js remains on Vercel while FastAPI+Celery+Postgres deploys to a "Background Worker" native PaaS (e.g., Render.com in the EU region) ensuring stable, long-running processing while preserving legal DP compliance for Senegal under the CDP.

### C. Advanced CP-SAT Optimization
- S1–S5 Soft Constraints are moving from post-solve grading to native CP-SAT `model.Maximize()`.
- To avoid infinite loops where the solver tries to prove ultimate optimality over 10 hours, a strict parameter `solver.parameters.max_time_in_seconds = 30` is enforced.

### D. Multi-Tenancy & Data Privacy
- **Row-Level Security (RLS):** Database queries are locked down at the Postgres level (`ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;`), ensuring structural mathematical isolation between rival schools.
- **Admin Collaboration Staging:** Availabilities requested by teachers route to a Staging DB for explicit school-administrator approval before converting to CP-SAT constraints.

### E. API Cost Optimization & Mypyc Compilation
- **Frontend Deterrence:** React structurally prevents execution if total requested class hours outweigh the physical school week, reducing LLM calls for silly human math errors.
- **Deterministic Fixes:** When `INFEASIBLE` occurs, native React UI handles it. The LLM is only triggered via an *"Ask AI"* opt-in button.
- **C-Extension (mypyc):** The pure Python `ConflictAnalyzer` iteratively trials constraints. To circumvent scaling bottlenecks, `conflicts.py` is strictly typed and compiled into native C-extensions using `mypyc`.

### F. Premium AI Concierge (UX layer)
- AI is elevated via transparent `AgentActionPill` micro-animations during tool execution.
- LLM outputs awaiting confirmation (`[✅ Confirmer]`) render as **inline-editable tables**, ensuring users can hand-correct AI math hallucinations without typing prompts or burning contextual tokens. 
