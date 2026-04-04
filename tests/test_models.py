"""
Tests for timease/engine/models.py.

Run with:  python -m pytest
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

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
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_JSON = Path(__file__).parent.parent / "timease" / "data" / "sample_school.json"


@pytest.fixture(scope="module")
def sample_school() -> SchoolData:
    """Load the sample school once for all tests that need realistic data."""
    return SchoolData.from_json(SAMPLE_JSON)


@pytest.fixture()
def minimal_timeslot() -> TimeslotConfig:
    """A small two-day, one-session config for slot-count tests."""
    return TimeslotConfig(
        days=["lundi", "mardi"],
        sessions=[SessionConfig("Matin", "08:00", "10:00")],
        base_unit_minutes=30,
    )


@pytest.fixture()
def base_school_data(sample_school: SchoolData) -> SchoolData:
    """
    A deep-copied SchoolData built fresh from JSON each time, so individual
    tests can mutate it without affecting others.
    """
    return SchoolData.from_json(SAMPLE_JSON)


# ---------------------------------------------------------------------------
# 1. Loading the sample JSON and verifying entity counts
# ---------------------------------------------------------------------------

class TestSampleSchoolLoading:
    def test_school_identity(self, sample_school: SchoolData) -> None:
        assert sample_school.school.name == "Lycée Excellence de Dakar"
        assert sample_school.school.academic_year == "2026-2027"
        assert sample_school.school.city == "Dakar"

    def test_subject_count(self, sample_school: SchoolData) -> None:
        assert len(sample_school.subjects) == 11

    def test_teacher_count(self, sample_school: SchoolData) -> None:
        assert len(sample_school.teachers) == 14

    def test_class_count(self, sample_school: SchoolData) -> None:
        assert len(sample_school.classes) == 8

    def test_room_count(self, sample_school: SchoolData) -> None:
        assert len(sample_school.rooms) == 9

    def test_curriculum_entry_count(self, sample_school: SchoolData) -> None:
        assert len(sample_school.curriculum) == 41

    def test_constraint_count(self, sample_school: SchoolData) -> None:
        assert len(sample_school.constraints) == 7

    def test_sample_school_passes_validation(self, sample_school: SchoolData) -> None:
        """The bundled sample data must be internally consistent."""
        errors = sample_school.validate()
        assert errors == [], f"Unexpected validation errors: {errors}"


# ---------------------------------------------------------------------------
# 2. Teacher validation — empty subjects list
# ---------------------------------------------------------------------------

class TestTeacherValidation:
    def test_reject_empty_subjects(self) -> None:
        teacher = Teacher(name="M. Test", subjects=[], max_hours_per_week=18)
        with pytest.raises(ValueError, match="matière"):
            teacher.validate()

    # 3. Teacher validation — max_hours <= 0
    def test_reject_zero_max_hours(self) -> None:
        teacher = Teacher(name="M. Test", subjects=["Maths"], max_hours_per_week=0)
        with pytest.raises(ValueError, match="volume horaire"):
            teacher.validate()

    def test_reject_negative_max_hours(self) -> None:
        teacher = Teacher(name="M. Test", subjects=["Maths"], max_hours_per_week=-5)
        with pytest.raises(ValueError, match="volume horaire"):
            teacher.validate()

    def test_valid_teacher_does_not_raise(self) -> None:
        teacher = Teacher(name="M. Test", subjects=["Maths"], max_hours_per_week=18)
        teacher.validate()  # must not raise


# ---------------------------------------------------------------------------
# 4. SchoolClass validation — student_count <= 0
# ---------------------------------------------------------------------------

class TestSchoolClassValidation:
    def test_reject_zero_students(self) -> None:
        klass = SchoolClass(name="6ème A", level="6ème", student_count=0)
        with pytest.raises(ValueError, match="élève"):
            klass.validate()

    def test_reject_negative_students(self) -> None:
        klass = SchoolClass(name="6ème A", level="6ème", student_count=-1)
        with pytest.raises(ValueError, match="élève"):
            klass.validate()

    def test_valid_class_does_not_raise(self) -> None:
        klass = SchoolClass(name="6ème A", level="6ème", student_count=35)
        klass.validate()  # must not raise


# ---------------------------------------------------------------------------
# 5. Room validation — capacity <= 0
# ---------------------------------------------------------------------------

class TestRoomValidation:
    def test_reject_zero_capacity(self) -> None:
        room = Room(name="Salle 01", capacity=0, types=["Salle standard"])
        with pytest.raises(ValueError, match="capacité"):
            room.validate()

    def test_reject_negative_capacity(self) -> None:
        room = Room(name="Salle 01", capacity=-10, types=["Salle standard"])
        with pytest.raises(ValueError, match="capacité"):
            room.validate()

    def test_valid_room_does_not_raise(self) -> None:
        room = Room(name="Salle 01", capacity=40, types=["Salle standard"])
        room.validate()  # must not raise


# ---------------------------------------------------------------------------
# 6. CurriculumEntry validation — manual mode with missing fields
# ---------------------------------------------------------------------------

class TestCurriculumEntryValidation:
    def test_reject_manual_missing_sessions_per_week(self) -> None:
        entry = CurriculumEntry(
            level="6ème",
            subject="SVT",
            total_minutes_per_week=120,
            mode="manual",
            sessions_per_week=None,        # missing
            minutes_per_session=60,
        )
        with pytest.raises(ValueError, match="manual"):
            entry.validate()

    def test_reject_manual_missing_minutes_per_session(self) -> None:
        entry = CurriculumEntry(
            level="6ème",
            subject="SVT",
            total_minutes_per_week=120,
            mode="manual",
            sessions_per_week=2,
            minutes_per_session=None,      # missing
        )
        with pytest.raises(ValueError, match="manual"):
            entry.validate()

    def test_reject_zero_total_minutes(self) -> None:
        entry = CurriculumEntry(
            level="6ème", subject="SVT", total_minutes_per_week=0
        )
        with pytest.raises(ValueError, match="positif"):
            entry.validate()

    def test_reject_invalid_mode(self) -> None:
        entry = CurriculumEntry(
            level="6ème", subject="SVT", total_minutes_per_week=120, mode="weekly"
        )
        with pytest.raises(ValueError, match="invalide"):
            entry.validate()

    def test_valid_manual_entry_does_not_raise(self) -> None:
        entry = CurriculumEntry(
            level="6ème",
            subject="SVT",
            total_minutes_per_week=120,
            mode="manual",
            sessions_per_week=1,
            minutes_per_session=120,
        )
        entry.validate()  # must not raise

    def test_valid_auto_entry_does_not_raise(self) -> None:
        entry = CurriculumEntry(
            level="6ème",
            subject="Mathématiques",
            total_minutes_per_week=300,
            mode="auto",
            min_session_minutes=60,
            max_session_minutes=120,
        )
        entry.validate()  # must not raise


# ---------------------------------------------------------------------------
# 7. SchoolData.validate() — no qualified teacher for a subject
# ---------------------------------------------------------------------------

class TestSchoolDataValidation:
    def test_catches_subject_with_no_teacher(self, base_school_data: SchoolData) -> None:
        """Add a curriculum entry for a subject no teacher can teach."""
        base_school_data.curriculum.append(
            CurriculumEntry(
                level="6ème",
                subject="Philosophie",   # exists nowhere in subjects or teachers
                total_minutes_per_week=60,
            )
        )
        # Also add it to subjects so it passes the subject-name check first.
        base_school_data.subjects.append(
            Subject("Philosophie", "Philo", "#FFFFFF")
        )
        errors = base_school_data.validate()
        assert any("Philosophie" in e for e in errors), (
            f"Expected an error about 'Philosophie', got: {errors}"
        )

    # 8. SchoolData.validate() — subject requires lab but no lab room exists
    def test_catches_missing_lab_room(self, base_school_data: SchoolData) -> None:
        """Remove all Laboratoire rooms; SVT validation should fire."""
        base_school_data.rooms = [
            r for r in base_school_data.rooms
            if "Laboratoire" not in r.types
        ]
        errors = base_school_data.validate()
        assert any("Laboratoire" in e for e in errors), (
            f"Expected an error about 'Laboratoire', got: {errors}"
        )

    def test_clean_data_has_no_errors(self, sample_school: SchoolData) -> None:
        assert sample_school.validate() == []


# ---------------------------------------------------------------------------
# 9. TimeslotConfig.get_all_slots() — correct slot count
# ---------------------------------------------------------------------------

class TestGetAllSlots:
    def test_sample_school_slot_count(self, sample_school: SchoolData) -> None:
        """
        6 days × (8 morning slots + 4 afternoon slots) = 72 slots.
        Matin  08:00-12:00 → 4 h / 30 min = 8 slots per day
        Apres-midi 15:00-17:00 → 2 h / 30 min = 4 slots per day
        """
        slots = sample_school.timeslot_config.get_all_slots()
        assert len(slots) == 72

    def test_slot_structure(self, sample_school: SchoolData) -> None:
        """Every slot is a (day, start, end) 3-tuple with HH:MM strings."""
        for slot in sample_school.timeslot_config.get_all_slots():
            day, start, end = slot
            assert day in sample_school.timeslot_config.days
            assert len(start) == 5 and start[2] == ":"
            assert len(end) == 5 and end[2] == ":"

    def test_no_slots_overlap_within_day(self, sample_school: SchoolData) -> None:
        """For each day, slot end times must equal the next slot's start time
        (within the same session — gaps between sessions are allowed)."""
        from itertools import groupby

        slots = sample_school.timeslot_config.get_all_slots()
        by_day: dict[str, list[tuple[str, str, str]]] = {}
        for day, start, end in slots:
            by_day.setdefault(day, []).append((day, start, end))

        for day, day_slots in by_day.items():
            for i in range(len(day_slots) - 1):
                _, s1, e1 = day_slots[i]
                _, s2, e2 = day_slots[i + 1]
                # Either slots are consecutive (no gap) or there is a session break.
                if e1 > "12:00" or s2 < "15:00":
                    # Both in the same session — must be consecutive.
                    assert e1 == s2, (
                        f"Gap within session on {day}: slot ends {e1}, next starts {s2}"
                    )

    def test_minimal_config_slot_count(self, minimal_timeslot: TimeslotConfig) -> None:
        """2 days × 1 session (08:00-10:00, 30 min unit) = 2 × 4 = 8 slots."""
        slots = minimal_timeslot.get_all_slots()
        assert len(slots) == 8

    def test_base_unit_larger_than_session_yields_no_slots(self) -> None:
        """A base unit longer than the session window should produce zero slots."""
        tc = TimeslotConfig(
            days=["lundi"],
            sessions=[SessionConfig("Court", "08:00", "08:20")],
            base_unit_minutes=30,
        )
        assert tc.get_all_slots() == []

    def test_slots_cover_all_days(self, sample_school: SchoolData) -> None:
        slots = sample_school.timeslot_config.get_all_slots()
        days_covered = {s[0] for s in slots}
        assert days_covered == set(sample_school.timeslot_config.days)


# ---------------------------------------------------------------------------
# 10. JSON round-trip
# ---------------------------------------------------------------------------

class TestJsonRoundTrip:
    def test_round_trip_preserves_school(self, sample_school: SchoolData) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            sample_school.to_json(tmp)
            restored = SchoolData.from_json(tmp)
            assert restored.school.name == sample_school.school.name
            assert restored.school.academic_year == sample_school.school.academic_year
            assert restored.school.city == sample_school.school.city
        finally:
            tmp.unlink(missing_ok=True)

    def test_round_trip_preserves_counts(self, sample_school: SchoolData) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            sample_school.to_json(tmp)
            restored = SchoolData.from_json(tmp)
            assert len(restored.subjects)    == len(sample_school.subjects)
            assert len(restored.teachers)    == len(sample_school.teachers)
            assert len(restored.classes)     == len(sample_school.classes)
            assert len(restored.rooms)       == len(sample_school.rooms)
            assert len(restored.curriculum)  == len(sample_school.curriculum)
            assert len(restored.constraints) == len(sample_school.constraints)
        finally:
            tmp.unlink(missing_ok=True)

    def test_round_trip_preserves_nested_objects(self, sample_school: SchoolData) -> None:
        """Nested dataclasses (sessions, unavailable_slots, etc.) survive the trip."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            sample_school.to_json(tmp)
            restored = SchoolData.from_json(tmp)

            orig_sessions  = sample_school.timeslot_config.sessions
            rest_sessions  = restored.timeslot_config.sessions
            assert len(rest_sessions) == len(orig_sessions)
            for orig, rest in zip(orig_sessions, rest_sessions):
                assert rest.name       == orig.name
                assert rest.start_time == orig.start_time
                assert rest.end_time   == orig.end_time

            # Teacher with unavailability (Mme Sanogo, index 2)
            orig_teacher = sample_school.teachers[2]
            rest_teacher = restored.teachers[2]
            assert rest_teacher.name == orig_teacher.name
            assert rest_teacher.unavailable_slots == orig_teacher.unavailable_slots
        finally:
            tmp.unlink(missing_ok=True)

    def test_round_trip_produces_valid_json(self, sample_school: SchoolData) -> None:
        """Output file must be valid UTF-8 JSON."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            sample_school.to_json(tmp)
            raw = tmp.read_text(encoding="utf-8")
            parsed = json.loads(raw)
            assert "school" in parsed
            assert "timeslot_config" in parsed
        finally:
            tmp.unlink(missing_ok=True)

    def test_round_trip_curriculum_modes_preserved(self, sample_school: SchoolData) -> None:
        """Manual and auto curriculum entries round-trip with correct mode field."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            sample_school.to_json(tmp)
            restored = SchoolData.from_json(tmp)
            orig_modes    = [e.mode for e in sample_school.curriculum]
            restored_modes = [e.mode for e in restored.curriculum]
            assert restored_modes == orig_modes
        finally:
            tmp.unlink(missing_ok=True)
