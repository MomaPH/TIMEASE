"""
Comprehensive solver tests for TIMEASE.

All tests except test_performance use a minimal school that solves in < 1 s,
keeping the full suite fast.  test_performance loads the real sample_school.json.

Run with:  uv run pytest tests/test_solver.py -v
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

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
    TeacherAssignment,
    TimeslotConfig,
    TimetableResult,
)
from timease.engine.solver import TimetableSolver

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_JSON = Path(__file__).parent.parent / "timease" / "data" / "sample_school.json"
FAST_TIMEOUT = 10   # seconds — plenty for the tiny fixture


def _to_min(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _sessions_overlap(a: Assignment, b: Assignment) -> bool:
    """True if two assignments share the same day and overlapping time window."""
    if a.day != b.day:
        return False
    a_start, a_end = _to_min(a.start_time), _to_min(a.end_time)
    b_start, b_end = _to_min(b.start_time), _to_min(b.end_time)
    return a_start < b_end and b_start < a_end


# ---------------------------------------------------------------------------
# Minimal school fixture
#
# 2 classes, 3 subjects, 3 teachers, 3 rooms, Mon-Fri 08:00-12:00 (60 min base)
# 9 sessions total — solves in < 0.5 s.
# ---------------------------------------------------------------------------

def _make_school(constraints: list[Constraint] | None = None) -> SchoolData:
    school = School("École Test", "2026-2027", "Dakar")
    tc = TimeslotConfig(
        days=["lundi", "mardi", "mercredi", "jeudi", "vendredi"],
        sessions=[SessionConfig("Matin", "08:00", "12:00")],
        base_unit_minutes=60,
    )
    subjects = [
        Subject("Mathématiques", "Maths", "#E6F1FB"),
        Subject("Français",      "Fr",    "#EAF3DE"),
        Subject("SVT",           "SVT",   "#E1F5EE", required_room_type="Laboratoire"),
    ]
    teachers = [
        Teacher("Prof Maths",    ["Mathématiques"], max_hours_per_week=10),
        Teacher("Prof Français", ["Français"],      max_hours_per_week=10),
        Teacher("Prof SVT",      ["SVT"],           max_hours_per_week=10),
    ]
    classes = [
        SchoolClass("6ème", "6ème", 28),
        SchoolClass("5ème", "5ème", 25),
    ]
    rooms = [
        Room("Salle 1", 35, ["Salle standard"]),
        Room("Salle 2", 35, ["Salle standard"]),
        Room("Labo",    30, ["Laboratoire"]),
    ]
    curriculum = [
        # 6ème: 3 subjects
        CurriculumEntry("6ème", "Mathématiques", 120, "manual",
                        sessions_per_week=2, minutes_per_session=60),
        CurriculumEntry("6ème", "Français",      120, "manual",
                        sessions_per_week=2, minutes_per_session=60),
        CurriculumEntry("6ème", "SVT",            60, "manual",
                        sessions_per_week=1, minutes_per_session=60),
        # 5ème: 3 subjects
        CurriculumEntry("5ème", "Mathématiques", 120, "manual",
                        sessions_per_week=2, minutes_per_session=60),
        CurriculumEntry("5ème", "Français",       60, "manual",
                        sessions_per_week=1, minutes_per_session=60),
        CurriculumEntry("5ème", "SVT",             60, "manual",
                        sessions_per_week=1, minutes_per_session=60),
    ]
    teacher_assignments = [
        TeacherAssignment("Prof Maths",    "Mathématiques", "6ème"),
        TeacherAssignment("Prof Français", "Français",      "6ème"),
        TeacherAssignment("Prof SVT",      "SVT",           "6ème"),
        TeacherAssignment("Prof Maths",    "Mathématiques", "5ème"),
        TeacherAssignment("Prof Français", "Français",      "5ème"),
        TeacherAssignment("Prof SVT",      "SVT",           "5ème"),
    ]
    return SchoolData(
        school=school,
        timeslot_config=tc,
        subjects=subjects,
        teachers=teachers,
        classes=classes,
        rooms=rooms,
        curriculum=curriculum,
        constraints=constraints or [],
        teacher_assignments=teacher_assignments,
    )


@pytest.fixture(scope="module")
def minimal_sd() -> SchoolData:
    return _make_school()


@pytest.fixture(scope="module")
def minimal_result(minimal_sd: SchoolData) -> TimetableResult:
    return TimetableSolver().solve(minimal_sd, timeout_seconds=FAST_TIMEOUT)


# ---------------------------------------------------------------------------
# 1. test_basic_solve
# ---------------------------------------------------------------------------

class TestBasicSolve:
    def test_solved_true(self, minimal_result: TimetableResult) -> None:
        assert minimal_result.solved is True

    def test_correct_session_count(self, minimal_result: TimetableResult) -> None:
        # 2+2+1 (6ème) + 2+1+1 (5ème) = 9 sessions
        assert len(minimal_result.assignments) == 9

    def test_assignments_have_required_fields(self, minimal_result: TimetableResult) -> None:
        for a in minimal_result.assignments:
            assert a.school_class
            assert a.subject
            assert a.teacher
            assert a.day
            assert a.start_time
            assert a.end_time
            assert a.start_time < a.end_time


# ---------------------------------------------------------------------------
# 2. test_no_class_double_booking
# ---------------------------------------------------------------------------

class TestNoClassDoubleBooking:
    def test_no_class_overlap(self, minimal_result: TimetableResult) -> None:
        assignments = minimal_result.assignments
        for i, a in enumerate(assignments):
            for b in assignments[i + 1:]:
                if a.school_class == b.school_class:
                    assert not _sessions_overlap(a, b), (
                        f"{a.school_class}: '{a.subject}' and '{b.subject}' "
                        f"overlap on {a.day}"
                    )


# ---------------------------------------------------------------------------
# 3. test_no_teacher_double_booking
# ---------------------------------------------------------------------------

class TestNoTeacherDoubleBooking:
    def test_no_teacher_overlap(self, minimal_result: TimetableResult) -> None:
        assignments = minimal_result.assignments
        for i, a in enumerate(assignments):
            for b in assignments[i + 1:]:
                if a.teacher == b.teacher:
                    assert not _sessions_overlap(a, b), (
                        f"{a.teacher}: '{a.subject} ({a.school_class})' and "
                        f"'{b.subject} ({b.school_class})' overlap on {a.day}"
                    )


# ---------------------------------------------------------------------------
# 4. test_no_room_double_booking
# ---------------------------------------------------------------------------

class TestNoRoomDoubleBooking:
    def test_no_room_overlap(self, minimal_result: TimetableResult) -> None:
        assignments = [a for a in minimal_result.assignments if a.room]
        for i, a in enumerate(assignments):
            for b in assignments[i + 1:]:
                if a.room == b.room:
                    assert not _sessions_overlap(a, b), (
                        f"Room '{a.room}': '{a.subject} ({a.school_class})' and "
                        f"'{b.subject} ({b.school_class})' overlap on {a.day}"
                    )


# ---------------------------------------------------------------------------
# 5. test_curriculum_hours_satisfied
# ---------------------------------------------------------------------------

class TestCurriculumHoursSatisfied:
    def test_each_entry_has_correct_minutes(
        self, minimal_result: TimetableResult, minimal_sd: SchoolData
    ) -> None:
        actual: dict[tuple[str, str], int] = {}
        for a in minimal_result.assignments:
            key = (a.school_class, a.subject)
            duration = _to_min(a.end_time) - _to_min(a.start_time)
            actual[key] = actual.get(key, 0) + duration

        for cls in minimal_sd.classes:
            for entry in minimal_sd.curriculum:
                if entry.level != cls.level:
                    continue
                expected = entry.total_minutes_per_week
                got = actual.get((cls.name, entry.subject), 0)
                assert got == expected, (
                    f"{cls.name}/{entry.subject}: expected {expected} min, got {got}"
                )

    def test_verify_passes(
        self, minimal_result: TimetableResult, minimal_sd: SchoolData
    ) -> None:
        violations = minimal_result.verify(minimal_sd)
        assert not violations, "\n".join(violations)


# ---------------------------------------------------------------------------
# 6. test_teacher_qualification
# ---------------------------------------------------------------------------

class TestTeacherQualification:
    def test_only_qualified_subjects(
        self, minimal_result: TimetableResult, minimal_sd: SchoolData
    ) -> None:
        teacher_subjects = {t.name: set(t.subjects) for t in minimal_sd.teachers}
        for a in minimal_result.assignments:
            qualified = teacher_subjects.get(a.teacher, set())
            assert a.subject in qualified, (
                f"{a.teacher} teaches '{a.subject}' but is only qualified for "
                f"{sorted(qualified)}"
            )


# ---------------------------------------------------------------------------
# 7. test_teacher_max_hours
# ---------------------------------------------------------------------------

class TestTeacherMaxHours:
    def test_no_teacher_exceeds_max_hours(
        self, minimal_result: TimetableResult, minimal_sd: SchoolData
    ) -> None:
        teacher_max = {t.name: t.max_hours_per_week * 60 for t in minimal_sd.teachers}
        teacher_minutes: dict[str, int] = {}
        for a in minimal_result.assignments:
            duration = _to_min(a.end_time) - _to_min(a.start_time)
            teacher_minutes[a.teacher] = teacher_minutes.get(a.teacher, 0) + duration

        for teacher, minutes in teacher_minutes.items():
            limit = teacher_max[teacher]
            assert minutes <= limit, (
                f"{teacher}: {minutes} min scheduled, max is {limit} min"
            )


# ---------------------------------------------------------------------------
# 8. test_room_capacity
# ---------------------------------------------------------------------------

class TestRoomCapacity:
    def test_rooms_can_hold_their_class(
        self, minimal_result: TimetableResult, minimal_sd: SchoolData
    ) -> None:
        room_capacity = {r.name: r.capacity for r in minimal_sd.rooms}
        class_size    = {c.name: c.student_count for c in minimal_sd.classes}

        for a in minimal_result.assignments:
            if not a.room:
                continue
            cap   = room_capacity[a.room]
            size  = class_size[a.school_class]
            assert cap >= size, (
                f"Room '{a.room}' (cap {cap}) too small for "
                f"'{a.school_class}' ({size} students)"
            )


# ---------------------------------------------------------------------------
# 9. test_room_type_match
# ---------------------------------------------------------------------------

class TestRoomTypeMatch:
    def test_lab_subject_gets_lab_room(
        self, minimal_result: TimetableResult, minimal_sd: SchoolData
    ) -> None:
        subj_type = {
            s.name: s.required_room_type
            for s in minimal_sd.subjects
            if s.required_room_type
        }
        room_types = {r.name: r.types for r in minimal_sd.rooms}

        for a in minimal_result.assignments:
            required = subj_type.get(a.subject)
            if required is None or not a.room:
                continue
            assert required in room_types[a.room], (
                f"'{a.subject}' needs '{required}' but got room "
                f"'{a.room}' (types: {room_types[a.room]})"
            )

    def test_standard_subject_not_in_lab(
        self, minimal_result: TimetableResult, minimal_sd: SchoolData
    ) -> None:
        lab_subjects = {
            s.name for s in minimal_sd.subjects if s.required_room_type == "Laboratoire"
        }
        lab_rooms = {
            r.name for r in minimal_sd.rooms if "Laboratoire" in r.types
        }
        for a in minimal_result.assignments:
            if a.subject not in lab_subjects and a.room in lab_rooms:
                pytest.fail(
                    f"'{a.subject}' (no lab required) assigned to lab room '{a.room}'"
                )


# ---------------------------------------------------------------------------
# 10. test_impossible_scenario
# ---------------------------------------------------------------------------

class TestImpossibleScenario:
    def test_no_teacher_returns_unsolved(self) -> None:
        """Zero teachers → no sessions can be built → solved=False."""
        sd = _make_school()
        sd = type(sd)(
            school=sd.school,
            timeslot_config=sd.timeslot_config,
            subjects=sd.subjects,
            teachers=[],          # no teachers
            classes=sd.classes,
            rooms=sd.rooms,
            curriculum=sd.curriculum,
            constraints=[],
        )
        result = TimetableSolver().solve(sd, timeout_seconds=5)
        assert result.solved is False

    def test_conflicts_returned_when_unsolved(self) -> None:
        """When infeasible, conflicts list is populated."""
        sd = _make_school()
        sd = type(sd)(
            school=sd.school,
            timeslot_config=sd.timeslot_config,
            subjects=sd.subjects,
            teachers=[],
            classes=sd.classes,
            rooms=sd.rooms,
            curriculum=sd.curriculum,
            constraints=[],
        )
        result = TimetableSolver().solve(sd, timeout_seconds=5)
        assert result.conflicts is not None
        assert len(result.conflicts) > 0

    def test_overcrowded_curriculum_returns_unsolved(self) -> None:
        """More curriculum hours than schedule slots → infeasible."""
        # 20 slots/week × 60 min = 1200 min available; demand 2000 min
        sd = _make_school()
        overloaded = [
            CurriculumEntry("6ème", "Mathématiques", 2000, "manual",
                            sessions_per_week=33, minutes_per_session=60),
        ]
        sd = type(sd)(
            school=sd.school,
            timeslot_config=sd.timeslot_config,
            subjects=sd.subjects,
            teachers=sd.teachers,
            classes=[SchoolClass("6ème", "6ème", 28)],
            rooms=sd.rooms,
            curriculum=overloaded,
            constraints=[],
        )
        result = TimetableSolver().solve(sd, timeout_seconds=5)
        assert result.solved is False


# ---------------------------------------------------------------------------
# 11. test_soft_constraints_matter
# ---------------------------------------------------------------------------

class TestSoftConstraintsMatter:
    """
    Build a school where one teacher prefers morning and another afternoon.
    After solving, the morning-preference teacher should have ≥ 50% of their
    sessions in the morning, and vice versa.
    """

    def _make_preference_school(self, preferred: str) -> SchoolData:
        school = School("École Préférence", "2026-2027", "Dakar")
        tc = TimeslotConfig(
            days=["lundi", "mardi", "mercredi", "jeudi", "vendredi"],
            sessions=[
                SessionConfig("Matin",      "08:00", "12:00"),
                SessionConfig("Après-midi", "14:00", "16:00"),
            ],
            base_unit_minutes=60,
        )
        subjects = [Subject("Mathématiques", "Maths", "#000")]
        teachers = [Teacher("Prof Test", ["Mathématiques"], max_hours_per_week=20)]
        classes  = [SchoolClass("6ème", "6ème", 28)]
        rooms    = [Room("Salle 1", 35, ["Salle standard"])]
        curriculum = [
            CurriculumEntry("6ème", "Mathématiques", 360, "manual",
                            sessions_per_week=6, minutes_per_session=60),
        ]
        soft = Constraint(
            id="S1",
            type="soft",
            category="teacher_time_preference",
            description_fr=f"Prof Test préfère {preferred}.",
            priority=9,
            parameters={"teacher": "Prof Test", "preferred_session": preferred},
        )
        return SchoolData(
            school=school,
            timeslot_config=tc,
            subjects=subjects,
            teachers=teachers,
            classes=classes,
            rooms=rooms,
            curriculum=curriculum,
            constraints=[soft],
            teacher_assignments=[
                TeacherAssignment("Prof Test", "Mathématiques", "6ème"),
            ],
        )

    def _morning_count(self, assignments: list[Assignment]) -> int:
        return sum(1 for a in assignments if a.start_time < "12:00")

    def test_morning_preference_respected(self) -> None:
        sd     = self._make_preference_school("Matin")
        result = TimetableSolver().solve(sd, timeout_seconds=FAST_TIMEOUT)
        assert result.solved
        morning = self._morning_count(result.assignments)
        total   = len(result.assignments)
        assert morning / total >= 0.5, (
            f"Expected ≥50% morning sessions with morning preference, "
            f"got {morning}/{total}"
        )

    def test_afternoon_preference_respected(self) -> None:
        sd     = self._make_preference_school("Après-midi")
        result = TimetableSolver().solve(sd, timeout_seconds=FAST_TIMEOUT)
        assert result.solved
        afternoon = len(result.assignments) - self._morning_count(result.assignments)
        total     = len(result.assignments)
        assert afternoon / total >= 0.5, (
            f"Expected ≥50% afternoon sessions with afternoon preference, "
            f"got {afternoon}/{total}"
        )

    def test_morning_beats_afternoon_across_preferences(self) -> None:
        """Morning school has more morning sessions than afternoon school."""
        sd_matin = self._make_preference_school("Matin")
        sd_aprem = self._make_preference_school("Après-midi")
        r_matin  = TimetableSolver().solve(sd_matin, timeout_seconds=FAST_TIMEOUT)
        r_aprem  = TimetableSolver().solve(sd_aprem, timeout_seconds=FAST_TIMEOUT)
        assert r_matin.solved and r_aprem.solved
        morning_matin = self._morning_count(r_matin.assignments)
        morning_aprem = self._morning_count(r_aprem.assignments)
        assert morning_matin >= morning_aprem


# ---------------------------------------------------------------------------
# 12. test_fixed_assignment  (H9)
# ---------------------------------------------------------------------------

class TestFixedAssignment:
    def test_fixed_session_appears_at_correct_slot(self) -> None:
        """H9 must pin the first Maths session of 6ème to Monday 08:00."""
        h9 = Constraint(
            id="H9",
            type="hard",
            category="fixed_assignment",
            description_fr="Maths 6ème fixé le lundi à 08h00.",
            parameters={
                "class":      "6ème",
                "subject":    "Mathématiques",
                "day":        "lundi",
                "slot_start": "08:00",
            },
        )
        sd     = _make_school(constraints=[h9])
        result = TimetableSolver().solve(sd, timeout_seconds=FAST_TIMEOUT)
        assert result.solved

        pinned = [
            a for a in result.assignments
            if a.school_class == "6ème"
            and a.subject == "Mathématiques"
            and a.day == "lundi"
            and a.start_time == "08:00"
        ]
        assert len(pinned) >= 1, (
            "Expected at least one Maths session for 6ème on lundi at 08:00"
        )

    def test_fixed_assignment_does_not_break_other_sessions(self) -> None:
        """All 9 sessions must still be scheduled despite the pin."""
        h9 = Constraint(
            id="H9",
            type="hard",
            category="fixed_assignment",
            description_fr="Maths 6ème fixé le lundi à 08h00.",
            parameters={
                "class":      "6ème",
                "subject":    "Mathématiques",
                "day":        "lundi",
                "slot_start": "08:00",
            },
        )
        sd     = _make_school(constraints=[h9])
        result = TimetableSolver().solve(sd, timeout_seconds=FAST_TIMEOUT)
        assert result.solved
        assert len(result.assignments) == 9


# ---------------------------------------------------------------------------
# 12b. test_min_sessions_per_day  (H11)
# ---------------------------------------------------------------------------

class TestMinSessionsPerDay:
    def test_all_days_used_with_h11(self) -> None:
        """With H11 min_sessions=1, every day must have ≥ 1 session per class."""
        h11 = Constraint(
            id="H11",
            type="hard",
            category="min_sessions_per_day",
            description_fr="Au moins 1 cours par jour par classe.",
            parameters={"min_sessions": 1},
        )
        sd = _make_school(constraints=[h11])
        # 5ème has only 4 sessions in the base fixture (2 Maths + 1 Fr + 1 SVT)
        # but H11 requires ≥1 session on each of 5 days → bump Français to 2 sessions.
        new_curriculum = [
            e if not (e.level == "5ème" and e.subject == "Français")
            else CurriculumEntry("5ème", "Français", 120, "manual",
                                 sessions_per_week=2, minutes_per_session=60)
            for e in sd.curriculum
        ]
        sd = type(sd)(
            school=sd.school,
            timeslot_config=sd.timeslot_config,
            subjects=sd.subjects,
            teachers=sd.teachers,
            classes=sd.classes,
            rooms=sd.rooms,
            curriculum=new_curriculum,
            constraints=sd.constraints,
            teacher_assignments=sd.teacher_assignments,
        )
        result = TimetableSolver().solve(sd, timeout_seconds=FAST_TIMEOUT)
        assert result.solved

        days = sd.timeslot_config.days
        for cls in sd.classes:
            cls_assignments = [a for a in result.assignments if a.school_class == cls.name]
            days_used = {a.day for a in cls_assignments}
            for day in days:
                assert day in days_used, (
                    f"Class '{cls.name}' has no sessions on '{day}' "
                    f"despite H11 min_sessions=1"
                )

    def test_impossible_min_exceeds_sessions(self) -> None:
        """min_sessions=10 on a class with 5 total sessions → infeasible."""
        h11 = Constraint(
            id="H11",
            type="hard",
            category="min_sessions_per_day",
            description_fr="10 cours par jour — impossible.",
            parameters={"min_sessions": 10},
        )
        sd     = _make_school(constraints=[h11])
        result = TimetableSolver().solve(sd, timeout_seconds=5)
        assert result.solved is False

    def test_without_h11_solver_may_skip_days(self) -> None:
        """Without H11, solver is free to leave some days empty."""
        # Tiny curriculum: 2 Maths sessions across 5 days — without H11
        # the solver can place both on the same day.
        sd = _make_school(constraints=[])
        result = TimetableSolver().solve(sd, timeout_seconds=FAST_TIMEOUT)
        assert result.solved  # must still solve


# ---------------------------------------------------------------------------
# 13. test_performance
# ---------------------------------------------------------------------------

class TestPerformance:
    @pytest.mark.skipif(
        not SAMPLE_JSON.exists(),
        reason="sample_school.json not found",
    )
    def test_sample_school_under_60_seconds(self) -> None:
        sd = SchoolData.from_json(SAMPLE_JSON)
        t0 = time.time()
        result = TimetableSolver().solve(sd, timeout_seconds=60)
        elapsed = time.time() - t0

        assert result.solved, "Sample school must produce a valid timetable"
        assert elapsed <= 62, (   # 2 s grace for test overhead
            f"Solver took {elapsed:.1f}s — expected ≤ 60s"
        )
        assert len(result.assignments) > 0


# ---------------------------------------------------------------------------
# 14. TeacherAssignment — explicit teacher assignment
# ---------------------------------------------------------------------------

REAL_SCHOOL_JSON = Path(__file__).parent.parent / "timease" / "data" / "real_school_dakar.json"


class TestExplicitTeacherAssignment:
    """
    TeacherAssignment objects drive the solver's teacher-to-class mapping.
    The solver must use exactly the assigned teacher for each (class, subject).
    """

    def test_explicit_teacher_is_used(self) -> None:
        """Solver uses the TeacherAssignment teacher, not a different one."""
        sd = _make_school()
        # All assignments are already explicit in _make_school().
        # Verify that 6ème Français is taught by Prof Français.
        result = TimetableSolver().solve(sd, timeout_seconds=FAST_TIMEOUT)
        assert result.solved or result.partial
        french_6 = [
            a for a in result.assignments
            if a.school_class == "6ème" and a.subject == "Français"
        ]
        assert all(a.teacher == "Prof Français" for a in french_6), (
            f"Expected all 6ème Français taught by 'Prof Français'; "
            f"got {[a.teacher for a in french_6]}"
        )

    def test_explicit_teacher_overrides_alternative(self) -> None:
        """With two qualified teachers, TeacherAssignment pins the correct one."""
        sd = _make_school()
        extra_teacher = Teacher("Prof Maths 2", ["Mathématiques"], max_hours_per_week=10)
        new_teachers  = sd.teachers + [extra_teacher]
        # Reassign 5ème Maths to Prof Maths 2 explicitly.
        new_assignments = [
            TeacherAssignment("Prof Maths 2", "Mathématiques", "5ème")
            if ta.school_class == "5ème" and ta.subject == "Mathématiques" else ta
            for ta in sd.teacher_assignments
        ]
        sd = type(sd)(
            school=sd.school, timeslot_config=sd.timeslot_config,
            subjects=sd.subjects, teachers=new_teachers,
            classes=sd.classes, rooms=sd.rooms,
            curriculum=sd.curriculum, constraints=[],
            teacher_assignments=new_assignments,
        )
        result = TimetableSolver().solve(sd, timeout_seconds=FAST_TIMEOUT)
        assert result.solved or result.partial
        maths_5 = [
            a for a in result.assignments
            if a.school_class == "5ème" and a.subject == "Mathématiques"
        ]
        assert all(a.teacher == "Prof Maths 2" for a in maths_5), (
            "TeacherAssignment 'Prof Maths 2' should be used for 5ème Maths"
        )

    def test_all_subjects_get_teacher(self) -> None:
        """Every curriculum entry must get a teacher from the assignments."""
        sd     = _make_school()
        result = TimetableSolver().solve(sd, timeout_seconds=FAST_TIMEOUT)
        assert result.solved or result.partial
        # All subjects must appear in the result
        assert any(a.subject == "Français"      for a in result.assignments)
        assert any(a.subject == "SVT"           for a in result.assignments)
        assert any(a.subject == "Mathématiques" for a in result.assignments)

    def test_validate_rejects_unknown_teacher(self) -> None:
        """A TeacherAssignment referencing a non-existent teacher must error."""
        sd = _make_school()
        sd.teacher_assignments.append(
            TeacherAssignment("Fantôme Inconnu", "Mathématiques", "6ème")
        )
        # Remove the valid duplicate so we only test the unknown one
        sd.teacher_assignments = [
            ta for ta in sd.teacher_assignments
            if not (ta.school_class == "6ème" and ta.subject == "Mathématiques"
                    and ta.teacher == "Prof Maths")
        ]
        errors = sd.validate()
        assert any("inconnu" in e for e in errors), (
            "Expected unknown-teacher error, got: " + str(errors)
        )

    def test_validate_rejects_unqualified_teacher(self) -> None:
        """A TeacherAssignment for a subject the teacher can't teach must error."""
        sd = _make_school()
        # Replace 6ème Maths assignment with Prof Français who can't teach Maths
        sd.teacher_assignments = [
            TeacherAssignment("Prof Français", "Mathématiques", "6ème")
            if ta.school_class == "6ème" and ta.subject == "Mathématiques" else ta
            for ta in sd.teacher_assignments
        ]
        errors = sd.validate()
        assert any("qualifié" in e for e in errors), (
            "Expected unqualified-teacher error, got: " + str(errors)
        )

    def test_validate_rejects_missing_assignment(self) -> None:
        """If a (class, subject) pair has no TeacherAssignment, validate() must error."""
        sd = _make_school()
        # Remove the assignment for 6ème SVT
        sd.teacher_assignments = [
            ta for ta in sd.teacher_assignments
            if not (ta.school_class == "6ème" and ta.subject == "SVT")
        ]
        errors = sd.validate()
        assert any("6ème" in e and "SVT" in e for e in errors), (
            "Expected missing-assignment error for 6ème/SVT, got: " + str(errors)
        )

    def test_validate_rejects_duplicate_assignment(self) -> None:
        """Two TeacherAssignments for the same (class, subject) must error."""
        sd = _make_school()
        sd.teacher_assignments.append(
            TeacherAssignment("Prof Maths", "Mathématiques", "6ème")
        )
        errors = sd.validate()
        assert any("double" in e.lower() for e in errors), (
            "Expected duplicate-assignment error, got: " + str(errors)
        )

    @pytest.mark.skipif(
        not REAL_SCHOOL_JSON.exists(),
        reason="real_school_dakar.json not found",
    )
    def test_real_school_cheikh_gets_anglais_3eme(self) -> None:
        """Cheikh Ndour is assigned Anglais 3ème via TeacherAssignment."""
        sd = SchoolData.from_json(REAL_SCHOOL_JSON)
        cheikh_anglais = next(
            (ta for ta in sd.teacher_assignments
             if ta.school_class == "3ème" and ta.subject == "Anglais"),
            None,
        )
        assert cheikh_anglais is not None
        assert cheikh_anglais.teacher == "Cheikh Ndour", (
            f"Expected Cheikh Ndour for 3ème Anglais, got {cheikh_anglais.teacher}"
        )
        # Validate passes
        assert sd.validate() == []

    @pytest.mark.skipif(
        not REAL_SCHOOL_JSON.exists(),
        reason="real_school_dakar.json not found",
    )
    def test_real_school_cheikh_actually_teaches(self) -> None:
        """After solving, Cheikh should have Anglais sessions in the timetable."""
        sd     = SchoolData.from_json(REAL_SCHOOL_JSON)
        result = TimetableSolver().solve(sd, timeout_seconds=60)
        assert result.solved or result.partial
        cheikh_sessions = [
            a for a in result.assignments if a.teacher == "Cheikh Ndour"
        ]
        assert len(cheikh_sessions) > 0, (
            "Cheikh Ndour should teach at least one session (Anglais 3ème)"
        )
