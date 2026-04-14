"""
Convert FET .fet files into TIMEASE JSON datasets.

Usage:
    uv run python scripts/convert_fet_to_timease.py \
      --input /path/to/file_or_dir \
      --output /path/to/output_dir
"""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FetActivity:
    teacher: str
    subject: str
    students: str
    duration: int


def _safe_slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_") or "X"


def _read_activities(root: ET.Element) -> list[FetActivity]:
    activities: list[FetActivity] = []
    for node in root.findall(".//Activities_List/Activity"):
        subject = (node.findtext("Subject") or "").strip()
        students = (node.findtext("Students") or "").strip()
        if not subject or not students:
            continue
        teacher_nodes = [t.text.strip() for t in node.findall("Teacher") if t.text and t.text.strip()]
        teacher = teacher_nodes[0] if teacher_nodes else "UNASSIGNED"
        duration = int((node.findtext("Duration") or "1").strip())
        activities.append(FetActivity(teacher=teacher, subject=subject, students=students, duration=max(1, duration)))
    return activities


def _subject_variants(activities: list[FetActivity]) -> dict[tuple[str, str, str, int], str]:
    """
    TIMEASE requires one teacher assignment per (class, subject).
    If FET has multiple teachers for a class+subject, split into variants.
    """
    by_class_subject: dict[tuple[str, str], set[str]] = defaultdict(set)
    for a in activities:
        by_class_subject[(a.students, a.subject)].add(a.teacher)

    mapping: dict[tuple[str, str, str, int], str] = {}
    for a in activities:
        teachers = by_class_subject[(a.students, a.subject)]
        if len(teachers) == 1:
            variant = a.subject
        else:
            variant = f"{a.subject}@{_safe_slug(a.teacher)}"
        if a.duration != 1:
            variant = f"{variant}__d{a.duration}"
        mapping[(a.students, a.subject, a.teacher, a.duration)] = variant
    return mapping


def _build_timease_payload(root: ET.Element, source_name: str) -> dict:
    day_names = [(d.findtext("Name") or "").strip() for d in root.findall(".//Days_List/Day")]
    day_names = [d for d in day_names if d]
    hour_names = [(h.findtext("Name") or "").strip() for h in root.findall(".//Hours_List/Hour")]
    hour_count = max(1, len([h for h in hour_names if h]))

    base_unit_minutes = 60
    start_hour = 8
    day_session_end = start_hour + hour_count

    days = [
        {
            "name": day,
            "sessions": [{"name": "Journée", "start_time": f"{start_hour:02d}:00", "end_time": f"{day_session_end:02d}:00"}],
            "breaks": [],
        }
        for day in day_names
    ]

    activities = _read_activities(root)
    variant_for = _subject_variants(activities)

    class_names = sorted({a.students for a in activities})
    teacher_names = sorted({a.teacher for a in activities})
    room_nodes = root.findall(".//Rooms_List/Room")
    room_payload = [
        {
            "name": (r.findtext("Name") or "").strip() or f"R{i+1}",
            "capacity": int((r.findtext("Capacity") or "40").strip() or "40"),
            "types": ["Salle standard"],
        }
        for i, r in enumerate(room_nodes)
    ]

    # Aggregate curriculum by (class, subject_variant, teacher, duration)
    bucket: Counter[tuple[str, str, str, int]] = Counter()
    for a in activities:
        subject_variant = variant_for[(a.students, a.subject, a.teacher, a.duration)]
        bucket[(a.students, subject_variant, a.teacher, a.duration)] += 1

    curriculum = []
    teacher_assignments = []
    teacher_subjects: dict[str, set[str]] = defaultdict(set)
    for (school_class, subject_variant, teacher, duration), sessions_count in sorted(bucket.items()):
        minutes_per_session = duration * base_unit_minutes
        curriculum.append(
            {
                "school_class": school_class,
                "subject": subject_variant,
                "total_minutes_per_week": sessions_count * minutes_per_session,
                "sessions_per_week": sessions_count,
                "minutes_per_session": minutes_per_session,
            }
        )
        teacher_assignments.append(
            {
                "teacher": teacher,
                "subject": subject_variant,
                "school_class": school_class,
            }
        )
        teacher_subjects[teacher].add(subject_variant)

    subjects = [
        {
            "name": s,
            "short_name": s[:12],
            "color": "#0d9488",
            "required_room_type": None,
            "needs_room": bool(room_payload),
        }
        for s in sorted({c["subject"] for c in curriculum})
    ]

    classes = [
        {"name": c, "level": c, "student_count": 30}
        for c in class_names
    ]

    teachers = []
    for t in teacher_names:
        declared = sorted(teacher_subjects.get(t, set()))
        teachers.append(
            {
                "name": t,
                "subjects": declared,
                "max_hours_per_week": 80,
                "unavailable_slots": [],
            }
        )

    payload = {
        "school": {"name": f"FET import: {source_name}", "academic_year": "2026-2027", "city": "Imported"},
        "timeslot_config": {"days": days, "base_unit_minutes": base_unit_minutes},
        "subjects": subjects,
        "teachers": teachers,
        "classes": classes,
        "rooms": room_payload,
        "curriculum": curriculum,
        "constraints": [
            {"id": "C1", "type": "hard", "category": "teacher_no_overlap", "description_fr": "Pas de chevauchement enseignant", "priority": 10, "parameters": {}},
            {"id": "C2", "type": "hard", "category": "class_no_overlap", "description_fr": "Pas de chevauchement classe", "priority": 10, "parameters": {}},
            {"id": "C3", "type": "hard", "category": "teacher_subject_declared", "description_fr": "Matière enseignant déclarée", "priority": 10, "parameters": {}},
            {"id": "C4", "type": "hard", "category": "teacher_calendar_declared", "description_fr": "Calendrier enseignant déclaré", "priority": 10, "parameters": {}},
        ],
        "teacher_assignments": teacher_assignments,
    }
    return payload


def convert_fet_file(path: Path, out_dir: Path) -> Path:
    root = ET.parse(path).getroot()
    payload = _build_timease_payload(root, path.stem)
    out_path = out_dir / f"{path.stem}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser(description="Convert FET .fet files to TIMEASE JSON")
    ap.add_argument("--input", required=True, help="Input .fet file or directory containing .fet files")
    ap.add_argument("--output", required=True, help="Output directory for converted JSON files")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    if in_path.is_file():
        files = [in_path]
    else:
        files = sorted(in_path.rglob("*.fet"))
    if not files:
        raise SystemExit("No .fet files found")

    for f in files:
        out = convert_fet_file(f, out_dir)
        print(f"{f} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
