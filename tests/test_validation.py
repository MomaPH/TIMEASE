"""
Tests for the expanded validation in timease/engine/models.py.

Covers:
- Individual entity validate() called from SchoolData.validate()
- Infrastructure safety checks
- Data integrity checks
- validate_warnings()
- TimetableResult.verify()

Run with:  uv run pytest
"""

from __future__ import annotations

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
    TimeslotConfig,
    TimetableResult,
    _MAX_CLASSES,
    _MAX_ROOMS,
    _MAX_TEACHERS,
)

SAMPLE_JSON = Path(__file__).parent.parent / "timease" / "data" / "sample_school.json"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def base() -> SchoolData:
    """Minimal but valid SchoolData — tests mutate copies of it."""
    return SchoolData.from_json(SAMPLE_JSON)


def _minimal_school() -> SchoolData:
    """Smallest possible valid school: 1 class, 1 teacher, 1 subject, 1 room."""
    return SchoolData(
        school=School("Lycée Test", "2026-2027", "Dakar"),
        timeslot_config=TimeslotConfig(
            days=["lundi"],
            sessions=[SessionConfig("Matin", "08:00", "10:00")],
            base_unit_minutes=30,
        ),
        subjects=[Subject("Maths", "M", "#FFF")],
        teachers=[Teacher("M. Test", ["Maths"], max_hours_per_week=10)],
        classes=[SchoolClass("6A", "6ème", 30)],
        rooms=[Room("Salle 1", 40, ["Salle standard"])],
        curriculum=[
            CurriculumEntry(
                level="6ème",
                subject="Maths",
                total_minutes_per_week=60,
                mode="manual",
                sessions_per_week=1,
                minutes_per_session=60,
            )
        ],
        constraints=[],
    )


# ---------------------------------------------------------------------------
# 1. Entity validate() methods are called by SchoolData.validate()
# ---------------------------------------------------------------------------

class TestEntityValidateCalledFromSchoolData:
    def test_invalid_teacher_propagates(self, base: SchoolData) -> None:
        base.teachers[0].subjects = []
        errors = base.validate()
        assert any("matière" in e for e in errors)

    def test_invalid_teacher_max_hours_propagates(self, base: SchoolData) -> None:
        base.teachers[0].max_hours_per_week = 0
        errors = base.validate()
        assert any("volume horaire" in e for e in errors)

    def test_invalid_class_student_count_propagates(self, base: SchoolData) -> None:
        base.classes[0].student_count = 0
        errors = base.validate()
        assert any("élève" in e for e in errors)

    def test_invalid_room_capacity_propagates(self, base: SchoolData) -> None:
        base.rooms[0].capacity = -5
        errors = base.validate()
        assert any("capacité" in e for e in errors)

    def test_invalid_curriculum_entry_propagates(self, base: SchoolData) -> None:
        base.curriculum[0].total_minutes_per_week = 0
        errors = base.validate()
        assert any("positif" in e for e in errors)


# ---------------------------------------------------------------------------
# 2. Infrastructure safety: base_unit_minutes
# ---------------------------------------------------------------------------

class TestBaseUnitValidation:
    def test_valid_units_accepted(self) -> None:
        for unit in (15, 30, 60):
            sd = _minimal_school()
            sd.timeslot_config.base_unit_minutes = unit
            errors = sd.validate()
            assert not any("unité de base" in e for e in errors), (
                f"unit={unit} unexpectedly rejected"
            )

    def test_invalid_unit_rejected(self) -> None:
        sd = _minimal_school()
        sd.timeslot_config.base_unit_minutes = 45
        errors = sd.validate()
        assert any("unité de base" in e for e in errors)

    def test_zero_unit_rejected(self) -> None:
        sd = _minimal_school()
        sd.timeslot_config.base_unit_minutes = 0
        errors = sd.validate()
        assert any("unité de base" in e for e in errors)


# ---------------------------------------------------------------------------
# 3. Infrastructure safety: session times
# ---------------------------------------------------------------------------

class TestSessionTimeValidation:
    def test_end_before_start_rejected(self) -> None:
        sd = _minimal_school()
        sd.timeslot_config.sessions[0].end_time = "07:00"
        errors = sd.validate()
        assert any("heure de fin" in e for e in errors)

    def test_end_equal_start_rejected(self) -> None:
        sd = _minimal_school()
        sd.timeslot_config.sessions[0].end_time = "08:00"
        errors = sd.validate()
        assert any("heure de fin" in e for e in errors)

    def test_valid_session_accepted(self) -> None:
        sd = _minimal_school()
        errors = sd.validate()
        assert not any("heure de fin" in e for e in errors)


# ---------------------------------------------------------------------------
# 4. Infrastructure safety: absolute ceilings
# ---------------------------------------------------------------------------

class TestAbsoluteCeilings:
    def test_too_many_classes(self, base: SchoolData) -> None:
        extra = [
            SchoolClass(f"X{i}", "6ème", 30) for i in range(_MAX_CLASSES + 1)
        ]
        base.classes = extra
        errors = base.validate()
        assert any("classes" in e and str(_MAX_CLASSES) in e for e in errors)

    def test_too_many_teachers(self, base: SchoolData) -> None:
        extra = [
            Teacher(f"Prof {i}", ["Maths"], 18) for i in range(_MAX_TEACHERS + 1)
        ]
        # Keep real teachers for cross-checks; just spike the count
        base.teachers = extra
        errors = base.validate()
        assert any("enseignants" in e and str(_MAX_TEACHERS) in e for e in errors)

    def test_too_many_rooms(self, base: SchoolData) -> None:
        extra = [Room(f"Salle {i}", 40, ["Salle standard"]) for i in range(_MAX_ROOMS + 1)]
        base.rooms = extra
        errors = base.validate()
        assert any("salles" in e and str(_MAX_ROOMS) in e for e in errors)

    def test_at_ceiling_is_accepted(self) -> None:
        sd = _minimal_school()
        sd.classes = [SchoolClass(f"C{i}", "6ème", 30) for i in range(_MAX_CLASSES)]
        # Only check that the "classes" ceiling error is absent
        errors = sd.validate()
        assert not any(
            "classes" in e and str(_MAX_CLASSES) in e for e in errors
        )


# ---------------------------------------------------------------------------
# 5. Data integrity: duplicate names
# ---------------------------------------------------------------------------

class TestDuplicateNames:
    def test_duplicate_teacher_names_rejected(self, base: SchoolData) -> None:
        dup = Teacher(base.teachers[0].name, ["Maths"], 10)
        base.teachers.append(dup)
        errors = base.validate()
        assert any("enseignant en double" in e for e in errors)

    def test_duplicate_class_names_rejected(self, base: SchoolData) -> None:
        dup = SchoolClass(base.classes[0].name, "6ème", 30)
        base.classes.append(dup)
        errors = base.validate()
        assert any("classe en double" in e for e in errors)

    def test_duplicate_room_names_rejected(self, base: SchoolData) -> None:
        dup = Room(base.rooms[0].name, 40, ["Salle standard"])
        base.rooms.append(dup)
        errors = base.validate()
        assert any("salle en double" in e for e in errors)

    def test_unique_names_accepted(self, base: SchoolData) -> None:
        errors = base.validate()
        assert not any("en double" in e for e in errors)


# ---------------------------------------------------------------------------
# 6. Data integrity: constraint type and priority
# ---------------------------------------------------------------------------

class TestConstraintValidation:
    def test_invalid_type_rejected(self) -> None:
        sd = _minimal_school()
        sd.constraints.append(
            Constraint(id="X1", type="maybe", category="start_time",
                       description_fr="test", priority=5)
        )
        errors = sd.validate()
        assert any("type invalide" in e for e in errors)

    def test_priority_zero_rejected(self) -> None:
        sd = _minimal_school()
        sd.constraints.append(
            Constraint(id="S1", type="soft", category="subject_spread",
                       description_fr="test", priority=0)
        )
        errors = sd.validate()
        assert any("priorité invalide" in e for e in errors)

    def test_priority_11_rejected(self) -> None:
        sd = _minimal_school()
        sd.constraints.append(
            Constraint(id="S2", type="soft", category="subject_spread",
                       description_fr="test", priority=11)
        )
        errors = sd.validate()
        assert any("priorité invalide" in e for e in errors)

    def test_priority_1_accepted(self) -> None:
        sd = _minimal_school()
        sd.constraints.append(
            Constraint(id="S1", type="soft", category="subject_spread",
                       description_fr="test", priority=1)
        )
        errors = sd.validate()
        assert not any("priorité invalide" in e for e in errors)

    def test_priority_10_accepted(self) -> None:
        sd = _minimal_school()
        sd.constraints.append(
            Constraint(id="S1", type="soft", category="subject_spread",
                       description_fr="test", priority=10)
        )
        errors = sd.validate()
        assert not any("priorité invalide" in e for e in errors)

    def test_valid_hard_constraint_accepted(self) -> None:
        sd = _minimal_school()
        sd.constraints.append(
            Constraint(id="H1", type="hard", category="start_time",
                       description_fr="test", priority=5)
        )
        errors = sd.validate()
        assert not any("type invalide" in e or "priorité invalide" in e
                       for e in errors)


# ---------------------------------------------------------------------------
# 7. Data integrity: curriculum mode consistency
# ---------------------------------------------------------------------------

class TestCurriculumModeConsistency:
    def test_auto_mode_min_greater_than_max_rejected(self) -> None:
        sd = _minimal_school()
        sd.curriculum[0] = CurriculumEntry(
            level="6ème", subject="Maths",
            total_minutes_per_week=120, mode="auto",
            min_session_minutes=90, max_session_minutes=60,
        )
        errors = sd.validate()
        assert any("min_session_minutes" in e and "max_session_minutes" in e
                   for e in errors)

    def test_auto_mode_min_equal_max_accepted(self) -> None:
        sd = _minimal_school()
        sd.curriculum[0] = CurriculumEntry(
            level="6ème", subject="Maths",
            total_minutes_per_week=60, mode="auto",
            min_session_minutes=60, max_session_minutes=60,
        )
        errors = sd.validate()
        assert not any("min_session_minutes" in e for e in errors)

    def test_manual_mode_inconsistent_total_rejected(self) -> None:
        sd = _minimal_school()
        sd.curriculum[0] = CurriculumEntry(
            level="6ème", subject="Maths",
            total_minutes_per_week=90,   # inconsistent: 2 × 60 = 120 ≠ 90
            mode="manual",
            sessions_per_week=2,
            minutes_per_session=60,
        )
        errors = sd.validate()
        assert any("incohérent" in e for e in errors)

    def test_manual_mode_consistent_total_accepted(self) -> None:
        sd = _minimal_school()
        sd.curriculum[0] = CurriculumEntry(
            level="6ème", subject="Maths",
            total_minutes_per_week=120,
            mode="manual",
            sessions_per_week=2,
            minutes_per_session=60,
        )
        errors = sd.validate()
        assert not any("incohérent" in e for e in errors)


# ---------------------------------------------------------------------------
# 8. validate_warnings(): room capacity
# ---------------------------------------------------------------------------

class TestValidateWarnings:
    def test_room_too_small_triggers_warning(self) -> None:
        sd = _minimal_school()
        sd.classes[0].student_count = 50   # room capacity is 40
        warnings = sd.validate_warnings()
        assert any("dépasse la capacité" in w for w in warnings)

    def test_room_exact_capacity_no_warning(self) -> None:
        sd = _minimal_school()
        sd.classes[0].student_count = 40   # exactly the room capacity
        warnings = sd.validate_warnings()
        assert not any("dépasse la capacité" in w for w in warnings)

    def test_no_room_subject_skipped(self) -> None:
        """EPS-style subjects (needs_room=False) must not trigger room warnings."""
        sd = _minimal_school()
        sd.subjects[0].needs_room = False
        sd.classes[0].student_count = 9999
        warnings = sd.validate_warnings()
        assert not any("dépasse la capacité" in w for w in warnings)

    def test_teacher_load_warning(self) -> None:
        """A teacher whose sole-subject demand exceeds 80 % of max should warn."""
        sd = _minimal_school()
        # Add a second class so that one teacher must teach 2 × 60 min = 120 min
        sd.classes.append(SchoolClass("6B", "6ème", 30))
        sd.curriculum.append(
            CurriculumEntry(
                level="6ème", subject="Maths",
                total_minutes_per_week=60,
                mode="manual", sessions_per_week=1, minutes_per_session=60,
            )
        )
        # Teacher max = 10 h = 600 min; sole demand = 2 × 60 = 120 min
        # 80 % threshold = 480 min — 120 < 480, so NO warning yet.
        warnings = sd.validate_warnings()
        assert not any("charge obligatoire" in w for w in warnings)

    def test_teacher_heavy_load_warning(self) -> None:
        """Sole demand > 80 % of max must produce a warning."""
        sd = _minimal_school()
        sd.teachers[0].max_hours_per_week = 2  # max = 120 min; 80 % = 96 min
        sd.classes.append(SchoolClass("6B", "6ème", 30))
        sd.curriculum.append(
            CurriculumEntry(
                level="6ème", subject="Maths",
                total_minutes_per_week=60,
                mode="manual", sessions_per_week=1, minutes_per_session=60,
            )
        )
        # Sole demand = 2 × 60 = 120 min > 96 min threshold
        warnings = sd.validate_warnings()
        assert any("charge obligatoire" in w for w in warnings)


# ---------------------------------------------------------------------------
# 9. TimetableResult.verify()
# ---------------------------------------------------------------------------

def _make_valid_result() -> tuple[TimetableResult, SchoolData]:
    """Return a minimal valid (result, school_data) pair for verify() tests."""
    sd = _minimal_school()
    result = TimetableResult(
        assignments=[
            Assignment(
                school_class="6A",
                subject="Maths",
                teacher="M. Test",
                day="lundi",
                start_time="08:00",
                end_time="09:00",
                room="Salle 1",
            )
        ],
        solved=True,
        solve_time_seconds=0.1,
    )
    return result, sd


class TestTimetableResultVerify:
    def test_valid_result_passes(self) -> None:
        result, sd = _make_valid_result()
        violations = result.verify(sd)
        assert violations == [], f"Unexpected violations: {violations}"

    def test_teacher_double_booked(self) -> None:
        result, sd = _make_valid_result()
        # Add a second assignment for the same teacher at the same time
        result.assignments.append(
            Assignment(
                school_class="6A",
                subject="Maths",
                teacher="M. Test",
                day="lundi",
                start_time="08:30",
                end_time="09:30",
                room=None,
            )
        )
        violations = result.verify(sd)
        assert any("M. Test" in v for v in violations)

    def test_room_double_booked(self) -> None:
        result, sd = _make_valid_result()
        sd.classes.append(SchoolClass("6B", "6ème", 30))
        sd.teachers.append(Teacher("M. Autre", ["Maths"], max_hours_per_week=10))
        result.assignments.append(
            Assignment(
                school_class="6B",
                subject="Maths",
                teacher="M. Autre",
                day="lundi",
                start_time="08:00",
                end_time="09:00",
                room="Salle 1",  # same room, same slot
            )
        )
        violations = result.verify(sd)
        assert any("Salle 1" in v for v in violations)

    def test_class_double_booked(self) -> None:
        result, sd = _make_valid_result()
        sd.subjects.append(Subject("Français", "Fr", "#EEE"))
        sd.teachers.append(Teacher("Mme Autre", ["Français"], max_hours_per_week=10))
        result.assignments.append(
            Assignment(
                school_class="6A",
                subject="Français",
                teacher="Mme Autre",
                day="lundi",
                start_time="08:00",
                end_time="09:00",
                room=None,
            )
        )
        violations = result.verify(sd)
        assert any("6A" in v for v in violations)

    def test_curriculum_mismatch_detected(self) -> None:
        result, sd = _make_valid_result()
        # Assignment covers only 30 min but curriculum requires 60 min
        result.assignments[0].end_time = "08:30"
        violations = result.verify(sd)
        assert any("Curriculum non respecté" in v for v in violations)

    def test_teacher_max_hours_exceeded(self) -> None:
        result, sd = _make_valid_result()
        sd.teachers[0].max_hours_per_week = 1   # max = 60 min
        # Assignment is 60 min — exactly at limit, should be OK
        violations = result.verify(sd)
        assert not any("dépasse son maximum" in v for v in violations)

    def test_teacher_over_max_hours_detected(self) -> None:
        result, sd = _make_valid_result()
        sd.teachers[0].max_hours_per_week = 1   # max = 60 min
        # Add another 60-min block → total 120 min > 60 min limit
        result.assignments.append(
            Assignment(
                school_class="6A",
                subject="Maths",
                teacher="M. Test",
                day="mardi",
                start_time="08:00",
                end_time="09:00",
                room=None,
            )
        )
        violations = result.verify(sd)
        assert any("dépasse son maximum" in v for v in violations)

    def test_room_capacity_exceeded(self) -> None:
        result, sd = _make_valid_result()
        sd.classes[0].student_count = 50   # room capacity is 40
        violations = result.verify(sd)
        assert any("trop petite" in v for v in violations)

    def test_room_capacity_exact_no_violation(self) -> None:
        result, sd = _make_valid_result()
        sd.classes[0].student_count = 40   # exactly at capacity
        violations = result.verify(sd)
        assert not any("trop petite" in v for v in violations)

    def test_non_overlapping_assignments_no_violation(self) -> None:
        """Two consecutive assignments for the same teacher must not flag."""
        result, sd = _make_valid_result()
        result.assignments.append(
            Assignment(
                school_class="6A",
                subject="Maths",
                teacher="M. Test",
                day="lundi",
                start_time="09:00",
                end_time="10:00",
                room=None,
            )
        )
        # Teacher total: 60 + 60 = 120 min = 2h < 10h max → no hour violation
        # Slots are consecutive, not overlapping → no double-booking
        violations = result.verify(sd)
        # Only possible issue: curriculum mismatch (total 120 min, expected 60 min)
        # We don't care about curriculum here — only check no double-booking
        assert not any("Double réservation" in v for v in violations)
