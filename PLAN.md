# TIMEASE — Engineering Plan (Performance + UX Overhaul)

**Status:** In progress — Batches 1, 2, 3 landed (not yet committed). Batches 4–6 remaining.
**Owner:** @sciencecontinum (PAPE MOMATH CAMARA)
**Last updated:** 2026-04-15 (post-Batch 3)
**Audience:** Any agent (Claude, Codex, etc.) or human engineer picking up this work mid-stream.

This document is **self-contained**. It should be readable cold, without access to prior chat context. All file paths are absolute from repo root (`/workspaces/TIMEASE`). Related docs: [`CLAUDE.md`](CLAUDE.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), [`AI_CONTRACT.md`](AI_CONTRACT.md).

---

## 0. Product thesis (read this first)

TIMEASE generates school timetables. Inputs from the school:

1. **Classes** with student count.
2. **Teachers** with the subjects they teach.
3. **Assignments**: for each (class, subject) pair — the teacher and hours/week.
4. **Rooms** (optional) — **pre-assigned by the school** to specific (class, subject) pairs. TIMEASE does **not** solve room allocation; it surfaces the school's assignments in the output.
5. **Constraints** — hard (must hold) and soft (optimize).

TIMEASE decides **only one thing**: **when** each session happens on the weekly timeline. That's it.

**Speed target:** match FET (seconds for typical schools, minutes for worst-case) by reducing scope to timeline placement only and applying the optimizations below.

**Selling points that must never regress:**
- **Intuitive UX.** Every input field must be obvious within 5 seconds of seeing it.
- **Faithful report.** The results page must show exactly what was scheduled, what wasn't, why, and suggest fixes.
- **French UI, English code.** Per `CLAUDE.md`.

---

## 1. Scope of this plan

Two tracks, executable in parallel:

- **Track A — Solver performance** (match FET speed).
- **Track B — UX simplification** (subjects input + constraints panel + fidelity report).

Do not add new dependencies (per `CLAUDE.md`).

---

## 2. Track A — Solver performance

Current state (as of 2026-04-15):
- `timease/engine/solver.py` — 1,595 lines, CP-SAT model with `IntVar` per session on global timeline, room BoolVars, class/teacher/room `no_overlap`, LNS repair fallback for fast-mode.
- Benchmarks: `scripts/benchmark/run_fet_timease_benchmark.py`, `scripts/benchmark/build_fet_manifest.py`, FET prefills in `frontend/data/fet-prefills/`. No saved baseline numbers in-repo.

### A0 — Room pre-assignment via eligible-set shrinkage [LANDED, partial — Batch 3]

**Delivered:**
- `TeacherAssignment.room: str | None = None` added (`timease/engine/models.py`).
- Solver honors `ta.room` by narrowing the session's `eligible_room_idxs` to a singleton at build time (`timease/engine/solver.py`). CP-SAT presolve collapses singleton BoolVars in O(1), so this realizes most of the perf benefit without deleting the room machinery.
- API round-trips the new field (`timease/api/main.py`).
- Regression test: `tests/test_solver.py::TestRoomPreassignment::test_preassigned_room_is_honored`.
- Unknown / capacity-insufficient preassigned rooms produce a French warning and fall back to the default eligibility search.

**Deliberately deferred (scope creep risk):**
- Full removal of `room_bvars`, `add_exactly_one`, and per-room `add_no_overlap` — currently still built even when every session has a singleton eligibility. CP-SAT presolve erases the decision, so remaining cost is constant-time model construction, not search.
- `timease/engine/room_validator.py` — pre-solve detection of unavoidable room double-booking.
- Frontend UI input for `room` in the assignment row. Backend accepts the field today; frontend will surface it in Batch 4 alongside the constraints redesign (both touch `ClassCardsStep.tsx`).

**Original scope (for reference / follow-up):**

**Why:** rooms are pre-assigned by the school per the product thesis. Current code creates one `BoolVar` per (session × eligible_room), `add_exactly_one` per session, and `add_no_overlap` per room. On realistic inputs this roughly doubles variable count and adds the dominant propagators.

**Files to change:**
- `timease/engine/models.py` — add `room: str | None` on `TeacherAssignment` (preferred) or on `CurriculumEntry`. Choose **`TeacherAssignment`** for consistency (rooms follow the pedagogical contract).
- `timease/engine/solver.py` — delete:
  - `eligible_room_idxs` / `preferred_room_idxs` / `fallback_room_idxs` computation (lines ~741–820).
  - Room BoolVars and the `add_exactly_one` / `add_no_overlap` per room.
  - `prefer_standard_rooms_for_general_subjects` parameter (no longer meaningful).
  - `enforce_room_conflicts` parameter — keep the name but make it a **pre-solve validator**, not a CP-SAT constraint.
- `timease/api/main.py` — update request/response schemas.
- `frontend/lib/types.ts` — add `room?: string` to `TeacherAssignment`.
- `frontend/components/steps/ClassCardsStep.tsx` — add room input next to teacher/hours in the assignment row.

**Pre-solve room validation** (new file `timease/engine/room_validator.py` or a function in `solver.py`):
- Group scheduled assignments by `room`. For any two assignments sharing a room, verify their time windows never overlap **after** scheduling. If they could overlap in any feasible schedule, surface a `conflicts[]` entry with `reason="Room double-booked: <room> shared by <class1>/<subject1> and <class2>/<subject2>"`.
- This runs **after** the solver. If conflicts exist, the AI layer suggests reassigning one.

**Output:** every scheduled session in `TimetableResult.assignments` carries `room` copied from the input. Empty string if the school didn't assign one.

**Acceptance:**
- All existing tests in `tests/test_solver.py` pass after assignments include `room`.
- Benchmark shows ≥30% variable reduction on `scripts/benchmark` datasets.
- Room conflicts (when deliberately introduced in test data) appear in `conflicts[]` not as CP-SAT infeasibility.

### A1 — Tighten the core model

After A0, the model is: `start_var` per session + class `no_overlap` + teacher `no_overlap` + domain pre-filters.

**Changes in `timease/engine/solver.py`:**

1. **Singleton fixing.** After domain filtering, if `len(session_domains[i]) == 1`, do not create an `IntVar`. Record the pre-placement in a `fixed_positions: dict[int, int]` and exclude from `no_overlap` intervals by baking the fixed interval directly (use `model.new_fixed_size_interval_var` at a constant start).
2. **AllDifferent on days for multi-session subjects.** For a `(class, subject)` with `N` sessions and `N ≤ len(day_names)` (almost always true), add `model.add_all_different([start_var[i] // n_slots_per_day for i in sessions_of(class, subject)])`. Encode via auxiliary `day_var = model.new_int_var(0, n_days-1)` + `model.add_division_equality(day_var, start_var, n_slots_per_day)`.
3. **Keep** the existing interchangeable-session cut (`start[i] ≤ start[i+1]`).

**Acceptance:** `tests/test_solver.py` still passes. Benchmark shows wall-clock improvement on medium datasets (300–600 sessions).

### A2 — Greedy warm start via hints [LANDED, fast-path only — Batch 2]

**Delivered:** `timease/engine/greedy.py` — reusable `greedy_warm_start(sessions, session_domains)` utility with integer-range overlap (no minute arithmetic, relies on the solver's "domain stays within one day" invariant). Wired into `solver.py` for the **fast-feasibility path only** (`not optimize_soft_constraints`).

**Why not the optimize path:** Tried it, broke `test_afternoon_preference_respected`. The greedy walks domains in ascending slot order → biases Phase A's feasibility solution toward morning → Phase B then hints from that morning-biased solution and can't recover soft time-of-day preferences within budget. A soft-aware greedy (sort domain by preference score before walking) is the fix — deferred.

**Original spec below for future reference:**



**New file:** `timease/engine/greedy.py` — 50–150 lines.

**Algorithm:**
1. Sort sessions by "most constrained first": primary key `len(session_domains[i])` ascending; secondary key `-dur_slots` (longer sessions first); tertiary key teacher load.
2. For each session, walk its domain in order and pick the first slot that conflicts with neither class nor teacher already placed.
3. If none fits, skip (return `None` for that session).
4. Return `dict[int, int | None]` of session_idx → slot (or None).

**Wire-up in `solver.py`:**
- Call greedy before building the CP-SAT model.
- For each session with a greedy placement, `model.add_hint(start_var[i], pos)`.
- Log the greedy coverage (`X/Y sessions pre-placed`).

**Acceptance:** on the largest benchmark, time-to-first-solution drops ≥3×. Hints never produce an infeasible model (if greedy is wrong, CP-SAT just ignores the hints).

### A3 — Search configuration [LANDED, partial — Batch 1]

**Delivered:** `linearization_level = 2` on the optimization-phase solver (`opt_solver` in `solver.py`), with a comment explaining why feasibility paths keep the default.

**Already present pre-Batch 1 (not changed):** `num_search_workers = min(8, os.cpu_count() or 1)`, `add_decision_strategy(CHOOSE_MIN_DOMAIN_SIZE, SELECT_MIN_VALUE)`, `PORTFOLIO_SEARCH` for optimization, `FIXED_SEARCH + stop_after_first_solution` for feasibility previews. A3 as originally scoped was largely a no-op on this codebase.

**Original spec below:**



**In `solver.py`, CP-SAT parameters:**

```python
solver.parameters.num_search_workers = os.cpu_count() or 8
solver.parameters.linearization_level = 2
solver.parameters.cp_model_presolve = True
solver.parameters.search_branching = cp_model.PORTFOLIO_SEARCH  # for optimization
# for feasibility-only previews: keep FIXED_SEARCH + stop_after_first_solution
```

Add an explicit decision strategy:

```python
model.add_decision_strategy(
    list(start_vars.values()),
    cp_model.CHOOSE_MIN_DOMAIN_SIZE,
    cp_model.SELECT_MIN_VALUE,
)
```

**Acceptance:** 2–4× speedup from parallelism alone on multi-core machines. Measurable on `run_fet_timease_benchmark.py`.

### A4 — Decomposition for hard/large cases

Only do this if A0–A3 leave a gap vs FET on the largest benchmarks.

**Approach:**
- **Fix-and-optimize by class level/group.** Solve one group at a time with teachers as shared resource. Previously-scheduled sessions from other groups become fixed intervals in the teacher `no_overlap`.
- **Promote LNS to primary path** (not fallback) for large inputs. Current LNS code is in `solver.py:157–438`; it's production-quality. Expose a threshold (`if len(sessions) > LNS_AS_PRIMARY_THRESHOLD: run LNS after greedy, before full CP-SAT`).

**Acceptance:** worst-case FET-equivalent datasets solve within 1-minute budget.

### A5 — Code hygiene [LANDED, partial — Batch 1]

**Delivered:**
- Replaced non-deterministic `hash((class, subject))` with `zlib.crc32` (`solver.py` fallback-room pick — deterministic across `PYTHONHASHSEED`).
- Replaced bare `except Exception` + string interpolation with `logger.exception` for proper tracebacks (`solver.py` LNS build catch).

**Not changed:** `ritual_blocked_prefix_by_day` — verified it IS read at `solver.py:845`, so the "possibly dead" note in the original plan was wrong.

**Original spec below:**



- `solver.py:781` — replace `hash((class, subject))` with `zlib.crc32` for deterministic behavior across `PYTHONHASHSEED`. **Obsolete after A0** (the code that uses it goes away). Still, grep for any other `hash(` usage.
- `solver.py:396` — replace bare `except Exception` with explicit exception types, log with stack trace.
- If `ritual_blocked_prefix_by_day` is computed but not read, remove it. Grep first.

---

## 3. Track B — UX simplification

### B1 — Subjects-per-teacher: chip input [LANDED — Batch 1]

**Delivered:** `frontend/components/ChipInput.tsx` (117 lines). Delimiters: space (when draft non-empty), comma, semicolon, Enter, Tab, blur. Backspace on empty deletes last chip. Paste splits on `[,;\n\t\s]+`. Case-insensitive dedup. Replaced the subjects input in `ClassCardsStep.tsx` and removed now-dead `subjectDrafts` state + `useEffect` + `commitTeacherSubjects` + `subjectsEqual`.

**Original spec below:**



**Problem:** `frontend/components/steps/ClassCardsStep.tsx:394–414` uses a plain `<input>`. Parser at `:225` splits on `[,;\n]+` (not space). Commit only on `onBlur` / `Enter`. Users type "Maths Physique" → one subject "Maths Physique"; typing comma appears to do nothing until blur. **Feels broken.**

**Fix:** build a reusable `ChipInput` component.

**New file:** `frontend/components/ChipInput.tsx`

**Behavior spec:**
- Props: `value: string[]`, `onChange: (next: string[]) => void`, `placeholder?: string`, `disabled?: boolean`.
- Rendering: chips (pill-shaped, teal bg, × button) + trailing `<input>` for typing.
- **Delimiters that instantly commit a chip:** `,`, `;`, **space** (when the current draft is non-empty), `Enter`, blur.
- **Backspace on empty input** deletes the last chip.
- Deduplicate case-insensitively (keep first occurrence's casing).
- Normalize with `.trim()`.
- Paste: split pasted content on `[,;\n\s]+` and add each as a chip.
- Tab: commit current draft as chip and move focus.
- No external dependency — plain React.

**Replace** the subjects input at `ClassCardsStep.tsx:394–414` with `<ChipInput value={t.subjects ?? []} onChange={next => updateTeacher(idx, 'subjects', next)} placeholder="Matières (ex: Maths, Physique, SVT)" />`.

**Delete dead code:**
- `subjectDrafts` state and its `useEffect` (`ClassCardsStep.tsx:281–307`).
- `commitTeacherSubjects` (`:309`).
- `parseSubjectsInput`, `normalizeSubject`, `subjectsEqual` move into `ChipInput.tsx` as internal helpers (or keep as utilities in `frontend/lib/text.ts`).

**Reuse:** use `ChipInput` anywhere else subjects are entered as lists (search for `fields.type === 'subjects'` in `ClassCardsStep.tsx:11`).

**Acceptance:**
- Typing "Maths<space>Physique<space>SVT" produces three chips.
- Typing "Maths, Physique, SVT" produces three chips on commas, no blur required.
- Backspace on empty removes last chip.
- Duplicates rejected silently.
- Paste of "Maths, Physique\nSVT" produces three chips.

### B2 — Constraints panel redesign

**Problem:** `CONSTRAINT_DEFS` at `ClassCardsStep.tsx:37–207` has 20 entries. Issues:
- `subject_on_days` + `subject_not_on_days` are mirror images.
- `teacher_time_preference` + `teacher_fallback_preference` differ only in weight.
- `one_teacher_per_subject_per_class` has 0 fields (should be a global toggle).
- `heavy_subjects_morning` has a `preferred_session` field allowing "Après-midi" — contradicts its label.
- `same_room_for_class` is obsolete after A0.
- `teacher_day_off` (soft) vs `day_off` (hard) — inconsistent scoping.
- Hard/soft grouping not visually prominent; user reads each label.

**Design goals:**
1. **Group by intent, not by hard/soft.** Sections: *Horaires*, *Matières*, *Enseignants*, *Qualité de vie* (soft globals).
2. **Merge mirrors.** One "Restriction de matière par jour" with radio: *Autoriser uniquement* / *Interdire* + days multi-select.
3. **Merge priority variants.** One "Préférence horaire enseignant" with a `priorité` slider (principale / secondaire).
4. **Promote always-on toggles.** `one_teacher_per_subject_per_class`, `balanced_daily_load`, `subject_spread` become checkboxes in a "Paramètres globaux" strip at the top, not constraints in the list.
5. **Drop** `same_room_for_class` entirely (rooms are pre-assigned).
6. **Rename & unify.** `teacher_day_off` (soft) → keep. `day_off` (global, hard) → stays in *Horaires* section as "Jour bloqué (école)".
7. **Fix `heavy_subjects_morning`.** Rename to "Matières à heures privilégiées" and let the `preferred_session` drive both label and semantics.

**Proposed new structure** (reduce from 20 → ~12 items, grouped):

```
PARAMÈTRES GLOBAUX (toggles, top strip)
  ☑ Un seul enseignant par matière/classe (on by default)
  ☑ Répartition équilibrée de la charge journalière
  ☑ Éviter deux séances de la même matière le même jour

HORAIRES (hard)
  • Heure de début minimum
  • Jour bloqué (école)
  • Max heures consécutives
  • Min sessions par jour
  • Créneau imposé

MATIÈRES (hard)
  • Restriction par jour  (autoriser|interdire + jours)
  • Pas en dernière heure
  • Pause minimale entre séances
  • Matières à heures privilégiées  (matières + matin|après-midi)  [soft]

ENSEIGNANTS
  • Préférence horaire (matin|après-midi, priorité principale|secondaire)  [soft]
  • Emploi du temps compact  [soft]
  • Jour de repos  [soft]

QUALITÉ DE VIE (soft)
  • Dernier jour allégé
  • Pas de matière enchaînée
```

**Backward-compat:** keep accepting old constraint names in the backend; add an input migrator in `frontend/lib/constraint-migrate.ts` that runs on session load. Old saved sessions must still work.

**Files:**
- `frontend/components/steps/ClassCardsStep.tsx` — rewrite `CONSTRAINT_DEFS` and the constraint render section.
- `frontend/lib/constraint-migrate.ts` (new) — map legacy constraint shapes to new shapes.
- `timease/engine/constraints.py` — backend should accept both legacy and new forms; add a single `_normalize_constraint(c)` at entry point.
- `tests/test_solver.py` — add cases that feed legacy constraints and assert equivalent behavior.

**Acceptance:**
- Number of constraint choices visible in UI ≤ 12 (plus 3 global toggles).
- Legacy sessions from before this change still solve identically.
- Every constraint label answers "what does this do?" in under 5 seconds of reading.

### B3 — Fidelity report on results page

**Current state:** `frontend/app/results/page.tsx:85–94, 314–367` already shows unscheduled count + grouped-by-cause + per-session reasons. Good foundation.

**Add:**

1. **Header strip with 4 KPIs:**
   - Sessions planifiées: X/Y
   - Contraintes dures satisfaites: X/Y
   - Score contraintes souples: X% (weighted average of soft scores from `timease/engine/analysis.py`)
   - Conflits d'entrée (salles, assignations manquantes): X

2. **"Ce qui n'a pas été fait" section** (rename from current unscheduled block):
   - List unscheduled sessions with human-readable reason (backend already provides `unscheduled_groups`).
   - For each reason cluster, show AI suggestion (calls `/api/ai/suggest-fix` — new endpoint per `AI_CONTRACT.md`).
   - Each suggestion should be actionable: "Professeur X a 23h de cours mais n'est disponible que 18h — réduire de 5h ou ajouter un créneau le vendredi après-midi".

3. **Soft constraint breakdown**: a collapsible list showing each active soft constraint with its satisfaction % and which sessions violated it.

4. **Download report as PDF.** Reuse `reportlab` (already in stack). New backend endpoint `GET /api/sessions/{id}/report.pdf`. Contents: the grid + KPIs + unscheduled list + soft scores.

**Files:**
- `frontend/app/results/page.tsx` — add KPI strip + soft breakdown section + PDF download button.
- `timease/api/main.py` — add `/sessions/{id}/report.pdf` route, delegate to new `timease/io/report_pdf.py`.
- `timease/io/report_pdf.py` (new) — reportlab-based PDF renderer.
- `timease/ai/` (new dir per `AI_CONTRACT.md`) — `suggest_fixes(unscheduled, constraints, data) -> list[str]`.

**Acceptance:**
- Every failed session has a reason AND a suggested fix visible on the page.
- PDF downloads and matches on-screen content.
- KPIs update live when a new job completes.

---

## 4. Execution order

### Landed (Batches 1–3, uncommitted)
- ✅ **Batch 1** — B1 chip input + A3 search config (partial) + A5 code hygiene (partial). 281 pytest / npm build green.
- ✅ **Batch 2** — A2 greedy warm start extracted to `timease/engine/greedy.py`. Fast-path only (optimize path regressed a soft-constraint test, reverted). 281 pytest / npm build green.
- ✅ **Batch 3** — A0 conservative: `TeacherAssignment.room` + solver honors pre-assigned room by singleton eligibility. API round-trip + new test. 282 pytest / npm build green.

### Remaining (Batches 4–6)
4. **Batch 4 — B2 constraints redesign + room UI input** (2 days).
   - Rewrite `CONSTRAINT_DEFS` to ~12 grouped entries + 3 global toggles.
   - Legacy migrator (`frontend/lib/constraint-migrate.ts`) + backend `_normalize_constraint`.
   - Piggyback: add the `room` selector to the assignment row in `ClassCardsStep.tsx` (deferred from Batch 3).
5. **Batch 5 — B3 fidelity report** (2 days). KPI strip, soft-constraint breakdown, AI fix suggestions stub, PDF export.
6. **Batch 6 — Remaining perf** (2–4 days, as needed).
   - **Full A0 completion**: delete `room_bvars` when every session is singleton-eligible; add `room_validator.py`.
   - **A1 model tightening**: singleton start_var fixing, AllDifferent on day for multi-session subjects.
   - **Soft-aware greedy** extension (unblocks A2 on the optimize path).
   - **A4 decomposition** only if benchmark gap vs FET remains.

Total remaining: ~6–8 engineer-days. Tracks are independent and can be split.

---

## 5. Benchmarking protocol

Every phase must be measured against the same datasets, not anecdotally.

- Run `uv run python scripts/benchmark/run_fet_timease_benchmark.py` before starting each phase — record wall-clock, variable count, constraint count per dataset into `benchmark_results/<YYYY-MM-DD>_<phase>.json`.
- Compare to FET's reported time for the same dataset.
- **Never commit a phase that regresses wall-clock by >10% vs the previous phase** without an explicit justification in the commit message.
- The benchmark manifest is built by `scripts/benchmark/build_fet_manifest.py`; FET prefills live in `frontend/data/fet-prefills/`.

---

## 6. Invariants that must not break

- UI strings remain French; code identifiers/docstrings English (`CLAUDE.md`).
- Type hints on every function.
- Logging via `logging.getLogger(__name__)`, never `print()`.
- Error messages reference the field name in French.
- No silent fallbacks: wrong input raises with clear message.
- The **class** is the root aggregate (`CLAUDE.md`).
- No new dependencies without justification in `CLAUDE.md`.
- All tests in `tests/` pass. `uv run pytest` green.
- Frontend builds: `cd frontend && npm run build` green.

---

## 7. How to resume this work mid-stream

1. Run `uv run pytest && cd frontend && npm run build` — confirm green baseline.
2. Check `git log --oneline -20` for recent work.
3. Read the latest entry under **Progress log** below to see which phase is in flight.
4. Open the files listed under that phase and continue.

---

## 8. Progress log

Append one bullet per working session. Keep entries ≤2 lines.

- 2026-04-15: Plan drafted. Baseline `uv run pytest` + `npm run build` green.
- 2026-04-15: **Batch 1** — ChipInput component + solver A3/A5 hygiene. 281 tests / build green.
- 2026-04-15: **Batch 2** — Extracted greedy to `greedy.py`. Optimize-path hints broke a soft-constraint test; reverted to fast-path-only (matches pre-existing behavior). 281 / build green.
- 2026-04-15: **Batch 3 (scoped down)** — `TeacherAssignment.room` + singleton-eligibility shortcut. Full `room_bvars` removal deferred. 282 / build green.
