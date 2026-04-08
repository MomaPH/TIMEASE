"""
Timetable solver for TIMEASE — Phase 2 logic (Human-in-the-Loop).

Model design
------------
Every curriculum session is represented by ONE IntVar (start_var[i]) on a
global timeline:

    global_slot = day_idx × n_slots_per_day + slot_within_day

The domain of each start_var is pre-filtered for:
  • Physical continuity: session cannot cross morning/afternoon break or day boundary
  • Teacher unavailability
  • Hard domain constraints encoded at build time:
      H1  start_time          — minimum start hour
      H3  day_off             — blocked day or session half
      H5  subject_on_days     — subject restricted to listed days
      H6  subject_not_on_days — subject excluded from listed days
      H7  subject_not_last_slot — cannot occupy last slot of day

Room assignment uses one BoolVar per (session, eligible_room) pair, with
add_exactly_one per session and add_no_overlap per room.

No-overlap constraints use a global timeline:
  • One add_no_overlap per class   — covers ALL days at once
  • One add_no_overlap per teacher — covers ALL days at once
  • One add_no_overlap per room    — optional intervals keyed on room BoolVars

Manual assignment
-----------------
Each (class, subject) pair must be explicitly assigned to a teacher by the
administrator via a TeacherAssignment record. This eliminates teacher-selection
complexity from the CP-SAT engine, ensuring high performance (near-instant
feasibility checks) and absolute adherence to administrative contracts.
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, NamedTuple

from ortools.sat.python import cp_model
from ortools.sat.python.cp_model import Domain

from timease.engine.analysis import SATISFACTION_THRESHOLD, SoftConstraintAnalyzer
from timease.engine.constraints import ConstraintBuilder, SoftConstraintBuilder
from timease.engine.models import (
    Assignment,
    CurriculumEntry,
    SchoolData,
    TimetableResult,
)

logger = logging.getLogger(__name__)

# Hard wall-clock limit.
# Default solver timeout.  30 s is enough for most schools (~100–300 sessions).
# Pass timeout_seconds= to TimetableSolver.solve() to override per call.
DEFAULT_SOLVE_TIMEOUT_SECONDS: int = 30


# ---------------------------------------------------------------------------
# Internal data structures
# ---------------------------------------------------------------------------

class _SessionSpec(NamedTuple):
    """Derived scheduling parameters for one curriculum entry."""
    sessions_per_week: int      # how many separate sessions to place
    duration_slots: int         # length of each session in base-unit slots
    remainder_duration_slots: int = 0  # last session may be shorter (0 = same as all)


@dataclass
class _Session:
    """All static facts about one scheduled session."""
    idx: int                         # unique index, also position in sessions list
    class_name: str
    subject_name: str
    k: int                           # session index within curriculum entry (0-based)
    dur_slots: int                   # session length in base-unit slots
    teacher_name: str                # pre-assigned teacher
    needs_room: bool
    eligible_room_idxs: list[int]    # indices into data.rooms
    student_count: int


# ---------------------------------------------------------------------------
# Helper functions (same as old model — kept identical for correctness)
# ---------------------------------------------------------------------------

def _compute_session_spec(
    entry: CurriculumEntry, base_unit_minutes: int
) -> _SessionSpec:
    """Derive (sessions_per_week, duration_slots) for a curriculum entry.
    All entries are 100% manual.
    """
    sessions = entry.sessions_per_week
    minutes  = entry.minutes_per_session
    return _SessionSpec(
        sessions_per_week=max(1, sessions),
        duration_slots=max(1, minutes // base_unit_minutes),
    )


def _valid_start_slots(
    day_slots: list[tuple[str, str]], duration_slots: int
) -> list[int]:
    """
    Return slot indices within a day where a session of `duration_slots` can
    legally start.  Consecutive-slot check prevents sessions from jumping over
    the morning/afternoon break.
    """
    valid: list[int] = []
    n = len(day_slots)
    for s in range(n - duration_slots + 1):
        ok = all(day_slots[s + i - 1][1] == day_slots[s + i][0]
                 for i in range(1, duration_slots))
        if ok:
            valid.append(s)
    return valid


def _session_overlaps_unavailability(
    session_start: str, session_end: str, unavail: dict
) -> bool:
    """True if [session_start, session_end) overlaps the unavailability window."""
    u_start = unavail.get("start") or "00:00"
    u_end   = unavail.get("end")   or "23:59"
    return session_start < u_end and u_start < session_end


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------

class TimetableSolver:
    """
    CP-SAT timetable solver — compact IntVar model.

    One start_var (IntVar) per session + room BoolVars.
    No-overlap via fixed-size IntervalVars on a global day-indexed timeline.
    Teachers pre-assigned before model build.
    """

    def solve(
        self,
        data: SchoolData,
        timeout_seconds: int = DEFAULT_SOLVE_TIMEOUT_SECONDS,
    ) -> TimetableResult:
        """Build and solve the model; return a TimetableResult.

        Parameters
        ----------
        data:
            The fully validated school data.
        timeout_seconds:
            Wall-clock limit for the CP-SAT solver.  The solver returns the
            best feasible solution found within this budget.
            Default: ``DEFAULT_SOLVE_TIMEOUT_SECONDS`` (30 s).
            Use a shorter value (e.g. 5 s) for quick previews.
        """
        wall_start = time.perf_counter()

        # Auto-derive subjects from curriculum/teachers if not explicitly provided
        data.derive_subjects_if_empty()

        tc        = data.timeslot_config
        base_unit = tc.base_unit_minutes

        # ==================================================================
        # Step 1 — Schedule structure
        # ==================================================================
        # Extract day names from DayConfig objects
        day_names = [d.name for d in tc.days]
        day_slot_times: dict[str, list[tuple[str, str]]] = {d: [] for d in day_names}
        for day, start, end in tc.get_all_slots():
            day_slot_times[day].append((start, end))

        n_slots_per_day = max(len(v) for v in day_slot_times.values())
        day_idx_map     = {d: i for i, d in enumerate(day_names)}

        # Number of morning slots (first session block) — used by soft S5.
        first_day = day_names[0]
        first_day_sessions = tc.days[0].sessions
        morning_end = first_day_sessions[0].end_time if first_day_sessions else "12:00"
        n_morning_slots = sum(
            1 for _st, en in day_slot_times[first_day] if en <= morning_end
        )

        # Session name → SessionConfig for blocked-session checks (aggregate from all days)
        session_name_map: dict[str, SessionConfig] = {}
        for day_config in tc.days:
            for sess in day_config.sessions:
                if sess.name not in session_name_map:
                    session_name_map[sess.name] = sess

        # ==================================================================
        # Step 2 — Curriculum index + session specs (class-based)
        # ==================================================================
        curriculum_by_class: dict[str, list[CurriculumEntry]] = defaultdict(list)
        for entry in data.curriculum:
            curriculum_by_class[entry.school_class].append(entry)

        subject_map = {s.name: s for s in data.subjects}
        teacher_map = {t.name: t for t in data.teachers}

        # Room types that are required by at least one subject — used to
        # determine which rooms are "general purpose" vs "specialized".
        # A room is eligible for a subject with no required_room_type only if
        # it has NO specialized type (prevents lab rooms being used for Maths).
        specialized_room_types: set[str] = {
            s.required_room_type
            for s in data.subjects
            if s.required_room_type is not None
        }

        spec_for: dict[tuple[str, str], _SessionSpec] = {}
        for school_class in data.classes:
            for entry in curriculum_by_class.get(school_class.name, []):
                spec_for[(school_class.name, entry.subject)] = (
                    _compute_session_spec(entry, base_unit)
                )

        # ==================================================================
        # Step 3 — Teacher assignment from TeacherAssignment list
        # ==================================================================
        teacher_assignment: dict[tuple[str, str], str] = {
            (ta.school_class, ta.subject): ta.teacher
            for ta in data.teacher_assignments
        }

        # ==================================================================
        # Step 4 — Pre-process domain-filtering hard constraints
        #
        # These constraints shrink start_var domains rather than adding
        # model constraints.  Handled categories:
        #   H1  start_time
        #   H3  day_off  (also covers H11 Saturday afternoon)
        #   H5  subject_on_days
        #   H6  subject_not_on_days
        #   H7  subject_not_last_slot
        # ==================================================================
        global_min_start: str = "00:00"
        blocked_day_info: dict[str, set[str]] = {}  # day → {"all"} or session names
        subject_allowed_days: dict[str, set[str]] = {}
        subject_blocked_days: dict[str, set[str]] = {}
        subject_not_last: set[str] = set()

        for c in data.constraints:
            if c.type != "hard":
                continue
            cat = c.category
            p   = c.parameters
            if cat == "start_time":
                hour = p.get("hour", "00:00")
                if hour > global_min_start:
                    global_min_start = hour
            elif cat in ("day_off",):
                day     = p.get("day", "")
                session = p.get("session", "all") or "all"
                if day:
                    blocked_day_info.setdefault(day, set()).add(session)
            elif cat == "subject_on_days":
                subj = p.get("subject", "")
                if subj:
                    subject_allowed_days[subj] = set(p.get("days", []))
            elif cat == "subject_not_on_days":
                subj = p.get("subject", "")
                if subj:
                    subject_blocked_days.setdefault(subj, set()).update(p.get("days", []))
            elif cat == "subject_not_last_slot":
                subj = p.get("subject", "")
                if subj:
                    subject_not_last.add(subj)

        def _is_slot_blocked(day: str, s: int, end_s: int) -> bool:
            """Return True if slots [s, end_s) on *day* are blocked by any day_off."""
            blocked = blocked_day_info.get(day)
            if not blocked:
                return False
            if "all" in blocked:
                return True
            start_t = day_slot_times[day][s][0]
            end_t   = day_slot_times[day][end_s - 1][1]
            for sess_name in blocked:
                so = session_name_map.get(sess_name)
                if so and start_t >= so.start_time and end_t <= so.end_time:
                    return True
            return False

        # ==================================================================
        # Step 5 — Build _Session objects and compute start_var domains
        # ==================================================================
        sessions: list[_Session]         = []
        session_domains: list[list[int]] = []   # session_domains[i] == domain for sessions[i]

        sessions_by_class:   dict[str, list[int]] = defaultdict(list)
        sessions_by_teacher: dict[str, list[int]] = defaultdict(list)
        sessions_by_subject: dict[str, list[int]] = defaultdict(list)
        conflicts: list[dict] = []
        solver_warnings: list[str] = []

        for school_class in data.classes:
            for entry in curriculum_by_class.get(school_class.name, []):
                spec = spec_for.get((school_class.name, entry.subject))
                if spec is None:
                    continue

                teacher_name = teacher_assignment.get((school_class.name, entry.subject))
                if teacher_name is None:
                    conflicts.append({
                        "class":   school_class.name,
                        "subject": entry.subject,
                        "reason":  "No TeacherAssignment found for this class/subject pair",
                    })
                    continue
                if teacher_name not in teacher_map:
                    conflicts.append({
                        "class":   school_class.name,
                        "subject": entry.subject,
                        "reason":  f"Teacher '{teacher_name}' not found in teachers list",
                    })
                    continue

                teacher = teacher_map[teacher_name]
                subject = subject_map[entry.subject]

                # Eligible rooms for this (class × subject)
                eligible_room_idxs: list[int] = []
                if subject.needs_room:
                    for r_idx, room in enumerate(data.rooms):
                        if room.capacity < school_class.student_count:
                            continue
                        if subject.required_room_type:
                            if subject.required_room_type not in room.types:
                                continue
                        else:
                            # Accept any room that has no specialized type.
                            # This prevents lab/specialist rooms from being
                            # assigned to general subjects.
                            if any(rt in specialized_room_types for rt in room.types):
                                continue
                        eligible_room_idxs.append(r_idx)

                    # When a required room type exists but no room of that type
                    # has enough capacity, record an explicit warning so the admin
                    # knows exactly why these sessions cannot be placed in the
                    # specialized room (e.g. why SVT goes to Salle A instead of
                    # the Laboratoire — in this case it won't be placed at all).
                    if not eligible_room_idxs and subject.required_room_type:
                        rooms_of_type = [
                            r for r in data.rooms
                            if subject.required_room_type in r.types
                        ]
                        if rooms_of_type:
                            max_cap = max(r.capacity for r in rooms_of_type)
                            if max_cap < school_class.student_count:
                                warn_key = (school_class.name, entry.subject)
                                warn_msg = (
                                    f"'{entry.subject}' pour '{school_class.name}' "
                                    f"({school_class.student_count} élèves) : "
                                    f"toutes les salles de type "
                                    f"'{subject.required_room_type}' ont une capacité "
                                    f"insuffisante (maximum {max_cap} places). "
                                    f"Les sessions ne peuvent pas être planifiées en "
                                    f"salle spécialisée et seront omises du planning."
                                )
                                if warn_msg not in solver_warnings:
                                    solver_warnings.append(warn_msg)

                for k in range(spec.sessions_per_week):
                    # Last session may use a shorter duration (remainder split).
                    is_last = (k == spec.sessions_per_week - 1)
                    dur_slots_k = (
                        spec.remainder_duration_slots
                        if is_last and spec.remainder_duration_slots
                        else spec.duration_slots
                    )
                    domain: list[int] = []

                    for d_idx, day in enumerate(day_names):
                        # H3: entire day blocked?
                        if "all" in blocked_day_info.get(day, set()):
                            continue
                        # H5
                        if entry.subject in subject_allowed_days:
                            if day not in subject_allowed_days[entry.subject]:
                                continue
                        # H6
                        if day in subject_blocked_days.get(entry.subject, set()):
                            continue

                        n_day = len(day_slot_times[day])
                        for s in _valid_start_slots(day_slot_times[day], dur_slots_k):
                            start_t = day_slot_times[day][s][0]
                            end_t   = day_slot_times[day][s + dur_slots_k - 1][1]

                            # H1
                            if start_t < global_min_start:
                                continue
                            # H3 partial (session-block level)
                            if _is_slot_blocked(day, s, s + dur_slots_k):
                                continue
                            # H7
                            if entry.subject in subject_not_last:
                                if s + dur_slots_k == n_day:
                                    continue
                            # Teacher unavailability
                            if any(
                                u["day"] == day
                                and _session_overlaps_unavailability(start_t, end_t, u)
                                for u in teacher.unavailable_slots
                            ):
                                continue

                            domain.append(d_idx * n_slots_per_day + s)

                    if not domain:
                        # No valid time slot survived domain filtering (H1/H3/H5/H6
                        # constraints + teacher unavailability).  Rather than adding
                        # a new_int_var(-1,-1) that forces CP-SAT INFEASIBLE and
                        # blocks ALL other sessions, we skip this session and mark it
                        # as unscheduled.  The remaining sessions can still be placed,
                        # yielding a partial timetable (partial=True in the result).
                        #
                        # Limitation: this only handles domain-filtering failures.
                        # True mutual-exclusion infeasibility (all domains non-empty
                        # but sessions can't coexist) requires an optional-interval
                        # model rewrite — tracked as future work.
                        conflicts.append({
                            "class":   school_class.name,
                            "subject": entry.subject,
                            "session": k,
                            "reason":  "No valid placement after domain filtering",
                        })
                        continue  # do NOT add to sessions / no-overlap groups

                    idx = len(sessions)
                    sess = _Session(
                        idx=idx,
                        class_name=school_class.name,
                        subject_name=entry.subject,
                        k=k,
                        dur_slots=dur_slots_k,
                        teacher_name=teacher_name,
                        needs_room=subject.needs_room,
                        eligible_room_idxs=eligible_room_idxs,
                        student_count=school_class.student_count,
                    )
                    sessions.append(sess)
                    session_domains.append(domain)
                    sessions_by_class[school_class.name].append(idx)
                    sessions_by_teacher[teacher_name].append(idx)
                    sessions_by_subject[entry.subject].append(idx)

        logger.info(
            "Built %d sessions for %d classes (%d pre-conflicts).",
            len(sessions), len(data.classes), len(conflicts),
        )

        # Early-exit: if every session failed pre-assignment (no sessions built
        # at all) there is nothing for CP-SAT to solve → return solved=False.
        if not sessions and conflicts:
            return TimetableResult(
                assignments=[],
                solved=False,
                solve_time_seconds=round(time.perf_counter() - wall_start, 3),
                conflicts=conflicts,
                soft_constraints_satisfied=[],
                soft_constraints_violated=[],
                soft_constraint_details=[],
            )

        # ==================================================================
        # Step 6 — Create CP-SAT model and start_vars
        # ==================================================================
        model = cp_model.CpModel()

        # Collect the sessions that were already excluded (empty domain) so we
        # can report them as unscheduled in the final result.
        domain_filtered_sessions: list[dict] = [
            c for c in conflicts
            if c.get("reason") == "No valid placement after domain filtering"
        ]

        start_vars: dict[int, cp_model.IntVar] = {}
        for sess in sessions:
            # Every session in `sessions` has a non-empty domain (empty-domain
            # sessions were skipped above and recorded in conflicts).
            dom = session_domains[sess.idx]
            var = model.new_int_var_from_domain(
                Domain.from_values(dom),
                f"s|{sess.idx}|{sess.class_name}|{sess.subject_name}|k{sess.k}",
            )
            start_vars[sess.idx] = var

        # ==================================================================
        # Step 7 — Class and teacher no-overlap (global timeline)
        #
        # On the global timeline, day d's slots are [d×N, (d+1)×N).
        # Sessions that start on day d span [d×N+s, d×N+s+dur), which never
        # crosses into the next day because only valid start slots (those
        # where the session fits within the day's consecutive slots) appear in
        # the domain.  Therefore ONE add_no_overlap per class (and per
        # teacher) covers all days simultaneously.
        # ==================================================================
        for class_name, s_idxs in sessions_by_class.items():
            if len(s_idxs) < 2:
                continue
            ivars = [
                model.new_fixed_size_interval_var(
                    start_vars[i], sessions[i].dur_slots, f"civ|{class_name}|{i}"
                )
                for i in s_idxs
            ]
            model.add_no_overlap(ivars)

        for teacher_name, s_idxs in sessions_by_teacher.items():
            if len(s_idxs) < 2:
                continue
            ivars = [
                model.new_fixed_size_interval_var(
                    start_vars[i], sessions[i].dur_slots, f"tiv|{teacher_name}|{i}"
                )
                for i in s_idxs
            ]
            model.add_no_overlap(ivars)

        # ==================================================================
        # Step 8 — Room assignment
        #
        # room_bvars[(session_idx, room_idx)] = 1 iff room is chosen.
        # add_exactly_one per session + add_no_overlap per room.
        # ==================================================================
        room_bvars: dict[tuple[int, int], cp_model.IntVar] = {}
        room_intervals: dict[int, list[cp_model.IntervalVar]] = defaultdict(list)

        for sess in sessions:
            if not sess.needs_room:
                continue
            if not sess.eligible_room_idxs:
                conflicts.append({
                    "class":   sess.class_name,
                    "subject": sess.subject_name,
                    "session": sess.k,
                    "reason":  "No eligible room (capacity or type mismatch)",
                })
                continue

            bvars: list[cp_model.IntVar] = []
            for r_idx in sess.eligible_room_idxs:
                bv = model.new_bool_var(f"r|{sess.idx}|{r_idx}")
                room_bvars[(sess.idx, r_idx)] = bv
                bvars.append(bv)
                room_intervals[r_idx].append(
                    model.new_optional_fixed_size_interval_var(
                        start_vars[sess.idx], sess.dur_slots, bv,
                        f"riv|{sess.idx}|r{r_idx}",
                    )
                )

            if len(bvars) == 1:
                model.add(bvars[0] == 1)
            else:
                model.add_exactly_one(bvars)

        for r_idx, ivars in room_intervals.items():
            if len(ivars) > 1:
                model.add_no_overlap(ivars)

        logger.info(
            "Model vars: %d start_vars + %d room BoolVars = %d total",
            len(start_vars), len(room_bvars), len(start_vars) + len(room_bvars),
        )

        # ==================================================================
        # Step 9 — Remaining hard constraints via ConstraintBuilder
        #
        # Domain-level constraints (H1, H3, H5, H6, H7) are already applied
        # above.  The builder handles: H4 (max_consecutive), H8
        # (min_break_between), H9 (fixed_assignment), H10 (no-op — satisfied
        # by pre-assignment), H2 (start_time_exceptions — partial).
        # ==================================================================
        hard_constraints = [c for c in data.constraints if c.type == "hard"]
        if hard_constraints:
            builder = ConstraintBuilder(
                model=model,
                data=data,
                sessions=sessions,
                start_vars=start_vars,
                n_slots_per_day=n_slots_per_day,
                day_slot_times=day_slot_times,
                sessions_by_class=sessions_by_class,
                sessions_by_subject=sessions_by_subject,
                session_domains=session_domains,
                tc=tc,
            )
            for w in builder.apply_all(hard_constraints):
                logger.warning("ConstraintBuilder: %s", w)

        # ==================================================================
        # Step 10 — Soft constraints and maximize objective
        # ==================================================================
        soft_constraints = [c for c in data.constraints if c.type == "soft"]
        soft_sat_vars: dict[str, cp_model.IntVar | None] = {}

        if soft_constraints:
            soft_builder = SoftConstraintBuilder(
                model=model,
                data=data,
                sessions=sessions,
                start_vars=start_vars,
                n_slots_per_day=n_slots_per_day,
                n_morning_slots=n_morning_slots,
                day_slot_times=day_slot_times,
                sessions_by_class=sessions_by_class,
                sessions_by_teacher=sessions_by_teacher,
                sessions_by_subject=sessions_by_subject,
                session_domains=session_domains,
                room_bvars=room_bvars,
                tc=tc,
            )
            obj_terms, soft_sat_vars, soft_warnings = soft_builder.apply_all(soft_constraints)
            for w in soft_warnings:
                logger.warning("SoftBuilder: %s", w)

            if obj_terms:
                model.maximize(
                    cp_model.LinearExpr.weighted_sum(
                        [v for _, v in obj_terms],
                        [c for c, _ in obj_terms],
                    )
                )
                logger.info("Objective: %d terms (soft constraints)", len(obj_terms))
        else:
            logger.info("No soft constraints — solving for feasibility only.")

        # ==================================================================
        # Step 11 — Solve
        # ==================================================================
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds  = timeout_seconds
        solver.parameters.log_search_progress  = False
        n_workers = min(8, max(1, os.cpu_count() or 1))
        solver.parameters.num_search_workers   = n_workers

        logger.info(
            "Launching CP-SAT (limit: %ds, workers: %d)...",
            timeout_seconds, n_workers,
        )
        status     = solver.solve(model)
        solve_time = time.perf_counter() - wall_start

        logger.info(
            "Solver finished — status: %s | wall time: %.2fs | conflicts: %d",
            solver.status_name(status), solve_time, solver.num_conflicts,
        )

        # ==================================================================
        # Step 12 — Extract results
        # ==================================================================
        feasible = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

        if not feasible:
            return TimetableResult(
                assignments=[],
                solved=False,
                solve_time_seconds=round(solve_time, 3),
                conflicts=conflicts or [{"reason": solver.status_name(status)}],
                unscheduled_sessions=domain_filtered_sessions,
                soft_constraints_satisfied=[],
                soft_constraints_violated=[],
                warnings=solver_warnings,
            )

        assignments: list[Assignment] = []
        for sess in sessions:
            global_pos = solver.value(start_vars[sess.idx])
            d_idx      = global_pos // n_slots_per_day
            s          = global_pos % n_slots_per_day
            day        = day_names[d_idx]
            start_time = day_slot_times[day][s][0]
            end_time   = day_slot_times[day][s + sess.dur_slots - 1][1]

            room_name: str | None = None
            if sess.needs_room:
                for r_idx in sess.eligible_room_idxs:
                    bv = room_bvars.get((sess.idx, r_idx))
                    if bv is not None and solver.value(bv) == 1:
                        room_name = data.rooms[r_idx].name
                        break

            assignments.append(Assignment(
                school_class=sess.class_name,
                subject=sess.subject_name,
                teacher=sess.teacher_name,
                room=room_name,
                day=day,
                start_time=start_time,
                end_time=end_time,
            ))

        day_order = {d: i for i, d in enumerate(day_names)}
        assignments.sort(
            key=lambda a: (a.school_class, day_order[a.day], a.start_time)
        )

        logger.info("Extracted %d assignments.", len(assignments))

        # Post-solve soft constraint analysis (pure Python, no CP-SAT access needed)
        soft_details:   list[dict] = []
        soft_satisfied: list[str]  = []
        soft_violated:  list[str]  = []

        if soft_constraints:
            analyzer     = SoftConstraintAnalyzer(assignments, data)
            soft_details = analyzer.analyze(soft_constraints)
            for detail in soft_details:
                if detail["satisfaction_percent"] >= SATISFACTION_THRESHOLD:
                    soft_satisfied.append(detail["details_fr"])
                else:
                    soft_violated.append(detail["details_fr"])

        # partial=True when some sessions were skipped due to domain filtering
        # but the remaining sessions were successfully placed.
        is_partial = len(domain_filtered_sessions) > 0
        return TimetableResult(
            assignments=assignments,
            solved=not is_partial,
            partial=is_partial,
            solve_time_seconds=round(solve_time, 3),
            conflicts=conflicts if conflicts else None,
            unscheduled_sessions=domain_filtered_sessions,
            soft_constraints_satisfied=soft_satisfied,
            soft_constraints_violated=soft_violated,
            soft_constraint_details=soft_details,
            warnings=solver_warnings,
        )
