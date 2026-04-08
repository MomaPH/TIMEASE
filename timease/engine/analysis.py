"""
Post-solve soft constraint analysis for TIMEASE.

SoftConstraintAnalyzer measures how well each soft constraint was respected
by looking at the final Assignment list.  It never touches the CP-SAT model —
pure Python over plain dataclasses.

Usage (called by TimetableSolver after extracting assignments)::

    analyzer = SoftConstraintAnalyzer(assignments, school_data)
    details  = analyzer.analyze(soft_constraints)
    # details: list[dict] — one entry per analyzed constraint

Each dict has:
    constraint_id        : str
    description_fr       : str    (from Constraint.description_fr)
    satisfaction_percent : float  (0–100)
    details_fr           : str    (human-readable measurement)
"""

from __future__ import annotations

import logging
import math
from collections import Counter, defaultdict

from timease.engine.models import Assignment, Constraint, SchoolData

logger = logging.getLogger(__name__)

# Constraints above this threshold are "satisfied"; below → "violated".
SATISFACTION_THRESHOLD: float = 80.0


class SoftConstraintAnalyzer:
    """
    Measures soft constraint satisfaction from the solved assignment list.

    Parameters
    ----------
    assignments : list[Assignment]
        The full list of scheduled sessions produced by the solver.
    school_data : SchoolData
        The original input (used for TimeslotConfig and class/room metadata).
    """

    def __init__(
        self,
        assignments: list[Assignment],
        school_data: SchoolData,
    ) -> None:
        self._a   = assignments
        self._sd  = school_data
        self._tc  = school_data.timeslot_config
        # Morning boundary: a session is "morning" if it starts before this.
        # Use first day's first session as reference
        first_day_sessions = self._tc.days[0].sessions if self._tc.days else []
        self._morning_end: str = (
            first_day_sessions[0].end_time if first_day_sessions else "12:00"
        )
        self._handlers = {
            "teacher_time_preference":     self._s1,
            "teacher_fallback_preference": self._s1,
            "balanced_daily_load":         self._s3,
            "subject_spread":              self._s4,
            "heavy_subjects_morning":      self._s5,
            "teacher_compact_schedule":    self._s6,
            "same_room_for_class":         self._s7,
            "teacher_day_off":             self._s8,
            "no_subject_back_to_back":     self._s9,
            "light_last_day":              self._s10,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, constraints: list[Constraint]) -> list[dict]:
        """
        Analyze every soft constraint and return one measurement dict per entry.
        Constraints with unknown categories are skipped with a warning log.
        """
        results: list[dict] = []
        for c in constraints:
            if c.type != "soft":
                continue
            handler = self._handlers.get(c.category)
            if handler is None:
                logger.warning(
                    "SoftConstraintAnalyzer: unknown category '%s' (%s) — skipped.",
                    c.category, c.id,
                )
                continue
            try:
                detail = handler(c)
                if detail is not None:
                    results.append(detail)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "SoftConstraintAnalyzer: error analyzing '%s': %s", c.id, exc
                )
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_min(t: str) -> int:
        """Convert "HH:MM" to total minutes."""
        h, m = t.split(":")
        return int(h) * 60 + int(m)

    def _is_morning(self, start_time: str) -> bool:
        """True when the session starts before the morning session ends."""
        return start_time < self._morning_end

    @staticmethod
    def _make(
        c: Constraint,
        pct: float,
        details_fr: str,
    ) -> dict:
        return {
            "constraint_id":        c.id,
            "description_fr":       c.description_fr,
            "satisfaction_percent": round(max(0.0, min(100.0, pct)), 1),
            "details_fr":           details_fr,
        }

    # ------------------------------------------------------------------
    # S1 / S2 — teacher_time_preference / teacher_fallback_preference
    #
    # Count how many of a teacher's sessions fall in their preferred period.
    # ------------------------------------------------------------------

    def _s1(self, c: Constraint) -> dict | None:
        teacher      = c.parameters.get("teacher", "")
        preferred    = c.parameters.get("preferred_session", "Matin")
        want_morning = preferred.lower() in ("matin", "morning")

        sessions = [a for a in self._a if a.teacher == teacher]
        total    = len(sessions)
        if total == 0:
            logger.debug("[%s] Aucune session trouvée pour '%s'.", c.id, teacher)
            return None

        morning_n       = sum(1 for a in sessions if self._is_morning(a.start_time))
        preferred_n     = morning_n if want_morning else (total - morning_n)
        pct             = preferred_n / total * 100
        period          = "matin" if want_morning else "après-midi"
        details_fr      = (
            f"{teacher} préfère le {period} — "
            f"{preferred_n}/{total} cours en {period} ({pct:.0f}%)"
        )
        return self._make(c, pct, details_fr)

    # ------------------------------------------------------------------
    # S3 — balanced_daily_load
    #
    # Compute per-class std-dev of daily teaching hours.
    # Lower std-dev → higher satisfaction.
    # Satisfaction: 100 % at 0 h std-dev, 0 % at ≥ 2 h std-dev.
    # ------------------------------------------------------------------

    def _s3(self, c: Constraint) -> dict | None:
        day_names = [d.name for d in self._tc.days]
        if not day_names:
            return None

        class_std_devs: list[float] = []
        summaries:       list[tuple[float, str]] = []  # (std_dev, label)

        for cls in sorted({a.school_class for a in self._a}):
            cls_a = [a for a in self._a if a.school_class == cls]
            hours = [
                sum(
                    (self._to_min(a.end_time) - self._to_min(a.start_time)) / 60
                    for a in cls_a if a.day == day
                )
                for day in day_names
            ]
            mean    = sum(hours) / len(hours)
            std_dev = math.sqrt(sum((h - mean) ** 2 for h in hours) / len(hours))
            class_std_devs.append(std_dev)
            quality = (
                "bon"          if std_dev < 0.5
                else "moyen"   if std_dev < 1.0
                else "à améliorer"
            )
            summaries.append((std_dev, f"{cls} ±{std_dev:.1f}h ({quality})"))

        if not class_std_devs:
            return None

        avg_std = sum(class_std_devs) / len(class_std_devs)
        pct     = (1.0 - avg_std / 2.0) * 100.0

        # Show the two worst classes
        top2    = "; ".join(label for _, label in sorted(summaries, reverse=True)[:2])
        details_fr = f"Écart-type moyen : ±{avg_std:.2f}h — {top2}"
        return self._make(c, pct, details_fr)

    # ------------------------------------------------------------------
    # S4 — subject_spread
    #
    # For every (class, subject) with ≥ 2 sessions/week, measure how many
    # distinct days the subject is spread across vs the maximum possible.
    # ------------------------------------------------------------------

    def _s4(self, c: Constraint) -> dict | None:
        n_days = len(self._tc.days)

        by_cs: dict[tuple[str, str], list[Assignment]] = defaultdict(list)
        for a in self._a:
            by_cs[(a.school_class, a.subject)].append(a)

        total_score = 0
        max_score   = 0
        worst:  list[tuple[float, str]] = []

        for (cls, subj), sessions in by_cs.items():
            n = len(sessions)
            if n < 2:
                continue
            distinct   = len({a.day for a in sessions})
            max_poss   = min(n, n_days)
            total_score += distinct
            max_score   += max_poss
            worst.append((distinct / max_poss, f"{subj} ({cls}): {distinct}/{max_poss} jours"))

        if max_score == 0:
            return self._make(
                c, 100.0,
                "Toutes les matières ont une seule session par semaine."
            )

        pct    = total_score / max_score * 100
        sample = "; ".join(label for _, label in sorted(worst)[:3])
        details_fr = f"{pct:.0f}% de répartition — moins bien répartis : {sample}"
        return self._make(c, pct, details_fr)

    # ------------------------------------------------------------------
    # S5 — heavy_subjects_morning
    #
    # Count how many sessions of the "heavy" subjects fall in the
    # preferred period (usually morning).
    # ------------------------------------------------------------------

    def _s5(self, c: Constraint) -> dict | None:
        subjects     = set(c.parameters.get("subjects", []))
        preferred    = c.parameters.get("preferred_session", "Matin")
        want_morning = preferred.lower() in ("matin", "morning")

        sessions = [a for a in self._a if a.subject in subjects]
        total    = len(sessions)
        if total == 0:
            return None

        morning_n   = sum(1 for a in sessions if self._is_morning(a.start_time))
        preferred_n = morning_n if want_morning else (total - morning_n)
        pct         = preferred_n / total * 100
        period      = "matin" if want_morning else "après-midi"
        subj_str    = ", ".join(sorted(subjects))
        details_fr  = (
            f"{subj_str} le {period} — "
            f"{preferred_n}/{total} sessions ({pct:.0f}%)"
        )
        return self._make(c, pct, details_fr)

    # ------------------------------------------------------------------
    # S6 — teacher_compact_schedule
    #
    # For each (teacher, day) with ≥ 2 sessions, compute the gap between
    # first and last session vs actual teaching time.  Average gap across
    # all days.  0 h gap → 100 %, ≥ 2 h avg gap → 0 %.
    # ------------------------------------------------------------------

    def _s6(self, c: Constraint) -> dict | None:
        target = c.parameters.get("teacher")  # None = all teachers

        by_td: dict[tuple[str, str], list[Assignment]] = defaultdict(list)
        for a in self._a:
            if target and a.teacher != target:
                continue
            by_td[(a.teacher, a.day)].append(a)

        gaps: list[float] = []
        for sessions in by_td.values():
            if len(sessions) < 2:
                continue
            span_start = min(self._to_min(a.start_time) for a in sessions)
            span_end   = max(self._to_min(a.end_time)   for a in sessions)
            teaching   = sum(
                self._to_min(a.end_time) - self._to_min(a.start_time)
                for a in sessions
            )
            gaps.append((span_end - span_start - teaching) / 60)

        if not gaps:
            return self._make(c, 100.0, "Aucun trou détecté dans les plannings.")

        avg_gap    = sum(gaps) / len(gaps)
        pct        = (1.0 - avg_gap / 2.0) * 100.0
        quality    = (
            "compact"     if avg_gap < 0.5
            else "moyen"  if avg_gap < 1.0
            else "fragmenté"
        )
        scope      = f"de {target}" if target else "de tous les enseignants"
        details_fr = f"Trous moyens {scope} : {avg_gap:.1f}h/jour ({quality})"
        return self._make(c, pct, details_fr)

    # ------------------------------------------------------------------
    # S7 — same_room_for_class
    #
    # For each class, find the most-used room and its share of all
    # room-using sessions.  Average that share across all classes.
    # ------------------------------------------------------------------

    def _s7(self, c: Constraint) -> dict | None:
        class_pcts:  list[float] = []
        worst_label: str         = ""
        worst_pct:   float       = 101.0

        for cls in sorted({a.school_class for a in self._a}):
            sessions = [a for a in self._a if a.school_class == cls and a.room]
            if not sessions:
                continue
            top_room, top_n = Counter(a.room for a in sessions).most_common(1)[0]
            room_pct = top_n / len(sessions) * 100
            class_pcts.append(room_pct)
            if room_pct < worst_pct:
                worst_pct   = room_pct
                worst_label = f"{cls} → {top_room} ({room_pct:.0f}%)"

        if not class_pcts:
            return None

        avg_pct    = sum(class_pcts) / len(class_pcts)
        details_fr = (
            f"Salle dominante utilisée en moyenne à {avg_pct:.0f}% — "
            f"plus dispersé : {worst_label}"
        )
        return self._make(c, avg_pct, details_fr)

    # ------------------------------------------------------------------
    # S8 — teacher_day_off
    #
    # Binary: 100 % if teacher has no sessions on their preferred day off,
    # 0 % otherwise.
    # ------------------------------------------------------------------

    def _s8(self, c: Constraint) -> dict | None:
        teacher     = c.parameters.get("teacher", "")
        pref_day    = c.parameters.get("preferred_day_off", "")
        if not teacher or not pref_day:
            logger.warning("[%s] S8 : paramètres 'teacher' ou 'preferred_day_off' manquants.", c.id)
            return None

        on_pref = [a for a in self._a if a.teacher == teacher and a.day == pref_day]
        if not on_pref:
            details_fr = f"{teacher} : pas de cours le {pref_day} — respecté"
            return self._make(c, 100.0, details_fr)

        n          = len(on_pref)
        details_fr = f"{teacher} : {n} cours le {pref_day} (non respecté)"
        return self._make(c, 0.0, details_fr)

    # ------------------------------------------------------------------
    # S9 — no_subject_back_to_back
    #
    # For every (class, day), sort sessions by time and find consecutive
    # pairs (end_time[i] == start_time[i+1]).  Count those where the two
    # sessions share the same subject.
    # pct = (1 − violations / consecutive_pairs) × 100
    # ------------------------------------------------------------------

    def _s9(self, c: Constraint) -> dict | None:
        target_subj = c.parameters.get("subject")  # None = all subjects

        by_cd: dict[tuple[str, str], list[Assignment]] = defaultdict(list)
        for a in self._a:
            if target_subj and a.subject != target_subj:
                continue
            by_cd[(a.school_class, a.day)].append(a)

        consecutive = 0
        violations  = 0
        for sessions in by_cd.values():
            ordered = sorted(sessions, key=lambda a: a.start_time)
            for i in range(len(ordered) - 1):
                a1, a2 = ordered[i], ordered[i + 1]
                if a1.end_time == a2.start_time:
                    consecutive += 1
                    if a1.subject == a2.subject:
                        violations += 1

        if consecutive == 0:
            return self._make(c, 100.0, "Aucune session adjacente détectée.")

        pct        = (1.0 - violations / consecutive) * 100.0
        scope      = f"de {target_subj}" if target_subj else "toutes matières"
        details_fr = (
            f"{violations} cours consécutifs de même matière "
            f"sur {consecutive} paires adjacentes ({scope})"
        )
        return self._make(c, pct, details_fr)

    # ------------------------------------------------------------------
    # S10 — light_last_day
    #
    # Compare the last day's total teaching hours (all classes combined)
    # to the daily average.
    # last ≤ avg  → 100 %
    # last = 2×avg → 0 %   (linear between avg and 2×avg)
    # ------------------------------------------------------------------

    def _s10(self, c: Constraint) -> dict | None:
        day_names = [d.name for d in self._tc.days]
        if not day_names:
            return None

        last_day      = day_names[-1]
        hours_per_day = {
            day: sum(
                (self._to_min(a.end_time) - self._to_min(a.start_time)) / 60
                for a in self._a if a.day == day
            )
            for day in day_names
        }
        avg_hours  = sum(hours_per_day.values()) / len(hours_per_day)
        last_hours = hours_per_day[last_day]

        if avg_hours == 0:
            return self._make(c, 100.0, "Aucune session planifiée.")

        if last_hours <= avg_hours:
            pct = 100.0
        else:
            # Linear: at last = avg → 100 %, at last = 2×avg → 0 %
            pct = (2.0 * avg_hours - last_hours) / avg_hours * 100.0

        quality    = (
            "léger"   if last_hours < avg_hours * 0.8
            else "normal" if last_hours <= avg_hours
            else "chargé"
        )
        details_fr = (
            f"Dernier jour ({last_day}) : {last_hours:.1f}h "
            f"vs {avg_hours:.1f}h/jour en moyenne ({quality})"
        )
        return self._make(c, pct, details_fr)
