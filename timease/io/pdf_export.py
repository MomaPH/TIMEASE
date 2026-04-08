"""Export TimetableResult to a landscape A4 PDF using reportlab."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

if TYPE_CHECKING:
    from timease.engine.models import Assignment, SchoolData, TimetableResult

logger = logging.getLogger(__name__)

_FMT = "%H:%M"
_PAGE_W, _PAGE_H = landscape(A4)
_MARGIN = 1.5 * cm

_CELL_STYLE = ParagraphStyle(
    "cell", fontName="Helvetica", fontSize=8, leading=10, alignment=1
)
_HDR_STYLE = ParagraphStyle(
    "hdr", fontName="Helvetica-Bold", fontSize=9, leading=11, alignment=1
)
_TITLE_STYLE = ParagraphStyle(
    "title", fontName="Helvetica-Bold", fontSize=16, leading=20, alignment=1
)
_SUB_STYLE = ParagraphStyle(
    "sub", fontName="Helvetica", fontSize=11, leading=14, alignment=1
)
_SECTION_STYLE = ParagraphStyle(
    "section", fontName="Helvetica-Bold", fontSize=12, leading=16
)


def _footer(c: object, doc: object) -> None:
    """Draw page number in the bottom-right corner."""
    c.saveState()  # type: ignore[attr-defined]
    c.setFont("Helvetica", 8)  # type: ignore[attr-defined]
    c.setFillGray(0.5)  # type: ignore[attr-defined]
    c.drawRightString(  # type: ignore[attr-defined]
        _PAGE_W - _MARGIN, 0.5 * cm, f"Page {c.getPageNumber()}"  # type: ignore[attr-defined]
    )
    c.restoreState()  # type: ignore[attr-defined]


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


def _slot_span(start: str, end: str, base_min: int) -> int:
    """Number of base-unit rows an assignment occupies."""
    s = datetime.strptime(start, _FMT)
    e = datetime.strptime(end, _FMT)
    return max(1, int((e - s).total_seconds()) // 60 // base_min)


def _hex_to_rl(hex_color: str) -> colors.HexColor:
    return colors.HexColor(f"#{hex_color.strip('#')}")


def _build_timetable(
    assignments: list[Assignment],
    perspective: str,
    entity: str,
    data: SchoolData,
) -> Table:
    """Build a reportlab Table for one class or teacher."""
    days = [d.name for d in data.timeslot_config.days]
    base_min = data.timeslot_config.base_unit_minutes
    subject_colors = {s.name: s.color for s in data.subjects}
    day_to_col = {day: i + 1 for i, day in enumerate(days)}

    if perspective == "class":
        filtered = [a for a in assignments if a.school_class == entity]
    else:
        filtered = [a for a in assignments if a.teacher == entity]
    lookup: dict[tuple[str, str], Assignment] = {
        (a.day, a.start_time): a for a in filtered
    }

    # Build ordered grid: (start, end) tuples or None for session separators
    # Use first day's sessions as reference (all days typically share same structure)
    grid: list[tuple[str, str] | None] = []
    first_day_sessions = data.timeslot_config.days[0].sessions if data.timeslot_config.days else []
    for session in first_day_sessions:
        for s, e in _time_slots(session.start_time, session.end_time, base_min):
            grid.append((s, e))
        grid.append(None)
    while grid and grid[-1] is None:
        grid.pop()

    # table_data[0] = header; subsequent rows follow grid order
    header = [Paragraph("Heure", _HDR_STYLE)] + [
        Paragraph(d.capitalize(), _HDR_STYLE) for d in days
    ]
    table_data: list[list] = [header]
    row_map: dict[str, int] = {}  # start_time -> index in table_data
    sep_rows: list[int] = []

    for slot in grid:
        idx = len(table_data)
        if slot is None:
            sep_rows.append(idx)
            table_data.append([""] * (len(days) + 1))
        else:
            start, end = slot
            row_map[start] = idx
            table_data.append(
                [Paragraph(f"{start}-{end}", _CELL_STYLE)] + [""] * len(days)
            )

    # Base style commands
    style: list[tuple] = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("BACKGROUND", (0, 0), (-1, 0), _hex_to_rl("#CCCCCC")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]
    sep_set = set(sep_rows)
    for sr in sep_rows:
        style += [
            ("BACKGROUND", (0, sr), (-1, sr), _hex_to_rl("#F0F0F0")),
            ("TOPPADDING", (0, sr), (-1, sr), 1),
            ("BOTTOMPADDING", (0, sr), (-1, sr), 1),
        ]

    # Fill assignments into the table
    for (day, start_time), a in lookup.items():
        if start_time not in row_map:
            continue
        ri = row_map[start_time]
        ci = day_to_col[day]
        span = _slot_span(a.start_time, a.end_time, base_min)
        rl_color = _hex_to_rl(subject_colors.get(a.subject, "#FFFFFF"))

        if perspective == "class":
            lines = [a.subject, a.teacher] + ([a.room] if a.room else [])
        else:
            lines = [a.subject, a.school_class] + ([a.room] if a.room else [])
        table_data[ri][ci] = Paragraph("<br/>".join(lines), _CELL_STYLE)

        # Compute end row, avoiding separator rows
        end_ri = ri
        steps = 0
        r = ri + 1
        while steps < span - 1 and r < len(table_data):
            if r not in sep_set:
                steps += 1
                end_ri = r
            r += 1

        style.append(("BACKGROUND", (ci, ri), (ci, end_ri), rl_color))
        if end_ri > ri:
            style.append(("SPAN", (ci, ri), (ci, end_ri)))

    usable = _PAGE_W - 2 * _MARGIN
    first_w = 2.2 * cm
    day_w = (usable - first_w) / len(days)
    col_widths = [first_w] + [day_w] * len(days)

    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle(style))
    return t


def export_pdf(
    result: TimetableResult,
    data: SchoolData,
    output_path: str,
    perspectives: list[str] | None = None,
) -> None:
    """Export a solved timetable to a landscape A4 PDF.

    Args:
        result:       Solved TimetableResult from the engine.
        data:         Original SchoolData.
        output_path:  Destination .pdf path.
        perspectives: Views to include. Defaults to ['class', 'teacher'].
    """
    if perspectives is None:
        perspectives = ["class", "teacher"]

    doc = SimpleDocTemplate(
        output_path,
        pagesize=(_PAGE_W, _PAGE_H),
        leftMargin=_MARGIN,
        rightMargin=_MARGIN,
        topMargin=_MARGIN,
        bottomMargin=1.5 * cm,
    )

    story: list = []

    # Title page
    story.append(Spacer(1, 2 * cm))
    story.append(Paragraph(data.school.name, _TITLE_STYLE))
    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(f"Annee academique : {data.school.academic_year}", _SUB_STYLE)
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(f"Ville : {data.school.city}", _SUB_STYLE))
    story.append(Spacer(1, 0.5 * cm))
    if result.solved:
        status = "Resolu"
    elif result.partial:
        status = "Partiel (sessions non placees : "
        status += f"{len(result.unscheduled_sessions)})"
    else:
        status = "Non resolu"
    story.append(Paragraph(f"Statut : {status}", _SUB_STYLE))
    story.append(
        Paragraph(
            f"Temps de resolution : {result.solve_time_seconds:.2f}s", _SUB_STYLE
        )
    )
    story.append(
        Paragraph(f"Sessions planifiees : {len(result.assignments)}", _SUB_STYLE)
    )
    story.append(PageBreak())

    # Entity pages
    first = True
    for perspective in perspectives:
        if perspective == "class":
            entities: list[tuple[str, str]] = [
                (c.name, f"Classe : {c.name}") for c in data.classes
            ]
        elif perspective == "teacher":
            entities = [
                (t.name, f"Enseignant : {t.name}") for t in data.teachers
            ]
        else:
            continue

        for entity, label in entities:
            if not first:
                story.append(PageBreak())
            first = False
            story.append(Paragraph(label, _SECTION_STYLE))
            story.append(Spacer(1, 0.3 * cm))
            story.append(
                _build_timetable(result.assignments, perspective, entity, data)
            )

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    logger.info("Export PDF : %s", output_path)
