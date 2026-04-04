"""
Data models for the TIMEASE timetable generation system.

All entities are plain dataclasses so they remain serialisable and fully
independent of the web layer (timease/app) and the I/O layer (timease/io).
"""

from __future__ import annotations

import dataclasses
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# School identity
# ---------------------------------------------------------------------------

@dataclass
class School:
    """Basic identity information about the school."""

    name: str
    academic_year: str  # e.g. "2026-2027"
    city: str


# ---------------------------------------------------------------------------
# Timeslot structure
# ---------------------------------------------------------------------------

@dataclass
class SessionConfig:
    """A named time block within a school day (e.g. morning, afternoon)."""

    name: str        # e.g. "Matin"
    start_time: str  # "HH:MM"
    end_time: str    # "HH:MM"


@dataclass
class TimeslotConfig:
    """
    Overall schedule structure: which days are active and how the day is
    divided into sessions made up of fixed-length base units.
    """

    days: list[str]                  # e.g. ["lundi", "mardi", ...]
    sessions: list[SessionConfig]
    base_unit_minutes: int = 30      # smallest schedulable block

    def get_all_slots(self) -> list[tuple[str, str, str]]:
        """
        Return every base-unit slot across all active days and sessions.

        Each element is a (day, start_time, end_time) tuple where times are
        "HH:MM" strings.  Slots that do not fit exactly within a session
        boundary are silently dropped.
        """
        slots: list[tuple[str, str, str]] = []
        delta = timedelta(minutes=self.base_unit_minutes)

        for day in self.days:
            for session in self.sessions:
                current = datetime.strptime(session.start_time, "%H:%M")
                end = datetime.strptime(session.end_time, "%H:%M")
                while current + delta <= end:
                    slot_end = current + delta
                    slots.append((
                        day,
                        current.strftime("%H:%M"),
                        slot_end.strftime("%H:%M"),
                    ))
                    current = slot_end

        return slots


# ---------------------------------------------------------------------------
# Curriculum entities
# ---------------------------------------------------------------------------

@dataclass
class Subject:
    """A taught discipline."""

    name: str               # e.g. "Mathématiques"
    short_name: str         # e.g. "Maths"
    color: str              # hex colour for UI, e.g. "#E6F1FB"
    required_room_type: str | None = None   # None → any standard room
    needs_room: bool = True                 # False for outdoor sports, etc.


@dataclass
class Teacher:
    """A staff member who can teach one or more subjects."""

    name: str
    subjects: list[str]         # subject names (must match Subject.name)
    max_hours_per_week: int
    unavailable_slots: list[dict] = field(default_factory=list)
    # Each dict: {day: str, start: str|None, end: str|None, session: str|None}
    # session defaults to "all" when omitted
    preference_weight: float = 1.0  # higher → more senior / preferred

    def validate(self) -> None:
        """Raise ValueError if the teacher data is internally inconsistent."""
        if not self.subjects:
            raise ValueError(
                f"L'enseignant '{self.name}' doit enseigner au moins une matière."
            )
        if self.max_hours_per_week <= 0:
            raise ValueError(
                f"L'enseignant '{self.name}' doit avoir un volume horaire hebdomadaire positif."
            )


@dataclass
class SchoolClass:
    """A class group (e.g. "6ème A")."""

    name: str           # e.g. "6ème A"
    level: str          # e.g. "6ème"
    student_count: int

    def validate(self) -> None:
        """Raise ValueError if the class data is internally inconsistent."""
        if self.student_count <= 0:
            raise ValueError(
                f"La classe '{self.name}' doit avoir au moins un élève."
            )


@dataclass
class Room:
    """A physical space that can host teaching sessions."""

    name: str
    capacity: int
    types: list[str] = field(default_factory=list)
    # e.g. ["Salle standard"] or ["Laboratoire", "Salle standard"]

    def validate(self) -> None:
        """Raise ValueError if the room data is internally inconsistent."""
        if self.capacity <= 0:
            raise ValueError(
                f"La salle '{self.name}' doit avoir une capacité positive."
            )


@dataclass
class CurriculumEntry:
    """
    Weekly teaching load for a subject at a given level.

    Two scheduling modes:
    - "manual": the caller fixes exactly how many sessions per week and their
      duration.
    - "auto": the solver decides session splits within the given bounds.
    """

    level: str                          # e.g. "6ème"
    subject: str                        # must match Subject.name
    total_minutes_per_week: int
    mode: str = "auto"                  # "manual" | "auto"
    # --- manual mode ---
    sessions_per_week: int | None = None
    minutes_per_session: int | None = None
    # --- auto mode ---
    min_session_minutes: int | None = None
    max_session_minutes: int | None = None

    def validate(self) -> None:
        """Raise ValueError if the entry is internally inconsistent."""
        if self.total_minutes_per_week <= 0:
            raise ValueError(
                f"Le volume horaire de '{self.subject}' (niveau {self.level}) "
                "doit être positif."
            )
        if self.mode == "manual":
            if self.sessions_per_week is None or self.minutes_per_session is None:
                raise ValueError(
                    f"Le curriculum '{self.subject}' (niveau {self.level}) est en mode "
                    "'manual' : sessions_per_week et minutes_per_session sont requis."
                )
        elif self.mode != "auto":
            raise ValueError(
                f"Le mode '{self.mode}' est invalide pour '{self.subject}' "
                f"(niveau {self.level}). Valeurs acceptées : 'manual', 'auto'."
            )


# ---------------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------------

@dataclass
class Constraint:
    """
    A scheduling constraint, either hard (must be satisfied) or soft
    (should be satisfied with a given priority).
    """

    id: str             # unique identifier, e.g. "H1", "S3"
    type: str           # "hard" | "soft"
    category: str       # constraint type code, e.g. "start_time"
    description_fr: str # human-readable description in French
    priority: int = 5   # 1–10, meaningful only for soft constraints
    parameters: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Solver output
# ---------------------------------------------------------------------------

@dataclass
class Assignment:
    """A single scheduled teaching session produced by the solver."""

    school_class: str
    subject: str
    teacher: str
    day: str
    start_time: str  # "HH:MM"
    end_time: str    # "HH:MM"
    room: str | None = None


@dataclass
class TimetableResult:
    """Container for all output produced by one solver run."""

    assignments: list[Assignment]
    solved: bool
    solve_time_seconds: float
    conflicts: list[dict] | None = None
    soft_constraints_satisfied: list[str] = field(default_factory=list)
    soft_constraints_violated: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Top-level containers
# ---------------------------------------------------------------------------

@dataclass
class SchoolData:
    """
    Complete input dataset for one timetable generation run.

    This is the single object passed to the solver and serialised to/from
    JSON for persistence and CLI usage.
    """

    school: School
    timeslot_config: TimeslotConfig
    subjects: list[Subject]
    teachers: list[Teacher]
    classes: list[SchoolClass]
    rooms: list[Room]
    curriculum: list[CurriculumEntry]
    constraints: list[Constraint]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> list[str]:
        """
        Cross-entity validation of the full dataset.

        Returns a list of error messages in French.  An empty list means the
        data is consistent and ready for the solver.
        """
        errors: list[str] = []

        subject_map = {s.name: s for s in self.subjects}
        subject_names = set(subject_map)

        # 1. All subject names in curriculum must exist in the subjects list.
        for entry in self.curriculum:
            if entry.subject not in subject_names:
                errors.append(
                    f"La matière '{entry.subject}' (niveau {entry.level}) "
                    "est absente de la liste des matières."
                )

        # 2. Every curriculum subject must have at least one qualified teacher.
        for entry in self.curriculum:
            if entry.subject not in subject_names:
                continue  # already reported above
            qualified = [t for t in self.teachers if entry.subject in t.subjects]
            if not qualified:
                errors.append(
                    f"Aucun enseignant qualifié pour la matière '{entry.subject}' "
                    f"(niveau {entry.level})."
                )

        # 3. Curriculum subjects that require a specific room type must have
        #    at least one compatible room available.
        for entry in self.curriculum:
            if entry.subject not in subject_names:
                continue
            required_type = subject_map[entry.subject].required_room_type
            if required_type is not None:
                compatible = [r for r in self.rooms if required_type in r.types]
                if not compatible:
                    errors.append(
                        f"Aucune salle de type '{required_type}' disponible "
                        f"pour la matière '{entry.subject}'."
                    )

        # 4. When only one teacher is qualified for a subject, that teacher's
        #    weekly capacity must cover the full curriculum load for that subject.
        subject_total_minutes: dict[str, int] = defaultdict(int)
        for entry in self.curriculum:
            subject_total_minutes[entry.subject] += entry.total_minutes_per_week

        for subject_name, total_minutes in subject_total_minutes.items():
            qualified = [t for t in self.teachers if subject_name in t.subjects]
            if len(qualified) == 1:
                teacher = qualified[0]
                if teacher.max_hours_per_week * 60 < total_minutes:
                    errors.append(
                        f"L'enseignant '{teacher.name}' est le seul qualifié pour "
                        f"'{subject_name}', mais sa capacité maximale "
                        f"({teacher.max_hours_per_week} h/semaine) est insuffisante "
                        f"pour couvrir les {total_minutes} minutes de curriculum hebdomadaire."
                    )

        return errors

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_json(self, path: str | Path) -> None:
        """Serialise the full dataset to a UTF-8 JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = dataclasses.asdict(self)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("SchoolData saved to %s", path)

    @classmethod
    def from_json(cls, path: str | Path) -> "SchoolData":
        """Load and reconstruct a SchoolData instance from a JSON file."""
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))

        return cls(
            school=School(**data["school"]),
            timeslot_config=TimeslotConfig(
                days=data["timeslot_config"]["days"],
                base_unit_minutes=data["timeslot_config"]["base_unit_minutes"],
                sessions=[
                    SessionConfig(**s)
                    for s in data["timeslot_config"]["sessions"]
                ],
            ),
            subjects=[Subject(**s) for s in data["subjects"]],
            teachers=[Teacher(**t) for t in data["teachers"]],
            classes=[SchoolClass(**c) for c in data["classes"]],
            rooms=[Room(**r) for r in data["rooms"]],
            curriculum=[CurriculumEntry(**e) for e in data["curriculum"]],
            constraints=[Constraint(**c) for c in data["constraints"]],
        )
