"""Export TimetableResult to a landscape A4 Word document using python-docx."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt

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


def _slot_span(start: str, end: str, base_min: int) -> int:
    """Number of base-unit rows an assignment occupies."""
    s = datetime.strptime(start, _FMT)
    e = datetime.strptime(end, _FMT)
    return max(1, int((e - s).total_seconds()) // 60 // base_min)


def _shade_cell(cell: object, hex_color: str) -> None:
    """Apply background shading to a Word table cell."""
    tc = cell._tc  # type: ignore[attr-defined]
    tcPr = tc.get_or_add_tcPr()
    for existing in tcPr.findall(qn("w:shd")):
        tcPr.remove(existing)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color.strip("#").upper())
    tcPr.append(shd)


def _write_cell(
    cell: object,
    lines: list[str],
    bold: bool = False,
    font_size: int = 8,
) -> None:
    """Write multiline content to a Word table cell, replacing existing content."""
    tc = cell._tc  # type: ignore[attr-defined]
    # Remove all paragraphs except the first
    paras = tc.findall(qn("w:p"))
    for p_el in paras[1:]:
        tc.remove(p_el)
    # Remove all runs from the first paragraph
    first_p = paras[0] if paras else OxmlElement("w:p")
    if not paras:
        tc.append(first_p)
    for r_el in first_p.findall(qn("w:r")):
        first_p.remove(r_el)

    # Set paragraph alignment
    pPr = first_p.find(qn("w:pPr"))
    if pPr is None:
        pPr = OxmlElement("w:pPr")
        first_p.insert(0, pPr)
    for jc_el in pPr.findall(qn("w:jc")):
        pPr.remove(jc_el)
    jc = OxmlElement("w:jc")
    jc.set(qn("w:val"), "center")
    pPr.append(jc)

    # Add runs with line breaks between them
    for i, line in enumerate(lines):
        if i > 0:
            br_r = OxmlElement("w:r")
            br_el = OxmlElement("w:br")
            br_r.append(br_el)
            first_p.append(br_r)
        r_el = OxmlElement("w:r")
        rPr = OxmlElement("w:rPr")
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), str(font_size * 2))  # half-points
        rPr.append(sz)
        sz_cs = OxmlElement("w:szCs")
        sz_cs.set(qn("w:val"), str(font_size * 2))
        rPr.append(sz_cs)
        if bold:
            rPr.append(OxmlElement("w:b"))
        r_el.append(rPr)
        t_el = OxmlElement("w:t")
        t_el.text = line
        r_el.append(t_el)
        first_p.append(r_el)


def _add_timetable(
    doc: Document,
    assignments: list[Assignment],
    perspective: str,
    entity: str,
    data: SchoolData,
) -> None:
    """Add a timetable table to the document for one entity."""
    days = data.timeslot_config.days
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

    # Build ordered grid
    grid: list[tuple[str, str] | None] = []
    for session in data.timeslot_config.sessions:
        for s, e in _time_slots(session.start_time, session.end_time, base_min):
            grid.append((s, e))
        grid.append(None)
    while grid and grid[-1] is None:
        grid.pop()

    n_rows = 1 + len(grid)
    n_cols = 1 + len(days)

    table = doc.add_table(rows=n_rows, cols=n_cols)
    table.style = "Table Grid"
    table.autofit = False

    # Column widths: time col + equal day cols
    # Landscape A4 with 2cm margins: ~25.7cm usable
    usable_mm = 257.0
    time_col_mm = 20.0
    day_col_mm = (usable_mm - time_col_mm) / len(days)

    for row in table.rows:
        row.cells[0].width = Mm(time_col_mm)
        for ci in range(1, n_cols):
            row.cells[ci].width = Mm(day_col_mm)

    # Header row
    hdr = table.rows[0]
    _write_cell(hdr.cells[0], ["Heure"], bold=True, font_size=9)
    _shade_cell(hdr.cells[0], "#CCCCCC")
    for ci, day in enumerate(days, 1):
        _write_cell(hdr.cells[ci], [day.capitalize()], bold=True, font_size=9)
        _shade_cell(hdr.cells[ci], "#CCCCCC")

    # Build row_map and style separator rows
    row_map: dict[str, int] = {}
    sep_set: set[int] = set()
    ri = 1
    for slot in grid:
        if slot is None:
            sep_set.add(ri)
            for ci in range(n_cols):
                _shade_cell(table.rows[ri].cells[ci], "#F0F0F0")
        else:
            start, end = slot
            row_map[start] = ri
            _write_cell(table.rows[ri].cells[0], [f"{start}-{end}"], font_size=8)
        ri += 1

    # Fill assignments
    for (day, start_time), a in lookup.items():
        if start_time not in row_map:
            continue
        ri_a = row_map[start_time]
        ci_a = day_to_col[day]
        span = _slot_span(a.start_time, a.end_time, base_min)
        hex_color = subject_colors.get(a.subject, "#FFFFFF")

        if perspective == "class":
            lines = [a.subject, a.teacher] + ([a.room] if a.room else [])
        else:
            lines = [a.subject, a.school_class] + ([a.room] if a.room else [])

        # Compute end row, skipping separator rows
        end_ri = ri_a
        steps = 0
        r = ri_a + 1
        while steps < span - 1 and r < n_rows:
            if r not in sep_set:
                steps += 1
                end_ri = r
            r += 1

        if end_ri > ri_a:
            merged = table.cell(ri_a, ci_a).merge(table.cell(end_ri, ci_a))
            _write_cell(merged, lines, font_size=8)
            _shade_cell(merged, hex_color)
        else:
            cell = table.rows[ri_a].cells[ci_a]
            _write_cell(cell, lines, font_size=8)
            _shade_cell(cell, hex_color)


def export_word(
    result: TimetableResult,
    data: SchoolData,
    output_path: str,
    perspectives: list[str] | None = None,
) -> None:
    """Export a solved timetable to a landscape A4 Word document.

    Args:
        result:       Solved TimetableResult from the engine.
        data:         Original SchoolData.
        output_path:  Destination .docx path.
        perspectives: Views to include. Defaults to ['class', 'teacher'].
    """
    if perspectives is None:
        perspectives = ["class", "teacher"]

    doc = Document()

    # Set landscape A4
    section = doc.sections[0]
    section.page_height = Mm(210)
    section.page_width = Mm(297)
    section.left_margin = Mm(20)
    section.right_margin = Mm(20)
    section.top_margin = Mm(15)
    section.bottom_margin = Mm(15)
    section.orientation = WD_ORIENT.LANDSCAPE

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
                doc.add_page_break()
            first = False
            doc.add_heading(label, level=1)
            _add_timetable(doc, result.assignments, perspective, entity, data)

    doc.save(output_path)
    logger.info("Export Word : %s", output_path)
