"""
Run side-by-side benchmark for FET and TIMEASE on a manifest of FET cases.

Pipeline per case:
1. Run FET on source .fet
2. Convert .fet to TIMEASE JSON
3. Run TIMEASE solver on converted JSON
4. Persist structured result JSON

Usage:
    uv run python scripts/benchmark/run_fet_timease_benchmark.py \
      --manifest scripts/benchmark/fet_manifest.json \
      --fet-bin /path/to/fet-cl \
      --output-dir /tmp/timease-bench \
      --timeout-seconds 60
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

# Allow importing project modules when executed as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.convert_fet_to_timease import convert_fet_file
from timease.engine.models import SchoolData
from timease.engine.solver import TimetableSolver


@dataclass
class EngineOutcome:
    status: str
    wall_seconds: float
    solve_seconds: float | None
    assigned_sessions: int
    unscheduled_sessions: int
    details: str


def _load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_fet(fet_bin: Path, fet_input: Path, timeout_seconds: int) -> EngineOutcome:
    run_dir = Path(tempfile.mkdtemp(prefix="timease_fet_"))
    cmd = [
        str(fet_bin),
        f"--inputfile={fet_input}",
        f"--outputdir={run_dir}",
        f"--timelimitseconds={timeout_seconds}",
        "--writetimetableconflicts=false",
        "--writetimetablesstatistics=false",
        "--writetimetablesxml=false",
        "--writetimetablesdayshorizontal=false",
        "--writetimetablesdaysvertical=false",
        "--writetimetablestimehorizontal=false",
        "--writetimetablestimevertical=false",
        "--writetimetablessubgroups=false",
        "--writetimetablesgroups=false",
        "--writetimetablesyears=false",
        "--writetimetablesteachers=false",
        "--writetimetablesteachersfreeperiods=false",
        "--writetimetablesbuildings=false",
        "--writetimetablesrooms=false",
        "--writetimetablessubjects=false",
        "--writetimetablesactivitytags=false",
        "--writetimetablesactivities=false",
    ]
    start = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    wall = time.perf_counter() - start

    combined = f"{proc.stdout}\n{proc.stderr}".strip()
    success = "Generation successful" in combined
    timed_out = "Time exceeded" in combined or "time exceeded" in combined
    if success:
        status = "solved"
    elif timed_out:
        status = "timeout"
    elif proc.returncode != 0:
        status = "error"
    else:
        status = "unknown"

    shutil.rmtree(run_dir, ignore_errors=True)
    return EngineOutcome(
        status=status,
        wall_seconds=round(wall, 3),
        solve_seconds=None,
        assigned_sessions=0,
        unscheduled_sessions=0,
        details=combined[:3000],
    )


def _run_timease(json_input: Path, timeout_seconds: int) -> EngineOutcome:
    sd = SchoolData.from_json(json_input)
    start = time.perf_counter()
    result = TimetableSolver().solve(
        sd,
        timeout_seconds=timeout_seconds,
        optimize_soft_constraints=False,
        stop_at_first_solution=True,
        enforce_room_conflicts=False,
    )
    wall = time.perf_counter() - start
    if result.solved:
        status = "solved"
    elif result.partial:
        status = "partial"
    else:
        status = "timeout"
    return EngineOutcome(
        status=status,
        wall_seconds=round(wall, 3),
        solve_seconds=round(float(result.solve_time_seconds), 3),
        assigned_sessions=len(result.assignments),
        unscheduled_sessions=len(result.unscheduled_sessions),
        details="",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run FET vs TIMEASE benchmark from manifest")
    parser.add_argument("--manifest", required=True, help="Manifest JSON path")
    parser.add_argument("--fet-bin", required=True, help="Path to fet-cl binary")
    parser.add_argument("--output-dir", required=True, help="Directory for benchmark outputs")
    parser.add_argument("--timeout-seconds", type=int, default=60, help="Per-case timeout")
    parser.add_argument("--limit", type=int, default=0, help="Optional cap on number of cases")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = _load_manifest(manifest_path)
    source_dir = Path(manifest["source_dir"])
    fet_bin = Path(args.fet_bin)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    converted_dir = output_dir / "converted_json"
    converted_dir.mkdir(parents=True, exist_ok=True)

    cases = manifest.get("cases", [])
    if args.limit > 0:
        cases = cases[: args.limit]

    rows: list[dict] = []
    for idx, case in enumerate(cases, start=1):
        fet_path = source_dir / case["source_path"]
        print(f"[{idx}/{len(cases)}] {case['id']}")
        try:
            converted_path = convert_fet_file(fet_path, converted_dir)
            fet_outcome = _run_fet(fet_bin, fet_path, args.timeout_seconds)
            timease_outcome = _run_timease(converted_path, args.timeout_seconds)
            row = {
                "case": case,
                "fet": asdict(fet_outcome),
                "timease": asdict(timease_outcome),
                "converted_json": str(converted_path),
            }
        except Exception as exc:  # noqa: BLE001
            row = {
                "case": case,
                "fet": asdict(
                    EngineOutcome(
                        status="error",
                        wall_seconds=0.0,
                        solve_seconds=None,
                        assigned_sessions=0,
                        unscheduled_sessions=0,
                        details=f"Benchmark failure: {exc}",
                    )
                ),
                "timease": asdict(
                    EngineOutcome(
                        status="error",
                        wall_seconds=0.0,
                        solve_seconds=None,
                        assigned_sessions=0,
                        unscheduled_sessions=0,
                        details=f"Benchmark failure: {exc}",
                    )
                ),
                "converted_json": "",
            }
        rows.append(row)

    summary = {
        "total_cases": len(rows),
        "fet_solved": sum(1 for r in rows if r["fet"]["status"] == "solved"),
        "timease_solved": sum(1 for r in rows if r["timease"]["status"] == "solved"),
        "timease_partial": sum(1 for r in rows if r["timease"]["status"] == "partial"),
        "timeout_seconds": args.timeout_seconds,
    }
    result_obj = {
        "manifest": str(manifest_path),
        "source_dir": str(source_dir),
        "fet_bin": str(fet_bin),
        "summary": summary,
        "results": rows,
    }

    out_json = output_dir / "benchmark_results.json"
    out_json.write_text(json.dumps(result_obj, indent=2), encoding="utf-8")
    print(f"Wrote results: {out_json}")
    print(
        "Summary: "
        f"FET solved {summary['fet_solved']}/{summary['total_cases']}, "
        f"TIMEASE solved {summary['timease_solved']}/{summary['total_cases']} "
        f"(partial {summary['timease_partial']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
