"""
Generate a realistic sample school dataset for TIMEASE testing.

Run from the project root:
    python scripts/generate_sample.py

Output:
    timease/data/sample_school.json
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from the project root without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent))

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
# Builder
# ---------------------------------------------------------------------------

def build_sample_school() -> SchoolData:
    """Build and return a fully populated SchoolData for Lycée Excellence de Dakar."""

    # --- School identity ---------------------------------------------------
    school = School(
        name="Lycée Excellence de Dakar",
        academic_year="2026-2027",
        city="Dakar",
    )

    # --- Schedule structure ------------------------------------------------
    # Saturday has only a morning session; the afternoon is blocked via constraint H11.
    timeslot_config = TimeslotConfig(
        days=["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"],
        sessions=[
            SessionConfig("Matin", "08:00", "12:00"),
            SessionConfig("Après-midi", "15:00", "17:00"),
        ],
        base_unit_minutes=30,
    )

    # --- Subjects ----------------------------------------------------------
    subjects = [
        Subject("Mathématiques",      "Maths",     "#E6F1FB"),
        Subject("Français",           "Fr",         "#EAF3DE"),
        Subject("Anglais",            "Ang",        "#EEEDFE"),
        Subject("SVT",                "SVT",        "#E1F5EE",  required_room_type="Laboratoire"),
        Subject("Physique-Chimie",    "PC",         "#FAECE7",  required_room_type="Laboratoire"),
        Subject("Histoire-Géographie","Hist-Géo",  "#FAEEDA"),
        Subject("EPS",                "EPS",        "#FBEAF0",  required_room_type="EPS", needs_room=False),
        Subject("Education Civique",  "Ed.Civ",    "#F1EFE8"),
        Subject("Arts Plastiques",    "Arts",       "#FBEAF0"),
        Subject("Musique",            "Mus",        "#FBEAF0"),
        Subject("Informatique",       "Info",       "#E6F1FB"),
    ]

    # --- Teachers ----------------------------------------------------------
    teachers = [
        Teacher(
            name="Mme Diallo",
            subjects=["Mathématiques", "Physique-Chimie"],
            max_hours_per_week=18,
        ),
        Teacher(
            name="M. Traoré",
            subjects=["Français"],
            max_hours_per_week=20,
        ),
        Teacher(
            name="Mme Sanogo",
            subjects=["Anglais"],
            max_hours_per_week=15,
            unavailable_slots=[
                {"day": "mercredi", "start": None, "end": None, "session": "all"},
            ],
        ),
        Teacher(
            name="M. Koné",
            subjects=["SVT", "Physique-Chimie"],
            max_hours_per_week=18,
        ),
        Teacher(
            name="M. Camara",
            subjects=["Histoire-Géographie"],
            max_hours_per_week=16,
        ),
        Teacher(
            name="M. Bamba",
            subjects=["EPS"],
            max_hours_per_week=20,
        ),
        Teacher(
            name="Mme Ndiaye",
            subjects=["Mathématiques"],
            max_hours_per_week=18,
        ),
        Teacher(
            name="Mme Kouyaté",
            subjects=["Mathématiques"],
            max_hours_per_week=22,
        ),
        Teacher(
            name="M. Coulibaly",
            subjects=["Français"],
            max_hours_per_week=22,
        ),
        Teacher(
            name="M. Sow",
            subjects=["Français", "Anglais"],
            max_hours_per_week=16,
        ),
        Teacher(
            name="Mme Fall",
            subjects=["SVT"],
            max_hours_per_week=12,
            unavailable_slots=[
                {"day": "vendredi", "start": "15:00", "end": "17:00", "session": "Après-midi"},
            ],
        ),
        Teacher(
            name="M. Diop",
            subjects=["Histoire-Géographie", "Education Civique"],
            max_hours_per_week=18,
        ),
        Teacher(
            name="Mme Touré",
            subjects=["Arts Plastiques", "Musique"],
            max_hours_per_week=12,
        ),
        Teacher(
            name="M. Ba",
            subjects=["Informatique"],
            max_hours_per_week=10,
        ),
    ]

    # --- Classes -----------------------------------------------------------
    classes = [
        SchoolClass("6ème A", "6ème", 38),
        SchoolClass("6ème B", "6ème", 35),
        SchoolClass("5ème A", "5ème", 40),
        SchoolClass("5ème B", "5ème", 37),
        SchoolClass("4ème A", "4ème", 42),
        SchoolClass("4ème B", "4ème", 39),
        SchoolClass("3ème A", "3ème", 36),
        SchoolClass("3ème B", "3ème", 32),
    ]

    # --- Rooms -------------------------------------------------------------
    rooms = [
        Room("Salle 101", 45, ["Salle standard"]),
        Room("Salle 102", 45, ["Salle standard"]),
        Room("Salle 103", 45, ["Salle standard"]),
        Room("Salle 104", 45, ["Salle standard"]),
        Room("Salle 105", 45, ["Salle standard"]),
        Room("Salle 106", 45, ["Salle standard"]),
        Room("Salle 107", 45, ["Laboratoire"]),
        Room("Salle 108", 45, ["Laboratoire"]),   # second lab — needed for 8 classes
        Room("Terrain de sport", 200, ["EPS"]),
    ]

    # --- Curriculum --------------------------------------------------------
    # Convenience factories to keep the table below readable.

    def auto(
        level: str, subject: str, hours: int,
        min_m: int = 60, max_m: int = 120,
    ) -> CurriculumEntry:
        """Auto-split mode: solver decides session lengths within [min_m, max_m]."""
        return CurriculumEntry(
            level=level,
            subject=subject,
            total_minutes_per_week=hours * 60,
            mode="auto",
            min_session_minutes=min_m,
            max_session_minutes=max_m,
        )

    def manual(
        level: str, subject: str, hours: int,
        sessions_per_week: int, minutes_per_session: int,
    ) -> CurriculumEntry:
        """Manual mode: exact session count and duration are fixed."""
        return CurriculumEntry(
            level=level,
            subject=subject,
            total_minutes_per_week=hours * 60,
            mode="manual",
            sessions_per_week=sessions_per_week,
            minutes_per_session=minutes_per_session,
        )

    curriculum: list[CurriculumEntry] = []

    # 6ème and 5ème share the same programme (26 h/week per class).
    for level in ("6ème", "5ème"):
        curriculum += [
            auto  (level, "Mathématiques",       5),
            auto  (level, "Français",             5),
            auto  (level, "Anglais",              3),
            manual(level, "SVT",                  2, sessions_per_week=1, minutes_per_session=120),
            auto  (level, "Physique-Chimie",      2),
            auto  (level, "Histoire-Géographie",  3),
            manual(level, "EPS",                  2, sessions_per_week=1, minutes_per_session=120),
            auto  (level, "Education Civique",    1, min_m=60, max_m=60),
            auto  (level, "Arts Plastiques",      1, min_m=60, max_m=60),
            auto  (level, "Musique",              1, min_m=60, max_m=60),
            auto  (level, "Informatique",         1, min_m=60, max_m=60),
        ]

    # 4ème (27 h/week per class — more Anglais and PC, Musique dropped).
    curriculum += [
        auto  ("4ème", "Mathématiques",       5),
        auto  ("4ème", "Français",             5),
        auto  ("4ème", "Anglais",              4),
        manual("4ème", "SVT",                  2, sessions_per_week=1, minutes_per_session=120),
        auto  ("4ème", "Physique-Chimie",      3),
        auto  ("4ème", "Histoire-Géographie",  3),
        manual("4ème", "EPS",                  2, sessions_per_week=1, minutes_per_session=120),
        auto  ("4ème", "Education Civique",    1, min_m=60, max_m=60),
        auto  ("4ème", "Arts Plastiques",      1, min_m=60, max_m=60),
        auto  ("4ème", "Informatique",         1, min_m=60, max_m=60),
    ]

    # 3ème (27 h/week per class — more SVT, Arts and Musique dropped).
    curriculum += [
        auto  ("3ème", "Mathématiques",       5),
        auto  ("3ème", "Français",             5),
        auto  ("3ème", "Anglais",              4),
        manual("3ème", "SVT",                  3, sessions_per_week=2, minutes_per_session=90),
        auto  ("3ème", "Physique-Chimie",      3),
        auto  ("3ème", "Histoire-Géographie",  3),
        manual("3ème", "EPS",                  2, sessions_per_week=1, minutes_per_session=120),
        auto  ("3ème", "Education Civique",    1, min_m=60, max_m=60),
        auto  ("3ème", "Informatique",         1, min_m=60, max_m=60),
    ]

    # --- Constraints -------------------------------------------------------
    constraints = [
        Constraint(
            id="H1",
            type="hard",
            category="start_time",
            description_fr="Toutes les classes commencent au créneau 08h00.",
            parameters={"hour": "08:00"},
        ),
        Constraint(
            id="H4",
            type="hard",
            category="max_consecutive",
            description_fr="Maximum 4 heures consécutives par classe.",
            parameters={"max_hours": 4},
        ),
        Constraint(
            id="H10",
            type="hard",
            category="one_teacher_per_subject_per_class",
            description_fr="Un seul enseignant assigné par matière et par classe sur l'année entière.",
            parameters={},
        ),
        Constraint(
            id="H11",
            type="hard",
            category="day_off",
            description_fr="Aucun cours le samedi après-midi.",
            parameters={"day": "samedi", "session": "Après-midi"},
        ),
        Constraint(
            id="S3",
            type="soft",
            category="balanced_daily_load",
            description_fr="Répartition équilibrée des heures de cours par jour.",
            priority=7,
            parameters={},
        ),
        Constraint(
            id="S4",
            type="soft",
            category="subject_spread",
            description_fr="Les matières doivent être réparties sur toute la semaine (pas deux fois le même jour).",
            priority=8,
            parameters={},
        ),
        Constraint(
            id="S5",
            type="soft",
            category="heavy_subjects_morning",
            description_fr="Les matières lourdes (Maths, Français) sont placées de préférence le matin.",
            priority=6,
            parameters={
                "subjects": ["Mathématiques", "Français"],
                "preferred_session": "Matin",
            },
        ),
    ]

    return SchoolData(
        school=school,
        timeslot_config=timeslot_config,
        subjects=subjects,
        teachers=teachers,
        classes=classes,
        rooms=rooms,
        curriculum=curriculum,
        constraints=constraints,
    )


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------

def print_summary(sd: SchoolData) -> None:
    """Print a structured summary of the generated dataset."""

    total_slots = len(sd.timeslot_config.get_all_slots())
    sessions_str = "  |  ".join(
        f"{s.name} {s.start_time}-{s.end_time}" for s in sd.timeslot_config.sessions
    )

    # Group curriculum by level for per-level totals.
    by_level: dict[str, list[CurriculumEntry]] = {}
    for entry in sd.curriculum:
        by_level.setdefault(entry.level, []).append(entry)

    grand_total_h = sum(e.total_minutes_per_week for e in sd.curriculum) / 60

    border = "=" * 60

    print(border)
    print(f"  {sd.school.name}")
    print(f"  Année scolaire : {sd.school.academic_year}  |  Ville : {sd.school.city}")
    print(border)

    print(f"  Jours          : {', '.join(sd.timeslot_config.days)}")
    print(f"  Sessions       : {sessions_str}")
    print(f"  Unité de base  : {sd.timeslot_config.base_unit_minutes} min"
          f"  |  Créneaux/semaine : {total_slots}")

    print(f"\n  Matières ({len(sd.subjects)})")
    for s in sd.subjects:
        room_tag = f"  [salle: {s.required_room_type}]" if s.required_room_type else ""
        no_room  = "  (sans salle)" if not s.needs_room else ""
        print(f"    {s.short_name:<10} {s.name}{room_tag}{no_room}")

    print(f"\n  Enseignants ({len(sd.teachers)})")
    for t in sd.teachers:
        unavail = f"  — {len(t.unavailable_slots)} indisponibilité(s)" if t.unavailable_slots else ""
        subjects_str = ", ".join(t.subjects)
        print(f"    {t.name:<16} {t.max_hours_per_week:>2}h max   [{subjects_str}]{unavail}")

    print(f"\n  Classes ({len(sd.classes)})")
    for c in sd.classes:
        print(f"    {c.name:<10}  {c.student_count} élèves")

    print(f"\n  Salles ({len(sd.rooms)})")
    for r in sd.rooms:
        print(f"    {r.name:<20} {r.capacity:>3} places   {', '.join(r.types)}")

    print(f"\n  Curriculum ({len(sd.curriculum)} entrées — {grand_total_h:.0f}h cumulées/sem.)")
    for level, entries in sorted(by_level.items()):
        level_h = sum(e.total_minutes_per_week for e in entries) / 60
        subjects_str = ", ".join(e.subject for e in entries)
        print(f"    {level:<6}  {level_h:>4.0f}h/sem.  —  {subjects_str}")

    print(f"\n  Contraintes ({len(sd.constraints)})")
    for c in sd.constraints:
        tag = "[DUR]" if c.type == "hard" else f"[SOF p{c.priority}]"
        print(f"    {c.id:<4} {tag:<10} {c.description_fr}")

    # Cross-entity validation
    errors = sd.validate()
    print()
    if errors:
        print(f"  ATTENTION — {len(errors)} erreur(s) de validation :")
        for err in errors:
            print(f"    - {err}")
    else:
        print("  Validation croisée : OK — donnees cohérentes")

    print(border)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    output_path = Path(__file__).parent.parent / "timease" / "data" / "sample_school.json"

    sd = build_sample_school()
    sd.to_json(output_path)
    print_summary(sd)
    print(f"\n  Fichier sauvegarde : {output_path.resolve()}\n")
