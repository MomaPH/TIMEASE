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
    BreakConfig,
    Constraint,
    CurriculumEntry,
    DayConfig,
    Room,
    School,
    SchoolClass,
    SchoolData,
    SessionConfig,
    Subject,
    Teacher,
    TeacherAssignment,
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
    return TimeslotConfig.from_simple(
        day_names=["lundi", "mardi"],
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
        # Class-based curriculum: 41 subjects × 2 classes per level = 82 entries
        assert len(sample_school.curriculum) == 82

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

    def test_qualification_is_case_and_space_tolerant(self) -> None:
        teacher = Teacher(name="M. Test", subjects=["  Mathématiques  "], max_hours_per_week=18)
        school = SchoolData(
            school=School(name="Test School", academic_year="2026-2027", city="Dakar"),
            timeslot_config=TimeslotConfig.from_simple(
                day_names=["lundi"],
                sessions=[SessionConfig("Matin", "08:00", "10:00")],
                base_unit_minutes=60,
            ),
            subjects=[Subject(name="Mathématiques", short_name="Maths", color="#FFFFFF")],
            teachers=[teacher],
            classes=[SchoolClass(name="6ème A", level="6ème", student_count=30)],
            rooms=[Room(name="Salle 1", capacity=40, types=["Salle standard"])],
            curriculum=[
                CurriculumEntry(
                    school_class="6ème A",
                    subject="Mathématiques",
                    total_minutes_per_week=60,
                    sessions_per_week=1,
                    minutes_per_session=60,
                )
            ],
            constraints=[],
            teacher_assignments=[
                TeacherAssignment(
                    teacher="M. Test",
                    subject=" mathématiques ",
                    school_class="6ème A",
                )
            ],
        )
        errors = school.validate()
        assert not any("qualifié" in e for e in errors), errors


# ---------------------------------------------------------------------------
# 4. SchoolClass validation — student_count < 0
# ---------------------------------------------------------------------------

class TestSchoolClassValidation:
    def test_accept_zero_students(self) -> None:
        klass = SchoolClass(name="6ème A", level="6ème", student_count=0)
        klass.validate()  # must not raise

    def test_reject_negative_students(self) -> None:
        klass = SchoolClass(name="6ème A", level="6ème", student_count=-1)
        with pytest.raises(ValueError, match="effectif"):
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
# 6. CurriculumEntry validation — Phase 2 (manual only, requires sessions)
# ---------------------------------------------------------------------------

class TestCurriculumEntryValidation:
    def test_reject_zero_sessions_per_week(self) -> None:
        entry = CurriculumEntry(
            school_class="6ème A",
            subject="SVT",
            total_minutes_per_week=120,
            sessions_per_week=0,       # invalid
            minutes_per_session=60,
        )
        with pytest.raises(ValueError, match="positives"):
            entry.validate()

    def test_reject_zero_minutes_per_session(self) -> None:
        entry = CurriculumEntry(
            school_class="6ème A",
            subject="SVT",
            total_minutes_per_week=120,
            sessions_per_week=2,
            minutes_per_session=0,     # invalid
        )
        with pytest.raises(ValueError, match="positives"):
            entry.validate()

    def test_reject_zero_total_minutes(self) -> None:
        entry = CurriculumEntry(
            school_class="6ème", subject="SVT", total_minutes_per_week=0,
            sessions_per_week=1, minutes_per_session=60,
        )
        with pytest.raises(ValueError, match="positif"):
            entry.validate()

    def test_valid_entry_does_not_raise(self) -> None:
        entry = CurriculumEntry(
            school_class="6ème A",
            subject="SVT",
            total_minutes_per_week=120,
            sessions_per_week=2,
            minutes_per_session=60,
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
                school_class="6ème A",
                subject="Philosophie",   # exists nowhere in subjects or teachers
                total_minutes_per_week=60,
                sessions_per_week=1,
                minutes_per_session=60,
            )
        )
        # Also add it to subjects so it passes the subject-name check first.
        base_school_data.subjects.append(
            Subject("Philosophie", "Philo", "#FFFFFF")
        )
        # Need to add a class for level 6ème if not present
        if not any(c.level == "6ème" for c in base_school_data.classes):
            base_school_data.classes.append(
                SchoolClass("6A", "6ème", 30)
            )
        errors = base_school_data.validate()
        # Should have error about missing assignment for the new subject
        assert any("Philosophie" in e for e in errors), (
            f"Expected an error about 'Philosophie', got: {errors}"
        )

    # 8. SchoolData.validate() — no longer validates room types, only assignments
    def test_clean_data_validation(self, base_school_data: SchoolData) -> None:
        """validate() should check teacher assignments, not room types."""
        # In Phase 2, we don't validate room types in validate() - that's for ConflictAnalyzer
        errors = base_school_data.validate()
        # Base data should be valid
        assert isinstance(errors, list)

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
        day_names = {d.name for d in sample_school.timeslot_config.days}
        for slot in sample_school.timeslot_config.get_all_slots():
            day, start, end = slot
            assert day in day_names
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
        tc = TimeslotConfig.from_simple(
            day_names=["lundi"],
            sessions=[SessionConfig("Court", "08:00", "08:20")],
            base_unit_minutes=30,
        )
        assert tc.get_all_slots() == []

    def test_slots_cover_all_days(self, sample_school: SchoolData) -> None:
        slots = sample_school.timeslot_config.get_all_slots()
        days_covered = {s[0] for s in slots}
        assert days_covered == {d.name for d in sample_school.timeslot_config.days}


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

            # Check first day's sessions
            orig_day_configs = sample_school.timeslot_config.days
            rest_day_configs = restored.timeslot_config.days
            assert len(rest_day_configs) == len(orig_day_configs)
            for orig_day, rest_day in zip(orig_day_configs, rest_day_configs):
                assert rest_day.name == orig_day.name
                assert len(rest_day.sessions) == len(orig_day.sessions)
                for orig_sess, rest_sess in zip(orig_day.sessions, rest_day.sessions):
                    assert rest_sess.name       == orig_sess.name
                    assert rest_sess.start_time == orig_sess.start_time
                    assert rest_sess.end_time   == orig_sess.end_time

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

    def test_round_trip_curriculum_sessions_preserved(self, sample_school: SchoolData) -> None:
        """Curriculum entries round-trip with sessions_per_week and minutes_per_session."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            sample_school.to_json(tmp)
            restored = SchoolData.from_json(tmp)
            for orig, rest in zip(sample_school.curriculum, restored.curriculum):
                assert rest.sessions_per_week == orig.sessions_per_week
                assert rest.minutes_per_session == orig.minutes_per_session
        finally:
            tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 11. BreakConfig and varied day schedules
# ---------------------------------------------------------------------------

class TestBreakConfig:
    """Tests for BreakConfig functionality and get_all_slots() with breaks."""

    def test_break_carves_hole_in_slots(self) -> None:
        """A break should remove slots that overlap with it."""
        sessions = [SessionConfig("Matin", "08:00", "12:00")]
        breaks = [BreakConfig("Récréation", "10:00", "10:30")]
        days = [DayConfig("lundi", sessions, breaks)]
        tc = TimeslotConfig(days=days, base_unit_minutes=30)

        slots = tc.get_all_slots()
        slot_starts = [s[1] for s in slots]

        # 08:00-12:00 = 8 slots normally, but 10:00-10:30 is a break = 7 slots
        assert len(slots) == 7
        assert "10:00" not in slot_starts

    def test_multiple_breaks_carve_multiple_holes(self) -> None:
        """Multiple breaks should each carve their own hole."""
        sessions = [SessionConfig("Matin", "08:00", "12:00")]
        breaks = [
            BreakConfig("Récréation 1", "09:30", "10:00"),
            BreakConfig("Récréation 2", "11:00", "11:30"),
        ]
        days = [DayConfig("lundi", sessions, breaks)]
        tc = TimeslotConfig(days=days, base_unit_minutes=30)

        slots = tc.get_all_slots()
        slot_starts = [s[1] for s in slots]

        # 8 slots normally, minus 2 breaks = 6 slots
        assert len(slots) == 6
        assert "09:30" not in slot_starts
        assert "11:00" not in slot_starts

    def test_break_spanning_multiple_slots(self) -> None:
        """A long break should remove all slots it overlaps."""
        sessions = [SessionConfig("Matin", "08:00", "12:00")]
        breaks = [BreakConfig("Pause longue", "09:00", "10:30")]  # 3 slots
        days = [DayConfig("lundi", sessions, breaks)]
        tc = TimeslotConfig(days=days, base_unit_minutes=30)

        slots = tc.get_all_slots()
        slot_starts = [s[1] for s in slots]

        # 8 slots minus 3 in the break = 5 slots
        assert len(slots) == 5
        assert "09:00" not in slot_starts
        assert "09:30" not in slot_starts
        assert "10:00" not in slot_starts

    def test_break_only_affects_its_day(self) -> None:
        """A break on one day should not affect other days."""
        sessions = [SessionConfig("Matin", "08:00", "10:00")]
        breaks_mon = [BreakConfig("Récréation", "08:30", "09:00")]
        days = [
            DayConfig("lundi", sessions, breaks_mon),
            DayConfig("mardi", sessions, []),  # No break
        ]
        tc = TimeslotConfig(days=days, base_unit_minutes=30)

        slots = tc.get_all_slots()
        mon_slots = [s for s in slots if s[0] == "lundi"]
        tue_slots = [s for s in slots if s[0] == "mardi"]

        assert len(mon_slots) == 3  # 4 minus 1 break
        assert len(tue_slots) == 4  # Full day

    def test_varied_day_schedules(self) -> None:
        """Different days can have different sessions."""
        # Monday: full day
        mon_sessions = [
            SessionConfig("Matin", "08:00", "12:00"),
            SessionConfig("Après-midi", "15:00", "17:00"),
        ]
        # Wednesday: morning only, starts later
        wed_sessions = [SessionConfig("Matin", "09:00", "12:00")]

        days = [
            DayConfig("lundi", mon_sessions, []),
            DayConfig("mercredi", wed_sessions, []),
        ]
        tc = TimeslotConfig(days=days, base_unit_minutes=30)

        slots = tc.get_all_slots()
        mon_slots = [s for s in slots if s[0] == "lundi"]
        wed_slots = [s for s in slots if s[0] == "mercredi"]

        assert len(mon_slots) == 12  # 8 morning + 4 afternoon
        assert len(wed_slots) == 6   # 6 morning only

        # Wednesday starts at 09:00
        assert wed_slots[0][1] == "09:00"

    def test_break_validation_within_sessions(self) -> None:
        """validate() should pass when breaks are within session bounds."""
        sessions = [SessionConfig("Matin", "08:00", "12:00")]
        breaks = [BreakConfig("Récréation", "10:00", "10:30")]
        days = [DayConfig("lundi", sessions, breaks)]
        tc = TimeslotConfig(days=days, base_unit_minutes=30)

        # Should not raise
        tc.validate()

    def test_break_outside_session_is_allowed(self) -> None:
        """validate() allows breaks outside session bounds."""
        sessions = [SessionConfig("Matin", "08:00", "12:00")]
        breaks = [BreakConfig("Invalid", "14:00", "14:30")]  # Outside morning
        days = [DayConfig("lundi", sessions, breaks)]
        tc = TimeslotConfig(days=days, base_unit_minutes=30)

        tc.validate()  # must not raise

    def test_overlapping_breaks_raises(self) -> None:
        """validate() should reject overlapping breaks."""
        sessions = [SessionConfig("Matin", "08:00", "12:00")]
        breaks = [
            BreakConfig("Récréation 1", "10:00", "10:30"),
            BreakConfig("Récréation 2", "10:15", "10:45"),  # Overlaps
        ]
        days = [DayConfig("lundi", sessions, breaks)]
        tc = TimeslotConfig(days=days, base_unit_minutes=30)

        with pytest.raises(ValueError, match="chevauch"):
            tc.validate()

    def test_break_json_round_trip(self) -> None:
        """Breaks should survive JSON serialization."""
        sessions = [SessionConfig("Matin", "08:00", "12:00")]
        breaks = [BreakConfig("Récréation", "10:00", "10:15")]
        days = [DayConfig("lundi", sessions, breaks)]
        tc = TimeslotConfig(days=days, base_unit_minutes=30)

        sd = SchoolData(
            school=School("Test", "2024-2025", "Test"),
            timeslot_config=tc,
            subjects=[],
            teachers=[],
            classes=[],
            rooms=[],
            curriculum=[],
            constraints=[],
        )

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        try:
            sd.to_json(tmp)
            restored = SchoolData.from_json(tmp)

            assert len(restored.timeslot_config.days) == 1
            rest_day = restored.timeslot_config.days[0]
            assert len(rest_day.breaks) == 1
            assert rest_day.breaks[0].name == "Récréation"
            assert rest_day.breaks[0].start_time == "10:00"
            assert rest_day.breaks[0].end_time == "10:15"
        finally:
            tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 12. Subject auto-derivation
# ---------------------------------------------------------------------------

class TestSubjectAutoDerivation:
    """Tests for SchoolData.derive_subjects_if_empty()."""

    def test_derives_from_curriculum(self) -> None:
        """Subjects should be auto-derived from curriculum entries."""
        tc = TimeslotConfig.from_simple(["lundi"], [SessionConfig("Matin", "08:00", "12:00")])
        sd = SchoolData(
            school=School("Test", "2024", "Test"),
            timeslot_config=tc,
            subjects=[],  # Empty
            teachers=[Teacher("M. Dupont", ["Maths"])],
            classes=[SchoolClass("6A", "6ème", 30)],
            rooms=[],
            curriculum=[
                CurriculumEntry("6A", "Maths", 120, sessions_per_week=2, minutes_per_session=60),
                CurriculumEntry("6A", "Français", 120, sessions_per_week=2, minutes_per_session=60),
            ],
            constraints=[],
        )

        assert len(sd.subjects) == 0
        sd.derive_subjects_if_empty()
        assert len(sd.subjects) == 2
        subject_names = {s.name for s in sd.subjects}
        assert "Maths" in subject_names
        assert "Français" in subject_names

    def test_derives_from_teacher_subjects(self) -> None:
        """Subjects should include those from teacher qualifications."""
        tc = TimeslotConfig.from_simple(["lundi"], [SessionConfig("Matin", "08:00", "12:00")])
        sd = SchoolData(
            school=School("Test", "2024", "Test"),
            timeslot_config=tc,
            subjects=[],
            teachers=[
                Teacher("M. Dupont", ["Maths", "Physique"]),
                Teacher("Mme Martin", ["Français", "Histoire"]),
            ],
            classes=[],
            rooms=[],
            curriculum=[],
            constraints=[],
        )

        sd.derive_subjects_if_empty()
        assert len(sd.subjects) == 4
        subject_names = {s.name for s in sd.subjects}
        assert subject_names == {"Maths", "Physique", "Français", "Histoire"}

    def test_does_not_override_existing_subjects(self) -> None:
        """If subjects are already defined, don't override them."""
        tc = TimeslotConfig.from_simple(["lundi"], [SessionConfig("Matin", "08:00", "12:00")])
        existing_subjects = [Subject("Maths", "MATH", "#FF0000")]
        sd = SchoolData(
            school=School("Test", "2024", "Test"),
            timeslot_config=tc,
            subjects=existing_subjects,
            teachers=[Teacher("M. Dupont", ["Physique"])],  # Different subject
            classes=[],
            rooms=[],
            curriculum=[],
            constraints=[],
        )

        sd.derive_subjects_if_empty()
        assert len(sd.subjects) == 1
        assert sd.subjects[0].name == "Maths"
        assert sd.subjects[0].color == "#FF0000"

    def test_auto_generates_colors(self) -> None:
        """Auto-derived subjects should have colors from the palette."""
        tc = TimeslotConfig.from_simple(["lundi"], [SessionConfig("Matin", "08:00", "12:00")])
        sd = SchoolData(
            school=School("Test", "2024", "Test"),
            timeslot_config=tc,
            subjects=[],
            teachers=[Teacher("M. Dupont", ["Maths"])],
            classes=[],
            rooms=[],
            curriculum=[],
            constraints=[],
        )

        sd.derive_subjects_if_empty()
        assert len(sd.subjects) == 1
        assert sd.subjects[0].color.startswith("#")
