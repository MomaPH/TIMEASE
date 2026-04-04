"""
Tests for timease/io modules: import, export (Excel/PDF/Word/Markdown),
file_parser, and ai_setup class structure.

All export tests share one module-scoped solver run to keep the suite fast.
"""

from __future__ import annotations

import dataclasses
import inspect
import tempfile
from pathlib import Path

import pytest
from openpyxl import load_workbook

from timease.engine.models import SchoolData

DAKAR_JSON = (
    Path(__file__).parent.parent / "timease" / "data" / "real_school_dakar_LOCKED.json"
)
TEMPLATE_XLSX = (
    Path(__file__).parent.parent / "timease" / "data" / "template.xlsx"
)


# ---------------------------------------------------------------------------
# Module-scoped fixtures  (solver runs once for the whole file)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def dakar_data() -> SchoolData:
    return SchoolData.from_json(DAKAR_JSON)


@pytest.fixture(scope="module")
def dakar_result(dakar_data: SchoolData):
    from timease.engine.solver import TimetableSolver
    return TimetableSolver().solve(dakar_data, timeout_seconds=120)


# ---------------------------------------------------------------------------
# Template tests
# ---------------------------------------------------------------------------

def test_template_has_10_sheets(tmp_path: Path) -> None:
    """create_template() produces exactly 10 sheets."""
    from timease.io.excel_import import create_template

    xlsx = tmp_path / "template.xlsx"
    create_template(str(xlsx))
    wb = load_workbook(str(xlsx))
    assert len(wb.sheetnames) == 10, f"Got sheets: {wb.sheetnames}"


def test_template_affectations_headers(tmp_path: Path) -> None:
    """Affectations sheet has the three expected column headers."""
    from timease.io.excel_import import create_template

    xlsx = tmp_path / "template.xlsx"
    create_template(str(xlsx))
    wb = load_workbook(str(xlsx))
    ws = wb["Affectations"]
    headers = [ws.cell(row=1, column=c).value for c in range(1, 4)]
    assert headers == ["Enseignant *", "Matière *", "Classe *"]


# ---------------------------------------------------------------------------
# Import tests
# ---------------------------------------------------------------------------

def test_import_strips_whitespace() -> None:
    """_cell_str strips leading/trailing whitespace from cell values."""
    from timease.io.excel_import import _cell_str

    class _FakeCell:
        def __init__(self, value: object) -> None:
            self.value = value

    assert _cell_str(_FakeCell("  Mme Diallo  ")) == "Mme Diallo"
    assert _cell_str(_FakeCell("\t6ème A\n"))      == "6ème A"
    assert _cell_str(_FakeCell("  "))              == ""
    assert _cell_str(_FakeCell(None))              == ""


def test_import_parses_3h30_as_210min() -> None:
    """_parse_duration correctly converts duration strings and numbers."""
    from timease.io.excel_import import _parse_duration

    assert _parse_duration("3H30") == 210
    assert _parse_duration("3h30") == 210
    assert _parse_duration("2H")   == 120
    assert _parse_duration("2h")   == 120
    assert _parse_duration(210)    == 210
    assert _parse_duration(90)     == 90
    assert _parse_duration("90")   == 90
    assert _parse_duration(None)   is None
    assert _parse_duration("")     is None


def test_import_rejects_unknown_teacher(tmp_path: Path) -> None:
    """read_template returns errors when Affectations references an unknown teacher."""
    from timease.io.excel_import import create_template, read_template

    xlsx = tmp_path / "bad.xlsx"
    create_template(str(xlsx))

    # Overwrite the example Affectations row with an unknown teacher
    wb = load_workbook(str(xlsx))
    ws = wb["Affectations"]
    ws.cell(row=2, column=1, value="Enseignant Fantôme")
    ws.cell(row=2, column=2, value="Mathématiques")
    ws.cell(row=2, column=3, value="6ème A")
    wb.save(str(xlsx))

    data, errors = read_template(str(xlsx))

    assert data is None, "read_template should return None on unknown teacher"
    assert errors, "errors list should be non-empty"
    combined = " ".join(errors)
    assert "Fantôme" in combined or "Enseignant Fantôme" in combined, (
        f"Expected unknown-teacher error, got: {errors}"
    )


# ---------------------------------------------------------------------------
# Export tests  (reuse module-scoped dakar_result)
# ---------------------------------------------------------------------------

def test_export_excel_has_all_perspectives(dakar_result, dakar_data, tmp_path: Path) -> None:
    """Default Excel export includes class, teacher, room, and subject sheets."""
    from timease.io.excel_export import export_timetable

    xlsx = tmp_path / "out.xlsx"
    export_timetable(dakar_result, dakar_data, str(xlsx))

    wb = load_workbook(str(xlsx))
    names = wb.sheetnames

    assert "Résumé" in names
    assert any("Classe" in n for n in names),    f"No class sheet in {names}"
    assert any("Prof"   in n for n in names),    f"No teacher sheet in {names}"
    assert any("Salle"  in n for n in names),    f"No room sheet in {names}"
    assert "Par matière" in names,               f"No subject summary in {names}"


def test_export_maguette_both_subjects(dakar_result, dakar_data, tmp_path: Path) -> None:
    """Markdown export contains both subjects that Maguette teaches."""
    from timease.io.md_export import export_markdown

    md_path = tmp_path / "out.md"
    export_markdown(dakar_result, dakar_data, str(md_path))
    content = md_path.read_text(encoding="utf-8")

    maguette_subjects = {
        a.subject for a in dakar_result.assignments if a.teacher == "Maguette"
    }
    assert len(maguette_subjects) >= 2, (
        f"Expected Maguette to teach ≥2 subjects in the result, "
        f"got: {maguette_subjects}"
    )
    assert "Maguette" in content, "Teacher name 'Maguette' missing from markdown"
    for subject in maguette_subjects:
        assert subject in content, f"Subject '{subject}' missing from markdown"


def test_export_pdf_creates_file(dakar_result, dakar_data, tmp_path: Path) -> None:
    """export_pdf writes a non-empty .pdf file."""
    from timease.io.pdf_export import export_pdf

    pdf = tmp_path / "out.pdf"
    export_pdf(dakar_result, dakar_data, str(pdf))

    assert pdf.exists(), "PDF file was not created"
    assert pdf.stat().st_size > 0, "PDF file is empty"


def test_export_word_creates_file(dakar_result, dakar_data, tmp_path: Path) -> None:
    """export_word writes a non-empty .docx file."""
    from timease.io.word_export import export_word

    docx = tmp_path / "out.docx"
    export_word(dakar_result, dakar_data, str(docx))

    assert docx.exists(), "DOCX file was not created"
    assert docx.stat().st_size > 0, "DOCX file is empty"


def test_export_markdown_has_all_classes(dakar_result, dakar_data, tmp_path: Path) -> None:
    """Markdown class-perspective export contains a section for every class."""
    from timease.io.md_export import export_markdown

    md = tmp_path / "out.md"
    export_markdown(dakar_result, dakar_data, str(md), perspectives=["class"])
    content = md.read_text(encoding="utf-8")

    for cls in dakar_data.classes:
        assert cls.name in content, f"Class '{cls.name}' missing from markdown"


# ---------------------------------------------------------------------------
# File parser tests
# ---------------------------------------------------------------------------

def test_file_parser_excel() -> None:
    """extract_content on the bundled template returns type='excel' and sheet names."""
    from timease.io.file_parser import extract_content

    content, ftype = extract_content(str(TEMPLATE_XLSX))

    assert ftype == "excel"
    assert "Affectations" in content, (
        "'Affectations' sheet name missing from parsed Excel content"
    )


def test_file_parser_unknown_format(tmp_path: Path) -> None:
    """extract_content returns ('Format non supporté', 'unknown') for unsupported extensions."""
    from timease.io.file_parser import extract_content

    fake = tmp_path / "data.xyz"
    fake.write_text("dummy content")

    content, ftype = extract_content(str(fake))

    assert ftype == "unknown"
    assert "non supporté" in content.lower(), (
        f"Expected 'non supporté' in content, got: {content!r}"
    )


# ---------------------------------------------------------------------------
# AI setup structure test  (no API call)
# ---------------------------------------------------------------------------

def test_ai_setup_class_structure() -> None:
    """SetupAssistant and SetupResponse have the expected structure and fields."""
    from timease.app.ai_setup import SYSTEM_PROMPT, SetupAssistant, SetupResponse

    # SYSTEM_PROMPT content
    assert "TIMEASE"     in SYSTEM_PROMPT
    assert "assignments" in SYSTEM_PROMPT
    assert "teachers"    in SYSTEM_PROMPT
    assert "extracted"   in SYSTEM_PROMPT

    # SetupResponse is a dataclass with the six expected fields
    fields = {f.name for f in dataclasses.fields(SetupResponse)}
    assert fields == {
        "message_fr",
        "extracted_data",
        "data_type",
        "needs_confirmation",
        "suggestions",
        "progress",
    }, f"Unexpected fields: {fields}"

    # SetupAssistant constructor requires api_key
    sig = inspect.signature(SetupAssistant.__init__)
    assert "api_key" in sig.parameters, (
        f"SetupAssistant.__init__ missing 'api_key' parameter: {list(sig.parameters)}"
    )

    # process_message method exists and has the right signature
    assert callable(getattr(SetupAssistant, "process_message", None))
    pm_sig = inspect.signature(SetupAssistant.process_message)
    assert "user_message"   in pm_sig.parameters
    assert "current_data"   in pm_sig.parameters
    assert "file_content"   in pm_sig.parameters
