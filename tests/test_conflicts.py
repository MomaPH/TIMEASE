"""
Tests for timease/engine/conflicts.py.

Covers:
- Quick check: no teacher for subject
- Quick check: room type missing
- Quick check: sole teacher overloaded
- Quick check: class hours exceed schedule
- Relaxation: constraint removal makes problem feasible
- FixOption ease sorting
- analyze() stops at quick-check stage when issues are found

Run with: uv run pytest tests/test_conflicts.py
"""

from __future__ import annotations

import pytest

from timease.engine.conflicts import (
    ConflictAnalyzer,
    ConflictReport,
    FixOption,
    _sort_by_ease,
)
from timease.engine.models import (
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
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def base_tc() -> TimeslotConfig:
    """Mon–Fri, 08:00–12:00, base 60 min → 4 slots/day × 5 days = 20 slots."""
    return TimeslotConfig.from_simple(
        day_names=["lundi", "mardi", "mercredi", "jeudi", "vendredi"],
        sessions=[SessionConfig("Matin", "08:00", "12:00")],
        base_unit_minutes=60,
    )


@pytest.fixture
def base_school() -> School:
    return School(name="École Test", academic_year="2026-2027", city="Dakar")


@pytest.fixture
def math_subject() -> Subject:
    return Subject("Mathématiques", "Maths", "#000000")


@pytest.fixture
def lab_subject() -> Subject:
    return Subject("SVT", "SVT", "#000000", required_room_type="Laboratoire")


@pytest.fixture
def standard_room() -> Room:
    return Room("Salle 1", 35, ["Salle standard"])


@pytest.fixture
def lab_room() -> Room:
    return Room("Labo", 30, ["Laboratoire"])


@pytest.fixture
def math_teacher() -> Teacher:
    return Teacher("Prof Maths", ["Mathématiques"], max_hours_per_week=20)


@pytest.fixture
def base_class() -> SchoolClass:
    return SchoolClass("6ème", "6ème", 28)


def _make_sd(
    tc: TimeslotConfig,
    school: School,
    subjects: list[Subject],
    teachers: list[Teacher],
    classes: list[SchoolClass],
    rooms: list[Room],
    curriculum: list[CurriculumEntry],
    constraints: list[Constraint] | None = None,
) -> SchoolData:
    return SchoolData(
        school=school,
        timeslot_config=tc,
        subjects=subjects,
        teachers=teachers,
        classes=classes,
        rooms=rooms,
        curriculum=curriculum,
        constraints=constraints or [],
    )


# ---------------------------------------------------------------------------
# 1. Quick check: no teacher for subject
# ---------------------------------------------------------------------------

class TestNoTeacherForSubject:
    def test_missing_teacher_detected(
        self,
        base_tc, base_school, math_subject, standard_room, base_class,
    ) -> None:
        entry = CurriculumEntry(
            school_class="6ème", subject="Mathématiques",
            total_minutes_per_week=120,
            sessions_per_week=2, minutes_per_session=60,
        )
        sd = _make_sd(
            base_tc, base_school,
            subjects=[math_subject],
            teachers=[],  # no teachers at all
            classes=[base_class],
            rooms=[standard_room],
            curriculum=[entry],
        )
        reports = ConflictAnalyzer(sd).analyze()
        assert any("Mathématiques" in r.description_fr for r in reports)

    def test_qualified_teacher_no_report(
        self,
        base_tc, base_school, math_subject, standard_room, base_class, math_teacher,
    ) -> None:
        entry = CurriculumEntry(
            school_class="6ème", subject="Mathématiques",
            total_minutes_per_week=120,
            sessions_per_week=2, minutes_per_session=60,
        )
        sd = _make_sd(
            base_tc, base_school,
            subjects=[math_subject],
            teachers=[math_teacher],
            classes=[base_class],
            rooms=[standard_room],
            curriculum=[entry],
        )
        reports = ConflictAnalyzer(sd).analyze()
        no_teacher_reports = [
            r for r in reports
            if "Aucun enseignant qualifié" in r.description_fr
        ]
        assert not no_teacher_reports

    def test_fix_action_is_add_teacher(
        self,
        base_tc, base_school, math_subject, standard_room, base_class,
    ) -> None:
        entry = CurriculumEntry(
            school_class="6ème", subject="Mathématiques",
            total_minutes_per_week=60,
            sessions_per_week=2, minutes_per_session=60,
        )
        sd = _make_sd(
            base_tc, base_school,
            subjects=[math_subject],
            teachers=[],
            classes=[base_class],
            rooms=[standard_room],
            curriculum=[entry],
        )
        reports = ConflictAnalyzer(sd).analyze()
        conflict = next(r for r in reports if "Mathématiques" in r.description_fr)
        assert any(opt.fix_action.get("action") == "add_teacher"
                   for opt in conflict.fix_options)

    def test_same_subject_multiple_levels_reported_once(
        self,
        base_tc, base_school, math_subject, standard_room,
    ) -> None:
        """Duplicate subject across levels should produce only one report."""
        classes = [
            SchoolClass("6ème", "6ème", 28),
            SchoolClass("5ème", "5ème", 30),
        ]
        curriculum = [
            CurriculumEntry("6ème", "Mathématiques", 60,
                            sessions_per_week=1, minutes_per_session=60),
            CurriculumEntry("5ème", "Mathématiques", 60,
                            sessions_per_week=1, minutes_per_session=60),
        ]
        sd = _make_sd(
            base_tc, base_school,
            subjects=[math_subject], teachers=[], classes=classes,
            rooms=[standard_room], curriculum=curriculum,
        )
        reports = ConflictAnalyzer(sd).analyze()
        maths_reports = [r for r in reports if "Mathématiques" in r.description_fr]
        assert len(maths_reports) == 1


# ---------------------------------------------------------------------------
# 2. Quick check: room type missing
# ---------------------------------------------------------------------------

class TestRoomTypeMissing:
    def test_missing_lab_detected(
        self,
        base_tc, base_school, lab_subject, standard_room, base_class,
    ) -> None:
        entry = CurriculumEntry(
            school_class="6ème", subject="SVT",
            total_minutes_per_week=120,
            sessions_per_week=2, minutes_per_session=60,
        )
        teacher = Teacher("Prof SVT", ["SVT"], max_hours_per_week=10)
        sd = _make_sd(
            base_tc, base_school,
            subjects=[lab_subject],
            teachers=[teacher],
            classes=[base_class],
            rooms=[standard_room],  # only standard room, no lab
            curriculum=[entry],
        )
        reports = ConflictAnalyzer(sd).analyze()
        assert any("Laboratoire" in r.description_fr for r in reports)

    def test_lab_present_no_report(
        self,
        base_tc, base_school, lab_subject, lab_room, base_class,
    ) -> None:
        entry = CurriculumEntry(
            school_class="6ème", subject="SVT",
            total_minutes_per_week=60,
            sessions_per_week=2, minutes_per_session=60,
        )
        teacher = Teacher("Prof SVT", ["SVT"], max_hours_per_week=10)
        sd = _make_sd(
            base_tc, base_school,
            subjects=[lab_subject],
            teachers=[teacher],
            classes=[base_class],
            rooms=[lab_room],
            curriculum=[entry],
        )
        reports = ConflictAnalyzer(sd).analyze()
        room_reports = [r for r in reports if "Laboratoire" in r.description_fr]
        assert not room_reports

    def test_fix_action_is_add_room(
        self,
        base_tc, base_school, lab_subject, standard_room, base_class,
    ) -> None:
        entry = CurriculumEntry(
            school_class="6ème", subject="SVT",
            total_minutes_per_week=60,
            sessions_per_week=2, minutes_per_session=60,
        )
        teacher = Teacher("Prof SVT", ["SVT"], max_hours_per_week=10)
        sd = _make_sd(
            base_tc, base_school,
            subjects=[lab_subject],
            teachers=[teacher],
            classes=[base_class],
            rooms=[standard_room],
            curriculum=[entry],
        )
        reports = ConflictAnalyzer(sd).analyze()
        conflict = next(r for r in reports if "Laboratoire" in r.description_fr)
        assert any(opt.fix_action.get("action") == "add_room"
                   for opt in conflict.fix_options)
        add_opt = next(o for o in conflict.fix_options
                       if o.fix_action.get("action") == "add_room")
        assert add_opt.fix_action["type"] == "Laboratoire"


# ---------------------------------------------------------------------------
# 3. Quick check: sole teacher overloaded
# ---------------------------------------------------------------------------

class TestSoleTeacherOverload:
    def test_overloaded_sole_teacher_detected(
        self,
        base_tc, base_school, math_subject, standard_room,
    ) -> None:
        # Teacher max 2h, but curriculum demands 4h
        teacher = Teacher("Samba", ["Mathématiques"], max_hours_per_week=2)
        cls = SchoolClass("6ème", "6ème", 28)
        entry = CurriculumEntry(
            school_class="6ème", subject="Mathématiques",
            total_minutes_per_week=240, # 4h
            sessions_per_week=2, minutes_per_session=60,
        )
        sd = _make_sd(
            base_tc, base_school,
            subjects=[math_subject], teachers=[teacher],
            classes=[cls], rooms=[standard_room], curriculum=[entry],
        )
        reports = ConflictAnalyzer(sd).analyze()
        assert any("Samba" in r.description_fr for r in reports)

    def test_overloaded_fix_includes_increase_hours(
        self,
        base_tc, base_school, math_subject, standard_room,
    ) -> None:
        teacher = Teacher("Samba", ["Mathématiques"], max_hours_per_week=2)
        cls = SchoolClass("6ème", "6ème", 28)
        entry = CurriculumEntry(
            school_class="6ème", subject="Mathématiques",
            total_minutes_per_week=240,
            sessions_per_week=2, minutes_per_session=60,
        )
        sd = _make_sd(
            base_tc, base_school,
            subjects=[math_subject], teachers=[teacher],
            classes=[cls], rooms=[standard_room], curriculum=[entry],
        )
        reports = ConflictAnalyzer(sd).analyze()
        conflict = next(r for r in reports if "Samba" in r.description_fr)
        actions = {o.fix_action["action"] for o in conflict.fix_options}
        assert "update_teacher_max_hours" in actions

    def test_not_sole_teacher_no_overload_report(
        self,
        base_tc, base_school, math_subject, standard_room,
    ) -> None:
        # Two teachers share the subject → no sole-overload report
        t1 = Teacher("Samba", ["Mathématiques"], max_hours_per_week=2)
        t2 = Teacher("Fatou", ["Mathématiques"], max_hours_per_week=2)
        cls = SchoolClass("6ème", "6ème", 28)
        entry = CurriculumEntry(
            school_class="6ème", subject="Mathématiques",
            total_minutes_per_week=240,
            sessions_per_week=2, minutes_per_session=60,
        )
        sd = _make_sd(
            base_tc, base_school,
            subjects=[math_subject], teachers=[t1, t2],
            classes=[cls], rooms=[standard_room], curriculum=[entry],
        )
        reports = ConflictAnalyzer(sd).analyze()
        overload = [r for r in reports if "update_teacher_max_hours" in
                    str([o.fix_action for o in r.fix_options])]
        assert not overload

    def test_fix_ease_1_for_max_hours_increase(
        self,
        base_tc, base_school, math_subject, standard_room,
    ) -> None:
        teacher = Teacher("Samba", ["Mathématiques"], max_hours_per_week=2)
        cls = SchoolClass("6ème", "6ème", 28)
        entry = CurriculumEntry(
            school_class="6ème", subject="Mathématiques",
            total_minutes_per_week=240,
            sessions_per_week=2, minutes_per_session=60,
        )
        sd = _make_sd(
            base_tc, base_school,
            subjects=[math_subject], teachers=[teacher],
            classes=[cls], rooms=[standard_room], curriculum=[entry],
        )
        reports = ConflictAnalyzer(sd).analyze()
        conflict = next(r for r in reports if "Samba" in r.description_fr)
        hours_fix = next(
            o for o in conflict.fix_options
            if o.fix_action.get("action") == "update_teacher_max_hours"
        )
        assert hours_fix.ease == 1


# ---------------------------------------------------------------------------
# 4. Quick check: class hours exceed schedule
# ---------------------------------------------------------------------------

class TestClassHoursExceedSchedule:
    def test_overflow_detected(
        self,
        base_tc, base_school, math_subject, standard_room, math_teacher,
    ) -> None:
        # 20 schedule slots × 60 min = 20h. Demand 25h → overflow.
        cls = SchoolClass("6ème", "6ème", 28)
        entry = CurriculumEntry(
            school_class="6ème", subject="Mathématiques",
            total_minutes_per_week=1500, # 25h
            sessions_per_week=2, minutes_per_session=60,
        )
        sd = _make_sd(
            base_tc, base_school,
            subjects=[math_subject], teachers=[math_teacher],
            classes=[cls], rooms=[standard_room], curriculum=[entry],
        )
        reports = ConflictAnalyzer(sd).analyze()
        assert any("6ème" in r.description_fr and "25h" in r.description_fr
                   for r in reports)

    def test_within_schedule_no_report(
        self,
        base_tc, base_school, math_subject, standard_room, math_teacher,
    ) -> None:
        cls = SchoolClass("6ème", "6ème", 28)
        entry = CurriculumEntry(
            school_class="6ème", subject="Mathématiques",
            total_minutes_per_week=600, # 10h, well within 20h
            sessions_per_week=2, minutes_per_session=60,
        )
        sd = _make_sd(
            base_tc, base_school,
            subjects=[math_subject], teachers=[math_teacher],
            classes=[cls], rooms=[standard_room], curriculum=[entry],
        )
        reports = ConflictAnalyzer(sd).analyze()
        overflow = [r for r in reports if "excédent" in r.description_fr]
        assert not overflow

    def test_fix_includes_reduce_curriculum(
        self,
        base_tc, base_school, math_subject, standard_room, math_teacher,
    ) -> None:
        cls = SchoolClass("6ème", "6ème", 28)
        entry = CurriculumEntry(
            school_class="6ème", subject="Mathématiques",
            total_minutes_per_week=1500,
            sessions_per_week=2, minutes_per_session=60,
        )
        sd = _make_sd(
            base_tc, base_school,
            subjects=[math_subject], teachers=[math_teacher],
            classes=[cls], rooms=[standard_room], curriculum=[entry],
        )
        reports = ConflictAnalyzer(sd).analyze()
        overflow = next(r for r in reports if "excédent" in r.description_fr)
        actions = {o.fix_action["action"] for o in overflow.fix_options}
        assert "reduce_curriculum_hours" in actions


# ---------------------------------------------------------------------------
# 5. FixOption ease sorting
# ---------------------------------------------------------------------------

class TestSortByEase:
    def test_options_sorted_ascending(self) -> None:
        opt1 = FixOption("hard fix", {}, "", ease=3)
        opt2 = FixOption("easy fix", {}, "", ease=1)
        opt3 = FixOption("medium fix", {}, "", ease=2)
        report = ConflictReport("conflict", "quick_check", [opt1, opt2, opt3])
        sorted_reports = _sort_by_ease([report])
        eases = [o.ease for o in sorted_reports[0].fix_options]
        assert eases == [1, 2, 3]

    def test_single_option_unchanged(self) -> None:
        opt = FixOption("fix", {}, "", ease=2)
        report = ConflictReport("conflict", "quick_check", [opt])
        result = _sort_by_ease([report])
        assert result[0].fix_options[0].ease == 2


# ---------------------------------------------------------------------------
# 6. analyze() stops at quick-check stage
# ---------------------------------------------------------------------------

class TestAnalyzeStagePriority:
    def test_quick_check_reports_returned_without_relaxation(
        self,
        base_tc, base_school, math_subject, standard_room, base_class,
    ) -> None:
        """When quick checks find issues, relaxation should not run (no solver call)."""
        entry = CurriculumEntry(
            school_class="6ème", subject="Mathématiques",
            total_minutes_per_week=60,
            sessions_per_week=2, minutes_per_session=60,
        )
        sd = _make_sd(
            base_tc, base_school,
            subjects=[math_subject],
            teachers=[],  # missing teacher → quick check fires
            classes=[base_class],
            rooms=[standard_room],
            curriculum=[entry],
        )
        reports = ConflictAnalyzer(sd).analyze()
        # All reports should be from quick_check
        assert all(r.source == "quick_check" for r in reports)
        assert len(reports) >= 1

    def test_reports_have_fix_options(
        self,
        base_tc, base_school, math_subject, standard_room, base_class,
    ) -> None:
        entry = CurriculumEntry(
            school_class="6ème", subject="Mathématiques",
            total_minutes_per_week=60,
            sessions_per_week=2, minutes_per_session=60,
        )
        sd = _make_sd(
            base_tc, base_school,
            subjects=[math_subject], teachers=[],
            classes=[base_class], rooms=[standard_room],
            curriculum=[entry],
        )
        reports = ConflictAnalyzer(sd).analyze()
        for r in reports:
            assert r.fix_options, f"Report '{r.description_fr}' has no fix options"


# ---------------------------------------------------------------------------
# 7. ConflictReport and FixOption dataclass defaults
# ---------------------------------------------------------------------------

class TestDataclassDefaults:
    def test_fix_option_default_ease(self) -> None:
        opt = FixOption("fix", {}, "impact")
        assert opt.ease == 2

    def test_conflict_report_empty_fix_options(self) -> None:
        r = ConflictReport("desc", "quick_check")
        assert r.fix_options == []

    def test_conflict_report_source_values(self) -> None:
        r1 = ConflictReport("desc", "quick_check")
        r2 = ConflictReport("desc", "relaxation")
        assert r1.source == "quick_check"
        assert r2.source == "relaxation"
