"""Deterministic teacher color utilities shared by API and exports."""
from __future__ import annotations

import hashlib
from typing import Iterable

_PALETTE: tuple[str, ...] = (
    "#0D9488", "#2563EB", "#DC2626", "#7C3AED", "#EA580C",
    "#0891B2", "#BE123C", "#65A30D", "#9333EA", "#0369A1",
    "#B45309", "#4F46E5", "#16A34A", "#D97706", "#0284C7",
)


def _norm_teacher_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def teacher_color(name: str) -> str:
    """Return a stable hex color for a teacher name."""
    normalized = _norm_teacher_name(name)
    if not normalized:
        return _PALETTE[0]
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()
    idx = int(digest[:8], 16) % len(_PALETTE)
    return _PALETTE[idx]


def teacher_color_map(teacher_names: Iterable[str]) -> dict[str, str]:
    """Return {teacher_name: color} for provided teacher names."""
    seen: dict[str, str] = {}
    for name in teacher_names:
        if name in seen:
            continue
        seen[name] = teacher_color(name)
    return seen
