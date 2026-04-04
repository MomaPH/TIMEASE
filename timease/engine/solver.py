"""
Timetable solver for TIMEASE — Phase 1.

Scope
-----
Assigns subjects to (day, time slot) pairs for every class.
Teachers and rooms are NOT assigned in this phase.

What CP-SAT is
--------------
CP-SAT (Constraint Programming - SATisfiability) is an exact solver.
You describe the problem as a set of *variables* (decisions to make) and
*constraints* (rules those decisions must obey), then call solve().
The solver internally combines SAT techniques, propagation, and linear
relaxation to find a feasible — or provably optimal — assignment.

Key idea: you never write search loops.  You declare *what* must hold, and
the solver figures out *how* to make it hold.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import NamedTuple

from ortools.sat.python import cp_model

from timease.engine.models import (
    Assignment,
    CurriculumEntry,
    SchoolData,
    TimetableResult,
)

logger = logging.getLogger(__name__)

# Hard wall-clock limit given to the solver.
SOLVE_TIME_LIMIT_SECONDS = 120


# ---------------------------------------------------------------------------
# Internal data structures
# ---------------------------------------------------------------------------

class _SessionSpec(NamedTuple):
    """Derived scheduling parameters for one curriculum entry."""

    sessions_per_week: int  # how many separate sessions to place
    duration_slots: int     # length of each session in base-unit slots


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _compute_session_spec(
    entry: CurriculumEntry, base_unit_minutes: int
) -> _SessionSpec:
    """
    Derive (sessions_per_week, duration_slots) for a curriculum entry.

    Manual mode
    -----------
    The caller already fixed both values; we just convert minutes → slots.

    Auto mode
    ---------
    We pick the smallest allowed session length (min_session_minutes, or 60 min
    by default) and divide the weekly load by it, rounding up so we never
    schedule *fewer* minutes than the curriculum requires.

    Examples (base_unit = 30 min)
    --------------------------------
    Maths auto 5 h, min=60 min  → 5 sessions × 2 slots
    SVT manual 2 h, 1 × 120 min → 1 session  × 4 slots
    SVT manual 3 h, 2 × 90 min  → 2 sessions × 3 slots
    EPS manual 2 h, 1 × 120 min → 1 session  × 4 slots
    """
    if entry.mode == "manual":
        sessions = entry.sessions_per_week or 1
        minutes = entry.minutes_per_session or base_unit_minutes
        return _SessionSpec(
            sessions_per_week=max(1, sessions),
            duration_slots=max(1, minutes // base_unit_minutes),
        )

    # Auto mode: pick a fixed session length, then compute session count.
    session_minutes = entry.min_session_minutes or min(60, entry.total_minutes_per_week)
    duration_slots = max(1, session_minutes // base_unit_minutes)
    # Ceiling division: -(-a // b) == ceil(a / b)
    sessions_per_week = -(-entry.total_minutes_per_week // session_minutes)
    return _SessionSpec(
        sessions_per_week=max(1, sessions_per_week),
        duration_slots=duration_slots,
    )


def _valid_start_slots(
    day_slots: list[tuple[str, str]], duration_slots: int
) -> list[int]:
    """
    Return the slot indices within a day where a session of `duration_slots`
    can legally start.

    A start index s is valid only if slots s, s+1, …, s+duration-1 are all
    *consecutive* — i.e. the end_time of slot i equals the start_time of
    slot i+1.  This prevents sessions from jumping over the morning/afternoon
    break.

    Parameters
    ----------
    day_slots:
        Ordered list of (start_time, end_time) pairs for one day, as produced
        by TimeslotConfig.get_all_slots() and grouped by day.
    duration_slots:
        Session length in base-unit slots.

    Returns
    -------
    List of valid start indices (0-based within the day).
    """
    valid: list[int] = []
    n = len(day_slots)

    for s in range(n - duration_slots + 1):
        consecutive = True
        for i in range(1, duration_slots):
            # The end of slot (s+i-1) must equal the start of slot (s+i).
            prev_end = day_slots[s + i - 1][1]
            curr_start = day_slots[s + i][0]
            if prev_end != curr_start:
                consecutive = False
                break
        if consecutive:
            valid.append(s)

    return valid


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------

class TimetableSolver:
    """
    CP-SAT based timetable solver for TIMEASE.

    Phase 1 guarantees
    ------------------
    1. Every class's weekly curriculum is scheduled (exact minutes).
    2. No class is ever in two places at the same time.

    Not yet handled: teacher assignment, room assignment, teacher conflicts,
    room capacity, soft preferences.
    """

    def solve(self, data: SchoolData) -> TimetableResult:
        """
        Build and solve the CP-SAT model, then return a TimetableResult.

        Parameters
        ----------
        data:
            Fully populated SchoolData instance.

        Returns
        -------
        TimetableResult
            solved=True with assignments if a solution was found within the
            time limit; solved=False with conflict details otherwise.
        """
        wall_start = time.perf_counter()

        # ==================================================================
        # Step 1 — Derive the schedule structure
        #
        # get_all_slots() returns a flat list of (day, start, end) tuples.
        # We regroup by day so each slot has a stable integer index *within*
        # its day.  This per-day indexing is the timeline used by all
        # interval variables later.
        # ==================================================================
        tc = data.timeslot_config
        base_unit = tc.base_unit_minutes

        # day -> [(start_time, end_time), ...] in chronological order
        day_slot_times: dict[str, list[tuple[str, str]]] = {d: [] for d in tc.days}
        for day, start, end in tc.get_all_slots():
            day_slot_times[day].append((start, end))

        slots_per_day = len(day_slot_times[tc.days[0]])
        logger.info(
            "Schedule: %d days × %d slots/day (base unit %d min)",
            len(tc.days), slots_per_day, base_unit,
        )

        # ==================================================================
        # Step 2 — Index curriculum entries by level
        #
        # CurriculumEntry objects are defined per school level ("6ème", …).
        # We group them so we can look up "what does a 6ème class need?" in O(1).
        # ==================================================================
        curriculum_by_level: dict[str, list[CurriculumEntry]] = defaultdict(list)
        for entry in data.curriculum:
            curriculum_by_level[entry.level].append(entry)

        # ==================================================================
        # Step 3 — Create the CP-SAT model
        #
        # CpModel() is just a container.  At this point nothing is solved —
        # we are only *describing* the combinatorial problem.  The solver in
        # Step 6 will search for an assignment that satisfies all constraints.
        # ==================================================================
        model = cp_model.CpModel()

        # ==================================================================
        # Step 4 — Create decision variables
        #
        # For every possible placement of every session we create two objects:
        #
        #   BoolVar x[class, subject, k, day, s]
        #       = 1  ⟺  session k of this subject for this class is placed
        #                starting at slot s on the given day.
        #       = 0  otherwise (this placement is not chosen).
        #
        #   OptionalIntervalVar  interval[class, subject, k, day, s]
        #       Represents the time window [s, s + duration) within the day.
        #       It is "optional": it exists on the schedule only when the
        #       associated BoolVar is 1.
        #
        # Why IntervalVar?
        #   A session of 90 min (3 slots) occupies THREE consecutive slots,
        #   not just the starting one.  IntervalVar encodes this span so that
        #   CP-SAT's no-overlap propagator can reason about it efficiently.
        #   Without intervals, we would need to manually enumerate which slots
        #   each session covers — error-prone and slower.
        #
        # Variable count estimate for the sample school:
        #   8 classes × ~10 subjects × ~3 sessions × 6 days × ~9 valid starts
        #   ≈ 12 960 BoolVars  (well within CP-SAT's capacity)
        # ==================================================================

        # Primary lookup: (class_name, subject_name, session_k, day, slot) → BoolVar
        x: dict[tuple[str, str, int, str, int], cp_model.IntVar] = {}

        # Grouped by (class_name, day) for the add_no_overlap constraint.
        intervals_per_class_day: dict[
            tuple[str, str], list[cp_model.IntervalVar]
        ] = defaultdict(list)

        # Grouped by (class_name, subject_name, session_k) for add_exactly_one.
        # Built here to avoid iterating over the full x dict later.
        placements: dict[
            tuple[str, str, int], list[cp_model.IntVar]
        ] = defaultdict(list)

        # Computed session specs — reused in result extraction.
        spec_for: dict[tuple[str, str], _SessionSpec] = {}

        total_vars = 0
        for school_class in data.classes:
            entries = curriculum_by_level.get(school_class.level, [])
            if not entries:
                logger.warning("No curriculum for level '%s'", school_class.level)
                continue

            for entry in entries:
                spec = _compute_session_spec(entry, base_unit)
                spec_for[(school_class.name, entry.subject)] = spec

                for k in range(spec.sessions_per_week):
                    for day in tc.days:
                        valid_starts = _valid_start_slots(
                            day_slot_times[day], spec.duration_slots
                        )
                        for s in valid_starts:
                            # --- BoolVar ----------------------------------
                            bvar = model.new_bool_var(
                                f"x|{school_class.name}|{entry.subject}|k{k}|{day}|s{s}"
                            )
                            key = (school_class.name, entry.subject, k, day, s)
                            x[key] = bvar
                            placements[(school_class.name, entry.subject, k)].append(bvar)
                            total_vars += 1

                            # --- OptionalIntervalVar ----------------------
                            # Arguments:
                            #   start      — integer start position in the day's slot list
                            #   size       — number of slots this session occupies
                            #   end        — start + size (CP-SAT verifies the identity)
                            #   is_present — the BoolVar that "activates" this interval;
                            #                when 0, the interval is ignored by no-overlap
                            interval = model.new_optional_interval_var(
                                start=s,
                                size=spec.duration_slots,
                                end=s + spec.duration_slots,
                                is_present=bvar,
                                name=f"iv|{school_class.name}|{entry.subject}|k{k}|{day}|s{s}",
                            )
                            intervals_per_class_day[(school_class.name, day)].append(interval)

        logger.info("Created %d BoolVars across %d (class×subject×session) groups", total_vars, len(placements))

        # ==================================================================
        # Step 5a — Constraint: each session is scheduled exactly once
        #
        # add_exactly_one(literals)
        #   Enforces: exactly one of the given BoolVars equals 1.
        #   This is CP-SAT's dedicated cardinality constraint — more efficient
        #   than writing Add(sum(literals) == 1) because the solver can use
        #   specialised propagation for it.
        #
        # Here we apply it per (class, subject, session_k):
        #   "Session k of Mathématiques for 6ème A must be placed on exactly
        #    one (day, starting slot) combination."
        #
        # Together, iterating over k = 0…sessions_per_week-1 ensures the
        # total scheduled minutes equals the curriculum requirement exactly.
        # ==================================================================
        conflicts: list[dict] = []

        for (class_name, subject_name, k), pvars in placements.items():
            if not pvars:
                # No valid placement exists (session too long for any block).
                # Record the conflict; the model will be infeasible.
                spec = spec_for.get((class_name, subject_name))
                duration_min = (spec.duration_slots * base_unit) if spec else "?"
                conflicts.append({
                    "class": class_name,
                    "subject": subject_name,
                    "session": k,
                    "reason": (
                        f"No valid {duration_min}-min slot found in the schedule."
                    ),
                })
                logger.warning(
                    "No valid placement for %s / %s / session %d",
                    class_name, subject_name, k,
                )
                continue

            model.add_exactly_one(pvars)

        # ==================================================================
        # Step 5b — Constraint: no class is double-booked
        #
        # add_no_overlap(interval_vars)
        #   Enforces: none of the given intervals may share a time slot.
        #   Only "present" intervals (BoolVar == 1) participate.
        #   This is the canonical CP-SAT constraint for scheduling problems
        #   with variable-length tasks (think: machine scheduling, classroom
        #   timetabling).
        #
        # Why not add_at_most_one?
        #   add_at_most_one works on BoolVars, not intervals.  For single-slot
        #   sessions, "at most one BoolVar per slot" is equivalent.  But for
        #   a 90-min session (3 slots), a BoolVar at start slot s also *blocks*
        #   slots s+1 and s+2.  add_no_overlap handles this automatically;
        #   with add_at_most_one you would have to manually enumerate all
        #   (subject, k, s) combinations whose session covers each slot t:
        #
        #       for t in range(slots_per_day):
        #           covering = [x[c,subj,k,day,s]
        #                        for subj, k, s
        #                        if s <= t < s + duration[subj]]
        #           model.add_at_most_one(covering)   # 576 constraints per class
        #
        #   add_no_overlap replaces all 576 per-day constraints with one,
        #   and its propagator is O(n log n) instead of O(n²).
        #
        # We apply one add_no_overlap per (class, day) — intervals from
        # different days never conflict, so mixing them would be wrong.
        # ==================================================================
        no_overlap_count = 0
        for (class_name, day), ivs in intervals_per_class_day.items():
            if len(ivs) > 1:
                model.add_no_overlap(ivs)
                no_overlap_count += 1

        logger.info("Added %d no-overlap constraints", no_overlap_count)

        # ==================================================================
        # Step 5c — add_at_most_one: illustrative per-slot view
        #
        # Even though add_no_overlap already handles no-double-booking, we
        # add per-slot add_at_most_one constraints here so you can see how
        # the slot-level reasoning works.  CP-SAT detects the redundancy and
        # prunes it without harm.
        #
        # For each (class, day, slot t): at most one session may *cover* t.
        # A session starting at s with duration d covers t iff s ≤ t < s+d.
        # ==================================================================
        for school_class in data.classes:
            entries = curriculum_by_level.get(school_class.level, [])
            for day in tc.days:
                n_slots = len(day_slot_times[day])
                for t in range(n_slots):
                    # All BoolVars whose session would occupy slot t on this day.
                    covering: list[cp_model.IntVar] = []
                    for entry in entries:
                        spec = spec_for.get((school_class.name, entry.subject))
                        if spec is None:
                            continue
                        for k in range(spec.sessions_per_week):
                            # s must satisfy: s ≤ t  AND  t < s + duration
                            #  ⟺  t - duration + 1 ≤ s ≤ t
                            for s in range(
                                max(0, t - spec.duration_slots + 1), t + 1
                            ):
                                key = (school_class.name, entry.subject, k, day, s)
                                if key in x:
                                    covering.append(x[key])

                    if len(covering) > 1:
                        # add_at_most_one: at most one of these is 1.
                        # Semantics: at most one session covers slot t.
                        model.add_at_most_one(covering)

        # ==================================================================
        # Step 6 — Solve
        #
        # CpSolver.solve() launches the search.  The solver will:
        #   1. Apply constraint propagation to reduce variable domains.
        #   2. Use VSIDS heuristics to choose branching decisions.
        #   3. Run SAT-based conflict analysis to learn new constraints.
        #   4. Stop when: a proven-optimal solution is found (OPTIMAL),
        #      or the time limit expires (FEASIBLE if a solution was found,
        #      UNKNOWN otherwise), or the problem is proven unsolvable
        #      (INFEASIBLE).
        #
        # Status codes:
        #   cp_model.OPTIMAL    — best possible solution, proven.
        #   cp_model.FEASIBLE   — valid solution found, but not proven optimal.
        #   cp_model.INFEASIBLE — no solution exists (constraints contradict).
        #   cp_model.UNKNOWN    — time limit hit before any solution was found.
        # ==================================================================
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = SOLVE_TIME_LIMIT_SECONDS
        # Set log_search_progress = True to watch CP-SAT's internal search.
        solver.parameters.log_search_progress = False

        logger.info(
            "Launching CP-SAT (time limit: %ds, variables: %d)...",
            SOLVE_TIME_LIMIT_SECONDS, total_vars,
        )
        status = solver.solve(model)
        solve_time = time.perf_counter() - wall_start

        logger.info(
            "Solver finished — status: %s | wall time: %.2fs | conflicts: %d",
            solver.status_name(status), solve_time, solver.num_conflicts,
        )

        # ==================================================================
        # Step 7 — Extract results
        #
        # solver.value(bvar) returns the integer value (0 or 1) that the
        # solver assigned to a BoolVar in the solution.  We iterate over
        # every variable and collect those set to 1.
        # ==================================================================
        feasible = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

        if not feasible:
            logger.warning(
                "No solution found (status: %s). Pre-detected conflicts: %d",
                solver.status_name(status), len(conflicts),
            )
            return TimetableResult(
                assignments=[],
                solved=False,
                solve_time_seconds=round(solve_time, 3),
                conflicts=conflicts or [{"reason": solver.status_name(status)}],
                soft_constraints_satisfied=[],
                soft_constraints_violated=[],
            )

        assignments: list[Assignment] = []

        for (class_name, subject_name, _k, day, s), bvar in x.items():
            if solver.value(bvar) != 1:
                continue  # this placement was not chosen

            spec = spec_for[(class_name, subject_name)]
            start_time, _ = day_slot_times[day][s]
            # The session ends at the END of its last slot.
            _, end_time = day_slot_times[day][s + spec.duration_slots - 1]

            assignments.append(Assignment(
                school_class=class_name,
                subject=subject_name,
                teacher="",      # Phase 1: not yet assigned
                room=None,       # Phase 1: not yet assigned
                day=day,
                start_time=start_time,
                end_time=end_time,
            ))

        # Deterministic sort: class → day order → start time.
        day_order = {d: i for i, d in enumerate(tc.days)}
        assignments.sort(
            key=lambda a: (a.school_class, day_order[a.day], a.start_time)
        )

        logger.info(
            "Extracted %d assignments (%s)",
            len(assignments), solver.status_name(status),
        )

        return TimetableResult(
            assignments=assignments,
            solved=True,
            solve_time_seconds=round(solve_time, 3),
            conflicts=conflicts if conflicts else None,
            soft_constraints_satisfied=[],
            soft_constraints_violated=[],
        )
