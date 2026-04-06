import pytest
from timease.engine.models import (
    SchoolData,
    School,
    SchoolClass,
    TimeslotConfig,
    SessionConfig,
    Teacher,
    Subject,
    CurriculumEntry,
    ManualAssignmentValidator,
    Room,
    TeacherAssignment
)

def test_valid_assignments():
    teachers = [Teacher(name="M. Diallo", subjects=["Maths"], max_hours_per_week=20)]
    curriculum = [
        CurriculumEntry(
            level="6ème",
            subject="Maths",
            total_minutes_per_week=360,
            sessions_per_week=4,
            minutes_per_session=90
        )
    ]
    subjects = [Subject(name="Maths", short_name="Maths", color="#3498db")]
    teachers = [Teacher(name="M. Diallo", subjects=["Maths"], max_hours_per_week=20)]
    classes = [SchoolClass(name="6ème", level="6ème", student_count=30)]
    school = School(name="Test School", academic_year="2026-2027", city="Dakar")
    timeslot_config = TimeslotConfig(
        days=["lundi"],
        sessions=[SessionConfig(name="Matin", start_time="08:00", end_time="12:00")],
        base_unit_minutes=30
    )
    rooms = [Room(name="Salle 1", capacity=30, types=["Standard"])]
    constraints = []
    school = SchoolData(
        school=school,
        timeslot_config=timeslot_config,
        subjects=subjects,
        teachers=teachers,
        classes=classes,
        rooms=rooms,
        curriculum=curriculum,
        constraints=constraints,
        teacher_assignments=[TeacherAssignment(
            teacher="M. Diallo",
            subject="Maths",
            school_class="6ème"
        )]
    )
    ManualAssignmentValidator.validate(school)  # Should not raise

def test_missing_assignments():
    """Empty teacher_assignments should trigger validation error."""
    school = SchoolData(
        school=School(name="Test School", academic_year="2026-2027", city="Dakar"),
        timeslot_config=TimeslotConfig(
            days=["lundi"],
            sessions=[SessionConfig(name="Matin", start_time="08:00", end_time="12:00")],
            base_unit_minutes=30
        ),
        subjects=[Subject(name="Maths", short_name="Maths", color="#3498db")],
        teachers=[Teacher(name="M. Diallo", subjects=["Maths"], max_hours_per_week=20)],
        classes=[SchoolClass(name="6ème", level="6ème", student_count=30)],
        rooms=[Room(name="Salle 1", capacity=30, types=["Standard"])],
        curriculum=[
            CurriculumEntry(level="6ème", subject="Maths", total_minutes_per_week=60,
                          sessions_per_week=1, minutes_per_session=60)
        ],
        constraints=[],
        teacher_assignments=[],  # Empty assignments
    )
    with pytest.raises(ValueError, match="doivent être fournies manuellement"):
        ManualAssignmentValidator.validate(school)

def test_multiple_teachers_per_subject():
    teachers = [Teacher(name="M. Diallo", subjects=["Maths"], max_hours_per_week=20), 
               Teacher(name="M. Ndiaye", subjects=["Maths"], max_hours_per_week=20)]
    curriculum = [
        CurriculumEntry(
            level="6ème",
            subject="Maths",
            total_minutes_per_week=360,
            sessions_per_week=4,
            minutes_per_session=90
        )
    ]
    subjects = [Subject(name="Maths", short_name="Maths", color="#3498db")]
    classes = [SchoolClass(name="6ème", level="6ème", student_count=30)]
    school_info = School(name="Test School", academic_year="2026-2027", city="Dakar")
    timeslot_config = TimeslotConfig(
        days=["lundi"],
        sessions=[SessionConfig(name="Matin", start_time="08:00", end_time="12:00")],
        base_unit_minutes=30
    )
    rooms = [Room(name="Salle 1", capacity=30, types=["Standard"])]
    constraints = []
    school = SchoolData(
        school=school_info,
        timeslot_config=timeslot_config,
        subjects=subjects,
        teachers=teachers,
        classes=classes,
        rooms=rooms,
        curriculum=curriculum,
        constraints=constraints,
        teacher_assignments=[
            TeacherAssignment(teacher="M. Diallo", subject="Maths", school_class="6ème"),
            TeacherAssignment(teacher="M. Ndiaye", subject="Maths", school_class="6ème")
        ]
    )
    with pytest.raises(ValueError, match="Plusieurs enseignants affectés"):
        ManualAssignmentValidator.validate(school)