"""
Timetable solver for TIMEASE — Phase 3.

Scope
-----
Assigns subjects, teachers, AND rooms to (day, time slot) pairs for every
class.  Soft preferences are not yet modelled.

What CP-SAT is
--------------
CP-SAT (Constraint Programming - SATisfiability) is an exact solver.
You describe the problem as a set of *variables* (decisions to make) and
*constraints* (rules those decisions must obey), then call solve().
The solver internally combines SAT techniques, propagation, and linear
relaxation to find a feasible — or provably optimal — assignment.

Key idea: you never write search loops.  You declare *what* must hold, and
the solver figures out *how* to make it hold.

Three-layer variable design
----------------------------
Layer 1 — Session placement:
    x[class, subject, k, day, s] = 1  iff session k starts at slot s on day d

Layer 2 — Teacher assignment:
    t[class, subject, k, day, s, teacher] = 1
        iff that teacher teaches session k of that subject for that class

Layer 3 — Room assignment:
    r[class, subject, k, day, s, room] = 1
        iff that room is used for session k of that subject for that class

Layers 2 and 3 are each linked to Layer 1 by:
    sum_teacher( t[…, teacher] ) == x[…]
    sum_room(    r[…, room]    ) == x[…]   (only when subject.needs_room is True)

These equalities enforce:
  • If the session is scheduled (x=1): exactly one teacher AND one room.
  • If it is not scheduled (x=0): neither teacher nor room is assigned.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import NamedTuple

from ortools.sat.python import cp_model

from timease.engine.constraints import ConstraintBuilder
from timease.engine.models import (
    Assignment,
    CurriculumEntry,
    SchoolData,
    Teacher,
    TimetableResult,
)

logger = logging.getLogger(__name__)

# Hard wall-clock limit given to the solver.
SOLVE_TIME_LIMIT_SECONDS = 300


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


def _session_overlaps_unavailability(
    session_start: str,
    session_end: str,
    unavail: dict,
) -> bool:
    """
    Return True if a session [session_start, session_end) overlaps with an
    unavailability window.

    The unavailability dict has the shape:
        {"day": str, "start": str|None, "end": str|None, "session": str|None}

    If both start and end are None the teacher is blocked for the entire day.
    None boundaries are treated as open (00:00 / 23:59).

    Time comparison works correctly on "HH:MM" strings as long as hours are
    zero-padded — which our slot generator always guarantees.
    """
    u_start: str = unavail.get("start") or "00:00"
    u_end: str   = unavail.get("end")   or "23:59"
    # Classic interval overlap: [a,b) ∩ [c,d) ≠ ∅  ⟺  a < d AND c < b
    return session_start < u_end and u_start < session_end


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------

class TimetableSolver:
    """
    CP-SAT based timetable solver for TIMEASE.

    Phase 3 guarantees
    ------------------
    1. Every class's weekly curriculum is scheduled (exact minutes).
    2. No class is ever in two places at the same time.
    3. Every scheduled session has exactly one qualified teacher.
    4. No teacher is in two places at the same time.
    5. Teacher weekly hours do not exceed their declared maximum.
    6. Teachers are not assigned to slots they marked as unavailable.
    7. Every session needing a room has exactly one assigned room.
    8. Room capacity is sufficient for the class student count.
    9. Subjects with required_room_type only use rooms of that type.
    10. No room is used by two classes at the same time.
    11. Subjects with needs_room=False receive room=None.

    Not yet handled: soft preferences (morning slots, spread, balance).
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
        # ==================================================================
        curriculum_by_level: dict[str, list[CurriculumEntry]] = defaultdict(list)
        for entry in data.curriculum:
            curriculum_by_level[entry.level].append(entry)

        # ==================================================================
        # Step 2b — Index teachers by subject
        #
        # For each subject name, collect which Teacher objects are qualified
        # to teach it.  This lookup drives both variable creation (which
        # teacher vars to create) and qualification filtering.
        # ==================================================================
        teachers_by_subject: dict[str, list[Teacher]] = defaultdict(list)
        for teacher in data.teachers:
            for subject in teacher.subjects:
                teachers_by_subject[subject].append(teacher)

        # ==================================================================
        # Step 2c — Index subjects and classes for room eligibility
        #
        # subject_map lets us look up needs_room and required_room_type in O(1).
        # class_student_count lets us filter out rooms that are too small.
        # ==================================================================
        subject_map = {s.name: s for s in data.subjects}
        class_student_count = {c.name: c.student_count for c in data.classes}

        # ==================================================================
        # Step 3 — Create the CP-SAT model
        # ==================================================================
        model = cp_model.CpModel()

        # ==================================================================
        # Step 4 — Create Layer 1 variables: session placement
        #
        # x[class, subject, k, day, s]  — BoolVar
        #   = 1 iff session k of this subject for this class starts at slot s
        #
        # Also creates one OptionalIntervalVar per x-var for the class
        # no-overlap constraint.
        # ==================================================================

        # (class_name, subject_name, session_k, day, slot) → BoolVar
        x: dict[tuple[str, str, int, str, int], cp_model.IntVar] = {}

        # (class_name, day) → list[IntervalVar]  — for class no-overlap
        intervals_per_class_day: dict[
            tuple[str, str], list[cp_model.IntervalVar]
        ] = defaultdict(list)

        # (class_name, subject_name, session_k) → list[BoolVar]
        # — for add_exactly_one (each session placed once)
        placements: dict[
            tuple[str, str, int], list[cp_model.IntVar]
        ] = defaultdict(list)

        # (class_name, subject_name) → _SessionSpec  — reused later
        spec_for: dict[tuple[str, str], _SessionSpec] = {}

        total_x_vars = 0
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
                            bvar = model.new_bool_var(
                                f"x|{school_class.name}|{entry.subject}|k{k}|{day}|s{s}"
                            )
                            key = (school_class.name, entry.subject, k, day, s)
                            x[key] = bvar
                            placements[(school_class.name, entry.subject, k)].append(bvar)
                            total_x_vars += 1

                            interval = model.new_optional_interval_var(
                                start=s,
                                size=spec.duration_slots,
                                end=s + spec.duration_slots,
                                is_present=bvar,
                                name=f"iv|{school_class.name}|{entry.subject}|k{k}|{day}|s{s}",
                            )
                            intervals_per_class_day[(school_class.name, day)].append(interval)

        # ==================================================================
        # Step 4b — Create Layer 2 variables: teacher assignment
        #
        # For every x-variable, and for every teacher qualified to teach that
        # subject, create one BoolVar:
        #
        #   t[class, subject, k, day, s, teacher] = 1
        #       iff that teacher teaches session k at (day, s).
        #
        # We skip creating a variable if the teacher is unavailable during
        # the entire session — this is equivalent to adding the constraint
        # t[…] == 0, but avoids creating a variable that will immediately
        # be forced to 0.
        #
        # We also create an OptionalIntervalVar for each teacher variable so
        # that CP-SAT's no-overlap propagator can ensure a teacher is never
        # in two places at once (Step 5f).
        #
        # Secondary indices built here for the constraint steps below:
        #
        #   teacher_vars_for_session[(cn, sn, k, day, s)]
        #       All teacher BoolVars for this specific placement.
        #       Used in Step 5d to link placement → teacher.
        #
        #   teacher_vars_by_teacher[teacher_name]
        #       All (BoolVar, duration_slots) pairs for a teacher.
        #       Used in Step 5e for the max-hours constraint.
        #
        #   teacher_intervals_by_day[(teacher_name, day)]
        #       Interval vars for a teacher on one day.
        #       Used in Step 5f for teacher no-overlap.
        # ==================================================================

        # (class_name, subject_name, k, day, s, teacher_name) → BoolVar
        teacher_x: dict[tuple[str, str, int, str, int, str], cp_model.IntVar] = {}

        teacher_vars_for_session: dict[
            tuple[str, str, int, str, int], list[cp_model.IntVar]
        ] = defaultdict(list)

        teacher_vars_by_teacher: dict[
            str, list[tuple[cp_model.IntVar, int]]   # (bvar, duration_slots)
        ] = defaultdict(list)

        teacher_intervals_by_day: dict[
            tuple[str, str], list[cp_model.IntervalVar]
        ] = defaultdict(list)

        total_t_vars = 0
        for (class_name, subject_name, k, day, s), x_var in x.items():
            spec = spec_for[(class_name, subject_name)]
            session_start, _  = day_slot_times[day][s]
            _, session_end    = day_slot_times[day][s + spec.duration_slots - 1]

            qualified = teachers_by_subject.get(subject_name, [])

            for teacher in qualified:
                # --- Unavailability filter --------------------------------
                # If this session overlaps ANY of the teacher's unavailable
                # windows on this day, skip creating the variable entirely.
                # This is more efficient than creating the var and forcing
                # it to 0 with a constraint.
                blocked = any(
                    unavail["day"] == day
                    and _session_overlaps_unavailability(
                        session_start, session_end, unavail
                    )
                    for unavail in teacher.unavailable_slots
                )
                if blocked:
                    continue

                # --- BoolVar ----------------------------------------------
                t_var = model.new_bool_var(
                    f"t|{class_name}|{subject_name}|k{k}|{day}|s{s}|{teacher.name}"
                )
                t_key = (class_name, subject_name, k, day, s, teacher.name)
                teacher_x[t_key] = t_var

                teacher_vars_for_session[(class_name, subject_name, k, day, s)].append(t_var)
                teacher_vars_by_teacher[teacher.name].append((t_var, spec.duration_slots))
                total_t_vars += 1

                # --- OptionalIntervalVar ----------------------------------
                # Same timeline (per-day slot indices) as the class intervals.
                # is_present = t_var: interval only "exists" when teacher
                # teaches this session.
                t_interval = model.new_optional_interval_var(
                    start=s,
                    size=spec.duration_slots,
                    end=s + spec.duration_slots,
                    is_present=t_var,
                    name=f"tiv|{teacher.name}|{class_name}|{subject_name}|k{k}|{day}|s{s}",
                )
                teacher_intervals_by_day[(teacher.name, day)].append(t_interval)

        logger.info(
            "Created %d session vars + %d teacher vars",
            total_x_vars, total_t_vars,
        )

        # ==================================================================
        # Step 4c — Create Layer 3 variables: room assignment
        #
        # For every session placement that needs a room, and for every
        # eligible room, create one BoolVar:
        #
        #   r[class, subject, k, day, s, room] = 1
        #       iff that room hosts session k of this subject for this class.
        #
        # A room is eligible for a placement iff ALL of the following hold:
        #   1. subject.needs_room is True  (EPS etc. skip room assignment)
        #   2. room.capacity >= class.student_count
        #   3. If subject.required_room_type is set, that type must appear
        #      in room.types  (e.g. SVT needs "Laboratoire")
        #
        # Secondary indices mirror the teacher-layer indices:
        #   room_vars_for_session[(cn, sn, k, day, s)]  → used in Step 5g
        #   room_intervals_by_day[(room_name, day)]      → used in Step 5h
        # ==================================================================

        # (class_name, subject_name, k, day, s, room_name) → BoolVar
        room_x: dict[tuple[str, str, int, str, int, str], cp_model.IntVar] = {}

        room_vars_for_session: dict[
            tuple[str, str, int, str, int], list[cp_model.IntVar]
        ] = defaultdict(list)

        room_intervals_by_day: dict[
            tuple[str, str], list[cp_model.IntervalVar]
        ] = defaultdict(list)

        total_r_vars = 0
        for (class_name, subject_name, k, day, s), x_var in x.items():
            subject = subject_map[subject_name]

            # Subjects that don't need a room (outdoor EPS, etc.) are skipped
            # entirely — no room variable, no room constraint, room=None in output.
            if not subject.needs_room:
                continue

            spec          = spec_for[(class_name, subject_name)]
            student_count = class_student_count[class_name]
            required_type = subject.required_room_type

            for room in data.rooms:
                # --- Capacity filter ------------------------------------------
                # A room with fewer seats than students is never eligible.
                if room.capacity < student_count:
                    continue

                # --- Room-type filter -----------------------------------------
                # Two cases:
                #
                # required_type is set (e.g. "Laboratoire" for SVT):
                #   The room must carry that type.  A room can carry multiple
                #   types (e.g. ["Laboratoire", "Salle standard"]), so it can
                #   still serve double duty.
                #
                # required_type is None (general subjects — Maths, Français…):
                #   Only rooms that carry "Salle standard" are eligible.
                #   This prevents specialty rooms (Laboratoire, EPS terrain)
                #   from being allocated to regular classes just because their
                #   large capacity makes them technically big enough.
                if required_type is not None:
                    if required_type not in room.types:
                        continue
                else:
                    if "Salle standard" not in room.types:
                        continue

                # --- BoolVar --------------------------------------------------
                r_var = model.new_bool_var(
                    f"r|{class_name}|{subject_name}|k{k}|{day}|s{s}|{room.name}"
                )
                room_x[(class_name, subject_name, k, day, s, room.name)] = r_var
                room_vars_for_session[(class_name, subject_name, k, day, s)].append(r_var)
                total_r_vars += 1

                # --- OptionalIntervalVar --------------------------------------
                # Same per-day slot timeline as class and teacher intervals.
                # is_present=r_var: the interval only "exists" when this room
                # is chosen for this placement.
                r_interval = model.new_optional_interval_var(
                    start=s,
                    size=spec.duration_slots,
                    end=s + spec.duration_slots,
                    is_present=r_var,
                    name=f"riv|{room.name}|{class_name}|{subject_name}|k{k}|{day}|s{s}",
                )
                room_intervals_by_day[(room.name, day)].append(r_interval)

        logger.info(
            "Created %d room vars (%d placements have eligible rooms)",
            total_r_vars, len(room_vars_for_session),
        )

        # ==================================================================
        # Step 5a — Constraint: each session is scheduled exactly once
        #
        # add_exactly_one(literals): exactly one BoolVar in the list is 1.
        # Applied per (class, subject, session_k): session k must be placed
        # on exactly one (day, slot) combination.
        # ==================================================================
        conflicts: list[dict] = []

        for (class_name, subject_name, k), pvars in placements.items():
            if not pvars:
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
        # add_no_overlap(intervals): no two present intervals may share time.
        # One constraint per (class, day).
        # ==================================================================
        no_overlap_count = 0
        for (class_name, day), ivs in intervals_per_class_day.items():
            if len(ivs) > 1:
                model.add_no_overlap(ivs)
                no_overlap_count += 1

        logger.info("Added %d class no-overlap constraints", no_overlap_count)

        # ==================================================================
        # Step 5c — add_at_most_one: illustrative per-slot view (redundant)
        #
        # Even though add_no_overlap already handles no-double-booking, we
        # add per-slot add_at_most_one constraints here to demonstrate the
        # slot-level reasoning.  CP-SAT detects the redundancy harmlessly.
        # ==================================================================
        for school_class in data.classes:
            entries = curriculum_by_level.get(school_class.level, [])
            for day in tc.days:
                n_slots = len(day_slot_times[day])
                for t_idx in range(n_slots):
                    covering: list[cp_model.IntVar] = []
                    for entry in entries:
                        spec = spec_for.get((school_class.name, entry.subject))
                        if spec is None:
                            continue
                        for k in range(spec.sessions_per_week):
                            for s in range(
                                max(0, t_idx - spec.duration_slots + 1), t_idx + 1
                            ):
                                key = (school_class.name, entry.subject, k, day, s)
                                if key in x:
                                    covering.append(x[key])
                    if len(covering) > 1:
                        model.add_at_most_one(covering)

        # ==================================================================
        # Step 5d — Constraint: link session placement to teacher assignment
        #
        # For each possible session placement (class, subject, k, day, s):
        #
        #   sum( t[…, teacher] for all qualified teachers ) == x[…]
        #
        # When x = 1 (session scheduled): the sum must equal 1, so exactly
        # one teacher var is 1 → exactly one teacher teaches it.
        #
        # When x = 0 (session not scheduled at this slot): the sum must
        # equal 0 → no teacher is assigned to a cancelled placement.
        #
        # Why not add_exactly_one here?
        # add_exactly_one is unconditional.  We need the count to equal x,
        # which varies.  A linear equality (sum == x) captures this cleanly.
        # CP-SAT handles linear equalities between BoolVars efficiently.
        #
        # Edge case: if no qualified teacher variable exists for a placement
        # (all teachers blocked by unavailability), sum=0 forces x=0.  If
        # this applies to ALL placements for a session, the add_exactly_one
        # from Step 5a will conflict → INFEASIBLE, correctly detected.
        # ==================================================================
        for key, x_var in x.items():
            class_name, subject_name, k, day, s = key
            tvars = teacher_vars_for_session.get(key, [])

            if not tvars:
                # No available teacher for this placement.
                # Force x=0: this placement cannot be used.
                model.add(x_var == 0)
                logger.debug(
                    "No available teacher for %s / %s on %s slot %d — placement disabled",
                    class_name, subject_name, day, s,
                )
            else:
                # sum(teacher vars) == x_var
                model.add(sum(tvars) == x_var)

        # ==================================================================
        # Step 5e — Constraint: teacher max hours per week
        #
        # For each teacher, the total minutes they are assigned must not
        # exceed their declared max_hours_per_week.
        #
        # total_assigned_minutes = sum(t_var * session_duration_minutes)
        #                        = sum(t_var * duration_slots * base_unit)
        #
        # Since t_var is a BoolVar (0 or 1), this is a weighted sum of
        # Boolean variables — a standard linear constraint in CP-SAT.
        #
        # Note: duration_slots * base_unit is a constant for each term,
        # so CP-SAT can treat it as a fixed coefficient.
        # ==================================================================
        for teacher in data.teachers:
            pairs = teacher_vars_by_teacher.get(teacher.name, [])
            if not pairs:
                continue

            # Build: sum( t_var * duration_minutes )
            total_minutes = sum(
                t_var * (duration_slots * base_unit)
                for t_var, duration_slots in pairs
            )
            model.add(total_minutes <= teacher.max_hours_per_week * 60)

        logger.info(
            "Added max-hours constraints for %d teachers",
            len(teacher_vars_by_teacher),
        )

        # ==================================================================
        # Step 5f — Constraint: no teacher teaches two classes simultaneously
        #
        # Same technique as Step 5b but applied per (teacher, day) instead
        # of per (class, day).
        #
        # Each teacher_interval is present only when the corresponding t_var
        # is 1.  add_no_overlap guarantees no two present intervals overlap
        # on the same day for the same teacher.
        # ==================================================================
        teacher_no_overlap_count = 0
        for (teacher_name, day), ivs in teacher_intervals_by_day.items():
            if len(ivs) > 1:
                model.add_no_overlap(ivs)
                teacher_no_overlap_count += 1

        logger.info(
            "Added %d teacher no-overlap constraints",
            teacher_no_overlap_count,
        )

        # ==================================================================
        # Step 5g — Constraint: link session placement to room assignment
        #
        # For each placement that needs a room:
        #
        #   sum( r[…, room] for all eligible rooms ) == x[…]
        #
        # Exactly the same pattern as the teacher link (Step 5d):
        #   x=1 → exactly one room is assigned to the session.
        #   x=0 → no room is assigned (all room vars for this placement = 0).
        #
        # If no eligible room exists for a placement (all rooms too small or
        # wrong type), that placement is disabled (x forced to 0).
        # ==================================================================
        room_disabled = 0
        for key, x_var in x.items():
            class_name, subject_name, k, day, s = key
            subject = subject_map[subject_name]

            if not subject.needs_room:
                # No room required — room will remain None in the output.
                continue

            rvars = room_vars_for_session.get(key, [])
            if not rvars:
                model.add(x_var == 0)
                room_disabled += 1
                logger.debug(
                    "No eligible room for %s / %s on %s slot %d — placement disabled",
                    class_name, subject_name, day, s,
                )
            else:
                model.add(sum(rvars) == x_var)

        if room_disabled:
            logger.warning(
                "%d placements disabled: no room satisfies capacity + type requirements",
                room_disabled,
            )

        # ==================================================================
        # Step 5h — Constraint: each room hosts at most one class at a time
        #
        # One add_no_overlap per (room, day) over all optional interval vars
        # for that room on that day.  The pattern is identical to Steps 5b
        # (class no-overlap) and 5f (teacher no-overlap).
        #
        # A room that only ever appears in one placement per day needs no
        # constraint — the `if len(ivs) > 1` guard handles this.
        # ==================================================================
        room_no_overlap_count = 0
        for (room_name, day), ivs in room_intervals_by_day.items():
            if len(ivs) > 1:
                model.add_no_overlap(ivs)
                room_no_overlap_count += 1

        logger.info("Added %d room no-overlap constraints", room_no_overlap_count)

        # ==================================================================
        # Step 5i — Apply user-defined hard constraints
        #
        # ConstraintBuilder translates each Constraint object from SchoolData
        # into one or more CP-SAT model constraints.  Only hard constraints
        # are applied here; soft constraints are handled separately (not yet
        # implemented).
        #
        # The builder receives the full variable maps so it can reference
        # any x or teacher_x variable without re-indexing.
        # ==================================================================
        hard_constraints = [c for c in data.constraints if c.type == "hard"]
        if hard_constraints:
            logger.info("Applying %d user-defined hard constraints...", len(hard_constraints))
            builder = ConstraintBuilder(
                model=model,
                data=data,
                x=x,
                teacher_x=teacher_x,
                spec_for=spec_for,
                day_slot_times=day_slot_times,
                curriculum_by_level=curriculum_by_level,
            )
            cb_warnings = builder.apply_all(hard_constraints)
            for w in cb_warnings:
                logger.warning("ConstraintBuilder: %s", w)
        else:
            logger.info("No hard constraints to apply.")

        # ==================================================================
        # Step 6 — Solve
        #
        # Status codes:
        #   cp_model.OPTIMAL    — best possible solution, proven.
        #   cp_model.FEASIBLE   — valid solution, not proven optimal.
        #   cp_model.INFEASIBLE — no solution exists.
        #   cp_model.UNKNOWN    — time limit hit before any solution found.
        # ==================================================================
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = SOLVE_TIME_LIMIT_SECONDS
        solver.parameters.log_search_progress = False

        logger.info(
            "Launching CP-SAT (time limit: %ds, vars: %d session + %d teacher + %d room)...",
            SOLVE_TIME_LIMIT_SECONDS, total_x_vars, total_t_vars, total_r_vars,
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
        # Walk every x-variable.  For each placement chosen (value=1), find
        # the teacher variable that is also 1 for that placement.
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

        # Build reverse maps: placement key → chosen teacher / chosen room.
        chosen_teacher: dict[tuple[str, str, int, str, int], str] = {}
        for (cn, sn, k, day, s, teacher_name), t_var in teacher_x.items():
            if solver.value(t_var) == 1:
                chosen_teacher[(cn, sn, k, day, s)] = teacher_name

        chosen_room: dict[tuple[str, str, int, str, int], str] = {}
        for (cn, sn, k, day, s, room_name), r_var in room_x.items():
            if solver.value(r_var) == 1:
                chosen_room[(cn, sn, k, day, s)] = room_name

        assignments: list[Assignment] = []

        for (class_name, subject_name, k, day, s), x_var in x.items():
            if solver.value(x_var) != 1:
                continue

            spec         = spec_for[(class_name, subject_name)]
            start_time, _ = day_slot_times[day][s]
            _, end_time   = day_slot_times[day][s + spec.duration_slots - 1]
            teacher_name  = chosen_teacher.get((class_name, subject_name, k, day, s), "")
            # room is None for subjects with needs_room=False (EPS etc.)
            room_name     = chosen_room.get((class_name, subject_name, k, day, s))

            assignments.append(Assignment(
                school_class=class_name,
                subject=subject_name,
                teacher=teacher_name,
                room=room_name,
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
