"""
User-defined constraint applicator for TIMEASE — compact IntVar model.

ConstraintBuilder  — hard constraints applied as CP-SAT model constraints.
SoftConstraintBuilder — soft preferences expressed as objective terms.

Both builders operate on the compact IntVar model produced by TimetableSolver:
  • start_vars[i]  : IntVar — global timeline position of session i
  • room_bvars[(i, r_idx)] : BoolVar — session i uses room r_idx

Global timeline
---------------
    global_slot = day_idx × n_slots_per_day + slot_within_day

Because sessions only have valid start positions in their domain (no cross-day
or cross-break positions), a single add_no_overlap per class and per teacher
covers all days simultaneously.

Domain-level constraints (applied before model build in solver.py)
-------------------------------------------------------------------
H1  start_time               — minimum start hour
H3  day_off                  — blocked day or session block
H5  subject_on_days          — subject restricted to listed days
H6  subject_not_on_days      — subject excluded from listed days
H7  subject_not_last_slot    — subject cannot occupy last slot of day

Model constraints (applied here by ConstraintBuilder)
------------------------------------------------------
H2  start_time_exceptions    — per-level/per-day start hour overrides
H4  max_consecutive          — max consecutive teaching hours per class
H8  min_break_between        — minimum gap between sessions of same subject
H9  fixed_assignment         — force specific (class, subject, day, slot)
H10 one_teacher_per_subject_per_class — auto-satisfied by pre-assignment (no-op)
H11 min_sessions_per_day    — at least N sessions per class per configured day

Soft preference categories (SoftConstraintBuilder)
---------------------------------------------------
S1  teacher_time_preference       — teacher prefers morning/afternoon
S2  teacher_fallback_preference   — cascading preference
S3  balanced_daily_load           — even hours per class across days
S4  subject_spread                — same subject not twice on the same day
S5  heavy_subjects_morning        — heavy subjects preferably in the morning
S6  teacher_compact_schedule      — minimise gaps in teacher's daily timetable
S7  same_room_for_class           — class sessions concentrated in one room
S8  teacher_day_off               — teacher prefers no sessions on a given day
S9  no_subject_back_to_back       — avoid consecutive sessions of same subject
S10 light_last_day                — few sessions on the last day of the week
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from ortools.sat.python import cp_model
from ortools.sat.python.cp_model import Domain

from timease.engine.models import Constraint, SchoolData

if TYPE_CHECKING:
    from timease.engine.solver import _Session, _SessionSpec

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helper — on_day BoolVar cache
# ---------------------------------------------------------------------------

class _OnDayCache:
    """
    Creates and caches on_day[session_idx][day_idx] BoolVars.

    on_day[i][d] == 1  iff  start_vars[i] is on day d.

    Uses two reified range constraints per (session, day) plus
    add_exactly_one to enforce that exactly one day is selected.
    """

    def __init__(
        self,
        model: cp_model.CpModel,
        start_vars: dict[int, cp_model.IntVar],
        session_domains: list[list[int]],
        n_slots_per_day: int,
        n_days: int,
    ) -> None:
        self._model           = model
        self._start_vars      = start_vars
        self._session_domains = session_domains
        self._n               = n_slots_per_day
        self._n_days          = n_days
        self._cache: dict[tuple[int, int], cp_model.IntVar] = {}
        self._initialized: set[int] = set()

    def get(self, sess_idx: int, d_idx: int) -> cp_model.IntVar:
        """Return (creating if needed) on_day BoolVar for (sess_idx, d_idx)."""
        if sess_idx not in self._initialized:
            self._init_session(sess_idx)
        return self._cache[(sess_idx, d_idx)]

    def _init_session(self, sess_idx: int) -> None:
        """
        Create all on_day BoolVars for one session.

        For each day d, on_day[i][d] == 1 iff start_var[i] is on that day.

        Encoding: two reified range constraints per (session, day) plus
        add_exactly_one to force a unique day assignment.
        """
        self._initialized.add(sess_idx)
        n   = self._n
        dom = self._session_domains[sess_idx]
        sv  = self._start_vars[sess_idx]

        days_in_domain = {v // n for v in dom}

        bvars: list[cp_model.IntVar] = []
        for d in range(self._n_days):
            b = self._model.new_bool_var(f"od|{sess_idx}|{d}")
            self._cache[(sess_idx, d)] = b
            bvars.append(b)

            if d not in days_in_domain:
                self._model.add(b == 0)
            else:
                # b == 1  ↔  start_var in day-d range [d*n, (d+1)*n - 1]
                self._model.add(sv >= d * n).only_enforce_if(b)
                self._model.add(sv <= (d + 1) * n - 1).only_enforce_if(b)

        if len(days_in_domain) > 1:
            self._model.add_exactly_one(bvars)


# ---------------------------------------------------------------------------
# ConstraintBuilder — hard constraints
# ---------------------------------------------------------------------------

class ConstraintBuilder:
    """
    Translate user-defined hard Constraint objects into CP-SAT model constraints.

    Parameters
    ----------
    model            : CpModel being built
    data             : full SchoolData (read-only)
    sessions         : list of _Session objects (indexed by idx)
    start_vars       : session_idx → IntVar (global timeline position)
    n_slots_per_day  : number of base-unit slots per day (same for all days)
    day_slot_times   : day → [(start_time, end_time), ...]
    sessions_by_class   : class_name → [session_idx, ...]
    sessions_by_subject : subject_name → [session_idx, ...]
    session_domains  : list[list[int]] — domain for each session
    tc               : TimeslotConfig
    """

    def __init__(
        self,
        model: cp_model.CpModel,
        data: SchoolData,
        sessions: list,
        start_vars: dict[int, cp_model.IntVar],
        n_slots_per_day: int,
        day_slot_times: dict[str, list[tuple[str, str]]],
        sessions_by_class: dict[str, list[int]],
        sessions_by_subject: dict[str, list[int]],
        session_domains: list[list[int]],
        tc,
    ) -> None:
        self._model            = model
        self._data             = data
        self._sessions         = sessions
        self._start_vars       = start_vars
        self._n                = n_slots_per_day
        self._day_slot_times   = day_slot_times
        self._sessions_by_class   = sessions_by_class
        self._sessions_by_subject = sessions_by_subject
        self._session_domains  = session_domains
        self._tc               = tc
        self._n_days           = len(tc.days)
        self._day_idx          = {d: i for i, d in enumerate(tc.days)}
        self._base_unit        = data.timeslot_config.base_unit_minutes

        self._on_day = _OnDayCache(
            model, start_vars, session_domains, n_slots_per_day, self._n_days
        )

        self._handlers = {
            "start_time":                        self._h1_domain_only,
            "start_time_exceptions":             self._h2_start_time_exceptions,
            "day_off":                           self._h3_domain_only,
            "max_consecutive":                   self._h4_max_consecutive,
            "subject_on_days":                   self._h5_domain_only,
            "subject_not_on_days":               self._h6_domain_only,
            "subject_not_last_slot":             self._h7_domain_only,
            "min_break_between":                 self._h8_min_break_between,
            "fixed_assignment":                  self._h9_fixed_assignment,
            "one_teacher_per_subject_per_class": self._h10_no_op,
            "min_sessions_per_day":              self._h11_min_sessions_per_day,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply_all(self, constraints: list[Constraint]) -> list[str]:
        """Apply all constraints; return warning strings for skipped ones."""
        warnings: list[str] = []
        for c in constraints:
            try:
                handler = self._handlers.get(c.category)
                if handler is None:
                    warnings.append(
                        f"[{c.id}] Unknown category '{c.category}' — skipped."
                    )
                else:
                    logger.debug("Applying %s (%s)", c.id, c.category)
                    handler(c, warnings)
            except Exception as exc:  # noqa: BLE001
                msg = f"[{c.id}] Error applying '{c.category}': {exc}"
                logger.error(msg)
                warnings.append(msg)
        return warnings

    # ------------------------------------------------------------------
    # Domain-only handlers (already applied in solver.py)
    # ------------------------------------------------------------------

    def _h1_domain_only(self, c: Constraint, warnings: list[str]) -> None:
        logger.debug("[%s] start_time already applied via domain pre-filtering.", c.id)

    def _h3_domain_only(self, c: Constraint, warnings: list[str]) -> None:
        logger.debug("[%s] day_off already applied via domain pre-filtering.", c.id)

    def _h5_domain_only(self, c: Constraint, warnings: list[str]) -> None:
        logger.debug("[%s] subject_on_days already applied via domain pre-filtering.", c.id)

    def _h6_domain_only(self, c: Constraint, warnings: list[str]) -> None:
        logger.debug("[%s] subject_not_on_days already applied via domain pre-filtering.", c.id)

    def _h7_domain_only(self, c: Constraint, warnings: list[str]) -> None:
        logger.debug("[%s] subject_not_last_slot already applied via domain pre-filtering.", c.id)

    # ------------------------------------------------------------------
    # H2 — start_time_exceptions
    # ------------------------------------------------------------------

    def _h2_start_time_exceptions(self, c: Constraint, warnings: list[str]) -> None:
        """
        Per-level / per-day start-hour overrides.  Applied by restricting
        start_var domains further.

        Parameters: {"default_hour": "HH:MM", "exceptions": [{level, day, hour}]}
        """
        p            = c.parameters
        default_hour = p.get("default_hour", "")
        exceptions   = p.get("exceptions", [])

        if not default_hour:
            warnings.append(f"[{c.id}] H2: missing 'default_hour' — skipped.")
            return

        override: dict[tuple[str | None, str | None], str] = {}
        for exc in exceptions:
            override[(exc.get("level"), exc.get("day"))] = exc.get("hour", default_hour)

        class_level = {cl.name: cl.level for cl in self._data.classes}
        n = self._n

        blocked = 0
        for sess in self._sessions:
            level = class_level.get(sess.class_name)
            dom   = self._session_domains[sess.idx]
            new_dom: list[int] = []
            for gpos in dom:
                d_idx = gpos // n
                s     = gpos % n
                day   = self._tc.days[d_idx]
                start_t = self._day_slot_times[day][s][0]
                eff_hour = (
                    override.get((level, day))
                    or override.get((level, None))
                    or override.get((None, day))
                    or default_hour
                )
                if start_t >= eff_hour:
                    new_dom.append(gpos)
                else:
                    blocked += 1
            if new_dom != dom:
                self._session_domains[sess.idx] = new_dom
                sv = self._start_vars[sess.idx]
                if new_dom:
                    self._model.add_linear_expression_in_domain(sv, Domain.from_values(new_dom))
                else:
                    self._model.add(sv == -1)  # force infeasibility

        logger.info("[%s] H2: blocked %d positions across sessions.", c.id, blocked)

    # ------------------------------------------------------------------
    # H4 — max_consecutive
    # ------------------------------------------------------------------

    def _h4_max_consecutive(self, c: Constraint, warnings: list[str]) -> None:
        """
        Limit consecutive teaching hours per class per session block.

        Because sessions cannot cross the morning/afternoon break (enforced by
        domain construction), "max consecutive" equals max load within any
        single session block (Matin, Après-midi, etc.).

        Optimisation: if max_hours ≥ longest block (in hours), the constraint
        is already satisfied by the physical session structure — no model
        constraints are added.

        Parameters: {"max_hours": int}
        """
        max_hours = c.parameters.get("max_hours")
        if max_hours is None:
            warnings.append(f"[{c.id}] H4: missing 'max_hours' parameter — skipped.")
            return

        max_slots = max_hours * 60 // self._base_unit
        n         = self._n

        # Compute block sizes from the reference day
        ref_day   = self._tc.days[0]
        ref_slots = self._day_slot_times[ref_day]

        block_of_slot: list[int] = [0]
        current_block = 0
        for i in range(1, len(ref_slots)):
            if ref_slots[i - 1][1] != ref_slots[i][0]:
                current_block += 1
            block_of_slot.append(current_block)
        n_blocks = current_block + 1

        # Count slots per block
        block_sizes = [
            sum(1 for b in block_of_slot if b == blk)
            for blk in range(n_blocks)
        ]
        max_block_size = max(block_sizes) if block_sizes else 0

        # Fast exit: if every block fits within max_slots, the constraint is
        # automatically satisfied — no model constraints needed.
        if max_slots >= max_block_size:
            logger.info(
                "[%s] H4: max_consecutive=%dh ≥ longest block (%d slots) — "
                "auto-satisfied by session structure, no constraints added.",
                c.id, max_hours, max_block_size,
            )
            return

        # Need explicit constraints: cap total load per (class, day, block)
        for class_name, s_idxs in self._sessions_by_class.items():
            for d_idx in range(self._n_days):
                for blk in range(n_blocks):
                    block_slots = {
                        s for s, b in enumerate(block_of_slot) if b == blk
                    }

                    load_terms = []
                    for i in s_idxs:
                        sess = self._sessions[i]
                        blk_positions = [
                            gpos for gpos in self._session_domains[i]
                            if gpos // n == d_idx and (gpos % n) in block_slots
                        ]
                        if not blk_positions:
                            continue

                        on_blk = self._model.new_bool_var(
                            f"h4|{class_name}|{i}|d{d_idx}|b{blk}"
                        )
                        self._model.add_linear_expression_in_domain(
                            self._start_vars[i], Domain.from_values(blk_positions)
                        ).only_enforce_if(on_blk)
                        not_blk = [
                            gpos for gpos in self._session_domains[i]
                            if gpos not in set(blk_positions)
                        ]
                        if not_blk:
                            self._model.add_linear_expression_in_domain(
                                self._start_vars[i], Domain.from_values(not_blk)
                            ).only_enforce_if(on_blk.Not())
                        else:
                            self._model.add(on_blk == 1)

                        load_terms.append(on_blk * sess.dur_slots)

                    if len(load_terms) > 1:
                        self._model.add(sum(load_terms) <= max_slots)

        logger.info("[%s] H4: max consecutive %dh enforced (blocks larger than limit).", c.id, max_hours)

    # ------------------------------------------------------------------
    # H8 — min_break_between
    # ------------------------------------------------------------------

    def _h8_min_break_between(self, c: Constraint, warnings: list[str]) -> None:
        """
        Minimum gap (in slots) between any two sessions of the same subject
        for the same class on the same day.

        Parameters: {"subject": str, "min_break_slots": int}
                    OR {"subject": str, "min_break_minutes": int}
        """
        p       = c.parameters
        subject = p.get("subject", "")
        if not subject:
            warnings.append(f"[{c.id}] H8: missing 'subject' — skipped.")
            return

        min_break_slots: int = p.get("min_break_slots") or (
            (p.get("min_break_minutes", 0)) // self._base_unit
        )
        if min_break_slots <= 0:
            warnings.append(f"[{c.id}] H8: min_break_slots must be > 0 — skipped.")
            return

        n = self._n
        s_idxs = self._sessions_by_subject.get(subject, [])

        # Group by class; pairs within same class on the same day need gap
        by_class: dict[str, list[int]] = defaultdict(list)
        for i in s_idxs:
            by_class[self._sessions[i].class_name].append(i)

        added = 0
        for class_name, idxs in by_class.items():
            for a in range(len(idxs)):
                for b in range(a + 1, len(idxs)):
                    ia, ib = idxs[a], idxs[b]
                    dur_a  = self._sessions[ia].dur_slots
                    dur_b  = self._sessions[ib].dur_slots
                    sv_a   = self._start_vars[ia]
                    sv_b   = self._start_vars[ib]

                    # Force minimum gap when on the same day:
                    # same_day indicator
                    same_day = self._model.new_bool_var(
                        f"h8|{c.id}|{class_name}|{ia}|{ib}|sameday"
                    )
                    # same_day = 1 iff sv_a // n == sv_b // n
                    # Approximate by: |sv_a - sv_b| < n  (sufficient for our days)
                    diff = self._model.new_int_var(-n * self._n_days, n * self._n_days,
                                                   f"h8|diff|{ia}|{ib}")
                    self._model.add(diff == sv_a - sv_b)
                    abs_diff = self._model.new_int_var(0, n * self._n_days,
                                                       f"h8|abs|{ia}|{ib}")
                    self._model.add_max_equality(abs_diff, [diff, -diff])

                    self._model.add(abs_diff < n).only_enforce_if(same_day)
                    self._model.add(abs_diff >= n).only_enforce_if(same_day.Not())

                    # If same day: sv_b >= sv_a + dur_a + min_break OR
                    #              sv_a >= sv_b + dur_b + min_break
                    after_b = self._model.new_bool_var(f"h8|ab|{ia}|{ib}")
                    self._model.add(sv_b >= sv_a + dur_a + min_break_slots).only_enforce_if(
                        [same_day, after_b]
                    )
                    self._model.add(sv_a >= sv_b + dur_b + min_break_slots).only_enforce_if(
                        [same_day, after_b.Not()]
                    )
                    added += 1

        logger.info("[%s] H8: added gap constraints for %d session pairs.", c.id, added)

    # ------------------------------------------------------------------
    # H9 — fixed_assignment
    # ------------------------------------------------------------------

    def _h9_fixed_assignment(self, c: Constraint, warnings: list[str]) -> None:
        """
        Force a specific (class, subject, day, slot) assignment.

        Parameters: {"class": str, "subject": str, "day": str, "slot_start": "HH:MM"}
        """
        p          = c.parameters
        class_name = p.get("class", "")
        subject    = p.get("subject", "")
        day        = p.get("day", "")
        slot_start = p.get("slot_start", "")

        if not all([class_name, subject, day, slot_start]):
            warnings.append(f"[{c.id}] H9: missing required parameter — skipped.")
            return

        d_idx = {d: i for i, d in enumerate(self._tc.days)}.get(day)
        if d_idx is None:
            warnings.append(f"[{c.id}] H9: day '{day}' not in schedule — skipped.")
            return

        day_slots = self._day_slot_times.get(day, [])
        s = next((i for i, (st, _) in enumerate(day_slots) if st == slot_start), None)
        if s is None:
            warnings.append(f"[{c.id}] H9: slot_start '{slot_start}' not found on {day} — skipped.")
            return

        gpos = d_idx * self._n + s
        fixed = 0
        for sess in self._sessions:
            if sess.class_name == class_name and sess.subject_name == subject:
                if gpos in self._session_domains[sess.idx]:
                    self._model.add(self._start_vars[sess.idx] == gpos)
                    fixed += 1
                    break  # only first unassigned session k

        logger.info("[%s] H9: fixed %d session(s) to %s %s %s.", c.id, fixed, class_name, day, slot_start)

    # ------------------------------------------------------------------
    # H10 — one_teacher_per_subject_per_class (no-op)
    # ------------------------------------------------------------------

    def _h10_no_op(self, c: Constraint, warnings: list[str]) -> None:
        """Satisfied automatically by teacher pre-assignment — nothing to add."""

    # ------------------------------------------------------------------
    # H11 — min_sessions_per_day
    # ------------------------------------------------------------------

    def _h11_min_sessions_per_day(self, c: Constraint, warnings: list[str]) -> None:
        """
        Require at least ``min_sessions`` sessions per class on every
        configured day.  Applies to all classes.

        Parameters
        ----------
        min_sessions : int   (default 1)
            Minimum number of sessions each class must have on each day.
        """
        min_n = int(c.parameters.get("min_sessions", 1))
        if min_n <= 0:
            warnings.append(
                f"[{c.id}] H11: 'min_sessions' must be ≥ 1 (got {min_n}) — skipped."
            )
            return

        added = 0
        for cls_name, sess_idxs in self._sessions_by_class.items():
            if not sess_idxs:
                continue
            for d_idx in range(self._n_days):
                day_bvars = [self._on_day.get(i, d_idx) for i in sess_idxs]
                self._model.add(sum(day_bvars) >= min_n)
                added += 1

        logger.info(
            "[%s] H11: min %d session(s)/day enforced across %d (class × day) pairs.",
            c.id, min_n, added,
        )


# ---------------------------------------------------------------------------
# SoftConstraintBuilder — soft preferences / objective
# ---------------------------------------------------------------------------

class SoftConstraintBuilder:
    """
    Translate soft Constraint objects into (coefficient, IntVar) objective terms.

    Parameters
    ----------
    model             : CpModel
    data              : SchoolData (read-only)
    sessions          : list[_Session]
    start_vars        : session_idx → IntVar
    n_slots_per_day   : int
    n_morning_slots   : int — how many slots belong to the morning session
    day_slot_times    : day → [(start_time, end_time), ...]
    sessions_by_class : class_name → [session_idx, ...]
    sessions_by_teacher: teacher_name → [session_idx, ...]
    sessions_by_subject: subject_name → [session_idx, ...]
    session_domains   : list[list[int]]
    room_bvars        : (session_idx, room_idx) → BoolVar
    tc                : TimeslotConfig
    """

    def __init__(
        self,
        model: cp_model.CpModel,
        data: SchoolData,
        sessions: list,
        start_vars: dict[int, cp_model.IntVar],
        n_slots_per_day: int,
        n_morning_slots: int,
        day_slot_times: dict[str, list[tuple[str, str]]],
        sessions_by_class: dict[str, list[int]],
        sessions_by_teacher: dict[str, list[int]],
        sessions_by_subject: dict[str, list[int]],
        session_domains: list[list[int]],
        room_bvars: dict[tuple[int, int], cp_model.IntVar],
        tc,
    ) -> None:
        self._model              = model
        self._data               = data
        self._sessions           = sessions
        self._start_vars         = start_vars
        self._n                  = n_slots_per_day
        self._n_morning          = n_morning_slots
        self._day_slot_times     = day_slot_times
        self._sessions_by_class  = sessions_by_class
        self._sessions_by_teacher = sessions_by_teacher
        self._sessions_by_subject = sessions_by_subject
        self._session_domains    = session_domains
        self._room_bvars         = room_bvars
        self._tc                 = tc
        self._n_days             = len(tc.days)

        # Shared on_day cache — one BoolVar per (session_idx, day_idx)
        self._on_day = _OnDayCache(
            model, start_vars, session_domains, n_slots_per_day, self._n_days
        )

        self._handlers = {
            "teacher_time_preference":       self._s1_teacher_time_preference,
            "teacher_fallback_preference":   self._s2_teacher_fallback_preference,
            "balanced_daily_load":           self._s3_balanced_daily_load,
            "subject_spread":                self._s4_subject_spread,
            "heavy_subjects_morning":        self._s5_heavy_subjects_morning,
            "teacher_compact_schedule":      self._s6_teacher_compact_schedule,
            "same_room_for_class":           self._s7_same_room_for_class,
            "teacher_day_off":               self._s8_teacher_day_off,
            "no_subject_back_to_back":       self._s9_no_subject_back_to_back,
            "light_last_day":                self._s10_light_last_day,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply_all(
        self, constraints: list[Constraint]
    ) -> tuple[list[tuple[int, cp_model.IntVar]], dict, list[str]]:
        """
        Apply all soft constraints.

        Returns
        -------
        obj_terms  : list of (coefficient, IntVar) to be maximised
        sat_vars   : dict[constraint_id, BoolVar | None]
        warnings   : list of warning strings
        """
        obj_terms: list[tuple[int, cp_model.IntVar]] = []
        sat_vars:  dict[str, cp_model.IntVar | None] = {}
        warnings:  list[str] = []

        for c in constraints:
            try:
                handler = self._handlers.get(c.category)
                if handler is None:
                    warnings.append(
                        f"[{c.id}] Unknown soft category '{c.category}' — skipped."
                    )
                    continue
                terms, sv, w = handler(c)
                obj_terms.extend(terms)
                sat_vars[c.id] = sv
                warnings.extend(w)
            except Exception as exc:  # noqa: BLE001
                msg = f"[{c.id}] Error applying '{c.category}': {exc}"
                logger.error(msg)
                warnings.append(msg)

        return obj_terms, sat_vars, warnings

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _morning_bvar(self, sess_idx: int) -> cp_model.IntVar | None:
        """
        Return a BoolVar = 1 iff session sess_idx is placed in the morning block.
        Returns None if the result is constant (always or never morning).
        """
        dom = self._session_domains[sess_idx]
        n   = self._n
        morning_vals    = [v for v in dom if v % n < self._n_morning]
        not_morning_vals = [v for v in dom if v % n >= self._n_morning]

        if not not_morning_vals:
            return self._model.new_constant(1)
        if not morning_vals:
            return self._model.new_constant(0)

        b = self._model.new_bool_var(f"morn|{sess_idx}")
        self._model.add_linear_expression_in_domain(
            self._start_vars[sess_idx], Domain.from_values(morning_vals)
        ).only_enforce_if(b)
        self._model.add_linear_expression_in_domain(
            self._start_vars[sess_idx], Domain.from_values(not_morning_vals)
        ).only_enforce_if(b.Not())
        return b

    # ------------------------------------------------------------------
    # S1 — teacher_time_preference
    # ------------------------------------------------------------------

    def _s1_teacher_time_preference(
        self, c: Constraint
    ) -> tuple[list, cp_model.IntVar | None, list[str]]:
        """
        Reward sessions where the teacher's preferred half is respected.

        Parameters: {"teacher": str, "preferred_session": "Matin"|"Après-midi"}
        """
        p        = c.parameters
        teacher  = p.get("teacher", "")
        preferred = p.get("preferred_session", "Matin")
        priority  = c.priority or 5
        warnings: list[str] = []

        want_morning = preferred.lower() in ("matin", "morning", "matin")
        terms: list[tuple[int, cp_model.IntVar]] = []

        for i in self._sessions_by_teacher.get(teacher, []):
            b = self._morning_bvar(i)
            if b is None:
                continue
            if want_morning:
                terms.append((priority, b))
            else:
                terms.append((priority, b.Not()))

        return terms, None, warnings

    # ------------------------------------------------------------------
    # S2 — teacher_fallback_preference
    # ------------------------------------------------------------------

    def _s2_teacher_fallback_preference(
        self, c: Constraint
    ) -> tuple[list, cp_model.IntVar | None, list[str]]:
        """
        Same as S1 with lower priority — used as a fallback default.
        Parameters: same as S1 but lower priority.
        """
        return self._s1_teacher_time_preference(c)

    # ------------------------------------------------------------------
    # S3 — balanced_daily_load
    # ------------------------------------------------------------------

    def _s3_balanced_daily_load(
        self, c: Constraint
    ) -> tuple[list, cp_model.IntVar | None, list[str]]:
        """
        Penalise daily loads that exceed the average, pulling sessions toward
        even distribution across the week.

        For each class and each day d:
            excess_d = max(0, load_d - target)
        Minimise sum(excess_d).  This avoids add_max_equality / add_min_equality
        and keeps the LP relaxation tight.

        Parameters: {}
        """
        priority = c.priority or 7
        terms: list[tuple[int, cp_model.IntVar]] = []
        warnings: list[str] = []

        for class_name, s_idxs in self._sessions_by_class.items():
            total_dur = sum(self._sessions[i].dur_slots for i in s_idxs)
            target    = total_dur // self._n_days

            # Tight upper bound: max load on any day ≤ n_slots_per_day
            # (physical limit of the day).  Excess is at most this minus target.
            max_day_load = self._n  # n_slots_per_day
            max_excess   = max(0, max_day_load - target)

            if max_excess == 0:
                continue  # perfectly divisible — no excess possible

            for d in range(self._n_days):
                load_d_terms = [
                    self._on_day.get(i, d) * self._sessions[i].dur_slots
                    for i in s_idxs
                ]
                # excess_d = max(0, load_d - target)
                # Encoded as: excess_d >= load_d - target  (domain clamps to ≥ 0)
                excess = self._model.new_int_var(
                    0, max_excess, f"s3|{c.id}|{class_name}|d{d}"
                )
                self._model.add(excess >= sum(load_d_terms) - target)
                terms.append((-priority, excess))

        return terms, None, warnings

    # ------------------------------------------------------------------
    # S4 — subject_spread
    # ------------------------------------------------------------------

    def _s4_subject_spread(
        self, c: Constraint
    ) -> tuple[list, cp_model.IntVar | None, list[str]]:
        """
        Penalise placing two sessions of the same subject on the same day
        for the same class.  For each (class, subject) with >1 session/week,
        count how many days have more than one session and minimise that.

        Parameters: {}
        """
        priority = c.priority or 8
        terms: list[tuple[int, cp_model.IntVar]] = []
        warnings: list[str] = []

        for class_name, c_idxs in self._sessions_by_class.items():
            by_subject: dict[str, list[int]] = defaultdict(list)
            for i in c_idxs:
                by_subject[self._sessions[i].subject_name].append(i)

            for subject, s_idxs in by_subject.items():
                if len(s_idxs) < 2:
                    continue
                # For each day, count how many sessions of this subject fall on that day
                for d in range(self._n_days):
                    on_day_vars = [self._on_day.get(i, d) for i in s_idxs]
                    # excess = max(0, count_on_day - 1)
                    count = sum(on_day_vars)
                    max_excess = len(s_idxs) - 1
                    excess = self._model.new_int_var(0, max_excess,
                                                     f"s4|{c.id}|{class_name}|{subject}|d{d}")
                    self._model.add(excess >= count - 1)
                    terms.append((-priority, excess))

        return terms, None, warnings

    # ------------------------------------------------------------------
    # S5 — heavy_subjects_morning
    # ------------------------------------------------------------------

    def _s5_heavy_subjects_morning(
        self, c: Constraint
    ) -> tuple[list, cp_model.IntVar | None, list[str]]:
        """
        Reward placing "heavy" subjects (Maths, Français, etc.) in the morning.
        One BoolVar per session of those subjects.

        Parameters: {"subjects": [str], "preferred_session": "Matin"}
        """
        p         = c.parameters
        subjects  = set(p.get("subjects", []))
        preferred = p.get("preferred_session", "Matin")
        priority  = c.priority or 6
        warnings: list[str] = []

        want_morning = preferred.lower() in ("matin", "morning")
        terms: list[tuple[int, cp_model.IntVar]] = []

        for subject in subjects:
            for i in self._sessions_by_subject.get(subject, []):
                b = self._morning_bvar(i)
                if b is None:
                    continue
                if want_morning:
                    terms.append((priority, b))
                else:
                    terms.append((priority, b.Not()))

        return terms, None, warnings

    # ------------------------------------------------------------------
    # S6 — teacher_compact_schedule
    # ------------------------------------------------------------------

    def _s6_teacher_compact_schedule(
        self, c: Constraint
    ) -> tuple[list, cp_model.IntVar | None, list[str]]:
        """
        Minimise gaps in a teacher's daily schedule.

        For each (teacher, day): gap = last_occupied_slot - first_occupied_slot
                                       - total_occupied_slots + 1
        A compact schedule has gap = 0.

        Implementation: for each teacher, on each day, use on_day BoolVars
        to find first/last/total occupied slots.

        Parameters: {}  (or {"teacher": str} to target a specific teacher)
        """
        priority = c.priority or 5
        target   = c.parameters.get("teacher")  # None = all teachers
        warnings: list[str] = []
        terms: list[tuple[int, cp_model.IntVar]] = []

        n = self._n

        for teacher_name, t_idxs in self._sessions_by_teacher.items():
            if target and teacher_name != target:
                continue

            for d in range(self._n_days):
                # Sessions of this teacher that CAN be on day d
                can_be_on_day = [
                    i for i in t_idxs
                    if any(v // n == d for v in self._session_domains[i])
                ]
                if len(can_be_on_day) < 2:
                    continue

                on_day_vars = [self._on_day.get(i, d) for i in can_be_on_day]
                sess_objects = [self._sessions[i] for i in can_be_on_day]

                # Total occupied slots on day d
                total_occ = sum(
                    od * sess.dur_slots
                    for od, sess in zip(on_day_vars, sess_objects)
                )
                max_total = sum(s.dur_slots for s in sess_objects)
                tot_var = self._model.new_int_var(0, max_total,
                                                  f"s6|tot|{teacher_name}|d{d}")
                self._model.add(tot_var == total_occ)

                # Build "effective start" of session i on day d (slot within day)
                # eff_start[i] = (start_var[i] % n) * on_day[i]  — only meaningful if on day d
                # We want min(eff_start) and max(eff_end) across active sessions.

                day_positions_per_sess = [
                    [v % n for v in self._session_domains[i] if v // n == d]
                    for i in can_be_on_day
                ]

                # Minimum possible start and maximum possible end across active sessions
                global_min = min((min(pos) for pos in day_positions_per_sess if pos), default=0)
                global_max = max(
                    (max(pos) + sess.dur_slots - 1
                     for pos, sess in zip(day_positions_per_sess, sess_objects)
                     if pos),
                    default=n - 1,
                )

                first_var = self._model.new_int_var(global_min, global_max,
                                                    f"s6|first|{teacher_name}|d{d}")
                last_var  = self._model.new_int_var(global_min, global_max,
                                                    f"s6|last|{teacher_name}|d{d}")

                # first_var <= effective_start of each active session
                # last_var  >= effective_end   of each active session
                for od, sess, day_pos in zip(on_day_vars, sess_objects, day_positions_per_sess):
                    if not day_pos:
                        continue
                    min_start = min(day_pos)
                    max_end   = max(day_pos) + sess.dur_slots - 1

                    # When session is on day d (od=1):
                    # derive its local start from start_var
                    i = sess.idx
                    sv = self._start_vars[i]

                    # Local slot of session i on day d
                    # = sv - d * n  (when sv // n == d)
                    local_start = self._model.new_int_var(
                        min_start, min_start + (max_end - min_start),
                        f"s6|ls|{i}|d{d}"
                    )
                    self._model.add(local_start == sv - d * n).only_enforce_if(od)
                    self._model.add(local_start == global_min).only_enforce_if(od.Not())

                    local_end = self._model.new_int_var(
                        global_min, global_max,
                        f"s6|le|{i}|d{d}"
                    )
                    self._model.add(local_end == local_start + sess.dur_slots - 1).only_enforce_if(od)
                    self._model.add(local_end == global_min).only_enforce_if(od.Not())

                    self._model.add(first_var <= local_start)
                    self._model.add(last_var  >= local_end)

                # gap = last_var - first_var + 1 - tot_var  (negative if compact)
                # We want to maximize -gap = minimize gap
                # Simplification: maximize (tot_var - last_var + first_var - 1)
                # = maximize tot_var - (last_var - first_var + 1)
                # Since we maximize: add terms (+priority, first_var), (-priority, last_var),
                #                    (+priority, tot_var)
                terms.append((priority, first_var))
                terms.append((-priority, last_var))
                terms.append((priority, tot_var))

        return terms, None, warnings

    # ------------------------------------------------------------------
    # S7 — same_room_for_class
    # ------------------------------------------------------------------

    def _s7_same_room_for_class(
        self, c: Constraint
    ) -> tuple[list, cp_model.IntVar | None, list[str]]:
        """
        Reward using the same room for all sessions of a class (where possible).

        For each class, for each room, sum room_bvars across all sessions of
        that class that can use that room.  Maximise the maximum such sum.

        Parameters: {}
        """
        priority = c.priority or 4
        warnings: list[str] = []
        terms: list[tuple[int, cp_model.IntVar]] = []

        n_rooms = len(self._data.rooms)
        for class_name, s_idxs in self._sessions_by_class.items():
            for r_idx in range(n_rooms):
                room_vars = [
                    self._room_bvars[(i, r_idx)]
                    for i in s_idxs
                    if (i, r_idx) in self._room_bvars
                ]
                if len(room_vars) < 2:
                    continue
                total = self._model.new_int_var(0, len(room_vars),
                                                f"s7|{c.id}|{class_name}|r{r_idx}")
                self._model.add(total == sum(room_vars))
                terms.append((priority, total))

        return terms, None, warnings

    # ------------------------------------------------------------------
    # S8 — teacher_day_off
    # ------------------------------------------------------------------

    def _s8_teacher_day_off(
        self, c: Constraint
    ) -> tuple[list, cp_model.IntVar | None, list[str]]:
        """
        Prefer a specific day to have no sessions for a teacher.

        Parameters: {"teacher": str, "day": str}
        """
        p        = c.parameters
        teacher  = p.get("teacher", "")
        day      = p.get("day", "")
        priority = c.priority or 5
        warnings: list[str] = []

        d_idx = next((i for i, d in enumerate(self._tc.days) if d == day), None)
        if not teacher or d_idx is None:
            warnings.append(f"[{c.id}] S8: missing teacher or day — skipped.")
            return [], None, warnings

        terms: list[tuple[int, cp_model.IntVar]] = []
        for i in self._sessions_by_teacher.get(teacher, []):
            od = self._on_day.get(i, d_idx)
            # Reward NOT being on this day
            terms.append((priority, od.Not()))

        return terms, None, warnings

    # ------------------------------------------------------------------
    # S9 — no_subject_back_to_back
    # ------------------------------------------------------------------

    def _s9_no_subject_back_to_back(
        self, c: Constraint
    ) -> tuple[list, cp_model.IntVar | None, list[str]]:
        """
        Penalise two sessions of the same subject scheduled back-to-back for
        the same class on the same day.

        Parameters: {} or {"subject": str} to limit to one subject.
        """
        priority  = c.priority or 6
        target_sb = c.parameters.get("subject")
        warnings: list[str] = []
        terms: list[tuple[int, cp_model.IntVar]] = []

        n = self._n

        for class_name, c_idxs in self._sessions_by_class.items():
            by_subject: dict[str, list[int]] = defaultdict(list)
            for i in c_idxs:
                sn = self._sessions[i].subject_name
                if target_sb and sn != target_sb:
                    continue
                by_subject[sn].append(i)

            for subject, s_idxs in by_subject.items():
                if len(s_idxs) < 2:
                    continue
                for a in range(len(s_idxs)):
                    for b in range(a + 1, len(s_idxs)):
                        ia, ib = s_idxs[a], s_idxs[b]
                        dur_a  = self._sessions[ia].dur_slots
                        dur_b  = self._sessions[ib].dur_slots
                        sv_a   = self._start_vars[ia]
                        sv_b   = self._start_vars[ib]

                        # back_to_back: sv_b == sv_a + dur_a OR sv_a == sv_b + dur_b
                        # AND both on the same day
                        btb = self._model.new_bool_var(
                            f"s9|{c.id}|{class_name}|{subject}|{ia}|{ib}"
                        )
                        # Penalise if back-to-back
                        terms.append((-priority, btb))

                        # Encode: btb = 1 iff (sv_b == sv_a + dur_a OR sv_a == sv_b + dur_b)
                        # AND same day
                        adj1 = self._model.new_bool_var(f"s9|adj1|{ia}|{ib}")
                        adj2 = self._model.new_bool_var(f"s9|adj2|{ia}|{ib}")
                        diff = self._model.new_int_var(
                            -n * self._n_days, n * self._n_days, f"s9|diff|{ia}|{ib}"
                        )
                        self._model.add(diff == sv_b - sv_a)
                        self._model.add(diff == dur_a).only_enforce_if(adj1)
                        self._model.add(diff != dur_a).only_enforce_if(adj1.Not())
                        self._model.add(diff == -dur_b).only_enforce_if(adj2)
                        self._model.add(diff != -dur_b).only_enforce_if(adj2.Not())

                        self._model.add(btb <= adj1 + adj2)

        return terms, None, warnings

    # ------------------------------------------------------------------
    # S10 — light_last_day
    # ------------------------------------------------------------------

    def _s10_light_last_day(
        self, c: Constraint
    ) -> tuple[list, cp_model.IntVar | None, list[str]]:
        """
        Minimise the number of sessions on the last day of the week.

        Parameters: {} or {"day": str} to specify the target day.
        """
        priority = c.priority or 4
        warnings: list[str] = []
        terms: list[tuple[int, cp_model.IntVar]] = []

        target_day = c.parameters.get("day", self._tc.days[-1])
        d_idx = next(
            (i for i, d in enumerate(self._tc.days) if d == target_day), None
        )
        if d_idx is None:
            warnings.append(f"[{c.id}] S10: day '{target_day}' not in schedule — skipped.")
            return [], None, warnings

        for i in range(len(self._sessions)):
            od = self._on_day.get(i, d_idx)
            # Reward NOT being on last day
            terms.append((priority, od.Not()))

        return terms, None, warnings
