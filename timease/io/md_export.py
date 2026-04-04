"""Export TimetableResult to a Markdown file."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from timease.engine.models import Assignment, SchoolData, TimetableResult

logger = logging.getLogger(__name__)

_FMT = "%H:%M"


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
    return text.replace("|", "\\|")


def _cell_text(a: Assignment, perspective: str) -> str:
    """Format a single assignment as 'Subject (Teacher, Room)' or similar."""
    room_part = f", {a.room}" if a.room else ""
    if perspective == "class":
        return f"{a.subject} ({a.teacher}{room_part})"
    else:
        return f"{a.subject} ({a.school_class}{room_part})"


def _render_entity(
    lines: list[str],
    assignments: list[Assignment],
    perspective: str,
    entity: str,
    data: SchoolData,
) -> None:
    """Append a Markdown table for one entity into *lines*."""
    days = data.timeslot_config.days
    base_min = data.timeslot_config.base_unit_minutes

    if perspective == "class":
        filtered = [a for a in assignments if a.school_class == entity]
        heading = f"Classe : {entity}"
    else:
        filtered = [a for a in assignments if a.teacher == entity]
        heading = f"Enseignant : {entity}"

    lookup: dict[tuple[str, str], Assignment] = {
        (a.day, a.start_time): a for a in filtered
    }

    lines.append(f"### {heading}")
    lines.append("")

    # Collect all base-unit slots (no separators in Markdown — just all slots)
    all_slots: list[tuple[str, str]] = []
    for session in data.timeslot_config.sessions:
        for s, e in _time_slots(session.start_time, session.end_time, base_min):
            all_slots.append((s, e))

    # Table header
    header_cols = ["Heure"] + [d.capitalize() for d in days]
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("| " + " | ".join(["---"] * len(header_cols)) + " |")

    # Data rows — show content only at the slot where the assignment STARTS
    for start, end in all_slots:
        row_cells = [f"{start}-{end}"]
        for day in days:
            a = lookup.get((day, start))
            if a is not None:
                row_cells.append(_escape(_cell_text(a, perspective)))
            else:
                row_cells.append("")
        lines.append("| " + " | ".join(row_cells) + " |")

    lines.append("")


def export_markdown(
    result: TimetableResult,
    data: SchoolData,
    output_path: str,
    perspectives: list[str] | None = None,
) -> None:
    """Export a solved timetable to a single Markdown file.

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

    lines: list[str] = []

    # Document header
    lines.append(f"# Emploi du temps — {data.school.name}")
    lines.append("")
    lines.append(f"**Annee academique :** {data.school.academic_year}  ")
    lines.append(f"**Ville :** {data.school.city}  ")
    if result.solved:
        status = "Resolu"
    elif result.partial:
        status = f"Partiel ({len(result.unscheduled_sessions)} sessions non placees)"
    else:
        status = "Non resolu"
    lines.append(f"**Statut :** {status}  ")
    lines.append(f"**Sessions planifiees :** {len(result.assignments)}")
    lines.append("")

    for perspective in perspectives:
        if perspective == "class":
            section_title = "## Classes"
            entities = [c.name for c in data.classes]
        elif perspective == "teacher":
            section_title = "## Enseignants"
            entities = [t.name for t in data.teachers]
        else:
            continue

        lines.append(section_title)
        lines.append("")

        for entity in entities:
            _render_entity(lines, result.assignments, perspective, entity, data)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info("Export Markdown : %s", output_path)
