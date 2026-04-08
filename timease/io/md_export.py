"""Export TimetableResult to a premium Markdown file."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from timease.engine.models import Assignment, SchoolData, TimetableResult

logger = logging.getLogger(__name__)

_FMT = "%H:%M"

# Subject emoji map (fallback by index)
_SUBJECT_EMOJIS = ["📘", "📗", "📙", "📕", "📓", "📔", "📒", "📃", "📄", "📑"]


def _time_slots(start: str, end: str, base_min: int) -> list[tuple[str, str]]:
    """All (start, end) base-unit intervals within [start, end)."""
    cur = datetime.strptime(start, _FMT)
    stop = datetime.strptime(end, _FMT)
    delta = timedelta(minutes=base_min)
    slots: list[tuple[str, str]] = []
    while cur < stop:
        nxt = cur + delta
        slots.append((cur.strftime(_FMT), nxt.strftime(_FMT)))
        cur = nxt
    return slots


def _escape(text: str) -> str:
    """Escape pipe characters for use inside Markdown table cells."""
    return text.replace("|", "\\|").replace("\n", " ")


def _cell_text(a: Assignment, perspective: str) -> str:
    """Format a single assignment for a Markdown table cell."""
    room_part = f", {a.room}" if a.room else ""
    if perspective == "class":
        return f"**{_escape(a.subject)}**<br/>{_escape(a.teacher)}{_escape(room_part)}"
    else:
        return f"**{_escape(a.subject)}**<br/>{_escape(a.school_class)}{_escape(room_part)}"


def _render_entity_table(
    lines: list[str],
    assignments: list[Assignment],
    perspective: str,
    entity: str,
    data: SchoolData,
) -> None:
    """Append a Markdown table for one entity into *lines*."""
    days = [d.name for d in data.timeslot_config.days]
    base_min = data.timeslot_config.base_unit_minutes

    if perspective == "class":
        filtered = [a for a in assignments if a.school_class == entity]
        heading = f"Classe : **{entity}**"
    else:
        filtered = [a for a in assignments if a.teacher == entity]
        heading = f"Enseignant : **{entity}**"

    lookup: dict[tuple[str, str], Assignment] = {
        (a.day, a.start_time): a for a in filtered
    }

    lines.append(f"#### {heading}")
    lines.append("")

    # Collect all base-unit slots (no separators in Markdown — just all slots)
    # Use first day's sessions as reference
    all_slots: list[tuple[str, str]] = []
    first_day_sessions = data.timeslot_config.days[0].sessions if data.timeslot_config.days else []
    for session in first_day_sessions:
        for s, e in _time_slots(session.start_time, session.end_time, base_min):
            all_slots.append((s, e))

    # Table header with alignment
    day_headers = [f" **{d.capitalize()}** " for d in days]
    lines.append("| **Heure** | " + " | ".join(day_headers) + " |")
    # Right-align time column, center day columns
    align_row = ["---:"] + [":---:"] * len(days)
    lines.append("| " + " | ".join(align_row) + " |")

    # Data rows
    for start, end in all_slots:
        row_cells = [f"`{start}–{end}`"]
        for day in days:
            a = lookup.get((day, start))
            row_cells.append(_cell_text(a, perspective) if a else " ")
        lines.append("| " + " | ".join(row_cells) + " |")

    lines.append("")


def _stats_block(
    result: TimetableResult,
    data: SchoolData,
    subjects_list: list[str],
) -> list[str]:
    """Build a summary stats block in Markdown."""
    lines: list[str] = []
    n_assigned = len(result.assignments)
    n_classes = len(data.classes)
    n_teachers = len(data.teachers)
    n_rooms = len(data.rooms)
    n_subjects = len(data.subjects)
    n_days = len(data.timeslot_config.days)

    if result.solved:
        status_badge = "✅ Résolu"
    elif getattr(result, "partial", False):
        status_badge = f"⚠️ Partiel ({len(getattr(result, 'unscheduled_sessions', []))} sessions non placées)"
    else:
        status_badge = "❌ Non résolu"

    lines.append("> | Indicateur | Valeur |")
    lines.append("> |---|---|")
    lines.append(f"> | Statut | {status_badge} |")
    lines.append(f"> | Sessions planifiées | {n_assigned} |")
    lines.append(f"> | Classes | {n_classes} |")
    lines.append(f"> | Enseignants | {n_teachers} |")
    lines.append(f"> | Salles | {n_rooms} |")
    lines.append(f"> | Matières | {n_subjects} |")
    lines.append(f"> | Jours | {n_days} |")
    lines.append("")

    # Subject legend
    lines.append("**Matières :**")
    lines.append("")
    for i, name in enumerate(subjects_list):
        emoji = _SUBJECT_EMOJIS[i % len(_SUBJECT_EMOJIS)]
        lines.append(f"- {emoji} {name}")
    lines.append("")
    return lines


def export_markdown(
    result: TimetableResult,
    data: SchoolData,
    output_path: str,
    perspectives: list[str] | None = None,
) -> None:
    """Export a solved timetable to a premium Markdown file.

    Each class/teacher gets a section with a Markdown table. Cells show
    "Subject (Teacher, Room)" for class perspective, or
    "Subject (Class, Room)" for teacher perspective.

    Args:
        result:       Solved TimetableResult from the engine.
        data:         Original SchoolData.
        output_path:  Destination .md path.
        perspectives: Views to include. Defaults to ['class', 'teacher'].
    """
    if perspectives is None:
        perspectives = ["class", "teacher"]

    gen_date = datetime.now().strftime("%d/%m/%Y à %H:%M")
    gen_date_iso = datetime.now().strftime("%Y-%m-%d")
    city = getattr(data.school, "city", "") or ""
    academic_year = getattr(data.school, "academic_year", "") or ""
    subjects_list = [s.name for s in data.subjects]

    lines: list[str] = []

    # ── YAML frontmatter ──
    lines.append("---")
    lines.append(f"title: Emploi du temps — {data.school.name}")
    if academic_year:
        lines.append(f"annee_academique: \"{academic_year}\"")
    if city:
        lines.append(f"ville: \"{city}\"")
    lines.append(f"date_generation: \"{gen_date_iso}\"")
    lines.append(f"sessions: {len(result.assignments)}")
    lines.append(f"genere_par: TIMEASE")
    lines.append("---")
    lines.append("")

    # ── Document title ──
    lines.append(f"# 📅 Emploi du temps — {data.school.name}")
    lines.append("")
    meta_parts = []
    if academic_year:
        meta_parts.append(f"Année académique **{academic_year}**")
    if city:
        meta_parts.append(f"📍 {city}")
    meta_parts.append(f"🗓️ Généré le {gen_date}")
    lines.append("  ".join(meta_parts))
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Stats block ──
    lines.append("## 📊 Récapitulatif")
    lines.append("")
    lines.extend(_stats_block(result, data, subjects_list))
    lines.append("---")
    lines.append("")

    # ── Per-perspective sections ──
    for perspective in perspectives:
        if perspective == "class":
            section_emoji = "🏫"
            section_title = "Classes"
            entities = [c.name for c in data.classes]
        elif perspective == "teacher":
            section_emoji = "👩‍🏫"
            section_title = "Enseignants"
            entities = [t.name for t in data.teachers]
        else:
            continue

        lines.append(f"## {section_emoji} {section_title}")
        lines.append("")

        for entity in entities:
            _render_entity_table(lines, result.assignments, perspective, entity, data)

        lines.append("---")
        lines.append("")

    # ── Footer ──
    lines.append("")
    lines.append(f"*Généré par [TIMEASE](https://timease.app) le {gen_date}*")
    lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info("Export Markdown premium : %s", output_path)
