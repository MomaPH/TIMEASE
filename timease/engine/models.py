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
# Infrastructure safety constants — enforced regardless of subscription plan
# ---------------------------------------------------------------------------

MAX_FILE_SIZE_MB: int = 10
MAX_SOLVE_TIMEOUT_SECONDS: int = 300
_VALID_BASE_UNITS: frozenset[int] = frozenset({15, 30, 60})
_MAX_CLASSES: int = 200
_MAX_TEACHERS: int = 200
_MAX_ROOMS: int = 100


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
            t.name: t.max_hours_per_week * 60 for t in school_data.teachers
        }
        curriculum_target: dict[tuple[str, str], int] = {
            (e.level, e.subject): e.total_minutes_per_week
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

        for cls in school_data.classes:
            level = class_level.get(cls.name)
            if level is None:
                continue
            for entry in school_data.curriculum:
                if entry.level != level:
                    continue
                expected = curriculum_target.get((level, entry.subject), 0)
                actual = actual_min.get((cls.name, entry.subject), 0)
                if actual != expected:
                    violations.append(
                        f"Curriculum non respecté pour '{cls.name}' / "
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
    teacher_assignments: list[TeacherAssignment] = field(default_factory=list)

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

        # --- Individual entity validation ---
        for teacher in self.teachers:
            try:
                teacher.validate()
            except ValueError as exc:
                errors.append(str(exc))

        for cls in self.classes:
            try:
                cls.validate()
            except ValueError as exc:
                errors.append(str(exc))

        for room in self.rooms:
            try:
                room.validate()
            except ValueError as exc:
                errors.append(str(exc))

        for entry in self.curriculum:
            try:
                entry.validate()
            except ValueError as exc:
                errors.append(str(exc))

        # --- Infrastructure safety ---
        if self.timeslot_config.base_unit_minutes not in _VALID_BASE_UNITS:
            errors.append(
                f"L'unité de base doit être 15, 30 ou 60 minutes "
                f"(valeur reçue : {self.timeslot_config.base_unit_minutes})."
            )

        for session in self.timeslot_config.sessions:
            try:
                start_dt = datetime.strptime(session.start_time, "%H:%M")
                end_dt = datetime.strptime(session.end_time, "%H:%M")
                if end_dt <= start_dt:
                    errors.append(
                        f"La session '{session.name}' a une heure de fin "
                        f"({session.end_time}) inférieure ou égale à l'heure de début "
                        f"({session.start_time})."
                    )
            except ValueError:
                errors.append(
                    f"La session '{session.name}' contient une heure invalide "
                    f"(format attendu : HH:MM)."
                )

        if len(self.classes) > _MAX_CLASSES:
            errors.append(
                f"Le nombre de classes ({len(self.classes)}) dépasse le maximum "
                f"autorisé ({_MAX_CLASSES})."
            )
        if len(self.teachers) > _MAX_TEACHERS:
            errors.append(
                f"Le nombre d'enseignants ({len(self.teachers)}) dépasse le maximum "
                f"autorisé ({_MAX_TEACHERS})."
            )
        if len(self.rooms) > _MAX_ROOMS:
            errors.append(
                f"Le nombre de salles ({len(self.rooms)}) dépasse le maximum "
                f"autorisé ({_MAX_ROOMS})."
            )

        # --- Data integrity: duplicate names ---
        seen: set[str] = set()
        for teacher in self.teachers:
            if teacher.name in seen:
                errors.append(f"Nom d'enseignant en double : '{teacher.name}'.")
            seen.add(teacher.name)

        seen = set()
        for cls in self.classes:
            if cls.name in seen:
                errors.append(f"Nom de classe en double : '{cls.name}'.")
            seen.add(cls.name)

        seen = set()
        for room in self.rooms:
            if room.name in seen:
                errors.append(f"Nom de salle en double : '{room.name}'.")
            seen.add(room.name)

        # --- Data integrity: constraints ---
        for constraint in self.constraints:
            if constraint.type not in ("hard", "soft"):
                errors.append(
                    f"La contrainte '{constraint.id}' a un type invalide "
                    f"'{constraint.type}' (valeurs acceptées : 'hard', 'soft')."
                )
            if constraint.type == "soft" and not (1 <= constraint.priority <= 10):
                errors.append(
                    f"La contrainte '{constraint.id}' a une priorité invalide "
                    f"({constraint.priority}) — doit être comprise entre 1 et 10."
                )

        # --- Data integrity: curriculum mode consistency ---
        for entry in self.curriculum:
            if entry.mode == "auto":
                min_s = entry.min_session_minutes
                max_s = entry.max_session_minutes
                if min_s is not None and max_s is not None and min_s > max_s:
                    errors.append(
                        f"Le curriculum '{entry.subject}' (niveau {entry.level}) "
                        f"en mode auto a min_session_minutes ({min_s}) > "
                        f"max_session_minutes ({max_s})."
                    )
            elif entry.mode == "manual":
                spw = entry.sessions_per_week
                mps = entry.minutes_per_session
                if spw is not None and mps is not None:
                    if spw * mps != entry.total_minutes_per_week:
                        errors.append(
                            f"Le curriculum '{entry.subject}' (niveau {entry.level}) "
                            f"est incohérent : {spw} × {mps} min = {spw * mps} min "
                            f"≠ total_minutes_per_week ({entry.total_minutes_per_week} min)."
                        )

        # --- Cross-entity validation ---
        subject_map = {s.name: s for s in self.subjects}
        subject_names = set(subject_map)

        for entry in self.curriculum:
            if entry.subject not in subject_names:
                errors.append(
                    f"La matière '{entry.subject}' (niveau {entry.level}) "
                    "est absente de la liste des matières."
                )

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

        # --- TeacherAssignment validation ---
        teacher_names = {t.name for t in self.teachers}
        class_names   = {c.name for c in self.classes}
        subject_names_set = {s.name for s in self.subjects}
        teacher_map_val = {t.name: t for t in self.teachers}

        # Check for unknown references in TeacherAssignment
        seen_assignments: set[tuple[str, str]] = set()
        for ta in self.teacher_assignments:
            if ta.teacher not in teacher_names:
                errors.append(
                    f"TeacherAssignment: l'enseignant '{ta.teacher}' est inconnu."
                )
            if ta.subject not in subject_names_set:
                errors.append(
                    f"TeacherAssignment: la matière '{ta.subject}' est inconnue."
                )
            if ta.school_class not in class_names:
                errors.append(
                    f"TeacherAssignment: la classe '{ta.school_class}' est inconnue."
                )
            # Check qualification
            t = teacher_map_val.get(ta.teacher)
            if t is not None and ta.subject in subject_names_set:
                if ta.subject not in t.subjects:
                    errors.append(
                        f"TeacherAssignment: l'enseignant '{ta.teacher}' n'est pas "
                        f"qualifié pour '{ta.subject}'."
                    )
            # Duplicate check
            key = (ta.school_class, ta.subject)
            if key in seen_assignments:
                errors.append(
                    f"TeacherAssignment en double pour la classe '{ta.school_class}' "
                    f"et la matière '{ta.subject}'."
                )
            seen_assignments.add(key)

        # Check that every (class, subject) pair has an assignment
        class_level_map = {c.name: c.level for c in self.classes}
        curriculum_by_level: dict[str, list] = defaultdict(list)
        for entry in self.curriculum:
            curriculum_by_level[entry.level].append(entry)

        for cls in self.classes:
            level_entries = curriculum_by_level.get(cls.level, [])
            for entry in level_entries:
                if entry.subject not in subject_names_set:
                    continue  # already reported above
                if (cls.name, entry.subject) not in seen_assignments:
                    errors.append(
                        f"Aucune TeacherAssignment pour la classe '{cls.name}' "
                        f"et la matière '{entry.subject}'."
                    )

        # Check teacher capacity
        curriculum_minutes_map: dict[tuple[str, str], int] = {
            (e.level, e.subject): e.total_minutes_per_week
            for e in self.curriculum
        }
        teacher_assigned_minutes: dict[str, int] = defaultdict(int)
        for ta in self.teacher_assignments:
            level = class_level_map.get(ta.school_class)
            if level is None:
                continue
            minutes = curriculum_minutes_map.get((level, ta.subject), 0)
            teacher_assigned_minutes[ta.teacher] += minutes

        for teacher in self.teachers:
            assigned = teacher_assigned_minutes.get(teacher.name, 0)
            max_min = teacher.max_hours_per_week * 60
            if assigned > max_min:
                errors.append(
                    f"L'enseignant '{teacher.name}' a {assigned} min assignées "
                    f"({assigned // 60}h{assigned % 60:02d}) mais son maximum est "
                    f"{teacher.max_hours_per_week}h/semaine."
                )

        return errors

    def validate_warnings(self) -> list[str]:
        """
        Non-blocking checks: returns informational warnings without preventing
        timetable generation. Returns a list of warning messages in French.
        """
        warnings: list[str] = []

        subject_map = {s.name: s for s in self.subjects}
        class_by_level: dict[str, list[SchoolClass]] = {}
        for cls in self.classes:
            class_by_level.setdefault(cls.level, []).append(cls)

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
            for cls in class_by_level.get(entry.level, []):
                if cls.student_count > max_cap:
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
            teacher_assignments=[
                TeacherAssignment(**ta)
                for ta in data.get("teacher_assignments", [])
            ],
        )
