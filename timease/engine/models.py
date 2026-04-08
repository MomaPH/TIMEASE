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
# Manual Assignment Validator
# ---------------------------------------------------------------------------

@dataclass
class ManualAssignmentValidator:
    @classmethod
    def validate(cls, school: SchoolData) -> None:
        """Phase 2: Validate manual assignments meet hard constraints"""
        if not school.teacher_assignments:
            raise ValueError("Les affectations des enseignants doivent être fournies manuellement")

        # Check H2: One teacher per (class, subject)
        class_subject_teachers = defaultdict(set)
        for assignment in school.teacher_assignments:
            key = (assignment.school_class, assignment.subject)
            class_subject_teachers[key].add(assignment.teacher)

        for key, teachers in class_subject_teachers.items():
            if len(teachers) > 1:
                raise ValueError(f"Plusieurs enseignants affectés à {key[0]} - {key[1]}: {', '.join(teachers)}")

        # Check H10: Teacher qualifications
        teacher_map = {t.name: t for t in school.teachers}
        for assignment in school.teacher_assignments:
            teacher = teacher_map.get(assignment.teacher)
            if not teacher:
                raise ValueError(f"Enseignant introuvable: {assignment.teacher}")
            if assignment.subject not in teacher.subjects:
                raise ValueError(f"{teacher.name} n'est pas qualifié pour enseigner {assignment.subject}")

# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

MAX_FILE_SIZE_MB: int = 10
MAX_SOLVE_TIMEOUT_SECONDS: int = 300
_VALID_BASE_UNITS: frozenset[int] = frozenset({15, 30, 60})
_MAX_CLASSES: int = 200
_MAX_TEACHERS: int = 200
_MAX_ROOMS: int = 100


def _time_to_min(t: str) -> int:
    """Convert 'HH:MM' to minutes since midnight."""
    h, m = t.split(":")
    return int(h) * 60 + int(m)


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
class BreakConfig:
    """A blocked interval inside a day where no teaching occurs."""
    name: str                # e.g. "Récréation", "Déjeuner"
    start_time: str          # "HH:MM"
    end_time: str            # "HH:MM"


@dataclass
class SessionConfig:
    """A contiguous teaching block within a day."""
    name: str                # e.g. "Matin", "Après-midi"
    start_time: str          # "HH:MM"
    end_time: str            # "HH:MM"


@dataclass
class DayConfig:
    """One working day's schedule."""
    name: str                # e.g. "lundi"
    sessions: list[SessionConfig]
    breaks: list[BreakConfig] = field(default_factory=list)


@dataclass
class TimeslotConfig:
    """
    Overall schedule structure: per-day schedules with sessions and breaks.
    Each day can have different sessions/breaks (e.g., Wednesday half-day).
    """
    days: list[DayConfig]
    base_unit_minutes: int = 30

    def get_all_slots(self) -> list[tuple[str, str, str]]:
        """
        Return every base-unit slot across all active days and sessions.

        Each element is a (day, start_time, end_time) tuple where times are
        "HH:MM" strings. Slots overlapping any break on that day are skipped.
        """
        slots: list[tuple[str, str, str]] = []
        delta = timedelta(minutes=self.base_unit_minutes)

        for day_config in self.days:
            # Build list of break intervals for this day
            break_intervals: list[tuple[int, int]] = []
            for brk in day_config.breaks:
                break_intervals.append((_time_to_min(brk.start_time), _time_to_min(brk.end_time)))

            for session in day_config.sessions:
                current = datetime.strptime(session.start_time, "%H:%M")
                end = datetime.strptime(session.end_time, "%H:%M")
                while current + delta <= end:
                    slot_end = current + delta
                    slot_start_min = current.hour * 60 + current.minute
                    slot_end_min = slot_end.hour * 60 + slot_end.minute

                    # Skip if slot overlaps any break
                    overlaps_break = False
                    for brk_start, brk_end in break_intervals:
                        if slot_start_min < brk_end and slot_end_min > brk_start:
                            overlaps_break = True
                            break

                    if not overlaps_break:
                        slots.append((
                            day_config.name,
                            current.strftime("%H:%M"),
                            slot_end.strftime("%H:%M"),
                        ))

                    current = slot_end

        return slots

    def validate(self) -> None:
        """Raise ValueError if the timeslot configuration is invalid."""
        if self.base_unit_minutes not in _VALID_BASE_UNITS:
            raise ValueError(
                f"L'unité de base {self.base_unit_minutes} min n'est pas valide. "
                f"Valeurs acceptées : {sorted(_VALID_BASE_UNITS)}."
            )

        if not self.days:
            raise ValueError("Au moins un jour doit être défini.")

        for day_config in self.days:
            if not day_config.sessions:
                raise ValueError(f"Le jour '{day_config.name}' doit avoir au moins une session.")

            # Validate sessions
            for sess in day_config.sessions:
                start_min = _time_to_min(sess.start_time)
                end_min = _time_to_min(sess.end_time)
                if end_min <= start_min:
                    raise ValueError(
                        f"Jour '{day_config.name}', session '{sess.name}' : "
                        f"l'heure de fin ({sess.end_time}) doit être après "
                        f"l'heure de début ({sess.start_time})."
                    )

            # Validate breaks
            for brk in day_config.breaks:
                brk_start = _time_to_min(brk.start_time)
                brk_end = _time_to_min(brk.end_time)

                if brk_end <= brk_start:
                    raise ValueError(
                        f"Jour '{day_config.name}', pause '{brk.name}' : "
                        f"l'heure de fin ({brk.end_time}) doit être après "
                        f"l'heure de début ({brk.start_time})."
                    )

                # Check break lies within some session
                in_session = False
                for sess in day_config.sessions:
                    sess_start = _time_to_min(sess.start_time)
                    sess_end = _time_to_min(sess.end_time)
                    if brk_start >= sess_start and brk_end <= sess_end:
                        in_session = True
                        break
                if not in_session:
                    raise ValueError(
                        f"Jour '{day_config.name}', pause '{brk.name}' ({brk.start_time}-{brk.end_time}) : "
                        f"la pause doit être entièrement contenue dans une session."
                    )

            # Check no overlapping breaks on same day
            for i, brk1 in enumerate(day_config.breaks):
                for brk2 in day_config.breaks[i+1:]:
                    b1_start, b1_end = _time_to_min(brk1.start_time), _time_to_min(brk1.end_time)
                    b2_start, b2_end = _time_to_min(brk2.start_time), _time_to_min(brk2.end_time)
                    if b1_start < b2_end and b2_start < b1_end:
                        raise ValueError(
                            f"Jour '{day_config.name}' : les pauses '{brk1.name}' et '{brk2.name}' "
                            f"se chevauchent."
                        )

    @classmethod
    def from_simple(
        cls,
        day_names: list[str],
        sessions: list[SessionConfig],
        base_unit_minutes: int = 30,
    ) -> "TimeslotConfig":
        """
        Factory method for backward compatibility and simpler test construction.

        Creates a TimeslotConfig where all days share the same sessions and have no breaks.
        """
        days = [
            DayConfig(name=day, sessions=sessions, breaks=[])
            for day in day_names
        ]
        return cls(days=days, base_unit_minutes=base_unit_minutes)


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
    max_hours_per_week: int | None = None  # None = unlimited
    unavailable_slots: list[dict] = field(default_factory=list)
    # Each dict: {day: str, start: str|None, end: str|None, session: str|None}
    # session defaults to "all" when omitted
    def validate(self) -> None:
        """Raise ValueError if the teacher data is internally inconsistent."""
        if not self.subjects:
            raise ValueError(
                f"L'enseignant '{self.name}' doit enseigner au moins une matière."
            )
        if self.max_hours_per_week is not None and self.max_hours_per_week <= 0:
            raise ValueError(
                f"L'enseignant '{self.name}' doit avoir un volume horaire hebdomadaire positif ou non défini."
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
    Weekly teaching load for a subject for a specific class.

    In Phase 2, this strictly requires exact manual specification of
    how many sessions per week and their duration per CLASS (not level).
    """

    school_class: str                   # e.g. "6ème A", "5ème B" - must match SchoolClass.name
    subject: str                        # must match Subject.name
    total_minutes_per_week: int
    sessions_per_week: int
    minutes_per_session: int

    def validate(self) -> None:
        """Raise ValueError if the entry is internally inconsistent."""
        if self.total_minutes_per_week <= 0:
            raise ValueError(
                f"Le volume horaire de '{self.subject}' (classe {self.school_class}) "
                "doit être positif."
            )
        if self.sessions_per_week <= 0 or self.minutes_per_session <= 0:
            raise ValueError(
                f"Le curriculum '{self.subject}' (classe {self.school_class}) "
                "doit définir sessions_per_week et minutes_per_session avec des valeurs positives."
            )

@dataclass
class TeacherAssignment:
    """Explicit binding: this teacher teaches this subject to this class."""

    teacher: str        # must match Teacher.name
    subject: str        # must match Subject.name
    school_class: str   # must match SchoolClass.name

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
# School Data Container
# ---------------------------------------------------------------------------

@dataclass
class SchoolData:
    """Conteneur principal pour toutes les données de l'école."""

    school: School
    timeslot_config: TimeslotConfig
    subjects: list[Subject]
    teachers: list[Teacher]
    classes: list[SchoolClass]
    rooms: list[Room]
    curriculum: list[CurriculumEntry]
    constraints: list[Constraint]
    teacher_assignments: list[TeacherAssignment] = field(default_factory=list)

    def validate_all(self) -> None:
        """Valide l'intégrité de toutes les données de l'école."""
        for teacher in self.teachers:
            teacher.validate()
        for cls in self.classes:
            cls.validate()
        for room in self.rooms:
            room.validate()
        for entry in self.curriculum:
            entry.validate()

    def validate(self) -> list[str]:
        """
        Comprehensive validation of school data.

        Returns an empty list if all validations pass.
        Checks:
        - Entity validation (teachers, classes, rooms, curriculum entries)
        - Infrastructure safety (base unit, session times)
        - Ceiling limits
        - Duplicate names
        - Constraint validation
        - Teacher assignment validation
        """
        errors: list[str] = []

        # --- Entity validation ---
        for teacher in self.teachers:
            try:
                teacher.validate()
            except ValueError as e:
                errors.append(str(e))

        for cls in self.classes:
            try:
                cls.validate()
            except ValueError as e:
                errors.append(str(e))

        for room in self.rooms:
            try:
                room.validate()
            except ValueError as e:
                errors.append(str(e))

        for entry in self.curriculum:
            try:
                entry.validate()
            except ValueError as e:
                errors.append(str(e))

        # --- Timeslot validation (delegates to TimeslotConfig.validate()) ---
        try:
            self.timeslot_config.validate()
        except ValueError as e:
            errors.append(str(e))

        # --- Ceiling limits ---
        if len(self.classes) > _MAX_CLASSES:
            errors.append(
                f"Trop de classes : {len(self.classes)} (max : {_MAX_CLASSES})."
            )
        if len(self.teachers) > _MAX_TEACHERS:
            errors.append(
                f"Trop d'enseignants : {len(self.teachers)} (max : {_MAX_TEACHERS})."
            )
        if len(self.rooms) > _MAX_ROOMS:
            errors.append(
                f"Trop de salles : {len(self.rooms)} (max : {_MAX_ROOMS})."
            )

        # --- Duplicate names ---
        teacher_names = [t.name for t in self.teachers]
        if len(teacher_names) != len(set(teacher_names)):
            errors.append("Nom d'enseignant en double détecté.")

        class_names = [c.name for c in self.classes]
        if len(class_names) != len(set(class_names)):
            errors.append("Nom de classe en double détecté.")

        room_names = [r.name for r in self.rooms]
        if len(room_names) != len(set(room_names)):
            errors.append("Nom de salle en double détecté.")

        # --- Constraint validation ---
        for c in self.constraints:
            if c.type not in ("hard", "soft"):
                errors.append(
                    f"Contrainte '{c.id}' : type '{c.type}' invalide "
                    f"(doit être 'hard' ou 'soft')."
                )
            if c.priority < 1 or c.priority > 10:
                errors.append(
                    f"Contrainte '{c.id}' : priorité {c.priority} invalide "
                    f"(doit être entre 1 et 10)."
                )

        # --- Teacher assignment validation ---
        teacher_map = {t.name: t for t in self.teachers}

        # Build curriculum requirements: which (class, subject) pairs need teachers
        # Now curriculum is class-based, so directly use school_class
        required_pairs: set[tuple[str, str]] = set()
        for entry in self.curriculum:
            required_pairs.add((entry.school_class, entry.subject))

        assigned_pairs: dict[tuple[str, str], list[str]] = defaultdict(list)

        for ta in self.teacher_assignments:
            key = (ta.school_class, ta.subject)
            assigned_pairs[key].append(ta.teacher)

            # Check unknown teacher
            if ta.teacher not in teacher_map:
                errors.append(
                    f"Enseignant inconnu : '{ta.teacher}' "
                    f"(affectation {ta.school_class} / {ta.subject})."
                )
                continue

            # Check teacher qualification
            teacher = teacher_map[ta.teacher]
            if ta.subject not in teacher.subjects:
                errors.append(
                    f"L'enseignant '{ta.teacher}' n'est pas qualifié pour "
                    f"enseigner '{ta.subject}' ({ta.school_class})."
                )

        # Check for duplicates
        for (cls_name, subj), teachers in assigned_pairs.items():
            if len(teachers) > 1:
                errors.append(
                    f"Double affectation pour {cls_name} / {subj} : "
                    f"{', '.join(teachers)}."
                )

        # Check for missing assignments
        for cls_name, subj in required_pairs:
            if (cls_name, subj) not in assigned_pairs:
                errors.append(
                    f"Affectation manquante : aucun enseignant pour "
                    f"{cls_name} / {subj}."
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

        # Legacy migration for Phase 2: Convert any "auto" mode curriculums to "manual"
        # Also migrate level -> school_class for class-based curriculum
        curriculum = []
        base_unit = data["timeslot_config"]["base_unit_minutes"]
        for e in data["curriculum"]:
            e.pop("mode", None)
            min_s = e.pop("min_session_minutes", None)
            max_s = e.pop("max_session_minutes", None)

            # Migration: level -> school_class (class-based curriculum)
            if "level" in e and "school_class" not in e:
                e["school_class"] = e.pop("level")

            if e.get("sessions_per_week") is None or e.get("minutes_per_session") is None:
                total = e["total_minutes_per_week"]
                min_s = min_s or min(60, total)
                min_s = max(base_unit, (min_s // base_unit) * base_unit) or base_unit
                # fallback
                sessions, minutes = 1, total
                for d in range(min_s, (max_s or total) + 1, base_unit):
                    if total % d == 0:
                        sessions = max(1, total // d)
                        minutes = max(1, d)
                        break
                e["sessions_per_week"] = sessions
                e["minutes_per_session"] = minutes

            curriculum.append(CurriculumEntry(**e))

        # Parse timeslot_config: support both legacy (flat days list) and new (per-day) format
        tc_data = data["timeslot_config"]
        if tc_data.get("days") and isinstance(tc_data["days"][0], str):
            # Legacy format: days is list[str], sessions is flat list
            # Convert to new per-day format
            legacy_sessions = [
                SessionConfig(**s) for s in tc_data.get("sessions", [])
            ]
            days = [
                DayConfig(name=day_name, sessions=legacy_sessions, breaks=[])
                for day_name in tc_data["days"]
            ]
        else:
            # New format: days is list[DayConfig]
            days = []
            for d in tc_data["days"]:
                sessions = [SessionConfig(**s) for s in d.get("sessions", [])]
                breaks = [BreakConfig(**b) for b in d.get("breaks", [])]
                days.append(DayConfig(name=d["name"], sessions=sessions, breaks=breaks))

        timeslot_config = TimeslotConfig(
            days=days,
            base_unit_minutes=tc_data.get("base_unit_minutes", 30),
        )

        return cls(
            school=School(**data["school"]),
            timeslot_config=timeslot_config,
            subjects=[Subject(**s) for s in data["subjects"]],
            teachers=[
                Teacher(**{k: v for k, v in t.items() if k != "preference_weight"})
                for t in data["teachers"]
            ],
            classes=[SchoolClass(**c) for c in data["classes"]],
            rooms=[Room(**r) for r in data["rooms"]],
            curriculum=curriculum,
            constraints=[Constraint(**c) for c in data["constraints"]],
            teacher_assignments=[
                TeacherAssignment(**ta)
                for ta in data.get("teacher_assignments", [])
            ],
        )

    def validate_warnings(self) -> list[str]:
        """
        Non-blocking checks: returns informational warnings without preventing
        timetable generation. Returns a list of warning messages in French.
        """
        warnings: list[str] = []

        subject_map = {s.name: s for s in self.subjects}
        class_map = {c.name: c for c in self.classes}

        # --- Room capacity vs class size ---
        for entry in self.curriculum:
            subj = subject_map.get(entry.subject)
            if subj is None or not subj.needs_room:
                continue
            room_type = subj.required_room_type or "Salle standard"
            compatible = [r for r in self.rooms if room_type in r.types]
            if not compatible:
                continue  # error already reported in validate()
            max_cap = max(r.capacity for r in compatible)
            # Now curriculum is class-based, get the class directly
            cls = class_map.get(entry.school_class)
            if cls and cls.student_count > max_cap:
                warnings.append(
                    f"La classe '{cls.name}' ({cls.student_count} élèves) "
                    f"dépasse la capacité maximale des salles de type "
                    f"'{room_type}' ({max_cap} places) "
                    f"pour la matière '{entry.subject}'."
                )

        # --- Teacher with zero assignments ---
        assigned_teachers = {ta.teacher for ta in self.teacher_assignments}
        for teacher in self.teachers:
            if teacher.name not in assigned_teachers:
                warnings.append(
                    f"L'enseignant '{teacher.name}' est enregistré mais n'a aucun cours "
                    f"assigné. Est-ce intentionnel ?"
                )

        # --- Conflicting soft constraints: afternoon preference vs morning subjects ---
        # Detect teacher with teacher_time_preference=Après-midi who also teaches
        # subjects listed in heavy_subjects_morning.  These constraints compete
        # directly and one will always be sacrificed.
        morning_subjects: set[str] = set()
        afternoon_pref_teachers: set[str] = set()
        for c in self.constraints:
            if c.type != "soft":
                continue
            if c.category == "heavy_subjects_morning":
                morning_subjects.update(c.parameters.get("subjects", []))
            elif c.category == "teacher_time_preference":
                pref = c.parameters.get("preferred_session", "")
                if "après" in pref.lower() or "apres" in pref.lower():
                    t_name = c.parameters.get("teacher", "")
                    if t_name:
                        afternoon_pref_teachers.add(t_name)

        for t_name in afternoon_pref_teachers:
            teacher = next((t for t in self.teachers if t.name == t_name), None)
            if teacher is None:
                continue
            conflicts_with_morning = [s for s in teacher.subjects if s in morning_subjects]
            if conflicts_with_morning:
                warnings.append(
                    f"L'enseignant '{t_name}' préfère l'après-midi (teacher_time_preference) "
                    f"mais enseigne des matières prioritairement le matin "
                    f"(heavy_subjects_morning) : {conflicts_with_morning}. "
                    f"Ces contraintes sont incompatibles — l'une sera sacrifiée."
                )

        return warnings


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
    # partial=True when some — but not all — curriculum sessions were placed.
    # unscheduled_sessions lists the sessions the solver had to skip (e.g. no
    # valid time slot after domain filtering).  See solver.py for details.
    partial: bool = False
    unscheduled_sessions: list[dict] = field(default_factory=list)
    soft_constraints_satisfied: list[str] = field(default_factory=list)
    soft_constraints_violated: list[str] = field(default_factory=list)
    soft_constraint_details: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def verify(self, school_data: "SchoolData") -> list[str]:
        """
        Post-solve safety net: verifies the solver output against school_data.

        Returns a list of violation messages in French.
        An empty list means all checks passed.
        """
        violations: list[str] = []

        def to_min(t: str) -> int:
            h, m = t.split(":")
            return int(h) * 60 + int(m)

        def overlaps(s1: str, e1: str, s2: str, e2: str) -> bool:
            return to_min(s1) < to_min(e2) and to_min(s2) < to_min(e1)

        # Lookups
        class_level = {c.name: c.level for c in school_data.classes}
        class_students = {c.name: c.student_count for c in school_data.classes}
        room_capacity = {r.name: r.capacity for r in school_data.rooms}
        teacher_max_min = {
            t.name: t.max_hours_per_week * 60 if t.max_hours_per_week is not None else None
            for t in school_data.teachers
        }
        # Class-based curriculum: map (class, subject) -> minutes
        curriculum_target: dict[tuple[str, str], int] = {
            (e.school_class, e.subject): e.total_minutes_per_week
            for e in school_data.curriculum
        }

        # --- No double-booking ---
        def check_no_overlap(groups: dict) -> None:
            for key, grp in groups.items():
                for i, a1 in enumerate(grp):
                    for a2 in grp[i + 1:]:
                        if overlaps(a1.start_time, a1.end_time,
                                    a2.start_time, a2.end_time):
                            violations.append(
                                f"Double réservation de '{key[0]}' "
                                f"le {a1.day} : "
                                f"{a1.start_time}–{a1.end_time} "
                                f"et {a2.start_time}–{a2.end_time}."
                            )

        teacher_day: dict[tuple[str, str], list] = {}
        room_day: dict[tuple[str, str], list] = {}
        class_day: dict[tuple[str, str], list] = {}

        for a in self.assignments:
            teacher_day.setdefault((a.teacher, a.day), []).append(a)
            class_day.setdefault((a.school_class, a.day), []).append(a)
            if a.room:
                room_day.setdefault((a.room, a.day), []).append(a)

        check_no_overlap(teacher_day)
        check_no_overlap(room_day)
        check_no_overlap(class_day)

        # --- Curriculum hours exactly matched ---
        actual_min: dict[tuple[str, str], int] = defaultdict(int)
        for a in self.assignments:
            actual_min[(a.school_class, a.subject)] += (
                to_min(a.end_time) - to_min(a.start_time)
            )

        # Class-based curriculum: directly check each entry
        for entry in school_data.curriculum:
            expected = entry.total_minutes_per_week
            actual = actual_min.get((entry.school_class, entry.subject), 0)
            if actual != expected:
                violations.append(
                    f"Curriculum non respecté pour '{entry.school_class}' / "
                    f"'{entry.subject}' : {actual} min planifiées, "
                    f"{expected} min attendues."
                )

        # --- Teacher max hours respected ---
        teacher_actual: dict[str, int] = defaultdict(int)
        for a in self.assignments:
            teacher_actual[a.teacher] += to_min(a.end_time) - to_min(a.start_time)

        for name, actual in teacher_actual.items():
            max_min = teacher_max_min.get(name)
            if max_min is not None and actual > max_min:
                violations.append(
                    f"L'enseignant '{name}' dépasse son maximum hebdomadaire : "
                    f"{actual // 60}h{actual % 60:02d} planifiées, "
                    f"{max_min // 60}h maximum."
                )

        # --- Room capacity respected ---
        for a in self.assignments:
            if a.room is None:
                continue
            cap = room_capacity.get(a.room)
            n_students = class_students.get(a.school_class)
            if cap is not None and n_students is not None and n_students > cap:
                violations.append(
                    f"La salle '{a.room}' (capacité {cap}) est trop petite pour "
                    f"la classe '{a.school_class}' ({n_students} élèves) "
                    f"le {a.day} à {a.start_time}."
                )

        return violations
