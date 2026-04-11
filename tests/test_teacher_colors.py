from __future__ import annotations

from timease.utils.teacher_colors import teacher_color, teacher_color_map


def test_teacher_color_is_deterministic() -> None:
    c1 = teacher_color("Mme Diallo")
    c2 = teacher_color("  mme   diallo ")
    assert c1 == c2
    assert c1.startswith("#")
    assert len(c1) == 7


def test_teacher_color_map_keeps_names_and_colors() -> None:
    mapping = teacher_color_map(["M. Sy", "Mme Fall", "M. Sy"])
    assert set(mapping.keys()) == {"M. Sy", "Mme Fall"}
    assert mapping["M. Sy"].startswith("#")
    assert mapping["Mme Fall"].startswith("#")
