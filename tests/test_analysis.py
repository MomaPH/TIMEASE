"""
Tests for timease/engine/analysis.py — SoftConstraintAnalyzer.

All tests use hand-crafted Assignment lists; no solver invocation needed.

Run with:  uv run pytest
"""

from __future__ import annotations

import pytest

from timease.engine.analysis import SATISFACTION_THRESHOLD, SoftConstraintAnalyzer
from timease.engine.models import (
    Assignment,
    Constraint,
    CurriculumEntry,
    Room,
    School,
    SchoolClass,
    SchoolData,
    SessionConfig,
    Subject,
    Teacher,
    TimeslotConfig,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def minimal_sd() -> SchoolData:
    """Minimal SchoolData used as an analysis context (not solved)."""
    return SchoolData(
        school=School("Test", "2026-2027", "Dakar"),
        timeslot_config=TimeslotConfig(
            days=["lundi", "mardi", "mercredi", "jeudi", "vendredi"],
            sessions=[
                SessionConfig("Matin",       "08:00", "12:00"),
                SessionConfig("Après-midi",  "15:00", "17:00"),
            ],
            base_unit_minutes=30,
        ),
        subjects=[
            Subject("Maths",   "M",  "#FFF"),
            Subject("Français","Fr", "#FFF"),
            Subject("EPS",     "EPS","#FFF", needs_room=False),
        ],
        teachers=[
            Teacher("M. Alpha",  ["Maths"],    max_hours_per_week=18),
            Teacher("Mme Bêta",  ["Français"], max_hours_per_week=18),
        ],
        classes=[SchoolClass("6A", "6ème", 30)],
        rooms=[
            Room("Salle 1", 40, ["Salle standard"]),
            Room("Salle 2", 40, ["Salle standard"]),
        ],
        curriculum=[
            CurriculumEntry("6ème", "Maths",    300, sessions_per_week=5, minutes_per_session=60),
            CurriculumEntry("6ème", "Français", 300, sessions_per_week=5, minutes_per_session=60),
        ],
        constraints=[],
    )


def _a(
    cls:     str = "6A",
    subject: str = "Maths",
    teacher: str = "M. Alpha",
    day:     str = "lundi",
    start:   str = "08:00",
    end:     str = "09:00",
    room:    str | None = "Salle 1",
) -> Assignment:
    return Assignment(
        school_class=cls, subject=subject, teacher=teacher,
        day=day, start_time=start, end_time=end, room=room,
    )


def _c(
    cid:      str,
    category: str,
    params:   dict | None = None,
    priority: int = 5,
) -> Constraint:
    return Constraint(
        id=cid, type="soft", category=category,
        description_fr=f"Test {cid}",
        priority=priority,
        parameters=params or {},
    )


def _analyzer(assignments: list[Assignment], sd: SchoolData) -> SoftConstraintAnalyzer:
    return SoftConstraintAnalyzer(assignments, sd)


# ---------------------------------------------------------------------------
# 1. analyze() — routing and edge cases
# ---------------------------------------------------------------------------

class TestAnalyzeRouting:
    def test_hard_constraints_skipped(self, minimal_sd: SchoolData) -> None:
        hard = Constraint(id="H1", type="hard", category="start_time",
                          description_fr="Dur", priority=5, parameters={})
        an = _analyzer([_a()], minimal_sd)
        assert an.analyze([hard]) == []

    def test_unknown_category_skipped(self, minimal_sd: SchoolData) -> None:
        c = _c("X1", "nonexistent_category")
        an = _analyzer([_a()], minimal_sd)
        assert an.analyze([c]) == []

    def test_detail_keys_present(self, minimal_sd: SchoolData) -> None:
        c  = _c("S5", "heavy_subjects_morning",
                 {"subjects": ["Maths"], "preferred_session": "Matin"})
        an = _analyzer([_a(start="08:00", end="09:00")], minimal_sd)
        details = an.analyze([c])
        assert len(details) == 1
        d = details[0]
        assert "constraint_id"        in d
        assert "description_fr"       in d
        assert "satisfaction_percent" in d
        assert "details_fr"           in d

    def test_satisfaction_percent_clamped_0_100(self, minimal_sd: SchoolData) -> None:
        c  = _c("S5", "heavy_subjects_morning",
                 {"subjects": ["Maths"], "preferred_session": "Matin"})
        # All sessions morning → 100 %
        assignments = [_a(start="08:00", end="09:00") for _ in range(5)]
        an = _analyzer(assignments, minimal_sd)
        d  = an.analyze([c])[0]
        assert 0.0 <= d["satisfaction_percent"] <= 100.0

    def test_satisfaction_threshold_constant(self) -> None:
        assert SATISFACTION_THRESHOLD == 80.0


# ---------------------------------------------------------------------------
# 2. S1 / S2 — teacher_time_preference
# ---------------------------------------------------------------------------

class TestS1TeacherTimePreference:
    def test_all_morning_is_100_pct(self, minimal_sd: SchoolData) -> None:
        sessions = [_a(teacher="M. Alpha", start="08:00", end="09:00") for _ in range(5)]
        c  = _c("S1", "teacher_time_preference",
                 {"teacher": "M. Alpha", "preferred_session": "Matin"})
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == 100.0

    def test_all_afternoon_when_prefers_afternoon_is_100_pct(
        self, minimal_sd: SchoolData
    ) -> None:
        sessions = [_a(teacher="M. Alpha", start="15:00", end="16:00") for _ in range(4)]
        c  = _c("S1", "teacher_time_preference",
                 {"teacher": "M. Alpha", "preferred_session": "Après-midi"})
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == 100.0

    def test_mixed_80_pct(self, minimal_sd: SchoolData) -> None:
        # 8 morning, 2 afternoon
        sessions = (
            [_a(teacher="M. Alpha", start="08:00", end="09:00")] * 8
            + [_a(teacher="M. Alpha", start="15:00", end="16:00")] * 2
        )
        c  = _c("S1", "teacher_time_preference",
                 {"teacher": "M. Alpha", "preferred_session": "Matin"})
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == pytest.approx(80.0)
        assert "8/10" in d["details_fr"]

    def test_unknown_teacher_returns_no_detail(self, minimal_sd: SchoolData) -> None:
        c  = _c("S1", "teacher_time_preference",
                 {"teacher": "Mme Fantôme", "preferred_session": "Matin"})
        an = _analyzer([_a()], minimal_sd)
        assert an.analyze([c]) == []

    def test_teacher_fallback_preference_same_as_s1(
        self, minimal_sd: SchoolData
    ) -> None:
        sessions = [_a(teacher="M. Alpha", start="08:00", end="09:00")] * 3
        c1 = _c("S1", "teacher_time_preference",
                 {"teacher": "M. Alpha", "preferred_session": "Matin"})
        c2 = _c("S2", "teacher_fallback_preference",
                 {"teacher": "M. Alpha", "preferred_session": "Matin"})
        an = _analyzer(sessions, minimal_sd)
        d1 = an.analyze([c1])[0]
        d2 = an.analyze([c2])[0]
        assert d1["satisfaction_percent"] == d2["satisfaction_percent"]


# ---------------------------------------------------------------------------
# 3. S3 — balanced_daily_load
# ---------------------------------------------------------------------------

class TestS3BalancedDailyLoad:
    def _sd_5days(self, minimal_sd: SchoolData) -> SchoolData:
        return minimal_sd  # already 5 days

    def test_perfectly_balanced_gives_high_satisfaction(
        self, minimal_sd: SchoolData
    ) -> None:
        # 1h per day per class → std_dev = 0 → 100 %
        sessions = [
            _a(cls="6A", day=day, start="08:00", end="09:00")
            for day in ["lundi", "mardi", "mercredi", "jeudi", "vendredi"]
        ]
        c  = _c("S3", "balanced_daily_load")
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == pytest.approx(100.0)

    def test_all_on_one_day_gives_low_satisfaction(
        self, minimal_sd: SchoolData
    ) -> None:
        # 5h on Monday, 0h on everything else → high std_dev
        sessions = [_a(cls="6A", day="lundi", start="08:00", end="09:00")] * 5
        c  = _c("S3", "balanced_daily_load")
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] < 80.0

    def test_detail_contains_stddev(self, minimal_sd: SchoolData) -> None:
        sessions = [_a(cls="6A", day="lundi", start="08:00", end="09:00")]
        c  = _c("S3", "balanced_daily_load")
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert "±" in d["details_fr"]

    def test_satisfaction_decreases_with_imbalance(
        self, minimal_sd: SchoolData
    ) -> None:
        balanced = [
            _a(cls="6A", day=day, start="08:00", end="09:00")
            for day in ["lundi", "mardi", "mercredi", "jeudi", "vendredi"]
        ]
        unbalanced = [_a(cls="6A", day="lundi", start="08:00", end="09:00")] * 5
        c  = _c("S3", "balanced_daily_load")
        an_b = _analyzer(balanced,   minimal_sd)
        an_u = _analyzer(unbalanced, minimal_sd)
        pct_b = an_b.analyze([c])[0]["satisfaction_percent"]
        pct_u = an_u.analyze([c])[0]["satisfaction_percent"]
        assert pct_b > pct_u


# ---------------------------------------------------------------------------
# 4. S4 — subject_spread
# ---------------------------------------------------------------------------

class TestS4SubjectSpread:
    def test_perfectly_spread_gives_100_pct(self, minimal_sd: SchoolData) -> None:
        # 5 Maths sessions on 5 different days
        sessions = [
            _a(subject="Maths", day=day)
            for day in ["lundi", "mardi", "mercredi", "jeudi", "vendredi"]
        ]
        c  = _c("S4", "subject_spread")
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == pytest.approx(100.0)

    def test_all_on_same_day_gives_low_pct(self, minimal_sd: SchoolData) -> None:
        # 5 Maths sessions all on Monday
        sessions = [_a(subject="Maths", day="lundi")] * 5
        c  = _c("S4", "subject_spread")
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] < 50.0

    def test_single_session_subjects_skipped(self, minimal_sd: SchoolData) -> None:
        # Only 1 Maths session — cannot spread, so result should be 100 %
        sessions = [_a(subject="Maths", day="lundi")]
        c  = _c("S4", "subject_spread")
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == pytest.approx(100.0)

    def test_partial_spread(self, minimal_sd: SchoolData) -> None:
        # 4 sessions on 2 days: max_possible = min(4,5)=4; actual=2 → 50 %
        sessions = (
            [_a(subject="Maths", day="lundi")] * 2
            + [_a(subject="Maths", day="mardi")] * 2
        )
        c  = _c("S4", "subject_spread")
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# 5. S5 — heavy_subjects_morning
# ---------------------------------------------------------------------------

class TestS5HeavySubjectsMorning:
    def test_all_morning_is_100_pct(self, minimal_sd: SchoolData) -> None:
        sessions = [_a(subject="Maths", start="08:00", end="09:00")] * 6
        c  = _c("S5", "heavy_subjects_morning",
                 {"subjects": ["Maths"], "preferred_session": "Matin"})
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == pytest.approx(100.0)

    def test_all_afternoon_is_0_pct(self, minimal_sd: SchoolData) -> None:
        sessions = [_a(subject="Maths", start="15:00", end="16:00")] * 6
        c  = _c("S5", "heavy_subjects_morning",
                 {"subjects": ["Maths"], "preferred_session": "Matin"})
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == pytest.approx(0.0)

    def test_mixed_percentage(self, minimal_sd: SchoolData) -> None:
        sessions = (
            [_a(subject="Maths",    start="08:00", end="09:00")] * 3
            + [_a(subject="Français", start="08:00", end="09:00")] * 3
            + [_a(subject="Maths",    start="15:00", end="16:00")] * 2
            + [_a(subject="Français", start="15:00", end="16:00")] * 2
        )
        c  = _c("S5", "heavy_subjects_morning",
                 {"subjects": ["Maths", "Français"], "preferred_session": "Matin"})
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == pytest.approx(60.0)

    def test_subject_not_in_assignments_returns_no_detail(
        self, minimal_sd: SchoolData
    ) -> None:
        c  = _c("S5", "heavy_subjects_morning",
                 {"subjects": ["Philosophie"], "preferred_session": "Matin"})
        an = _analyzer([_a()], minimal_sd)
        assert an.analyze([c]) == []

    def test_detail_contains_subject_name(self, minimal_sd: SchoolData) -> None:
        sessions = [_a(subject="Maths", start="08:00", end="09:00")]
        c  = _c("S5", "heavy_subjects_morning",
                 {"subjects": ["Maths"], "preferred_session": "Matin"})
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert "Maths" in d["details_fr"]


# ---------------------------------------------------------------------------
# 6. S6 — teacher_compact_schedule
# ---------------------------------------------------------------------------

class TestS6TeacherCompactSchedule:
    def test_no_gaps_is_100_pct(self, minimal_sd: SchoolData) -> None:
        # Consecutive sessions: 08:00-09:00, 09:00-10:00 — no gap
        sessions = [
            _a(teacher="M. Alpha", day="lundi", start="08:00", end="09:00"),
            _a(teacher="M. Alpha", day="lundi", start="09:00", end="10:00"),
        ]
        c  = _c("S6", "teacher_compact_schedule")
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == pytest.approx(100.0)

    def test_gap_reduces_satisfaction(self, minimal_sd: SchoolData) -> None:
        # 08:00-09:00 then 11:00-12:00 → 2h span, 1h teaching → 1h gap
        sessions = [
            _a(teacher="M. Alpha", day="lundi", start="08:00", end="09:00"),
            _a(teacher="M. Alpha", day="lundi", start="11:00", end="12:00"),
        ]
        c  = _c("S6", "teacher_compact_schedule")
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] < 80.0

    def test_single_session_per_day_no_gap(self, minimal_sd: SchoolData) -> None:
        # Only 1 session per day — can't compute gap, should return 100 %
        sessions = [_a(teacher="M. Alpha", day="lundi", start="08:00", end="09:00")]
        c  = _c("S6", "teacher_compact_schedule")
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == pytest.approx(100.0)

    def test_target_teacher_filter(self, minimal_sd: SchoolData) -> None:
        # Gap for M. Alpha, compact for Mme Bêta — targeting M. Alpha should show gap
        sessions = [
            _a(teacher="M. Alpha", day="lundi", start="08:00", end="09:00"),
            _a(teacher="M. Alpha", day="lundi", start="11:00", end="12:00"),
            _a(teacher="Mme Bêta", day="lundi", start="08:00", end="09:00"),
            _a(teacher="Mme Bêta", day="lundi", start="09:00", end="10:00"),
        ]
        c_all    = _c("S6", "teacher_compact_schedule")
        c_alpha  = _c("S6b", "teacher_compact_schedule", {"teacher": "M. Alpha"})
        an       = _analyzer(sessions, minimal_sd)
        pct_all  = an.analyze([c_all])[0]["satisfaction_percent"]
        pct_only = an.analyze([c_alpha])[0]["satisfaction_percent"]
        # Targeting M. Alpha (who has gaps) should be worse than including compact Bêta
        assert pct_only <= pct_all


# ---------------------------------------------------------------------------
# 7. S7 — same_room_for_class
# ---------------------------------------------------------------------------

class TestS7SameRoomForClass:
    def test_always_same_room_is_100_pct(self, minimal_sd: SchoolData) -> None:
        sessions = [_a(cls="6A", room="Salle 1") for _ in range(5)]
        c  = _c("S7", "same_room_for_class")
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == pytest.approx(100.0)

    def test_split_equally_is_50_pct(self, minimal_sd: SchoolData) -> None:
        sessions = (
            [_a(cls="6A", room="Salle 1")] * 3
            + [_a(cls="6A", room="Salle 2")] * 3
        )
        c  = _c("S7", "same_room_for_class")
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == pytest.approx(50.0)

    def test_no_room_assignments_returns_no_detail(
        self, minimal_sd: SchoolData
    ) -> None:
        sessions = [_a(cls="6A", room=None) for _ in range(3)]
        c  = _c("S7", "same_room_for_class")
        an = _analyzer(sessions, minimal_sd)
        assert an.analyze([c]) == []


# ---------------------------------------------------------------------------
# 8. S8 — teacher_day_off
# ---------------------------------------------------------------------------

class TestS8TeacherDayOff:
    def test_no_sessions_on_pref_day_is_100_pct(self, minimal_sd: SchoolData) -> None:
        sessions = [_a(teacher="M. Alpha", day="lundi")]
        c  = _c("S8", "teacher_day_off",
                 {"teacher": "M. Alpha", "preferred_day_off": "mercredi"})
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == pytest.approx(100.0)
        assert "respecté" in d["details_fr"]

    def test_sessions_on_pref_day_is_0_pct(self, minimal_sd: SchoolData) -> None:
        sessions = [_a(teacher="M. Alpha", day="mercredi")]
        c  = _c("S8", "teacher_day_off",
                 {"teacher": "M. Alpha", "preferred_day_off": "mercredi"})
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == pytest.approx(0.0)
        assert "non respecté" in d["details_fr"]

    def test_missing_parameter_returns_no_detail(
        self, minimal_sd: SchoolData
    ) -> None:
        c  = _c("S8", "teacher_day_off", {"teacher": "M. Alpha"})  # no preferred_day_off
        an = _analyzer([_a()], minimal_sd)
        assert an.analyze([c]) == []


# ---------------------------------------------------------------------------
# 9. S9 — no_subject_back_to_back
# ---------------------------------------------------------------------------

class TestS9NoSubjectBackToBack:
    def test_no_consecutive_sessions_is_100_pct(self, minimal_sd: SchoolData) -> None:
        # 08:00-09:00 and 11:00-12:00 — not consecutive (gap in between)
        sessions = [
            _a(cls="6A", subject="Maths", day="lundi", start="08:00", end="09:00"),
            _a(cls="6A", subject="Maths", day="lundi", start="11:00", end="12:00"),
        ]
        c  = _c("S9", "no_subject_back_to_back")
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == pytest.approx(100.0)

    def test_back_to_back_same_subject_is_0_pct(
        self, minimal_sd: SchoolData
    ) -> None:
        # Both consecutive AND same subject → violation
        sessions = [
            _a(cls="6A", subject="Maths", day="lundi", start="08:00", end="09:00"),
            _a(cls="6A", subject="Maths", day="lundi", start="09:00", end="10:00"),
        ]
        c  = _c("S9", "no_subject_back_to_back")
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == pytest.approx(0.0)

    def test_back_to_back_different_subject_is_100_pct(
        self, minimal_sd: SchoolData
    ) -> None:
        # Consecutive but different subjects → no violation
        sessions = [
            _a(cls="6A", subject="Maths",    day="lundi", start="08:00", end="09:00"),
            _a(cls="6A", subject="Français", day="lundi", start="09:00", end="10:00"),
        ]
        c  = _c("S9", "no_subject_back_to_back")
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == pytest.approx(100.0)

    def test_partial_violations(self, minimal_sd: SchoolData) -> None:
        # 2 consecutive pairs: 1 violation (same subject), 1 ok (different)
        sessions = [
            _a(cls="6A", subject="Maths",    day="lundi", start="08:00", end="09:00"),
            _a(cls="6A", subject="Maths",    day="lundi", start="09:00", end="10:00"),
            _a(cls="6A", subject="Français", day="lundi", start="10:00", end="11:00"),
        ]
        c  = _c("S9", "no_subject_back_to_back")
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == pytest.approx(50.0)

    def test_subject_filter(self, minimal_sd: SchoolData) -> None:
        # Back-to-back Français; Maths sessions not consecutive
        sessions = [
            _a(cls="6A", subject="Français", day="lundi", start="08:00", end="09:00"),
            _a(cls="6A", subject="Français", day="lundi", start="09:00", end="10:00"),
            _a(cls="6A", subject="Maths",    day="lundi", start="10:00", end="11:00"),
            _a(cls="6A", subject="Maths",    day="lundi", start="11:00", end="12:00"),
        ]
        # Filter to Français only: 1 consecutive Français pair → violation
        c  = _c("S9", "no_subject_back_to_back", {"subject": "Français"})
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 10. S10 — light_last_day
# ---------------------------------------------------------------------------

class TestS10LightLastDay:
    def test_last_day_empty_is_100_pct(self, minimal_sd: SchoolData) -> None:
        # Sessions only on lundi–jeudi; vendredi empty
        sessions = [_a(day=d) for d in ["lundi", "mardi", "mercredi", "jeudi"]]
        c  = _c("S10", "light_last_day")
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == pytest.approx(100.0)

    def test_last_day_lighter_than_avg_is_100_pct(
        self, minimal_sd: SchoolData
    ) -> None:
        # 2h on each of lundi–jeudi, 1h on vendredi
        sessions = (
            [_a(day=d, start="08:00", end="10:00")
             for d in ["lundi", "mardi", "mercredi", "jeudi"]]
            + [_a(day="vendredi", start="08:00", end="09:00")]
        )
        c  = _c("S10", "light_last_day")
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] == pytest.approx(100.0)
        assert "léger" in d["details_fr"]

    def test_last_day_heavier_than_avg_reduces_satisfaction(
        self, minimal_sd: SchoolData
    ) -> None:
        # 1h on lundi–jeudi, 2h on vendredi → last is heavier
        sessions = (
            [_a(day=d, start="08:00", end="09:00")
             for d in ["lundi", "mardi", "mercredi", "jeudi"]]
            + [_a(day="vendredi", start="08:00", end="10:00")]
        )
        c  = _c("S10", "light_last_day")
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] < 100.0

    def test_last_day_double_average_is_0_pct(self, minimal_sd: SchoolData) -> None:
        # 1h on each of lundi–jeudi, 2h on vendredi
        # avg = (1*4 + 2) / 5 = 1.2h; last = 2h; ratio = 2/1.2 ≈ 1.67
        # pct = (2*1.2 - 2) / 1.2 * 100 = 0.4/1.2*100 ≈ 33.3 %
        sessions = (
            [_a(day=d, start="08:00", end="09:00")
             for d in ["lundi", "mardi", "mercredi", "jeudi"]]
            + [_a(day="vendredi", start="08:00", end="10:00")]
        )
        c  = _c("S10", "light_last_day")
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert d["satisfaction_percent"] < 80.0

    def test_detail_mentions_last_day(self, minimal_sd: SchoolData) -> None:
        sessions = [_a(day="vendredi", start="08:00", end="09:00")]
        c  = _c("S10", "light_last_day")
        an = _analyzer(sessions, minimal_sd)
        d  = an.analyze([c])[0]
        assert "vendredi" in d["details_fr"]
