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
import concurrent.futures
import json
import os
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


def _case_key(case: dict) -> str:
    return str(case.get("source_path") or case.get("id") or "")


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


def _benchmark_case(case: dict, source_dir: Path, fet_bin: Path, converted_dir: Path, timeout_seconds: int) -> dict:
    fet_path = source_dir / case["source_path"]
    converted_path = convert_fet_file(fet_path, converted_dir)
    fet_outcome = _run_fet(fet_bin, fet_path, timeout_seconds)
    timease_outcome = _run_timease(converted_path, timeout_seconds)
    return {
        "case": case,
        "fet": asdict(fet_outcome),
        "timease": asdict(timease_outcome),
        "converted_json": str(converted_path),
        "cached": False,
    }


def _compute_summary(rows: list[dict], timeout_seconds: int, *, stopped_early: bool, skipped_by_gate: int) -> dict:
    return {
        "total_cases": len(rows),
        "fet_solved": sum(1 for r in rows if r["fet"]["status"] == "solved"),
        "timease_solved": sum(1 for r in rows if r["timease"]["status"] == "solved"),
        "timease_partial": sum(1 for r in rows if r["timease"]["status"] == "partial"),
        "cached_cases": sum(1 for r in rows if bool(r.get("cached"))),
        "timeout_seconds": timeout_seconds,
        "stopped_early": stopped_early,
        "skipped_by_gate": skipped_by_gate,
    }


def _save_results(
    *,
    output_path: Path,
    manifest_path: Path,
    source_dir: Path,
    fet_bin: Path,
    timeout_seconds: int,
    rows: list[dict],
    stopped_early: bool,
    skipped_by_gate: int,
    args: argparse.Namespace,
) -> None:
    result_obj = {
        "manifest": str(manifest_path),
        "source_dir": str(source_dir),
        "fet_bin": str(fet_bin),
        "run_config": {
            "timeout_seconds": timeout_seconds,
            "workers": args.workers,
            "tiers": args.tiers,
            "limit": args.limit,
            "sample_per_tier": args.sample_per_tier,
            "resume": args.resume,
            "early_stop_window": args.early_stop_window,
            "early_stop_min_ratio": args.early_stop_min_ratio,
        },
        "summary": _compute_summary(
            rows,
            timeout_seconds,
            stopped_early=stopped_early,
            skipped_by_gate=skipped_by_gate,
        ),
        "results": rows,
    }
    output_path.write_text(json.dumps(result_obj, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run FET vs TIMEASE benchmark from manifest")
    parser.add_argument("--manifest", required=True, help="Manifest JSON path")
    parser.add_argument("--fet-bin", required=True, help="Path to fet-cl binary")
    parser.add_argument("--output-dir", required=True, help="Directory for benchmark outputs")
    parser.add_argument("--timeout-seconds", type=int, default=60, help="Per-case timeout")
    parser.add_argument("--limit", type=int, default=0, help="Optional cap on number of cases")
    parser.add_argument(
        "--tiers",
        default="small,medium,hard",
        help="Comma-separated tiers to include (small,medium,hard)",
    )
    parser.add_argument(
        "--sample-per-tier",
        type=int,
        default=0,
        help="Optional max number of cases per tier after filtering (0=all)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, (os.cpu_count() or 2) // 2),
        help="Parallel workers for per-case benchmark",
    )
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Reuse cached case results from existing benchmark_results.json",
    )
    parser.add_argument(
        "--early-stop-window",
        type=int,
        default=25,
        help="Evaluate early-stop gate after this many executed (non-cached) cases",
    )
    parser.add_argument(
        "--early-stop-min-ratio",
        type=float,
        default=0.05,
        help="Minimum TIMEASE success ratio ((solved+partial)/executed) to continue",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = _load_manifest(manifest_path)
    source_dir = Path(manifest["source_dir"])
    fet_bin = Path(args.fet_bin)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    converted_dir = output_dir / "converted_json"
    converted_dir.mkdir(parents=True, exist_ok=True)
    out_json = output_dir / "benchmark_results.json"

    selected_tiers = {
        t.strip().lower()
        for t in str(args.tiers or "").split(",")
        if t.strip()
    }
    allowed_tiers = {"small", "medium", "hard"}
    invalid_tiers = selected_tiers - allowed_tiers
    if invalid_tiers:
        raise SystemExit(f"Invalid tiers: {sorted(invalid_tiers)}")

    cases = [
        c for c in manifest.get("cases", [])
        if str(c.get("tier", "")).lower() in selected_tiers
    ]

    if args.sample_per_tier > 0:
        sampled: list[dict] = []
        for tier in ("small", "medium", "hard"):
            tier_cases = [c for c in cases if str(c.get("tier")) == tier]
            sampled.extend(tier_cases[: args.sample_per_tier])
        cases = sampled

    if args.limit > 0:
        cases = cases[: args.limit]

    cached_by_key: dict[str, dict] = {}
    if args.resume and out_json.exists():
        existing = json.loads(out_json.read_text(encoding="utf-8"))
        for row in existing.get("results", []):
            key = _case_key(row.get("case", {}))
            if key:
                cached_row = dict(row)
                cached_row["cached"] = True
                cached_by_key[key] = cached_row

    rows: list[dict] = []
    pending_cases: list[dict] = []
    for case in cases:
        key = _case_key(case)
        cached = cached_by_key.get(key)
        if cached is not None:
            rows.append(cached)
        else:
            pending_cases.append(case)

    stopped_early = False
    skipped_by_gate = 0
    executed = 0
    executed_success = 0

    def submit_next(
        *,
        pool: concurrent.futures.ThreadPoolExecutor,
        pending: list[dict],
        in_flight: dict[concurrent.futures.Future, dict],
    ) -> None:
        while pending and len(in_flight) < max(1, args.workers):
            case = pending.pop(0)
            fut = pool.submit(
                _benchmark_case,
                case,
                source_dir,
                fet_bin,
                converted_dir,
                args.timeout_seconds,
            )
            in_flight[fut] = case

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        in_flight: dict[concurrent.futures.Future, dict] = {}
        submit_next(pool=pool, pending=pending_cases, in_flight=in_flight)
        completed_count = len(rows)
        total_count = len(cases)

        while in_flight:
            done, _ = concurrent.futures.wait(
                in_flight.keys(),
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            for fut in done:
                case = in_flight.pop(fut)
                completed_count += 1
                print(f"[{completed_count}/{total_count}] {case['id']}")
                try:
                    row = fut.result()
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
                        "cached": False,
                    }
                rows.append(row)
                executed += 1
                if row["timease"]["status"] in {"solved", "partial"}:
                    executed_success += 1

            if executed >= args.early_stop_window and pending_cases:
                ratio = executed_success / max(1, executed)
                if ratio < args.early_stop_min_ratio:
                    stopped_early = True
                    skipped_by_gate = len(pending_cases)
                    pending_cases.clear()

            _save_results(
                output_path=out_json,
                manifest_path=manifest_path,
                source_dir=source_dir,
                fet_bin=fet_bin,
                timeout_seconds=args.timeout_seconds,
                rows=rows,
                stopped_early=stopped_early,
                skipped_by_gate=skipped_by_gate,
                args=args,
            )
            if not stopped_early:
                submit_next(pool=pool, pending=pending_cases, in_flight=in_flight)

    _save_results(
        output_path=out_json,
        manifest_path=manifest_path,
        source_dir=source_dir,
        fet_bin=fet_bin,
        timeout_seconds=args.timeout_seconds,
        rows=rows,
        stopped_early=stopped_early,
        skipped_by_gate=skipped_by_gate,
        args=args,
    )
    summary = _compute_summary(
        rows,
        args.timeout_seconds,
        stopped_early=stopped_early,
        skipped_by_gate=skipped_by_gate,
    )
    print(f"Wrote results: {out_json}")
    print(
        "Summary: "
        f"FET solved {summary['fet_solved']}/{summary['total_cases']}, "
        f"TIMEASE solved {summary['timease_solved']}/{summary['total_cases']} "
        f"(partial {summary['timease_partial']}), cached {summary['cached_cases']}, "
        f"early-stop={summary['stopped_early']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
