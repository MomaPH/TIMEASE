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
      H12 ritual_slots_blocked  — block ritual-coded slots (S00/BRK/B1/B2/L01/L02)

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
import random
import time
import zlib
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, NamedTuple

from ortools.sat.python import cp_model
from ortools.sat.python.cp_model import Domain

from timease.engine.analysis import SATISFACTION_THRESHOLD, SoftConstraintAnalyzer
from timease.engine.constraints import ConstraintBuilder, SoftConstraintBuilder
from timease.engine.greedy import greedy_warm_start
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

# ---- Fast-mode LNS (Large Neighborhood Search) repair constants ----
# Budget split when fast-mode multi-attempt CP-SAT fails.  Values apply only
# when timeout_seconds >= FAST_MODE_LNS_MIN_TIMEOUT.
FAST_MODE_CPSAT_BUDGET_RATIO: float = 0.40
FAST_MODE_LNS_BUDGET_RATIO: float   = 0.55
FAST_MODE_LNS_MIN_TIMEOUT: int      = 6      # seconds; below this LNS is disabled
LNS_PER_ITER_SECONDS_MIN: float     = 0.8
LNS_PER_ITER_SECONDS_MAX: float     = 2.0
LNS_INITIAL_K: int                  = 6
LNS_K_GROWTH: int                   = 4
LNS_MAX_K: int                      = 40
LNS_NO_IMPROVE_LIMIT: int           = 6
LNS_RANDOM_NOISE_FRAC: float        = 0.15
LNS_MIN_BUDGET_SECONDS: float       = 1.0


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
# LNS (Large Neighborhood Search) helpers — fast-mode feasibility repair
# ---------------------------------------------------------------------------

def _build_lns_feasibility_model(
    sessions: list[_Session],
    session_domains: list[list[int]],
    sessions_by_class: dict[str, list[int]],
    sessions_by_teacher: dict[str, list[int]],
    sessions_by_subject: dict[str, list[int]],
    hard_constraints: list,
    data: SchoolData,
    tc,
    n_slots_per_day: int,
    day_slot_times: dict[str, list[tuple[str, str]]],
    locked_positions: dict[int, int],
    hints: dict[int, int],
) -> tuple[cp_model.CpModel, dict[int, cp_model.IntVar], list[str]]:
    """Build a fresh CP-SAT feasibility model for one LNS iteration.

    Sessions whose idx is in ``locked_positions`` receive a singleton start
    domain (CP-SAT presolve eliminates them in O(1)); all others get their
    full pre-filtered domain.

    Room coupling is intentionally omitted — LNS only runs when the caller
    passes ``enforce_room_conflicts=False`` (the benchmark/fast-mode path).

    Hints are attached via ``add_hint`` for every session with a known
    position to bias the search toward the current incumbent.
    """
    model = cp_model.CpModel()
    start_vars: dict[int, cp_model.IntVar] = {}

    for sess in sessions:
        dom = session_domains[sess.idx]
        if sess.idx in locked_positions:
            pos = locked_positions[sess.idx]
            # Guard: a locked position must lie in the domain.  If not, fall
            # back to the full domain (the caller should not have locked an
            # infeasible session, but defensive correctness matters more than
            # strict locking for a single iteration).
            if pos in dom:
                dom_values = [pos]
            else:
                dom_values = dom
        else:
            dom_values = dom
        var = model.new_int_var_from_domain(
            Domain.from_values(dom_values),
            f"s|{sess.idx}|{sess.class_name}|{sess.subject_name}|k{sess.k}",
        )
        start_vars[sess.idx] = var

    # Symmetry breaking (same as main model) — cheap when vars are singletons.
    interchangeable: dict[tuple, list[int]] = defaultdict(list)
    for sess in sessions:
        key = (
            sess.class_name,
            sess.subject_name,
            sess.teacher_name,
            sess.dur_slots,
            tuple(session_domains[sess.idx]),
        )
        interchangeable[key].append(sess.idx)
    for idxs in interchangeable.values():
        if len(idxs) < 2:
            continue
        idxs.sort()
        for left, right in zip(idxs, idxs[1:], strict=False):
            model.add(start_vars[left] <= start_vars[right])

    # Class no-overlap.
    for s_idxs in sessions_by_class.values():
        if len(s_idxs) < 2:
            continue
        ivars = [
            model.new_fixed_size_interval_var(
                start_vars[i], sessions[i].dur_slots, f"civ|{i}"
            )
            for i in s_idxs
        ]
        model.add_no_overlap(ivars)

    # Teacher no-overlap.
    for s_idxs in sessions_by_teacher.values():
        if len(s_idxs) < 2:
            continue
        ivars = [
            model.new_fixed_size_interval_var(
                start_vars[i], sessions[i].dur_slots, f"tiv|{i}"
            )
            for i in s_idxs
        ]
        model.add_no_overlap(ivars)

    # Hard constraints via ConstraintBuilder (H2/H4/H8/H9/H11).
    lns_warnings: list[str] = []
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
        lns_warnings = builder.apply_all(hard_constraints)

    # Hints: incumbent positions for free sessions bias CP-SAT toward the
    # current solution; locked sessions already have singleton domains.
    for i, pos in hints.items():
        if i in start_vars and i not in locked_positions:
            model.add_hint(start_vars[i], pos)

    return model, start_vars, lns_warnings


def _build_neighborhood(
    unscheduled_idxs: set[int],
    all_idxs: list[int],
    sessions: list[_Session],
    sessions_by_class: dict[str, list[int]],
    sessions_by_teacher: dict[str, list[int]],
    K: int,
    rng: random.Random,
) -> set[int]:
    """Grow a free neighborhood around the unscheduled core.

    Tier 1 — same class or same teacher as any unscheduled session.
    Tier 2 — random noise drawn from remaining sessions for diversification.

    Deterministic given a fixed ``rng``.
    """
    nbhd: set[int] = set(unscheduled_idxs)
    tier1: set[int] = set()
    for i in unscheduled_idxs:
        s = sessions[i]
        tier1.update(sessions_by_class.get(s.class_name, ()))
        tier1.update(sessions_by_teacher.get(s.teacher_name, ()))
    tier1 -= nbhd

    structured_budget = max(0, K - int(K * LNS_RANDOM_NOISE_FRAC))
    tier1_list = sorted(tier1)
    rng.shuffle(tier1_list)
    nbhd.update(tier1_list[:structured_budget])

    added_so_far = len(nbhd) - len(unscheduled_idxs)
    noise_budget = max(0, K - added_so_far)
    remaining = sorted(i for i in all_idxs if i not in nbhd)
    rng.shuffle(remaining)
    nbhd.update(remaining[:noise_budget])

    return nbhd


def _run_lns_repair(
    sessions: list[_Session],
    session_domains: list[list[int]],
    sessions_by_class: dict[str, list[int]],
    sessions_by_teacher: dict[str, list[int]],
    sessions_by_subject: dict[str, list[int]],
    hard_constraints: list,
    data: SchoolData,
    tc,
    n_slots_per_day: int,
    day_slot_times: dict[str, list[tuple[str, str]]],
    current_pos: dict[int, int | None],
    budget_seconds: float,
    n_workers: int,
    rng: random.Random,
) -> tuple[dict[int, int | None], int, bool]:
    """Iteratively repair an incumbent by re-solving a small free neighborhood.

    Returns ``(updated_pos, n_iters_run, improved_flag)``.  ``improved_flag``
    is True iff at least one iteration strictly reduced the unscheduled count.
    """
    t_deadline = time.perf_counter() + budget_seconds
    best_pos: dict[int, int | None] = dict(current_pos)
    best_unscheduled: set[int] = {i for i, p in best_pos.items() if p is None}
    if not best_unscheduled:
        return best_pos, 0, False

    all_idxs = sorted(best_pos.keys())
    no_improve = 0
    K = LNS_INITIAL_K
    iters = 0
    improved_ever = False
    strategies = [
        cp_model.FIXED_SEARCH,
        cp_model.PORTFOLIO_SEARCH,
        cp_model.AUTOMATIC_SEARCH,
    ]

    while (
        best_unscheduled
        and time.perf_counter() < t_deadline
        and no_improve < LNS_NO_IMPROVE_LIMIT
    ):
        iters += 1
        remaining = t_deadline - time.perf_counter()
        if remaining <= LNS_PER_ITER_SECONDS_MIN:
            per_iter = max(LNS_PER_ITER_SECONDS_MIN, remaining)
        else:
            per_iter = max(
                LNS_PER_ITER_SECONDS_MIN,
                min(LNS_PER_ITER_SECONDS_MAX, remaining / 3.0),
            )

        nbhd = _build_neighborhood(
            unscheduled_idxs=best_unscheduled,
            all_idxs=all_idxs,
            sessions=sessions,
            sessions_by_class=sessions_by_class,
            sessions_by_teacher=sessions_by_teacher,
            K=K,
            rng=rng,
        )
        locked_positions = {
            i: best_pos[i]
            for i in all_idxs
            if i not in nbhd and best_pos[i] is not None
        }
        hints = {i: p for i, p in best_pos.items() if p is not None}

        try:
            model, start_vars, _ = _build_lns_feasibility_model(
                sessions=sessions,
                session_domains=session_domains,
                sessions_by_class=sessions_by_class,
                sessions_by_teacher=sessions_by_teacher,
                sessions_by_subject=sessions_by_subject,
                hard_constraints=hard_constraints,
                data=data,
                tc=tc,
                n_slots_per_day=n_slots_per_day,
                day_slot_times=day_slot_times,
                locked_positions=locked_positions,
                hints=hints,
            )
        except Exception:  # pragma: no cover — build errors shouldn't happen
            logger.exception("LNS model build failed at iter %d", iters)
            break

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds       = per_iter
        solver.parameters.log_search_progress       = False
        solver.parameters.stop_after_first_solution = True
        solver.parameters.search_branching          = strategies[iters % 3]
        solver.parameters.random_seed               = 1000 + 7 * iters
        solver.parameters.num_search_workers        = n_workers
        status = solver.solve(model)

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            new_pos: dict[int, int | None] = {}
            for i in all_idxs:
                var = start_vars.get(i)
                if var is None:
                    new_pos[i] = best_pos[i]
                else:
                    new_pos[i] = int(solver.value(var))
            new_unscheduled = {i for i, p in new_pos.items() if p is None}
            if len(new_unscheduled) < len(best_unscheduled):
                best_pos = new_pos
                best_unscheduled = new_unscheduled
                improved_ever = True
                no_improve = 0
                K = LNS_INITIAL_K
                logger.info(
                    "LNS iter %d: improved — unscheduled %d→%d (nbhd=%d, K=%d, time=%.2fs)",
                    iters, len(new_unscheduled) + (len(best_unscheduled) - len(new_unscheduled)),
                    len(new_unscheduled), len(nbhd), K, per_iter,
                )
                continue

        no_improve += 1
        K = min(LNS_MAX_K, K + LNS_K_GROWTH)
        logger.info(
            "LNS iter %d: no improvement (status=%s, nbhd=%d, next K=%d)",
            iters, solver.status_name(status), len(nbhd), K,
        )

    return best_pos, iters, improved_ever


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
        optimize_soft_constraints: bool = True,
        stop_at_first_solution: bool = False,
        prefer_standard_rooms_for_general_subjects: bool = True,
        enforce_room_conflicts: bool = True,
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

        build_start = time.perf_counter()

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
        # Optional room pre-assignment. When the school sets ta.room, we
        # narrow the session's eligible-room set to that single room.
        # Unknown / capacity-insufficient rooms fall back to the default
        # logic with a warning.
        room_preassignment: dict[tuple[str, str], str] = {
            (ta.school_class, ta.subject): (ta.room or "").strip()
            for ta in data.teacher_assignments
            if (ta.room or "").strip()
        }
        room_name_to_idx: dict[str, int] = {
            r.name: i for i, r in enumerate(data.rooms)
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
        #   H12 ritual_slots_blocked
        # ==================================================================
        global_min_start: str = "00:00"
        blocked_day_info: dict[str, set[str]] = {}  # day → {"all"} or session names
        subject_allowed_days: dict[str, set[str]] = {}
        subject_blocked_days: dict[str, set[str]] = {}
        subject_not_last: set[str] = set()
        ritual_slot_codes: set[str] = set()

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
            elif cat == "ritual_slots_blocked":
                slots = p.get("slots", [])
                if isinstance(slots, list):
                    ritual_slot_codes.update(str(slot).upper() for slot in slots)

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

        # Map ritual slot codes to actual base-unit slot indices for each day.
        # BRK has no schedulable slot in current modeling (breaks are removed), so
        # it is effectively covered already by slot generation.
        ritual_blocked_slots_by_day: dict[str, set[int]] = {}
        if ritual_slot_codes:
            for day, slots in day_slot_times.items():
                blocked_indices: set[int] = set()
                if not slots:
                    ritual_blocked_slots_by_day[day] = blocked_indices
                    continue

                block_starts: list[int] = []
                block_ends: list[int] = []
                for idx in range(len(slots)):
                    if idx == 0 or slots[idx - 1][1] != slots[idx][0]:
                        block_starts.append(idx)
                    if idx == len(slots) - 1 or slots[idx][1] != slots[idx + 1][0]:
                        block_ends.append(idx)

                if "S00" in ritual_slot_codes and block_starts:
                    blocked_indices.add(block_starts[0])
                if "B1" in ritual_slot_codes and block_ends:
                    blocked_indices.add(block_ends[0])
                if "B2" in ritual_slot_codes and len(block_starts) >= 2:
                    blocked_indices.add(block_starts[1])
                if "L01" in ritual_slot_codes and block_starts:
                    blocked_indices.add(block_starts[-1])
                if "L02" in ritual_slot_codes and block_starts:
                    l02_idx = block_starts[-1] + 1
                    if l02_idx < len(slots):
                        blocked_indices.add(l02_idx)

                ritual_blocked_slots_by_day[day] = blocked_indices

        # Prefix sums allow O(1) blocked-interval checks:
        # blocked in [s, e) iff prefix[e] > prefix[s].
        hard_blocked_prefix_by_day: dict[str, list[int]] = {}
        ritual_blocked_prefix_by_day: dict[str, list[int]] = {}
        for day in day_names:
            slots = day_slot_times[day]
            n_day = len(slots)

            hard_blocked = [0] * n_day
            blocked = blocked_day_info.get(day)
            if blocked:
                if "all" in blocked:
                    hard_blocked = [1] * n_day
                else:
                    for i in range(n_day):
                        if _is_slot_blocked(day, i, i + 1):
                            hard_blocked[i] = 1

            hard_prefix = [0] * (n_day + 1)
            for i, value in enumerate(hard_blocked, start=1):
                hard_prefix[i] = hard_prefix[i - 1] + value
            hard_blocked_prefix_by_day[day] = hard_prefix

            ritual_blocked = [0] * n_day
            for i in ritual_blocked_slots_by_day.get(day, set()):
                if 0 <= i < n_day:
                    ritual_blocked[i] = 1
            ritual_prefix = [0] * (n_day + 1)
            for i, value in enumerate(ritual_blocked, start=1):
                ritual_prefix[i] = ritual_prefix[i - 1] + value
            ritual_blocked_prefix_by_day[day] = ritual_prefix

        # Cache valid start slots by (day, duration) to avoid recomputing
        # continuity checks for every generated session domain.
        duration_values: set[int] = set()
        for spec in spec_for.values():
            duration_values.add(spec.duration_slots)
            if spec.remainder_duration_slots:
                duration_values.add(spec.remainder_duration_slots)
        valid_starts_cache: dict[tuple[str, int], list[int]] = {}
        for day in day_names:
            slots = day_slot_times[day]
            for dur in duration_values:
                valid_starts_cache[(day, dur)] = _valid_start_slots(slots, dur)

        # Pre-index teacher unavailability by (teacher, day) for fast filtering.
        teacher_unavailable_by_day: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
        for teacher in data.teachers:
            for u in teacher.unavailable_slots:
                day = str(u.get("day") or "")
                if day:
                    teacher_unavailable_by_day[teacher.name][day].append(u)

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
                # Phase D: Rooms are optional with soft room-type matching.
                # For general subjects (no required_room_type), prefer standard
                # rooms first but fall back to specialized rooms if needed to
                # preserve feasibility in room-tight datasets.
                eligible_room_idxs: list[int] = []
                preferred_room_idxs: list[int] = []  # Rooms that match required_room_type
                fallback_room_idxs: list[int] = []   # Rooms without required_room_type match

                # School-provided room pre-assignment short-circuits the
                # eligibility computation: the solver no longer chooses a
                # room, it just places the session in the given room.
                preassigned_room = room_preassignment.get(
                    (school_class.name, entry.subject), ""
                )
                if subject.needs_room and preassigned_room:
                    r_idx = room_name_to_idx.get(preassigned_room, -1)
                    if r_idx >= 0:
                        room = data.rooms[r_idx]
                        if room.capacity >= school_class.student_count:
                            eligible_room_idxs = [r_idx]
                        else:
                            warn_msg = (
                                f"'{entry.subject}' pour '{school_class.name}' : "
                                f"la salle imposée '{preassigned_room}' a une "
                                f"capacité insuffisante — attribution annulée."
                            )
                            if warn_msg not in solver_warnings:
                                solver_warnings.append(warn_msg)
                    else:
                        warn_msg = (
                            f"'{entry.subject}' pour '{school_class.name}' : "
                            f"la salle imposée '{preassigned_room}' n'existe pas — "
                            f"attribution annulée."
                        )
                        if warn_msg not in solver_warnings:
                            solver_warnings.append(warn_msg)

                if subject.needs_room and data.rooms and not eligible_room_idxs:
                    for r_idx, room in enumerate(data.rooms):
                        if room.capacity < school_class.student_count:
                            continue
                        if subject.required_room_type:
                            if subject.required_room_type in room.types:
                                preferred_room_idxs.append(r_idx)
                            else:
                                # Soft matching: allow any room as fallback
                                fallback_room_idxs.append(r_idx)
                        else:
                            # For general subjects, default to standard-room preference.
                            # In fallback mode we allow all capacity-compatible rooms.
                            if prefer_standard_rooms_for_general_subjects:
                                if any(rt in specialized_room_types for rt in room.types):
                                    fallback_room_idxs.append(r_idx)
                                else:
                                    preferred_room_idxs.append(r_idx)
                            else:
                                preferred_room_idxs.append(r_idx)

                    # Phase D: Use preferred rooms first, fallback if none available.
                    #
                    # For general subjects in room-tight schools (few standard rooms
                    # compared with class count), we add one deterministic fallback
                    # room candidate so CP-SAT can escape deadlocks without exploding
                    # the room decision space.
                    if preferred_room_idxs:
                        eligible_room_idxs = list(preferred_room_idxs)
                        if (
                            not subject.required_room_type
                            and prefer_standard_rooms_for_general_subjects
                            and fallback_room_idxs
                            and len(preferred_room_idxs) < len(data.classes)
                        ):
                            # crc32 keeps the pick deterministic across runs
                            # (builtin hash() varies with PYTHONHASHSEED).
                            pick_key = f"{school_class.name}|{entry.subject}".encode()
                            fallback_pick = fallback_room_idxs[
                                zlib.crc32(pick_key) % len(fallback_room_idxs)
                            ]
                            if fallback_pick not in eligible_room_idxs:
                                eligible_room_idxs.append(fallback_pick)
                    elif fallback_room_idxs:
                        # Soft matching: use fallback rooms with a warning
                        eligible_room_idxs = fallback_room_idxs
                        if subject.required_room_type:
                            warn_msg = (
                                f"'{entry.subject}' pour '{school_class.name}' : "
                                f"aucune salle de type '{subject.required_room_type}' n'est "
                                f"disponible avec une capacité suffisante. "
                                f"Les sessions seront placées dans une salle standard."
                            )
                        else:
                            if prefer_standard_rooms_for_general_subjects:
                                warn_msg = (
                                    f"'{entry.subject}' pour '{school_class.name}' : "
                                    "aucune salle standard disponible avec une capacité suffisante. "
                                    "Les sessions pourront utiliser une salle spécialisée."
                                )
                            else:
                                warn_msg = (
                                    f"'{entry.subject}' pour '{school_class.name}' : "
                                    "mode de secours activé — toutes les salles compatibles en capacité "
                                    "sont autorisées."
                                )
                        if warn_msg not in solver_warnings:
                            solver_warnings.append(warn_msg)

                # Phase D: Empty rooms list is valid - sessions can be scheduled without room
                # When needs_room=True but no rooms defined, generate a warning
                if subject.needs_room and not data.rooms:
                    warn_msg = (
                        "Aucune salle n'est définie. Les sessions seront planifiées "
                        "sans attribution de salle."
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
                        hard_prefix = hard_blocked_prefix_by_day[day]
                        ritual_prefix = ritual_blocked_prefix_by_day[day]
                        day_unavailability = teacher_unavailable_by_day.get(teacher.name, {}).get(day, [])
                        for s in valid_starts_cache.get((day, dur_slots_k), []):
                            start_t = day_slot_times[day][s][0]
                            end_t   = day_slot_times[day][s + dur_slots_k - 1][1]

                            # H1
                            if start_t < global_min_start:
                                continue
                            # H3 partial (session-block level)
                            if hard_prefix[s + dur_slots_k] > hard_prefix[s]:
                                continue
                            # H12 ritual blocked slots
                            if ritual_prefix[s + dur_slots_k] > ritual_prefix[s]:
                                continue
                            # H7
                            if entry.subject in subject_not_last:
                                if s + dur_slots_k == n_day:
                                    continue
                            # Teacher unavailability
                            if any(
                                _session_overlaps_unavailability(start_t, end_t, u)
                                for u in day_unavailability
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

        # Symmetry breaking: interchangeable sessions with identical static
        # characteristics and domains are ordered by start time.
        interchangeable: dict[tuple, list[int]] = defaultdict(list)
        for sess in sessions:
            key = (
                sess.class_name,
                sess.subject_name,
                sess.teacher_name,
                sess.dur_slots,
                tuple(session_domains[sess.idx]),
            )
            interchangeable[key].append(sess.idx)
        for idxs in interchangeable.values():
            if len(idxs) < 2:
                continue
            idxs.sort()
            for left, right in zip(idxs, idxs[1:], strict=False):
                model.add(start_vars[left] <= start_vars[right])

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
        #
        # Phase D: Empty rooms list is valid. Sessions can be scheduled
        # without room assignment. Soft room-type matching means we
        # don't mark sessions as conflicts when no matching room exists.
        # ==================================================================
        room_bvars: dict[tuple[int, int], cp_model.IntVar] = {}
        room_intervals: dict[int, list[cp_model.IntervalVar]] = defaultdict(list)
        fixed_room_for_session: dict[int, int] = {}

        # Skip room assignment entirely if no rooms are defined or when
        # fast feasibility mode disables room coupling for speed.
        if data.rooms and enforce_room_conflicts:
            for sess in sessions:
                if not sess.needs_room:
                    continue
                if not sess.eligible_room_idxs:
                    # Phase D: Soft room matching - sessions without eligible rooms
                    # are scheduled but without room assignment (room will be None)
                    continue

                bvars: list[cp_model.IntVar] = []
                for r_idx in sess.eligible_room_idxs:
                    if len(sess.eligible_room_idxs) == 1:
                        fixed_room_for_session[sess.idx] = r_idx
                        room_intervals[r_idx].append(
                            model.new_fixed_size_interval_var(
                                start_vars[sess.idx], sess.dur_slots,
                                f"riv_fixed|{sess.idx}|r{r_idx}",
                            )
                        )
                        break
                    bv = model.new_bool_var(f"r|{sess.idx}|{r_idx}")
                    room_bvars[(sess.idx, r_idx)] = bv
                    bvars.append(bv)
                    room_intervals[r_idx].append(
                        model.new_optional_fixed_size_interval_var(
                            start_vars[sess.idx], sess.dur_slots, bv,
                            f"riv|{sess.idx}|r{r_idx}",
                        )
                    )

                if len(sess.eligible_room_idxs) > 1:
                    model.add_exactly_one(bvars)

            for r_idx, ivars in room_intervals.items():
                if len(ivars) > 1:
                    model.add_no_overlap(ivars)

        # Constrained-first branching for feasibility speed.
        ordered_session_vars = [
            start_vars[s.idx]
            for s in sorted(
                sessions,
                key=lambda s: (
                    len(session_domains[s.idx]),
                    -s.dur_slots,
                    len(s.eligible_room_idxs) if s.needs_room else 9999,
                    s.idx,
                ),
            )
        ]
        if ordered_session_vars:
            model.add_decision_strategy(
                ordered_session_vars,
                cp_model.CHOOSE_MIN_DOMAIN_SIZE,
                cp_model.SELECT_MIN_VALUE,
            )
        if room_bvars:
            model.add_decision_strategy(
                list(room_bvars.values()),
                cp_model.CHOOSE_MIN_DOMAIN_SIZE,
                cp_model.SELECT_MAX_VALUE,
            )

        if not optimize_soft_constraints:
            # Fast-feasibility path only: seed CP-SAT with a greedy non-overlap
            # placement via hints. Skipped when soft constraints are active —
            # the greedy walks domains in ascending order, which biases Phase A
            # toward morning slots and can hurt time-of-day soft preferences.
            greedy_placements = greedy_warm_start(sessions, session_domains)
            for i, gpos in greedy_placements.items():
                model.add_hint(start_vars[i], gpos)
            logger.info(
                "Greedy warm start: %d/%d sessions pre-placed",
                len(greedy_placements), len(sessions),
            )

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
            hard_warnings = builder.apply_all(hard_constraints)
            for w in hard_warnings:
                logger.warning("ConstraintBuilder: %s", w)
                if w not in solver_warnings:
                    solver_warnings.append(w)

        # ==================================================================
        # Step 10 — Soft constraints and maximize objective
        # ==================================================================
        soft_constraints = [c for c in data.constraints if c.type == "soft"] if optimize_soft_constraints else []
        obj_terms: list[tuple[int, cp_model.IntVar]] = []
        soft_sat_vars: dict[str, cp_model.IntVar | None] = {}

        if soft_constraints and optimize_soft_constraints:
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
                if w not in solver_warnings:
                    solver_warnings.append(w)

            if obj_terms:
                model.maximize(
                    cp_model.LinearExpr.weighted_sum(
                        [v for _, v in obj_terms],
                        [c for c, _ in obj_terms],
                    )
                )
                logger.info("Objective: %d terms (soft constraints)", len(obj_terms))
        elif not optimize_soft_constraints:
            logger.info("Soft objective disabled — solving for feasibility only.")
        else:
            logger.info("No soft constraints — solving for feasibility only.")

        feasibility_model = model
        if optimize_soft_constraints and obj_terms:
            # Phase A should search feasibility without objective pressure.
            feasibility_model = cp_model.CpModel()
            feasibility_model.proto.copy_from(model.proto)
            feasibility_model.proto.clear_objective()
            feasibility_model.proto.clear_floating_point_objective()

        # ==================================================================
        # Step 11 — Solve
        # ==================================================================
        build_time = time.perf_counter() - build_start
        n_workers = min(8, max(1, os.cpu_count() or 1))
        solver_diagnostics: dict = {
            "phase": "init",
            "build_time_seconds": round(build_time, 3),
            "timeout_seconds": int(timeout_seconds),
            "optimize_soft_constraints": bool(optimize_soft_constraints),
            "stop_at_first_solution": bool(stop_at_first_solution),
            "enforce_room_conflicts": bool(enforce_room_conflicts),
            "session_count": len(sessions),
            "domain_filtered_sessions": len(domain_filtered_sessions),
        }

        logger.info(
            "Launching CP-SAT (limit: %ds, workers: %d, first_solution=%s, build=%.2fs)...",
            timeout_seconds, n_workers, stop_at_first_solution, build_time,
        )

        solver = cp_model.CpSolver()
        status = cp_model.UNKNOWN
        solve_time = 0.0
        if optimize_soft_constraints:
            # Solve contract for balanced/complete:
            # 1) find a complete feasible timetable first
            # 2) improve soft objective with remaining budget
            phase_a_time = max(1.0, float(timeout_seconds) * 0.6)
            phase_b_time = max(0.0, float(timeout_seconds) - phase_a_time)
            solver_diagnostics["phase"] = "staged"
            solver_diagnostics["phase_a_budget_seconds"] = round(phase_a_time, 3)
            solver_diagnostics["phase_b_budget_seconds"] = round(phase_b_time, 3)

            feas_solver = cp_model.CpSolver()
            feas_solver.parameters.max_time_in_seconds = phase_a_time
            feas_solver.parameters.log_search_progress = False
            feas_solver.parameters.stop_after_first_solution = True
            feas_solver.parameters.search_branching = cp_model.PORTFOLIO_SEARCH
            feas_solver.parameters.num_search_workers = n_workers
            feas_start = time.perf_counter()
            feas_status = feas_solver.solve(feasibility_model)
            feas_elapsed = time.perf_counter() - feas_start
            solve_time += feas_elapsed
            solver = feas_solver
            status = feas_status
            solver_diagnostics["feasibility_phase_status"] = feas_solver.status_name(feas_status)
            solver_diagnostics["feasibility_phase_time_seconds"] = round(feas_elapsed, 3)
            solver_diagnostics["feasibility_num_conflicts"] = int(feas_solver.num_conflicts)
            solver_diagnostics["feasibility_num_branches"] = int(feas_solver.num_branches)

            if feas_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                solver_diagnostics["feasible_solution_found"] = True

                remaining_budget = max(0.0, float(timeout_seconds) - float(solve_time))
                if remaining_budget >= 1.0 and obj_terms:
                    for sess in sessions:
                        model.add_hint(start_vars[sess.idx], feas_solver.value(start_vars[sess.idx]))
                    for bv in room_bvars.values():
                        model.add_hint(bv, feas_solver.value(bv))

                    opt_solver = cp_model.CpSolver()
                    opt_solver.parameters.max_time_in_seconds = min(phase_b_time, remaining_budget)
                    opt_solver.parameters.log_search_progress = False
                    opt_solver.parameters.stop_after_first_solution = False
                    opt_solver.parameters.search_branching = cp_model.PORTFOLIO_SEARCH
                    opt_solver.parameters.num_search_workers = n_workers
                    # Stronger linear relaxation helps prove optimality on
                    # the soft-objective phase. Keep feasibility paths on
                    # the default (level 1) — they don't need the extra cuts.
                    opt_solver.parameters.linearization_level = 2
                    opt_start = time.perf_counter()
                    opt_status = opt_solver.solve(model)
                    opt_elapsed = time.perf_counter() - opt_start
                    solve_time += opt_elapsed
                    solver_diagnostics["optimization_phase_status"] = opt_solver.status_name(opt_status)
                    solver_diagnostics["optimization_phase_time_seconds"] = round(opt_elapsed, 3)
                    solver_diagnostics["optimization_num_conflicts"] = int(opt_solver.num_conflicts)
                    solver_diagnostics["optimization_num_branches"] = int(opt_solver.num_branches)
                    if opt_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                        solver = opt_solver
                        status = opt_status
            else:
                solver_diagnostics["feasible_solution_found"] = False
                remaining_budget = max(0.0, float(timeout_seconds) - float(solve_time))
                if remaining_budget >= 1.0:
                    # If stage A times out/gets stuck, run a short portfolio of
                    # feasibility attempts instead of a single rescue solve.
                    rescue_attempts = [
                        ("fixed", cp_model.FIXED_SEARCH, 101),
                        ("portfolio", cp_model.PORTFOLIO_SEARCH, 202),
                        ("auto", cp_model.AUTOMATIC_SEARCH, 303),
                    ]
                    per_attempt = max(1.0, remaining_budget / len(rescue_attempts))
                    last_rescue_status = feas_status
                    for idx, (label, branching, seed) in enumerate(rescue_attempts):
                        rescue_solver = cp_model.CpSolver()
                        rescue_solver.parameters.max_time_in_seconds = max(1.0, per_attempt)
                        rescue_solver.parameters.log_search_progress = False
                        rescue_solver.parameters.stop_after_first_solution = True
                        rescue_solver.parameters.search_branching = branching
                        rescue_solver.parameters.random_seed = seed
                        rescue_solver.parameters.num_search_workers = n_workers
                        rescue_start = time.perf_counter()
                        rescue_status = rescue_solver.solve(feasibility_model)
                        rescue_elapsed = time.perf_counter() - rescue_start
                        solve_time += rescue_elapsed
                        solver_diagnostics[f"rescue_{idx+1}_status"] = rescue_solver.status_name(rescue_status)
                        solver_diagnostics[f"rescue_{idx+1}_time_seconds"] = round(rescue_elapsed, 3)
                        solver_diagnostics[f"rescue_{idx+1}_num_conflicts"] = int(rescue_solver.num_conflicts)
                        solver_diagnostics[f"rescue_{idx+1}_num_branches"] = int(rescue_solver.num_branches)
                        last_rescue_status = rescue_status
                        solver = rescue_solver
                        status = rescue_status
                        if rescue_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                            break
                    solver_diagnostics["rescue_phase_status"] = solver.status_name(last_rescue_status)
        elif timeout_seconds >= 3:
            # Multi-attempt feasibility search in fast mode:
            # same model, different branching strategies/seeds under the same
            # global timeout budget, stopping at first feasible solution.
            attempt_configs = [
                ("fixed", cp_model.FIXED_SEARCH, 101),
                ("portfolio", cp_model.PORTFOLIO_SEARCH, 202),
                ("auto", cp_model.AUTOMATIC_SEARCH, 303),
            ]
            # When LNS repair is available (fast mode + rooms decoupled + enough
            # budget), reserve a share of the timeout for Phase C LNS. Otherwise
            # Phase A gets the full budget (legacy behavior).
            lns_reserved = (
                not enforce_room_conflicts
                and timeout_seconds >= FAST_MODE_LNS_MIN_TIMEOUT
            )
            phase_a_total = (
                max(2, int(timeout_seconds * FAST_MODE_CPSAT_BUDGET_RATIO))
                if lns_reserved
                else timeout_seconds
            )
            per_attempt = max(1, phase_a_total // len(attempt_configs))
            for attempt_idx, (label, branching, seed) in enumerate(attempt_configs):
                remaining_attempts = len(attempt_configs) - attempt_idx
                remaining_budget = max(1, phase_a_total - int(solve_time))
                attempt_limit = (
                    remaining_budget
                    if remaining_attempts == 1
                    else min(per_attempt, remaining_budget)
                )
                attempt_solver = cp_model.CpSolver()
                attempt_solver.parameters.max_time_in_seconds = attempt_limit
                attempt_solver.parameters.log_search_progress = False
                attempt_solver.parameters.stop_after_first_solution = True
                attempt_solver.parameters.search_branching = branching
                attempt_solver.parameters.random_seed = seed
                attempt_solver.parameters.num_search_workers = n_workers
                attempt_start = time.perf_counter()
                attempt_status = attempt_solver.solve(model)
                attempt_elapsed = time.perf_counter() - attempt_start
                solve_time += attempt_elapsed
                logger.info(
                    "Fast attempt %d/%d (%s): status=%s time=%.2fs seed=%d",
                    attempt_idx + 1,
                    len(attempt_configs),
                    label,
                    attempt_solver.status_name(attempt_status),
                    attempt_elapsed,
                    seed,
                )
                solver = attempt_solver
                status = attempt_status
                if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                    break
                if solve_time >= phase_a_total:
                    break
            solver_diagnostics["phase"] = "multi_attempt"
        else:
            solver.parameters.max_time_in_seconds = timeout_seconds
            solver.parameters.log_search_progress = False
            solver.parameters.stop_after_first_solution = stop_at_first_solution
            if not optimize_soft_constraints:
                solver.parameters.search_branching = cp_model.FIXED_SEARCH
            solver.parameters.num_search_workers = n_workers
            solve_start = time.perf_counter()
            status = solver.solve(model)
            solve_time = time.perf_counter() - solve_start
            solver_diagnostics["phase"] = "single_pass"
            solver_diagnostics["solver_status"] = solver.status_name(status)
            solver_diagnostics["num_conflicts"] = int(solver.num_conflicts)
            solver_diagnostics["num_branches"] = int(solver.num_branches)
            if obj_terms:
                try:
                    solver_diagnostics["best_objective_bound"] = float(solver.best_objective_bound)
                    solver_diagnostics["objective_value"] = float(solver.objective_value)
                except Exception:  # noqa: BLE001
                    pass

        logger.info(
            "Solver finished — status: %s | solve time: %.2fs | total: %.2fs | conflicts: %d",
            solver.status_name(status), solve_time, (time.perf_counter() - wall_start), solver.num_conflicts,
        )

        # ==================================================================
        # Step 12 — Extract results
        # ==================================================================
        feasible = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

        if not feasible:
            timeout_unknown = solver.status_name(status).upper() == "UNKNOWN"
            # Fast-mode fallback: return a deterministic partial timetable instead
            # of an empty timeout result when CP-SAT finds no feasible solution.
            if timeout_unknown:
                class_busy: dict[str, dict[str, list[tuple[int, int]]]] = defaultdict(lambda: defaultdict(list))
                teacher_busy: dict[str, dict[str, list[tuple[int, int]]]] = defaultdict(lambda: defaultdict(list))
                room_busy: dict[int, dict[str, list[tuple[int, int]]]] = defaultdict(lambda: defaultdict(list))

                def _to_min(hm: str) -> int:
                    h, m = hm.split(":")
                    return int(h) * 60 + int(m)

                greedy_assignments: list[Assignment] = []
                greedy_unscheduled: list[dict] = []

                ordered_sessions = sorted(
                    sessions,
                    key=lambda s: (len(session_domains[s.idx]), -s.dur_slots, s.idx),
                )
                for sess in ordered_sessions:
                    placed = False
                    for global_pos in session_domains[sess.idx]:
                        d_idx = global_pos // n_slots_per_day
                        s = global_pos % n_slots_per_day
                        day = day_names[d_idx]
                        start_time = day_slot_times[day][s][0]
                        end_time = day_slot_times[day][s + sess.dur_slots - 1][1]
                        start_min = _to_min(start_time)
                        end_min = _to_min(end_time)

                        has_class_overlap = any(
                            start_min < e and b < end_min
                            for b, e in class_busy[sess.class_name][day]
                        )
                        if has_class_overlap:
                            continue
                        has_teacher_overlap = any(
                            start_min < e and b < end_min
                            for b, e in teacher_busy[sess.teacher_name][day]
                        )
                        if has_teacher_overlap:
                            continue

                        room_name: str | None = None
                        if sess.needs_room and enforce_room_conflicts and sess.eligible_room_idxs:
                            selected_room: int | None = None
                            for r_idx in sess.eligible_room_idxs:
                                has_room_overlap = any(
                                    start_min < e and b < end_min
                                    for b, e in room_busy[r_idx][day]
                                )
                                if not has_room_overlap:
                                    selected_room = r_idx
                                    break
                            if selected_room is None:
                                continue
                            room_busy[selected_room][day].append((start_min, end_min))
                            room_name = data.rooms[selected_room].name

                        class_busy[sess.class_name][day].append((start_min, end_min))
                        teacher_busy[sess.teacher_name][day].append((start_min, end_min))
                        greedy_assignments.append(
                            Assignment(
                                school_class=sess.class_name,
                                subject=sess.subject_name,
                                teacher=sess.teacher_name,
                                room=room_name,
                                day=day,
                                start_time=start_time,
                                end_time=end_time,
                            )
                        )
                        placed = True
                        break

                    if not placed:
                        greedy_unscheduled.append(
                            {
                                "class": sess.class_name,
                                "subject": sess.subject_name,
                                "session": sess.k,
                                "reason": "No placement found in greedy fallback",
                            }
                        )

                if greedy_assignments:
                    day_order = {d: i for i, d in enumerate(day_names)}
                    greedy_assignments.sort(
                        key=lambda a: (a.school_class, day_order[a.day], a.start_time)
                    )
                    return TimetableResult(
                        assignments=greedy_assignments,
                        solved=False,
                        partial=True,
                        solve_time_seconds=round(solve_time, 3),
                        conflicts=(
                            conflicts
                            + [{"reason": solver.status_name(status)}]
                            + [{"reason": "GREEDY_FALLBACK_PARTIAL"}]
                        ),
                        unscheduled_sessions=domain_filtered_sessions + greedy_unscheduled,
                        soft_constraints_satisfied=[],
                        soft_constraints_violated=[],
                        warnings=solver_warnings + [
                            "Aucune solution complète trouvée dans le temps imparti: solution partielle générée par fallback glouton.",
                        ],
                        solver_diagnostics=solver_diagnostics,
                    )
            return TimetableResult(
                assignments=[],
                solved=False,
                solve_time_seconds=round(solve_time, 3),
                conflicts=conflicts or [{"reason": solver.status_name(status)}],
                unscheduled_sessions=domain_filtered_sessions,
                soft_constraints_satisfied=[],
                soft_constraints_violated=[],
                warnings=solver_warnings,
                solver_diagnostics=solver_diagnostics,
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
            if sess.needs_room and enforce_room_conflicts:
                fixed_r_idx = fixed_room_for_session.get(sess.idx)
                if fixed_r_idx is not None:
                    room_name = data.rooms[fixed_r_idx].name
                else:
                    for r_idx in sess.eligible_room_idxs:
                        bv = room_bvars.get((sess.idx, r_idx))
                        if bv is not None and solver.value(bv) == 1:
                            room_name = data.rooms[r_idx].name
                            break
            # When room conflicts are disabled, room assignment is intentionally
            # left empty (manual post-processing by the school).

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
            solver_diagnostics=solver_diagnostics,
        )
