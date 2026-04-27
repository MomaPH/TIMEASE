"""
Build a benchmark manifest from a directory of FET .fet files.

Usage:
    uv run python scripts/benchmark/build_fet_manifest.py \
      --input-dir /path/to/fet/examples \
      --output-manifest scripts/benchmark/fet_manifest.json \
      --max-cases 50
"""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def _count_nodes(root: ET.Element, xpath: str) -> int:
    return len(root.findall(xpath))


def _classify_tier(activities: int, constraints: int) -> str:
    score = activities + (constraints // 2)
    if score < 300:
        return "small"
    if score < 1200:
        return "medium"
    return "hard"


def _load_case(path: Path, input_root: Path) -> dict:
    root = ET.parse(path).getroot()
    activities = _count_nodes(root, ".//Activities_List/Activity")
    teachers = _count_nodes(root, ".//Teachers_List/Teacher")
    rooms = _count_nodes(root, ".//Rooms_List/Room")
    students = _count_nodes(root, ".//Students_List/Year")
    constraints = _count_nodes(root, ".//Time_Constraints_List/*") + _count_nodes(
        root, ".//Space_Constraints_List/*"
    )
    relative = str(path.relative_to(input_root))
    return {
        "id": path.stem,
        "source_path": relative,
        "activities": activities,
        "teachers": teachers,
        "rooms": rooms,
        "student_years": students,
        "constraints": constraints,
        "tier": _classify_tier(activities, constraints),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build manifest for FET benchmark corpus")
    parser.add_argument("--input-dir", required=True, help="Directory containing .fet files")
    parser.add_argument("--output-manifest", required=True, help="Output manifest JSON path")
    parser.add_argument(
        "--max-cases",
        type=int,
        default=0,
        help="Optional cap on number of cases (0 = all)",
    )
    parser.add_argument(
        "--exclude-generated",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Exclude *_data_and_timetable.fet generated artifacts",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        raise SystemExit(f"Input directory not found: {input_dir}")

    fet_files = sorted(input_dir.rglob("*.fet"))
    if not fet_files:
        raise SystemExit(f"No .fet files found under {input_dir}")

    if args.exclude_generated:
        fet_files = [p for p in fet_files if not p.name.endswith("_data_and_timetable.fet")]

    if args.max_cases > 0:
        fet_files = fet_files[: args.max_cases]

    cases = [_load_case(p, input_dir) for p in fet_files]
    summary = {
        "total_cases": len(cases),
        "tiers": {
            "small": sum(1 for c in cases if c["tier"] == "small"),
            "medium": sum(1 for c in cases if c["tier"] == "medium"),
            "hard": sum(1 for c in cases if c["tier"] == "hard"),
        },
    }
    manifest = {
        "schema_version": 1,
        "source_dir": str(input_dir),
        "summary": summary,
        "cases": cases,
    }

    out_path = Path(args.output_manifest)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote manifest: {out_path} ({len(cases)} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
