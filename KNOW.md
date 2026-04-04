# TIMEASE — Technical Knowledge Base

State as of 2026-04-04. Phase 0 — Foundation complete.

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
│   │   └── plans.py     # (exists, not detailed yet)
│   ├── io/              # Empty stub — future Excel/PDF import-export
│   ├── app/             # Empty stub — future Reflex web UI
│   └── data/
│       ├── sample_school.json       # Lycée Excellence de Dakar
│       └── real_school_dakar.json   # Institut Islamique de Dakar
├── scripts/
│   └── solve_from_json.py  # CLI solver with ANSI grid display
└── tests/               # pytest suite — 232 tests
```

**Dependency rule**: `engine/` imports nothing from `app/` or `io/`. `io/` may import `engine/`. `app/` may import both. This boundary is enforced and tested.

---

## 2. Data Model

All models are Python dataclasses defined in `timease/engine/models.py`.

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
| `assignments` | list[...] | Scheduled sessions |
| `solved` | bool | True = full solution found |
| `partial` | bool | True = some sessions skipped (domain filtering) |
| `unscheduled_sessions` | list[...] | Sessions that couldn't be placed |
| `conflicts` | list[...] | ConflictReport entries |
| `soft_constraint_details` | list[...] | S1–S5 satisfaction data |

### Constraint
| Field | Type | Notes |
|-------|------|-------|
| `id` | str | e.g. "H1", "S3" |
| `type` | str | `"hard"` or `"soft"` |
| `category` | str | Constraint family name |
| `parameters` | dict | Constraint-specific config |

---

## 3. Solver Architecture

Defined in `timease/engine/solver.py`. This is the most critical component.

### Variable model

Each session gets **one IntVar** on a global timeline:

```
slot_value = day_idx × n_slots_per_day + slot_within_day
```

For a 196-session school this produces ~1,204 variables. A naive BoolVar grid (session × slot) would produce ~97,000. The compact model is what makes performance acceptable.

### Build pipeline (in order)

1. **Greedy teacher pre-assignment** — runs before CP-SAT model construction. For each `(class, subject)` pair, scores eligible teachers on `(n_other_subjects, current_assigned_count, -remaining_capacity)` and picks the best. If `CurriculumEntry.teacher` is set explicitly, that teacher is used directly and greedy is skipped for that entry.

2. **Domain pre-filtering** — applies H1, H3, H5, H6, H7, and teacher unavailability to shrink each session's valid slot set before the model is built. Sessions with an empty domain after filtering are **skipped** (not added to the model) and recorded in `unscheduled_sessions`. This sets `partial=True`.

3. **CP-SAT model build** — adds no-overlap constraints:
   - One `add_no_overlap` per class (all days, global timeline)
   - One `add_no_overlap` per teacher (all days, global timeline)
   - One `add_no_overlap` per room (optional, if room tracking enabled)

4. **Room assignment** — BoolVars per `(session, eligible_room)`, enforced with `add_exactly_one`.

5. **Solve** — feasibility only. No CP-SAT objective function. The solver finds any valid assignment.

6. **Post-solve analysis** — soft constraints S1–S5 are evaluated in Python against the solution. Satisfaction percentages are computed and attached to `TimetableResult`.

### Performance (sample_school.json)
- 196 sessions, 8 classes, 14 teachers
- ~1,204 CP-SAT variables
- Solves in ~15 seconds

---

## 4. Hard Constraints (H1–H11)

Defined in `timease/engine/constraints.py`.

| ID | Category | Mechanism | What it enforces |
|----|----------|-----------|-----------------|
| H1 | `start_time` | Domain filtering | Minimum start hour for sessions |
| H2 | `one_teacher_per_subject_per_class` | Greedy pre-assignment | Each (class, subject) pair has exactly one teacher |
| H3 | `day_off` | Domain filtering | Block a full day or session-half (AM/PM) for a class |
| H4 | `max_consecutive` | CP-SAT model | Max consecutive teaching hours per class |
| H5 | `subject_on_days` | Domain filtering | Subject sessions only allowed on listed days |
| H6 | `subject_not_on_days` | Domain filtering | Subject sessions excluded from listed days |
| H7 | `subject_not_last_slot` | Domain filtering | Subject can't occupy the last slot of any day |
| H8 | `teacher_day_off` | CP-SAT model | Teacher unavailable on specific day/session |
| H9 | `fixed_assignment` | CP-SAT model | Pin a session to an exact day + time slot |
| H10 | (no-op) | Pre-assignment | Automatically satisfied by greedy assignment |
| H11 | `min_sessions_per_day` | CP-SAT model | Minimum sessions per class on configured days |

H1, H3, H5, H6, H7 act as **domain filters** — they run before CP-SAT and reduce the search space. H4, H8, H9, H11 are expressed as CP-SAT constraints inside the model.

---

## 5. Soft Constraints (S1–S5)

Defined in `timease/engine/analysis.py`. All are **post-solve Python analysis only** — they do not add any CP-SAT objective or penalty. The solver does not try to optimize them; it only measures them.

| ID | Category | What it measures |
|----|----------|-----------------|
| S1 | `teacher_time_preference` | Whether teacher sessions fall in their preferred period (morning/afternoon) |
| S2 | (not yet implemented) | — |
| S3 | `balanced_daily_load` | Daily hour variance per class (lower = more balanced) |
| S4 | `subject_spread` | Whether subject sessions are spread across different days |
| S5 | `heavy_subjects_morning` | Whether cognitively heavy subjects are scheduled in the morning |

**Known S1/S5 conflict**: a teacher can have `afternoon` preference (S1) while also teaching a `heavy` subject (S5 wants morning). `validate_warnings()` detects and reports this conflict. The solver cannot resolve it automatically.

---

## 6. ConflictAnalyzer

Defined in `timease/engine/conflicts.py`. Runs automatically when the solver fails and the CLI is invoked. Returns `list[ConflictReport]`.

### Three-step diagnosis

**Step 1 — Quick checks** (O(n) Python, no re-solve):
- Missing teacher for a subject
- Missing room with required type/capacity
- Teacher load exceeds `max_hours_per_week`
- Total scheduled time exceeds available week slots

**Step 2 — Constraint relaxation** (re-solve with 5s timeout per constraint):
- Removes each hard constraint one at a time and re-solves
- If the model becomes feasible without constraint C, C is flagged as a culprit
- Source tagged as `"relaxation"` in the report

**Step 3 — Fix suggestions**:
- Each `ConflictReport` includes a list of `FixOption` objects
- Each `FixOption` has French-language text and an `ease` score (1 = easy config change, 3 = requires hiring or major restructure)

---

## 7. Validation Warnings

`validate_warnings()` runs before solving and returns non-fatal warnings. Key detections:

| Warning | Condition |
|---------|-----------|
| Room too small | Room capacity < class size |
| Teacher sole-subject overload | Teacher's only subject requires >80% of their `max_hours_per_week` |
| Overshadowed teacher | Teacher whose every subject has a more-specialized competitor — greedy will never select them, they get 0 assignments |
| S1/S5 conflict | Teacher prefers afternoon but is assigned to a morning-preferred (heavy) subject |

Warnings don't block solving. They surface likely misconfiguration before the model runs.

---

## 8. Partial Solutions

**Trigger**: domain pre-filtering (H1/H3/H5/H6 + unavailability) removes all valid slots for one or more sessions.

**Behavior**: those sessions are skipped from the CP-SAT model. The solver runs on the remaining sessions. If CP-SAT succeeds on the reduced set:
- `solved = False`
- `partial = True`
- `assignments` contains all placed sessions
- `unscheduled_sessions` lists the skipped sessions

**Current limitation**: if the model is infeasible due to mutual exclusion (sessions have non-empty domains but can't coexist given no-overlap constraints), the solver returns `solved=False, partial=False` with empty assignments. This case is not yet handled gracefully. Fixing it would require an optional-interval model rewrite.

---

## 9. CLI

```
uv run python scripts/solve_from_json.py <school.json> [--timeout N] [--class NAME]
```

Defined in `scripts/solve_from_json.py`.

**Features:**
- ANSI-colored timetable grid with box-drawing characters
- Visual column width is correct (strips ANSI codes before measuring string length for padding)
- On failure, automatically runs ConflictAnalyzer and prints ★-rated fix suggestions
- On success, prints soft constraint satisfaction % per constraint (S1–S5)
- `--class NAME` filters the grid display to a single class
- `--timeout N` overrides the CP-SAT solver timeout (seconds)

---

## 10. Test Suite

232 tests across 5 files. Run with `uv run pytest`.

| File | Tests | Coverage focus |
|------|-------|---------------|
| `test_models.py` | — | Entity `validate()` methods, `SchoolData` fields, field types |
| `test_validation.py` | — | Cross-entity validation, `validate_warnings()`, `verify()`, JSON round-trip, S1/S5 conflict detection, overshadowed teacher detection, ConflictAnalyzer relaxation path |
| `test_conflicts.py` | 21 | ConflictAnalyzer — all three diagnosis steps, fix suggestions, ease scores |
| `test_solver.py` | 25 | Double-booking prevention, room type matching, soft constraint measurement, H9 fixed assignment, H11 min sessions, solve performance |
| `test_analysis.py`, `test_plans.py` | — | Soft constraint analysis, plans module |

---

## 11. Data Files

### `timease/data/sample_school.json`
- School: Lycée Excellence de Dakar
- 8 classes, 14 teachers, Mon–Sat schedule
- 196 sessions per week
- Solves in ~15 seconds

### `timease/data/real_school_dakar.json`
- School: Institut Islamique de Dakar
- 4 classes, 14 teachers, Mon–Fri schedule
- 97 sessions per week
- Explicit teacher assignments for Anglais:
  - Cheikh Ndour → 3ème
  - Mariama Ba → 5ème, 4ème
  - Ndeye Toure → 6ème
- Solves in ~60 seconds (tight: high Coran volume + teacher availability constraints)

---

## 12. Known Limitations and Future Work

| # | Area | Description |
|---|------|-------------|
| 1 | Web UI | `timease/app/` is an empty stub. No Reflex pages built yet. |
| 2 | Export | `timease/io/` is an empty stub. No Excel, PDF, or Word output. |
| 3 | Persistence | Results live only in memory during a CLI run. No database writes. |
| 4 | Soft constraint optimization | S1–S5 are measured post-solve but not driven by a CP-SAT objective. The solver does not try to improve their scores. |
| 5 | Partial solution completeness | Mutual-exclusion INFEASIBLE (non-empty domains but conflicting sessions) still returns empty assignments. Requires optional-interval model rewrite. |
| 6 | Teacher granularity | `CurriculumEntry.teacher` is level-scoped. Can't assign different teachers to 6ème A vs 6ème B for the same subject without creating separate curriculum entries. |
| 7 | Greedy irreversibility | Once the greedy phase pre-assigns a teacher, CP-SAT cannot reassign them. A suboptimal greedy choice cannot be corrected by the solver. |

---

## 13. Commands

```bash
# Install dependencies
uv sync

# Run all tests
uv run pytest

# Run tests with verbose output
uv run pytest -v --tb=short

# Solve sample school (8 classes, ~15s)
uv run python scripts/solve_from_json.py timease/data/sample_school.json

# Solve real school with longer timeout (~60s needed)
uv run python scripts/solve_from_json.py timease/data/real_school_dakar.json --timeout 90

# Solve and display only one class
uv run python scripts/solve_from_json.py timease/data/sample_school.json --class "6ème A"
```
