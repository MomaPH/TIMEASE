"""
User-defined constraint applicator for TIMEASE.

ConstraintBuilder receives the CP-SAT model and all variable maps already
built by TimetableSolver, then applies the user-defined hard constraints
from SchoolData.constraints.

Supported constraint categories
--------------------------------
H1  start_time               — no session may start before a given hour
H2  start_time_exceptions     — H1 with per-level or per-day overrides
H3  day_off                   — entire day or session is blocked
H4  max_consecutive           — limit consecutive teaching slots per class
H5  subject_on_days           — subject must only appear on listed days
H6  subject_not_on_days       — subject must not appear on listed days
H7  subject_not_last_slot     — subject cannot occupy the last slot of the day
H8  min_break_between         — minimum gap between two sessions of same subject
H9  fixed_assignment          — force a specific (class, subject, day, slot)
H10 one_teacher_per_subject_per_class — one teacher per (class, subject) pair

All handlers add CP-SAT constraints (model.add / model.add_bool_and / etc.)
and never raise — unknown or inapplicable constraints produce a warning in
the returned list.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from ortools.sat.python import cp_model

from timease.engine.models import Constraint, SchoolData

if TYPE_CHECKING:
    from timease.engine.solver import _SessionSpec

logger = logging.getLogger(__name__)


class ConstraintBuilder:
    """
    Translates user-defined Constraint objects into CP-SAT model constraints.

    Parameters
    ----------
    model        : the cp_model.CpModel being built
    data         : full SchoolData (read-only)
    x            : Layer-1 BoolVars keyed by (class, subject, k, day, slot)
    teacher_x    : Layer-2 BoolVars keyed by (class, subject, k, day, slot, teacher)
    spec_for     : (class, subject) → _SessionSpec — sessions/duration per entry
    day_slot_times : day → [(start_time, end_time), ...] (chronological)
    curriculum_by_level : level → [CurriculumEntry, ...]
    """

    def __init__(
        self,
        model: cp_model.CpModel,
        data: SchoolData,
        x: dict,
        teacher_x: dict,
        spec_for: dict,
        day_slot_times: dict[str, list[tuple[str, str]]],
        curriculum_by_level: dict,
    ) -> None:
        self._model = model
        self._data = data
        self._x = x
        self._teacher_x = teacher_x
        self._spec_for = spec_for
        self._day_slot_times = day_slot_times
        self._curriculum_by_level = curriculum_by_level
        self._base_unit = data.timeslot_config.base_unit_minutes

        # Fast-lookup helpers
        self._class_by_name = {c.name: c for c in data.classes}
        self._subject_by_name = {s.name: s for s in data.subjects}
        self._sessions_by_name = {
            sess.name: sess for sess in data.timeslot_config.sessions
        }

        # Group x-vars by (day, slot) for H3 / H5 / H6 style blocking.
        self._x_by_day: dict[str, list[tuple]] = defaultdict(list)
        for key in x:
            _cn, _sn, _k, day, _s = key
            self._x_by_day[day].append(key)

        # Dispatch table: category → handler method
        self._handlers: dict[str, object] = {
            "start_time":                      self._h1_start_time,
            "start_time_exceptions":           self._h2_start_time_exceptions,
            "day_off":                         self._h3_day_off,
            "max_consecutive":                 self._h4_max_consecutive,
            "subject_on_days":                 self._h5_subject_on_days,
            "subject_not_on_days":             self._h6_subject_not_on_days,
            "subject_not_last_slot":           self._h7_subject_not_last_slot,
            "min_break_between":               self._h8_min_break_between,
            "fixed_assignment":                self._h9_fixed_assignment,
            "one_teacher_per_subject_per_class": self._h10_one_teacher_per_subject,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply_all(self, constraints: list[Constraint]) -> list[str]:
        """
        Apply every constraint in *constraints*.

        Returns a list of warning strings for constraints that were skipped
        or could not be fully applied.
        """
        warnings: list[str] = []
        for c in constraints:
            try:
                self._apply(c, warnings)
            except Exception as exc:  # noqa: BLE001
                msg = f"[{c.id}] Unexpected error applying '{c.category}': {exc}"
                logger.error(msg)
                warnings.append(msg)
        return warnings

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def _apply(self, c: Constraint, warnings: list[str]) -> None:
        handler = self._handlers.get(c.category)
        if handler is None:
            msg = f"[{c.id}] Unknown constraint category '{c.category}' — skipped."
            logger.warning(msg)
            warnings.append(msg)
            return
        logger.debug("Applying constraint %s (%s)", c.id, c.category)
        handler(c.parameters, warnings)  # type: ignore[call-arg]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _slot_in_session(self, day: str, slot_idx: int, session_name: str) -> bool:
        """Return True if the slot at *slot_idx* belongs to *session_name*."""
        sess = self._sessions_by_name.get(session_name)
        if sess is None:
            return False
        start_t, end_t = self._day_slot_times[day][slot_idx]
        return start_t >= sess.start_time and end_t <= sess.end_time

    def _slot_start_time(self, day: str, slot_idx: int) -> str:
        """Return the 'HH:MM' start time for a given slot index on a day."""
        return self._day_slot_times[day][slot_idx][0]

    def _slot_end_time(self, day: str, slot_idx: int) -> str:
        """Return the 'HH:MM' end time for a given slot index on a day."""
        return self._day_slot_times[day][slot_idx][1]

    # ------------------------------------------------------------------
    # H1 — start_time
    # ------------------------------------------------------------------

    def _h1_start_time(self, params: dict, warnings: list[str]) -> None:
        """
        Forbid any session from starting before params["hour"].

        All x-vars whose slot start_time < hour are forced to 0.

        Parameters
        ----------
        params : {"hour": "HH:MM"}
        """
        hour: str = params.get("hour", "")
        if not hour:
            warnings.append("H1 start_time: missing 'hour' parameter — skipped.")
            return

        blocked = 0
        for key, x_var in self._x.items():
            _cn, _sn, _k, day, s = key
            if self._slot_start_time(day, s) < hour:
                self._model.add(x_var == 0)
                blocked += 1

        logger.info("H1 start_time=%s: blocked %d placement vars", hour, blocked)

    # ------------------------------------------------------------------
    # H2 — start_time_exceptions
    # ------------------------------------------------------------------

    def _h2_start_time_exceptions(self, params: dict, warnings: list[str]) -> None:
        """
        H1 with per-level and/or per-day overrides.

        Parameters
        ----------
        params : {
            "default_hour": "HH:MM",
            "exceptions": [{"level": str, "day": str, "hour": "HH:MM"}, ...]
        }
        """
        default_hour: str = params.get("default_hour", "")
        exceptions: list[dict] = params.get("exceptions", [])

        if not default_hour:
            warnings.append("H2 start_time_exceptions: missing 'default_hour' — skipped.")
            return

        # Build an override map: (level_or_None, day_or_None) → hour
        override: dict[tuple[str | None, str | None], str] = {}
        for exc in exceptions:
            key = (exc.get("level"), exc.get("day"))
            override[key] = exc.get("hour", default_hour)

        blocked = 0
        for x_key, x_var in self._x.items():
            class_name, subject_name, _k, day, s = x_key
            klass = self._class_by_name.get(class_name)
            level = klass.level if klass else None

            # Pick the most specific override: (level, day) > (level, *) > (*, day) > default
            eff_hour = (
                override.get((level, day))
                or override.get((level, None))
                or override.get((None, day))
                or default_hour
            )
            if self._slot_start_time(day, s) < eff_hour:
                self._model.add(x_var == 0)
                blocked += 1

        logger.info("H2 start_time_exceptions: blocked %d placement vars", blocked)

    # ------------------------------------------------------------------
    # H3 — day_off
    # ------------------------------------------------------------------

    def _h3_day_off(self, params: dict, warnings: list[str]) -> None:
        """
        Block all placements on a given day, or within a specific session.

        Parameters
        ----------
        params : {"day": str, "session": str | None}
            session is optional; if absent or "all", the entire day is blocked.
        """
        target_day: str = params.get("day", "")
        target_session: str | None = params.get("session")

        if not target_day:
            warnings.append("H3 day_off: missing 'day' parameter — skipped.")
            return

        if target_day not in self._day_slot_times:
            warnings.append(
                f"H3 day_off: day '{target_day}' not in schedule — skipped."
            )
            return

        block_all = not target_session or target_session == "all"

        blocked = 0
        for key in self._x_by_day.get(target_day, []):
            _cn, _sn, _k, day, s = key
            if block_all or self._slot_in_session(day, s, target_session):  # type: ignore[arg-type]
                self._model.add(self._x[key] == 0)
                blocked += 1

        logger.info(
            "H3 day_off day=%s session=%s: blocked %d placement vars",
            target_day, target_session or "all", blocked,
        )

    # ------------------------------------------------------------------
    # H4 — max_consecutive
    # ------------------------------------------------------------------

    def _h4_max_consecutive(self, params: dict, warnings: list[str]) -> None:
        """
        For each class, at most *max_hours* consecutive teaching hours per day.

        Uses a sliding-window sum: in any window of (max_slots + 1) consecutive
        base-unit slots, the number of "occupied" slots must be ≤ max_slots.

        An "occupied" slot at index s is 1 iff any x-var for this class that
        covers slot s is chosen.

        Implementation note
        -------------------
        We pre-build a coverage index (class, day, slot) → [x-vars] in a
        single O(n) pass over all x-vars, so the constraint generation is
        O(classes × days × slots) rather than O(slots × x-vars).

        Parameters
        ----------
        params : {"max_hours": float}
            max_hours is converted to slots via base_unit_minutes.
        """
        max_hours: float = params.get("max_hours", 4)
        max_slots = int(max_hours * 60 / self._base_unit)

        if max_slots <= 0:
            warnings.append("H4 max_consecutive: max_hours too small — skipped.")
            return

        # ------------------------------------------------------------------
        # Build coverage index: (class_name, day, slot_idx) → [BoolVar]
        # One O(n) scan over all x-vars.
        # ------------------------------------------------------------------
        coverage: dict[tuple[str, str, int], list] = defaultdict(list)
        for key, x_var in self._x.items():
            class_name, subject_name, _k, day, start_s = key
            spec = self._spec_for.get((class_name, subject_name))
            dur = spec.duration_slots if spec else 1
            for offset in range(dur):
                coverage[(class_name, day, start_s + offset)].append(x_var)

        # ------------------------------------------------------------------
        # For each (class, day), build occupancy vars then sliding windows.
        # ------------------------------------------------------------------
        windows_added = 0
        for school_class in self._data.classes:
            cn = school_class.name
            for day, slots in self._day_slot_times.items():
                n = len(slots)
                if n <= max_slots:
                    continue  # day shorter than window — no constraint needed

                # occupied[s] = 1 iff any session covers base-unit slot s.
                occupied: list[cp_model.IntVar] = []
                for s in range(n):
                    covering = coverage.get((cn, day, s), [])
                    if not covering:
                        occupied.append(self._model.new_constant(0))
                    else:
                        occ = self._model.new_bool_var(f"occ|{cn}|{day}|s{s}")
                        # occ = max(covering) for BoolVars = OR
                        self._model.add_max_equality(occ, covering)
                        occupied.append(occ)

                # Sliding window: sum of any (max_slots+1) adjacent slots ≤ max_slots
                for w in range(n - max_slots):
                    self._model.add(sum(occupied[w : w + max_slots + 1]) <= max_slots)
                    windows_added += 1

        logger.info("H4 max_consecutive=%dh (%d slots): added %d window constraints",
                    max_hours, max_slots, windows_added)

    # ------------------------------------------------------------------
    # H5 — subject_on_days
    # ------------------------------------------------------------------

    def _h5_subject_on_days(self, params: dict, warnings: list[str]) -> None:
        """
        A subject may only be scheduled on the listed days.

        Parameters
        ----------
        params : {"subject": str, "days": [str, ...]}
        """
        subject_name: str = params.get("subject", "")
        allowed_days: list[str] = params.get("days", [])

        if not subject_name or not allowed_days:
            warnings.append("H5 subject_on_days: missing 'subject' or 'days' — skipped.")
            return

        blocked = 0
        for key, x_var in self._x.items():
            _cn, sn, _k, day, _s = key
            if sn == subject_name and day not in allowed_days:
                self._model.add(x_var == 0)
                blocked += 1

        logger.info("H5 subject_on_days %s → %s: blocked %d vars", subject_name, allowed_days, blocked)

    # ------------------------------------------------------------------
    # H6 — subject_not_on_days
    # ------------------------------------------------------------------

    def _h6_subject_not_on_days(self, params: dict, warnings: list[str]) -> None:
        """
        A subject must not be scheduled on the listed days.

        Parameters
        ----------
        params : {"subject": str, "days": [str, ...]}
        """
        subject_name: str = params.get("subject", "")
        blocked_days: list[str] = params.get("days", [])

        if not subject_name or not blocked_days:
            warnings.append("H6 subject_not_on_days: missing 'subject' or 'days' — skipped.")
            return

        blocked = 0
        for key, x_var in self._x.items():
            _cn, sn, _k, day, _s = key
            if sn == subject_name and day in blocked_days:
                self._model.add(x_var == 0)
                blocked += 1

        logger.info("H6 subject_not_on_days %s on %s: blocked %d vars", subject_name, blocked_days, blocked)

    # ------------------------------------------------------------------
    # H7 — subject_not_last_slot
    # ------------------------------------------------------------------

    def _h7_subject_not_last_slot(self, params: dict, warnings: list[str]) -> None:
        """
        The given subject's session may not overlap the last slot of the day.

        A session of duration D starting at slot s covers slots s…s+D-1.
        The session must not cover the last slot, so:
            s + D - 1 < len(day_slots) - 1  →  s < len(day_slots) - D

        Parameters
        ----------
        params : {"subject": str}
        """
        subject_name: str = params.get("subject", "")
        if not subject_name:
            warnings.append("H7 subject_not_last_slot: missing 'subject' — skipped.")
            return

        blocked = 0
        for key, x_var in self._x.items():
            class_name, sn, _k, day, s = key
            if sn != subject_name:
                continue
            spec = self._spec_for.get((class_name, sn))
            if spec is None:
                continue
            n = len(self._day_slot_times[day])
            # If the session's last slot index (s + dur - 1) == last slot of day
            if s + spec.duration_slots - 1 >= n - 1:
                self._model.add(x_var == 0)
                blocked += 1

        logger.info("H7 subject_not_last_slot %s: blocked %d vars", subject_name, blocked)

    # ------------------------------------------------------------------
    # H8 — min_break_between
    # ------------------------------------------------------------------

    def _h8_min_break_between(self, params: dict, warnings: list[str]) -> None:
        """
        Between two sessions of the same subject for the same class on the
        same day, there must be at least *min_break_minutes* of gap.

        Implementation: for every pair of x-vars (session i, session j) for
        the same (class, subject, day), enforce that they don't end up less
        than min_break_slots apart.

        Because CP-SAT requires deterministic ordering, we use:
            if x_i = 1 and x_j = 1 then |s_i - s_j| >= min_break + dur_i

        We implement this with a disjunction:
            s_j >= s_i + dur_i + gap  OR  s_i >= s_j + dur_j + gap

        using auxiliary BoolVars and only_enforce_if.

        Parameters
        ----------
        params : {"subject": str, "min_break_minutes": int}
        """
        subject_name: str = params.get("subject", "")
        min_break_min: int = params.get("min_break_minutes", 0)
        gap_slots = max(0, min_break_min // self._base_unit)

        if not subject_name:
            warnings.append("H8 min_break_between: missing 'subject' — skipped.")
            return
        if gap_slots == 0:
            warnings.append(f"H8 min_break_between {subject_name}: gap_slots=0, no constraint added.")
            return

        # Group x-vars by (class, subject, day)
        groups: dict[tuple[str, str, str], list[tuple[int, object]]] = defaultdict(list)
        for key, x_var in self._x.items():
            class_name, sn, _k, day, s = key
            if sn == subject_name:
                groups[(class_name, sn, day)].append((s, x_var))

        pair_count = 0
        for (cn, sn, day), items in groups.items():
            spec = self._spec_for.get((cn, sn))
            dur = spec.duration_slots if spec else 1
            if len(items) < 2:
                continue
            for i in range(len(items)):
                s_i, xv_i = items[i]
                for j in range(i + 1, len(items)):
                    s_j, xv_j = items[j]
                    # Both active → must be far enough apart.
                    # |s_i - s_j| >= dur + gap
                    min_sep = dur + gap_slots
                    if abs(s_i - s_j) >= min_sep:
                        continue  # already satisfied structurally

                    # They are too close — they cannot both be chosen.
                    self._model.add_bool_and([xv_i.negated(), xv_j.negated()])  # type: ignore[union-attr]
                    pair_count += 1

        logger.info("H8 min_break_between %s gap=%d slots: added %d pair constraints",
                    subject_name, gap_slots, pair_count)

    # ------------------------------------------------------------------
    # H9 — fixed_assignment
    # ------------------------------------------------------------------

    def _h9_fixed_assignment(self, params: dict, warnings: list[str]) -> None:
        """
        Force a specific (class, subject, day, start_time) assignment.

        The x-var matching (class, subject, k=0, day, slot_with_start=start_time)
        is forced to 1; all other x-vars for the same (class, subject, k=0)
        triple are forced to 0.

        If no matching x-var exists, a warning is emitted.

        Parameters
        ----------
        params : {"class": str, "subject": str, "day": str, "start_time": "HH:MM"}
        """
        class_name: str = params.get("class", "")
        subject_name: str = params.get("subject", "")
        day: str = params.get("day", "")
        start_time: str = params.get("start_time", "")

        if not all([class_name, subject_name, day, start_time]):
            warnings.append("H9 fixed_assignment: missing required params — skipped.")
            return

        # Find slot index for start_time on this day
        target_slot: int | None = None
        for idx, (st, _et) in enumerate(self._day_slot_times.get(day, [])):
            if st == start_time:
                target_slot = idx
                break

        if target_slot is None:
            warnings.append(
                f"H9 fixed_assignment: no slot at {start_time} on {day} — skipped."
            )
            return

        found = False
        for key, x_var in self._x.items():
            cn, sn, _k, d, s = key
            if cn != class_name or sn != subject_name:
                continue
            if d == day and s == target_slot:
                self._model.add(x_var == 1)
                found = True
            else:
                self._model.add(x_var == 0)

        if not found:
            warnings.append(
                f"H9 fixed_assignment: no x-var for {class_name}/{subject_name} "
                f"on {day} at slot {target_slot} — constraint has no effect."
            )
            return

        logger.info(
            "H9 fixed_assignment: pinned %s / %s to %s %s (slot %d)",
            class_name, subject_name, day, start_time, target_slot,
        )

    # ------------------------------------------------------------------
    # H10 — one_teacher_per_subject_per_class
    # ------------------------------------------------------------------

    def _h10_one_teacher_per_subject(self, params: dict, warnings: list[str]) -> None:
        """
        Exactly one teacher is assigned to each (class, subject) pair for the
        entire week — no mixing of teachers for the same subject across sessions.

        Implementation — "designated teacher" pattern:
        -----------------------------------------------
        For each (class, subject) pair, collect all teacher names that appear
        in teacher_x for that pair.  Create one BoolVar desig[T] per teacher
        meaning "T is THE teacher for this (class, subject) this week".

        add_exactly_one(desig_vars) — exactly one teacher is designated.

        Then: if desig[T] = 0 → force all t[class, subject, *, *, *, T] = 0.
        This is encoded as:
            desig[T] = 0  →  t_var = 0  for every session of this teacher.

        Parameters
        ----------
        params : {}  (no parameters required)
        """
        # Group teacher_x by (class, subject)
        pairs: dict[tuple[str, str], dict[str, list]] = defaultdict(lambda: defaultdict(list))
        for key, t_var in self._teacher_x.items():
            class_name, subject_name, _k, _day, _s, teacher_name = key
            pairs[(class_name, subject_name)][teacher_name].append(t_var)

        designation_count = 0
        for (class_name, subject_name), teachers in pairs.items():
            if len(teachers) <= 1:
                # Only one possible teacher — no constraint needed.
                continue

            # Create one BoolVar per candidate teacher.
            desig: dict[str, cp_model.IntVar] = {}
            for teacher_name in teachers:
                desig[teacher_name] = self._model.new_bool_var(
                    f"desig|{class_name}|{subject_name}|{teacher_name}"
                )

            # Exactly one teacher is designated.
            self._model.add_exactly_one(list(desig.values()))

            # If a teacher is NOT designated, all their t_vars for this pair are 0.
            for teacher_name, t_vars in teachers.items():
                d_var = desig[teacher_name]
                for t_var in t_vars:
                    # desig[T] = 0  →  t_var = 0
                    self._model.add(t_var == 0).only_enforce_if(d_var.negated())

            designation_count += 1

        logger.info(
            "H10 one_teacher_per_subject_per_class: added designation constraints for %d (class, subject) pairs",
            designation_count,
        )
