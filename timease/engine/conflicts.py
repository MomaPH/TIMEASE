"""
Infeasibility analysis for TIMEASE.

ConflictAnalyzer diagnoses why a timetable is INFEASIBLE and produces
concrete French fix suggestions.  Call it after TimetableSolver returns
``solved=False``.

Three-step strategy
-------------------
1. Quick checks  — mathematical impossibilities caught before running the solver
   (missing teacher, missing room type, teacher overload, schedule overflow).
2. Constraint relaxation — remove each hard user-constraint one at a time and
   re-solve with a short timeout.  If feasible without constraint C → C is a
   culprit.
3. Fix suggestions — each detected conflict gets ranked ``FixOption`` objects
   that the UI can apply automatically.

Usage::

    analyzer = ConflictAnalyzer(school_data)
    reports  = analyzer.analyze()
    for r in reports:
        print(r.description_fr)
        for opt in r.fix_options:
            print(" →", opt.fix_fr)
"""

from __future__ import annotations

import dataclasses
import logging
from collections import defaultdict
from dataclasses import dataclass, field

from timease.engine.models import Constraint, SchoolData

logger = logging.getLogger(__name__)

# Timeout (seconds) for each relaxation re-solve.
RELAXATION_TIMEOUT_SECONDS: int = 5


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FixOption:
    """One possible remedy for a conflict, ranked by ease of implementation."""

    fix_fr: str
    """Human-readable fix description (French)."""

    fix_action: dict
    """Structured action the UI can apply automatically."""

    impact_fr: str
    """What changes if this fix is applied (French)."""

    ease: int = 2
    """Ease rank: 1 = easy (tweak a number), 2 = medium, 3 = hard (hire/build)."""


@dataclass
class ConflictReport:
    """One detected infeasibility cause with ranked remedies."""

    description_fr: str
    """Human-readable description of the conflict (French)."""

    source: str
    """How it was found: ``"quick_check"`` or ``"relaxation"``."""

    fix_options: list[FixOption] = field(default_factory=list)
    """Fix options, sorted by ease (easiest first)."""

    severity: str = "error"
    """Severity level: ``"error"`` (blocks scheduling) or ``"warning"`` (degraded quality)."""


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class ConflictAnalyzer:
    """
    Diagnoses infeasibility and generates French fix suggestions.

    Parameters
    ----------
    school_data : SchoolData
        The input that produced an infeasible solver result.
    """

    def __init__(self, school_data: SchoolData) -> None:
        self._sd = school_data
        self._tc = school_data.timeslot_config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self) -> list[ConflictReport]:
        """
        Run all analysis steps and return conflict reports.

        Step 1 (quick checks) always runs.  If it finds conflicts, step 2
        is skipped (structural issues must be fixed first).  Reports are
        sorted: quick-check reports first, then relaxation reports.
        """
        reports: list[ConflictReport] = self._quick_checks()

        if reports:
            logger.info(
                "ConflictAnalyzer: %d quick-check conflict(s) found — "
                "skipping relaxation step.",
                len(reports),
            )
            return _sort_by_ease(reports)

        reports = self._relaxation_check()
        logger.info(
            "ConflictAnalyzer: %d relaxation conflict(s) found.", len(reports)
        )
        return _sort_by_ease(reports)

    # ------------------------------------------------------------------
    # Step 1 — Quick mathematical checks
    # ------------------------------------------------------------------

    def _quick_checks(self) -> list[ConflictReport]:
        reports: list[ConflictReport] = []
        reports += self._check_no_teacher_for_subject()
        reports += self._check_room_type_missing()
        reports += self._check_teacher_sole_overload()
        reports += self._check_class_hours_exceed_schedule()
        reports += self._check_room_capacity_for_assignments()
        return reports

    def _check_no_teacher_for_subject(self) -> list[ConflictReport]:
        """Every curriculum subject must have at least one qualified teacher."""
        reported: set[str] = set()
        reports: list[ConflictReport] = []

        for entry in self._sd.curriculum:
            if entry.subject in reported:
                continue
            qualified = [t for t in self._sd.teachers if entry.subject in t.subjects]
            if not qualified:
                reported.add(entry.subject)
                reports.append(ConflictReport(
                    description_fr=(
                        f"Aucun enseignant qualifié pour '{entry.subject}'. "
                        f"Toutes les sessions de cette matière sont impossibles."
                    ),
                    source="quick_check",
                    fix_options=[
                        FixOption(
                            fix_fr=(
                                f"Recruter un enseignant capable d'enseigner "
                                f"'{entry.subject}'."
                            ),
                            fix_action={
                                "action": "add_teacher",
                                "subject": entry.subject,
                            },
                            impact_fr=(
                                "Permet au solveur de planifier toutes les sessions "
                                f"de '{entry.subject}'."
                            ),
                            ease=3,
                        )
                    ],
                ))
        return reports

    def _check_room_type_missing(self) -> list[ConflictReport]:
        """Every required room type must exist in the rooms list."""
        subj_room_type = {
            s.name: s.required_room_type
            for s in self._sd.subjects
            if s.required_room_type
        }
        available_types = {rtype for r in self._sd.rooms for rtype in r.types}

        needed: dict[str, list[str]] = defaultdict(list)  # rtype → subject names
        for entry in self._sd.curriculum:
            rt = subj_room_type.get(entry.subject)
            if rt and rt not in available_types:
                if entry.subject not in needed[rt]:
                    needed[rt].append(entry.subject)

        reports: list[ConflictReport] = []
        for rtype, subjects in needed.items():
            subj_str = ", ".join(subjects)
            reports.append(ConflictReport(
                description_fr=(
                    f"Aucune salle de type '{rtype}' n'existe "
                    f"(nécessaire pour : {subj_str})."
                ),
                source="quick_check",
                fix_options=[
                    FixOption(
                        fix_fr=f"Ajouter au moins 1 salle de type '{rtype}'.",
                        fix_action={
                            "action": "add_room",
                            "type": rtype,
                            "capacity": 30,
                        },
                        impact_fr=f"Débloque les sessions de {subj_str}.",
                        ease=3,
                    )
                ],
            ))
        return reports

    def _check_room_capacity_for_assignments(self) -> list[ConflictReport]:
        """
        For each TeacherAssignment where the subject requires a specific room type,
        verify that at least one room of that type has capacity >= class student_count.
        Reports a warning (not a hard error) when all specialized rooms are too small —
        the solver will be unable to place those sessions in the required room type.
        """
        subject_map = {s.name: s for s in self._sd.subjects}
        class_map = {c.name: c for c in self._sd.classes}

        rooms_by_type: dict[str, list] = defaultdict(list)
        for room in self._sd.rooms:
            for rtype in room.types:
                rooms_by_type[rtype].append(room)

        reports: list[ConflictReport] = []
        seen: set[tuple[str, str]] = set()  # (school_class, subject) pairs already reported

        for ta in self._sd.teacher_assignments:
            key = (ta.school_class, ta.subject)
            if key in seen:
                continue

            subj = subject_map.get(ta.subject)
            if subj is None or not subj.required_room_type:
                continue

            cls = class_map.get(ta.school_class)
            if cls is None:
                continue

            room_type = subj.required_room_type
            rooms_of_type = rooms_by_type.get(room_type, [])
            if not rooms_of_type:
                continue  # already caught by _check_room_type_missing

            max_cap = max(r.capacity for r in rooms_of_type)
            if cls.student_count <= max_cap:
                continue  # at least one room fits — no conflict

            seen.add(key)
            best_room = max(rooms_of_type, key=lambda r: r.capacity)
            needed = cls.student_count

            reports.append(ConflictReport(
                description_fr=(
                    f"La classe {ta.school_class} ({cls.student_count} élèves) "
                    f"dépasse la capacité des salles de type {room_type} "
                    f"({max_cap} places) pour {ta.subject}."
                ),
                source="quick_check",
                severity="warning",
                fix_options=[
                    FixOption(
                        fix_fr=(
                            f"Augmenter la capacité du {best_room.name} "
                            f"à {needed} places"
                        ),
                        fix_action={
                            "action": "update_room_capacity",
                            "room": best_room.name,
                            "new_capacity": needed,
                        },
                        impact_fr="Nécessite vérification physique de la salle",
                        ease=2,
                    ),
                    FixOption(
                        fix_fr=(
                            f"Autoriser {ta.subject} pour {ta.school_class} "
                            f"en salle standard"
                        ),
                        fix_action={
                            "action": "remove_required_room_type",
                            "subject": ta.subject,
                            "class": ta.school_class,
                        },
                        impact_fr=(
                            f"Les cours de {ta.subject} se feront sans "
                            f"équipement de laboratoire"
                        ),
                        ease=2,
                    ),
                    FixOption(
                        fix_fr=(
                            f"Diviser {ta.school_class} en deux groupes "
                            f"pour les cours de {ta.subject}"
                        ),
                        fix_action={
                            "action": "split_class",
                            "class": ta.school_class,
                            "subject": ta.subject,
                        },
                        impact_fr=(
                            "Nécessite deux créneaux au lieu d'un — "
                            "fonctionnalité groupes requise"
                        ),
                        ease=3,
                    ),
                ],
            ))
        return reports

    def _check_teacher_sole_overload(self) -> list[ConflictReport]:
        """
        If a teacher is the sole option for a subject and their required hours
        exceed their weekly maximum, it is impossible.
        """
        # subject → list of teacher names
        subj_teachers: dict[str, list[str]] = defaultdict(list)
        for t in self._sd.teachers:
            for subj in t.subjects:
                subj_teachers[subj].append(t.name)

        # Accumulate minimum required hours for each sole-option teacher
        sole_load: dict[str, float] = defaultdict(float)
        for entry in self._sd.curriculum:
            qualified = subj_teachers.get(entry.subject, [])
            if len(qualified) == 1:
                sole_load[qualified[0]] += entry.total_minutes_per_week / 60

        teacher_map = {t.name: t for t in self._sd.teachers}
        reports: list[ConflictReport] = []

        for name, min_hours in sole_load.items():
            teacher = teacher_map[name]
            if min_hours > teacher.max_hours_per_week:
                gap = min_hours - teacher.max_hours_per_week
                reports.append(ConflictReport(
                    description_fr=(
                        f"{name} est le seul enseignant pour certaines matières "
                        f"et doit assurer au minimum {min_hours:.0f}h/sem., "
                        f"mais son plafond est {teacher.max_hours_per_week}h/sem. "
                        f"(manque : {gap:.0f}h)."
                    ),
                    source="quick_check",
                    fix_options=[
                        FixOption(
                            fix_fr=(
                                f"Augmenter le plafond horaire de {name} "
                                f"à {int(min_hours)}h/sem."
                            ),
                            fix_action={
                                "action": "update_teacher_max_hours",
                                "teacher": name,
                                "new_max_hours": int(min_hours),
                            },
                            impact_fr=(
                                f"Lève le blocage sur {name} "
                                f"({gap:.0f}h supplémentaires autorisées)."
                            ),
                            ease=1,
                        ),
                        FixOption(
                            fix_fr=(
                                f"Recruter un deuxième enseignant pour les matières "
                                f"de {name} ({', '.join(teacher.subjects)})."
                            ),
                            fix_action={
                                "action": "add_teacher",
                                "subjects": list(teacher.subjects),
                            },
                            impact_fr=(
                                f"Répartit la charge de {name} entre deux enseignants."
                            ),
                            ease=3,
                        ),
                    ],
                ))
        return reports

    def _check_class_hours_exceed_schedule(self) -> list[ConflictReport]:
        """
        Total curriculum hours for a level must fit in the weekly schedule.
        """
        total_slots = len(self._tc.get_all_slots())
        schedule_hours = total_slots * self._tc.base_unit_minutes / 60

        level_hours: dict[str, float] = defaultdict(float)
        for entry in self._sd.curriculum:
            level_hours[entry.level] += entry.total_minutes_per_week / 60

        reports: list[ConflictReport] = []
        for cls in self._sd.classes:
            demanded = level_hours.get(cls.level, 0.0)
            if demanded > schedule_hours:
                excess = demanded - schedule_hours
                reports.append(ConflictReport(
                    description_fr=(
                        f"La classe '{cls.name}' exige {demanded:.0f}h/sem., "
                        f"mais le planning n'offre que {schedule_hours:.0f}h/sem. "
                        f"(excédent : {excess:.0f}h)."
                    ),
                    source="quick_check",
                    fix_options=[
                        FixOption(
                            fix_fr=(
                                f"Réduire le programme du niveau {cls.level} "
                                f"d'au moins {int(excess) + 1}h."
                            ),
                            fix_action={
                                "action": "reduce_curriculum_hours",
                                "level": cls.level,
                                "by_hours": int(excess) + 1,
                            },
                            impact_fr="Rend le programme compatible avec les créneaux disponibles.",
                            ease=2,
                        ),
                        FixOption(
                            fix_fr="Ajouter un jour ou une session au calendrier hebdomadaire.",
                            fix_action={"action": "extend_schedule"},
                            impact_fr=(
                                f"Augmente la capacité hebdomadaire "
                                f"({self._tc.base_unit_minutes * len(self._tc.sessions)} "
                                f"min/jour supplémentaire possible)."
                            ),
                            ease=3,
                        ),
                    ],
                ))
        return reports

    # ------------------------------------------------------------------
    # Step 2 — Constraint relaxation
    # ------------------------------------------------------------------

    def _relaxation_check(self) -> list[ConflictReport]:
        """
        Try removing each hard constraint and re-solving.
        Constraints whose removal makes the problem feasible are culprits.
        """
        # Import here to avoid a circular import at module load time.
        from timease.engine.solver import TimetableSolver  # noqa: PLC0415

        hard = [c for c in self._sd.constraints if c.type == "hard"]
        if not hard:
            logger.debug("ConflictAnalyzer: no hard constraints to relax.")
            return []

        reports: list[ConflictReport] = []
        solver = TimetableSolver()

        for c in hard:
            relaxed_constraints = [x for x in self._sd.constraints if x.id != c.id]
            relaxed_data = dataclasses.replace(
                self._sd, constraints=relaxed_constraints
            )
            try:
                result = solver.solve(relaxed_data, timeout_seconds=RELAXATION_TIMEOUT_SECONDS)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "ConflictAnalyzer: error relaxing constraint %s: %s", c.id, exc
                )
                continue

            if result.solved:
                logger.info(
                    "ConflictAnalyzer: removing '%s' makes the problem feasible — "
                    "it is a conflict source.",
                    c.id,
                )
                report = self._build_relaxation_report(c)
                if report:
                    reports.append(report)

        if not reports:
            reports.append(ConflictReport(
                description_fr=(
                    "Aucune contrainte unique n'a pu être identifiée comme cause "
                    "principale. Le conflit résulte probablement d'une combinaison "
                    "de contraintes ou d'une pénurie de ressources complexe."
                ),
                source="relaxation",
                fix_options=[
                    FixOption(
                        fix_fr=(
                            "Vérifier les disponibilités des enseignants, "
                            "le nombre de salles et le volume horaire par classe."
                        ),
                        fix_action={"action": "manual_review"},
                        impact_fr="Identifie les goulets d'étranglement combinés.",
                        ease=2,
                    )
                ],
            ))

        return reports

    def _build_relaxation_report(self, c: Constraint) -> ConflictReport | None:
        """Generate a ConflictReport for a constraint identified as a culprit."""
        cat = c.category

        if cat == "start_time":
            hour = c.parameters.get("hour", "08:00")
            return ConflictReport(
                description_fr=(
                    f"La contrainte '{c.id}' impose que les cours commencent "
                    f"exactement à {hour}, ce qui bloque le planning."
                ),
                source="relaxation",
                fix_options=[
                    FixOption(
                        fix_fr=f"Supprimer l'obligation de commencer à {hour}.",
                        fix_action={"action": "remove_constraint", "constraint_id": c.id},
                        impact_fr="Les cours peuvent démarrer à n'importe quel créneau libre.",
                        ease=1,
                    ),
                    FixOption(
                        fix_fr=(
                            "Vérifier les indisponibilités des enseignants "
                            f"au premier créneau ({hour})."
                        ),
                        fix_action={"action": "review_teacher_unavailability"},
                        impact_fr=(
                            "Peut révéler un conflit entre indisponibilités "
                            f"d'enseignants et l'heure de début {hour}."
                        ),
                        ease=2,
                    ),
                ],
            )

        if cat == "max_consecutive":
            max_h = c.parameters.get("max_hours", 4)
            return ConflictReport(
                description_fr=(
                    f"La contrainte '{c.id}' limite à {max_h}h consécutives par classe, "
                    f"ce qui empêche de placer toutes les sessions dans les créneaux disponibles."
                ),
                source="relaxation",
                fix_options=[
                    FixOption(
                        fix_fr=f"Augmenter la limite à {max_h + 1}h consécutives.",
                        fix_action={
                            "action": "update_constraint_parameter",
                            "constraint_id": c.id,
                            "parameter": "max_hours",
                            "new_value": max_h + 1,
                        },
                        impact_fr="Offre plus de flexibilité au solveur.",
                        ease=1,
                    ),
                    FixOption(
                        fix_fr="Réduire le volume horaire hebdomadaire par niveau.",
                        fix_action={"action": "reduce_curriculum_hours"},
                        impact_fr="Réduit la pression sur les créneaux disponibles.",
                        ease=2,
                    ),
                ],
            )

        if cat == "one_teacher_per_subject_per_class":
            return ConflictReport(
                description_fr=(
                    f"La contrainte '{c.id}' (un seul enseignant par matière et par classe) "
                    f"génère un conflit. Plusieurs enseignants sont peut-être disponibles "
                    f"aux mêmes créneaux pour la même matière."
                ),
                source="relaxation",
                fix_options=[
                    FixOption(
                        fix_fr=(
                            "Vérifier qu'aucun enseignant n'est affecté à deux classes "
                            "différentes pour la même matière au même moment."
                        ),
                        fix_action={"action": "review_teacher_assignments"},
                        impact_fr="Peut révéler un conflit d'affectation.",
                        ease=2,
                    ),
                ],
            )

        if cat == "day_off":
            day = c.parameters.get("day", "")
            session = c.parameters.get("session", "")
            return ConflictReport(
                description_fr=(
                    f"La contrainte '{c.id}' (pas de cours le {day} {session}) "
                    f"empêche de caser toutes les sessions."
                ),
                source="relaxation",
                fix_options=[
                    FixOption(
                        fix_fr=f"Autoriser les cours le {day} {session}.",
                        fix_action={"action": "remove_constraint", "constraint_id": c.id},
                        impact_fr=f"Ouvre {day} {session} comme créneau disponible.",
                        ease=1,
                    ),
                    FixOption(
                        fix_fr="Réduire le volume horaire pour compenser.",
                        fix_action={"action": "reduce_curriculum_hours"},
                        impact_fr="Réduit le besoin de créneaux supplémentaires.",
                        ease=2,
                    ),
                ],
            )

        if cat == "teacher_day_off":
            teacher = c.parameters.get("teacher", "")
            day = c.parameters.get("preferred_day_off", "")
            return ConflictReport(
                description_fr=(
                    f"Le congé de {teacher} le {day} (contrainte '{c.id}') "
                    f"rend le planning infaisable avec les ressources actuelles."
                ),
                source="relaxation",
                fix_options=[
                    FixOption(
                        fix_fr=f"Assouplir ou supprimer le congé de {teacher} le {day}.",
                        fix_action={"action": "remove_constraint", "constraint_id": c.id},
                        impact_fr=f"{teacher} peut être planifié le {day}.",
                        ease=2,
                    ),
                    FixOption(
                        fix_fr=f"Recruter un remplaçant pour couvrir le {day}.",
                        fix_action={"action": "add_teacher", "substitute_for": teacher},
                        impact_fr=f"Assure la couverture de toutes les matières le {day}.",
                        ease=3,
                    ),
                ],
            )

        # Generic fallback
        return ConflictReport(
            description_fr=(
                f"La contrainte '{c.id}' ({c.description_fr}) "
                f"est une cause d'infaisabilité. La supprimer permet de trouver un planning."
            ),
            source="relaxation",
            fix_options=[
                FixOption(
                    fix_fr=f"Supprimer ou assouplir la contrainte '{c.id}'.",
                    fix_action={"action": "remove_constraint", "constraint_id": c.id},
                    impact_fr="Lève le blocage identifié par le solveur.",
                    ease=1,
                ),
            ],
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sort_by_ease(reports: list[ConflictReport]) -> list[ConflictReport]:
    """Sort fix options within each report by ease (ascending)."""
    for r in reports:
        r.fix_options.sort(key=lambda opt: opt.ease)
    return reports
