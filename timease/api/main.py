"""
TIMEASE FastAPI backend.

Wraps the engine (timease/engine/) and I/O layer (timease/io/) behind a
clean REST API.  Sessions are kept in-memory (replace with a DB in Phase 4).
"""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import dataclasses
import json
import logging
import multiprocessing
import os
import tempfile
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="TIMEASE API", version="1.0.0")
logger = logging.getLogger(__name__)


MODE_TIMEOUT_CAP_SECONDS = {"fast": 60, "balanced": 180, "complete": 360}


def _resolve_mode_timeout(
    *,
    solve_mode: str,
    requested_timeout: int,
    adaptive_timeout: int,
) -> int:
    mode = (solve_mode or "balanced").strip().lower()
    cap = MODE_TIMEOUT_CAP_SECONDS.get(mode, MODE_TIMEOUT_CAP_SECONDS["balanced"])
    base = adaptive_timeout if requested_timeout <= 0 else requested_timeout
    return min(max(base, 30), cap)


def _solver_flags_for_mode(solve_mode: str) -> tuple[bool, bool]:
    mode = (solve_mode or "balanced").strip().lower()
    if mode == "fast":
        return (False, True)  # optimize_soft_constraints, stop_at_first_solution
    return (True, False)


def _enforce_room_conflicts_for_mode(solve_mode: str) -> bool:
    mode = (solve_mode or "balanced").strip().lower()
    return mode != "fast"


_SUPPORTED_HARD_CATEGORIES: set[str] = {
    "start_time",
    "start_time_exceptions",
    "day_off",
    "max_consecutive",
    "subject_on_days",
    "subject_not_on_days",
    "subject_not_last_slot",
    "ritual_slots_blocked",
    "min_break_between",
    "fixed_assignment",
    "one_teacher_per_subject_per_class",
    "min_sessions_per_day",
    # Semantically covered elsewhere in TIMEASE pipeline.
    "teacher_no_overlap",
    "class_no_overlap",
    "teacher_subject_declared",
    "teacher_calendar_declared",
}


def _unsupported_hard_constraints(constraints: list) -> list[str]:
    errors: list[str] = []
    for c in constraints:
        if getattr(c, "type", "") != "hard":
            continue
        cat = str(getattr(c, "category", "") or "")
        if cat not in _SUPPORTED_HARD_CATEGORIES:
            cid = str(getattr(c, "id", "") or "?")
            errors.append(
                f"Contrainte dure non supportée: '{cat}' (id={cid}). "
                "Supprimez-la ou remplacez-la par une contrainte compatible."
            )
    return errors


def _new_short_id(existing_ids: set[str], length: int) -> str:
    """Generate a collision-free short id for in-memory records."""
    while True:
        value = uuid.uuid4().hex[:length]
        if value not in existing_ids:
            return value


def _allowed_origins() -> list[str]:
    origins = {"http://localhost:3000", "http://localhost:3001"}
    frontend_port = os.getenv("FRONTEND_PORT")
    if frontend_port:
        origins.add(f"http://localhost:{frontend_port}")
    return sorted(origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# ── Model normalization helpers ────────────────────────────────────────────────

def _pick(d: dict, keys: list[str]) -> dict:
    return {k: v for k, v in d.items() if k in keys}


def _norm_subject(d: dict) -> dict:
    return {
        "name":               d.get("name", ""),
        "short_name":         d.get("short_name") or d.get("name", "")[:4].upper(),
        "color":              d.get("color", "#0d9488"),
        "required_room_type": d.get("required_room_type") or d.get("room_type"),
        "needs_room":         d.get("needs_room", True),
    }


def _norm_teacher(d: dict) -> dict:
    return {
        "name":               d.get("name", ""),
        "subjects":           d.get("subjects", []),
        "max_hours_per_week": d.get("max_hours_per_week"),  # None = unlimited
        "unavailable_slots":  d.get("unavailable_slots", []),
    }


def _norm_class(d: dict) -> dict:
    return {
        "name":          d.get("name", ""),
        "level":         d.get("level") or d.get("name", ""),
        "student_count": int(d.get("student_count", 0)),
    }


def _norm_room(d: dict) -> dict:
    return {
        "name":     d.get("name", ""),
        "capacity": int(d.get("capacity", 0)),
        "types":    d.get("types", ["Standard"]),
    }


def _norm_curriculum(d: dict) -> dict:
    school_class = d.get("school_class", "")
    subject = d.get("subject", "")
    total = int(d.get("total_minutes_per_week", 60) or 60)
    # Phase 2 compatibility:
    # - drop legacy "mode", "min_session_minutes", "max_session_minutes"
    # - always provide strict manual split fields required by CurriculumEntry
    sessions = d.get("sessions_per_week")
    minutes = d.get("minutes_per_session")
    if sessions is None or minutes is None:
        # Deterministic fallback for old payloads and imported legacy data.
        # Prefer 1 session if not specified, with full weekly volume.
        sessions_i = 1
        minutes_i = max(1, total)
    else:
        sessions_i = max(1, int(sessions))
        minutes_i = max(1, int(minutes))
    total_i = sessions_i * minutes_i

    return {
        "school_class": school_class,
        "subject": subject,
        "total_minutes_per_week": max(1, total_i),
        "sessions_per_week": sessions_i,
        "minutes_per_session": minutes_i,
    }


def _norm_constraint(d: dict) -> dict:
    category_raw = d.get("category", "")
    category_aliases = {
        "one_teacher_per_subject_class": "one_teacher_per_subject_per_class",
    }
    category = category_aliases.get(category_raw, category_raw)
    category_type_map = {
        "start_time": "hard",
        "start_time_exceptions": "hard",
        "day_off": "hard",
        "max_consecutive": "hard",
        "subject_on_days": "hard",
        "subject_not_on_days": "hard",
        "subject_not_last_slot": "hard",
        "ritual_slots_blocked": "hard",
        "min_break_between": "hard",
        "fixed_assignment": "hard",
        "one_teacher_per_subject_per_class": "hard",
        "min_sessions_per_day": "hard",
        "teacher_time_preference": "soft",
        "teacher_fallback_preference": "soft",
        "balanced_daily_load": "soft",
        "subject_spread": "soft",
        "heavy_subjects_morning": "soft",
        "teacher_compact_schedule": "soft",
        "same_room_for_class": "soft",
        "teacher_day_off": "soft",
        "no_subject_back_to_back": "soft",
        "light_last_day": "soft",
    }
    normalized_type = category_type_map.get(category, d.get("type", "hard"))
    return {
        "id":             d.get("id") or str(uuid.uuid4())[:8],
        "type":           normalized_type,
        "category":       category,
        "description_fr": d.get("description_fr") or d.get("description", ""),
        "priority":       int(d.get("priority", 5)),
        "parameters":     d.get("parameters", {}),
    }


def _norm_timeslot_config(sd: dict) -> "TimeslotConfig":
    """
    Normalize timeslot configuration from API payload.

    Accepts ONLY the new nested format with DayConfig objects.
    Legacy flat format (days: list[str], sessions: list) is rejected with HTTP 400.
    """
    from timease.engine.models import (
        BreakConfig, DayConfig, SessionConfig, TimeslotConfig,
    )

    days_raw = sd.get("days", [])
    sessions_raw = sd.get("sessions")
    base_unit = int(sd.get("base_unit_minutes", 30))

    # Detect legacy flat format: days is list of strings + sessions at top level
    if days_raw and isinstance(days_raw[0], str):
        # Legacy format - reject it
        raise HTTPException(
            400,
            "Format de créneaux obsolète. Utilisez le nouveau format avec "
            "days: [{name: 'lundi', sessions: [...], breaks: [...]}, ...]. "
            "Le format plat (days: ['lundi', ...], sessions: [...]) n'est plus accepté."
        )

    # New format: days is list of DayConfig dicts
    if not days_raw:
        # Provide sensible default for empty payload
        default_sessions = [
            SessionConfig("Matin", "08:00", "12:00"),
            SessionConfig("Après-midi", "15:00", "17:00"),
        ]
        days_raw = [
            {"name": d, "sessions": [{"name": s.name, "start_time": s.start_time, "end_time": s.end_time} for s in default_sessions], "breaks": []}
            for d in ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"]
        ]

    day_configs = []
    for day_dict in days_raw:
        if not isinstance(day_dict, dict):
            raise HTTPException(400, f"Jour invalide: {day_dict}. Attendu un objet DayConfig.")

        name = day_dict.get("name", "")
        if not name:
            raise HTTPException(400, "Chaque jour doit avoir un nom.")

        sessions = [
            SessionConfig(
                name=s.get("name", ""),
                start_time=s.get("start_time", ""),
                end_time=s.get("end_time", ""),
            )
            for s in day_dict.get("sessions", [])
        ]

        breaks = [
            BreakConfig(
                name=b.get("name", ""),
                start_time=b.get("start_time", ""),
                end_time=b.get("end_time", ""),
            )
            for b in day_dict.get("breaks", [])
        ]

        day_configs.append(DayConfig(name=name, sessions=sessions, breaks=breaks))

    return TimeslotConfig(days=day_configs, base_unit_minutes=base_unit)


# ── In-memory session store ────────────────────────────────────────────────────

sessions: dict[str, dict] = {}
job_runtime_handles: dict[str, dict] = {}


class SessionData(BaseModel):
    school_data: dict = {}
    teacher_assignments: list[dict] = []
    timetable_result: dict = {}
    last_conflict_reports: list[dict] = []
    last_solve_issues: dict = {}
    snapshots: list[dict] = []
    jobs: list[dict] = []


def _build_job_report(
    *,
    outcome: str,
    reason_code: str,
    reason_message: str,
    summary: str,
    diagnostics: dict | None = None,
) -> dict:
    return {
        "outcome": outcome,
        "reason_code": reason_code,
        "reason_message": reason_message,
        "summary": summary,
        "diagnostics": diagnostics or {},
    }


def _report_from_worker_payload(payload: dict, job: dict) -> dict:
    status = str(payload.get("status", "")).strip().upper()
    conflict_summary = str(payload.get("conflict_summary", "") or "").strip()
    diagnostics = {
        "request_id": job.get("request_id"),
        "mode": job.get("mode"),
        "effective_timeout_seconds": job.get("effective_timeout_seconds"),
        "solve_time_seconds": payload.get("solve_time"),
    }

    if status == "OPTIMAL":
        return _build_job_report(
            outcome="success",
            reason_code="SOLVED",
            reason_message="Emploi du temps généré avec succès.",
            summary="Génération complète réussie.",
            diagnostics=diagnostics,
        )
    if status == "PARTIAL":
        return _build_job_report(
            outcome="partial",
            reason_code="PARTIAL_SOLUTION",
            reason_message="Solution partielle générée.",
            summary=conflict_summary or "La génération est partielle.",
            diagnostics=diagnostics,
        )
    if status == "TIMEOUT":
        return _build_job_report(
            outcome="failed",
            reason_code="TIMEOUT",
            reason_message="Limite de calcul atteinte avant de trouver une solution.",
            summary=conflict_summary or "Temps limite atteint.",
            diagnostics=diagnostics,
        )
    if status == "INFEASIBLE":
        return _build_job_report(
            outcome="failed",
            reason_code="INFEASIBLE",
            reason_message="Aucune solution compatible avec les contraintes actuelles.",
            summary=conflict_summary or "Aucune solution trouvée.",
            diagnostics=diagnostics,
        )
    if status == "ERROR":
        errors = payload.get("errors", [])
        details = ""
        if isinstance(errors, list) and errors:
            details = str(errors[0])
        return _build_job_report(
            outcome="failed",
            reason_code="WORKER_ERROR",
            reason_message="Erreur interne pendant la génération.",
            summary=details or conflict_summary or "Le worker a rencontré une erreur.",
            diagnostics=diagnostics,
        )
    return _build_job_report(
        outcome="failed",
        reason_code="UNKNOWN_RESULT",
        reason_message="Résultat du worker non reconnu.",
        summary=conflict_summary or "État final non reconnu.",
        diagnostics=diagnostics,
    )


# ── Data merge helpers ────────────────────────────────────────────────────────

def _upsert(existing: list, new_items: list, key: str) -> list:
    """Upsert new_items into existing by a single string key field."""
    index = {item[key]: i for i, item in enumerate(existing) if key in item}
    result = list(existing)
    for item in new_items:
        k = item.get(key)
        if k and k in index:
            result[index[k]] = item          # replace existing entry
        else:
            result.append(item)              # new entry
            if k:
                index[k] = len(result) - 1
    return result


def _upsert_composite(existing: list, new_items: list, keys: list[str]) -> list:
    """Upsert new_items into existing by a composite key (tuple of fields)."""
    def mk(item: dict) -> tuple:
        return tuple(item.get(k, "") for k in keys)
    index = {mk(item): i for i, item in enumerate(existing)}
    result = list(existing)
    for item in new_items:
        k = mk(item)
        if k in index:
            result[index[k]] = item
        else:
            result.append(item)
            index[k] = len(result) - 1
    return result


def _estimate_solve_complexity(school_data: dict, teacher_assignments: list[dict]) -> dict:
    """Return a lightweight solve complexity estimate and suggested timeout."""
    classes = school_data.get("classes", []) or []
    curriculum = school_data.get("curriculum", []) or []
    constraints = school_data.get("constraints", []) or []
    days = school_data.get("days", []) or []
    rooms = school_data.get("rooms", []) or []
    teachers = school_data.get("teachers", []) or []

    sessions_total = 0
    for row in curriculum:
        sessions = int(row.get("sessions_per_week", 1) or 1)
        sessions_total += max(1, sessions)

    n_days = max(1, len(days))
    n_hard = sum(1 for c in constraints if _norm_constraint(c).get("type") == "hard")
    n_soft = max(0, len(constraints) - n_hard)

    assign_pairs = {
        (a.get("school_class", ""), a.get("subject", ""))
        for a in teacher_assignments
    }
    curriculum_pairs = {
        (c.get("school_class", ""), c.get("subject", ""))
        for c in curriculum
    }
    assignment_coverage = 0.0
    if curriculum_pairs:
        assignment_coverage = len(assign_pairs & curriculum_pairs) / len(curriculum_pairs)

    room_pressure = 1.0
    has_rooms = len(rooms) > 0
    if classes and has_rooms:
        room_pressure = len(rooms) / len(classes)
    room_penalty = max(0.0, (1.0 - room_pressure) * 12.0) if has_rooms else 0.0

    score = (
        sessions_total * 1.2
        + len(classes) * 2.0
        + len(curriculum) * 0.9
        + n_hard * 2.5
        + n_soft * 0.8
        + n_days * 1.5
        + max(0, (len(classes) - len(teachers)) * 1.0)
        + room_penalty
        + max(0, (1.0 - assignment_coverage) * 10.0)
    )

    if score < 95:
        tier = "fast"
        label = "Rapide"
        suggested_timeout_seconds = 60
        predicted_seconds = "10-30 s"
    elif score < 190:
        tier = "medium"
        label = "Moyen"
        suggested_timeout_seconds = 120
        predicted_seconds = "30-90 s"
    else:
        tier = "long"
        label = "Long"
        suggested_timeout_seconds = 240
        predicted_seconds = "90-240 s"

    factors: list[str] = []
    if sessions_total >= 120:
        factors.append("beaucoup de sessions hebdomadaires à placer")
    if n_hard >= 8:
        factors.append("volume important de contraintes dures")
    if not has_rooms:
        factors.append("aucune salle définie (ne bloque pas si les matières n'en exigent pas)")
    elif room_pressure < 0.8:
        factors.append("pression sur les salles")
    if assignment_coverage < 0.9:
        factors.append("affectations enseignant/matière incomplètes")
    if not factors:
        factors.append("complexité standard")

    return {
        "tier": tier,
        "label": label,
        "score": round(score, 1),
        "predicted_seconds": predicted_seconds,
        "suggested_timeout_seconds": suggested_timeout_seconds,
        "factors": factors,
        "inputs": {
            "classes": len(classes),
            "teachers": len(teachers),
            "rooms": len(rooms),
            "curriculum_entries": len(curriculum),
            "sessions_total": sessions_total,
            "hard_constraints": n_hard,
            "soft_constraints": n_soft,
            "days": len(days),
            "assignment_coverage": round(assignment_coverage, 2),
        },
    }


# ── Session management ─────────────────────────────────────────────────────────

@app.post("/api/session")
def create_session():
    sid = uuid.uuid4().hex[:12]
    sessions[sid] = SessionData().model_dump()
    return {"session_id": sid}


@app.get("/api/session/{sid}")
def get_session(sid: str):
    if sid not in sessions:
        raise HTTPException(404, "Session not found")
    _poll_jobs(sid)
    return sessions[sid]


@app.post("/api/session/{sid}/restore")
def restore_session(sid: str, payload: dict):
    """Re-hydrate a session from localStorage data (survives backend restart)."""
    if sid not in sessions:
        sessions[sid] = SessionData().model_dump()
    if "school_data" in payload:
        sessions[sid]["school_data"] = payload["school_data"]
    if "teacher_assignments" in payload:
        sessions[sid]["teacher_assignments"] = payload["teacher_assignments"]
    if "timetable_result" in payload:
        sessions[sid]["timetable_result"] = payload["timetable_result"]
    if "last_conflict_reports" in payload:
        sessions[sid]["last_conflict_reports"] = payload["last_conflict_reports"]
    sessions[sid].setdefault("snapshots", [])
    sessions[sid].setdefault("jobs", [])
    return {"ok": True}


@app.put("/api/session/{sid}/school_data")
def put_school_data(sid: str, payload: dict):
    """Replace the entire school_data for direct edits from the UI."""
    if sid not in sessions:
        raise HTTPException(404, "Session not found")
    sessions[sid]["school_data"] = payload
    return {"ok": True}


@app.put("/api/session/{sid}/assignments")
def put_assignments(sid: str, payload: dict):
    """Replace the teacher_assignments list."""
    if sid not in sessions:
        raise HTTPException(404, "Session not found")
    sessions[sid]["teacher_assignments"] = payload.get("assignments", [])
    return {"ok": True}


def _next_snapshot_name(existing: list[dict], school_data: dict) -> str:
    school_name = str(school_data.get("name", "") or "").strip() or "École"
    prefix = f"{school_name} v"
    version_numbers: list[int] = []
    for snap in existing:
        name = str(snap.get("name", "") or "")
        if not name.startswith(prefix):
            continue
        suffix = name[len(prefix):].strip()
        if suffix.isdigit():
            version_numbers.append(int(suffix))
    next_num = (max(version_numbers) + 1) if version_numbers else 1
    return f"{school_name} v{next_num}"


@app.post("/api/session/{sid}/snapshots")
def create_snapshot(sid: str, payload: dict = {}):
    if sid not in sessions:
        raise HTTPException(404, "Session not found")
    snapshots = sessions[sid].setdefault("snapshots", [])
    existing_snapshot_ids = {str(s.get("id", "")) for s in snapshots}
    snap_id = _new_short_id(existing_snapshot_ids, 8)
    school_data = payload.get("school_data", sessions[sid].get("school_data", {}))
    name = str(payload.get("name", "") or "").strip() or _next_snapshot_name(snapshots, school_data)
    snapshot = {
        "id": snap_id,
        "name": name,
        "created_at": time.time(),
        "school_data": school_data,
        "teacher_assignments": payload.get("teacher_assignments", sessions[sid].get("teacher_assignments", [])),
    }
    snapshots.append(snapshot)
    return {"snapshot": snapshot}


@app.get("/api/session/{sid}/snapshots")
def list_snapshots(sid: str):
    if sid not in sessions:
        raise HTTPException(404, "Session not found")
    return {"snapshots": sessions[sid].get("snapshots", [])}


@app.patch("/api/session/{sid}/snapshots/{snapshot_id}")
def rename_snapshot(sid: str, snapshot_id: str, payload: dict = {}):
    if sid not in sessions:
        raise HTTPException(404, "Session not found")
    new_name = str(payload.get("name", "") or "").strip()
    if not new_name:
        raise HTTPException(400, "Le nom de la version est requis.")
    snapshots = sessions[sid].setdefault("snapshots", [])
    snapshot = next((s for s in snapshots if s.get("id") == snapshot_id), None)
    if snapshot is None:
        raise HTTPException(404, "Snapshot not found")
    snapshot["name"] = new_name
    return {"snapshot": snapshot}


@app.post("/api/session/{sid}/snapshots/{snapshot_id}/duplicate")
def duplicate_snapshot(sid: str, snapshot_id: str):
    if sid not in sessions:
        raise HTTPException(404, "Session not found")
    snapshots = sessions[sid].setdefault("snapshots", [])
    source = next((s for s in snapshots if s.get("id") == snapshot_id), None)
    if source is None:
        raise HTTPException(404, "Snapshot not found")
    existing_snapshot_ids = {str(s.get("id", "")) for s in snapshots}
    clone = {
        "id": _new_short_id(existing_snapshot_ids, 8),
        "name": f"{source.get('name', 'Version')} (copie)",
        "created_at": time.time(),
        "school_data": json.loads(json.dumps(source.get("school_data", {}))),
        "teacher_assignments": json.loads(json.dumps(source.get("teacher_assignments", []))),
    }
    snapshots.append(clone)
    return {"snapshot": clone}


@app.delete("/api/session/{sid}/snapshots/{snapshot_id}")
def delete_snapshot(sid: str, snapshot_id: str):
    if sid not in sessions:
        raise HTTPException(404, "Session not found")
    _poll_jobs(sid)
    snapshots = sessions[sid].setdefault("snapshots", [])
    jobs = sessions[sid].setdefault("jobs", [])

    snap_idx = next((i for i, s in enumerate(snapshots) if s.get("id") == snapshot_id), None)
    if snap_idx is None:
        raise HTTPException(404, "Snapshot not found")

    blocking_job = next(
        (
            j for j in jobs
            if j.get("snapshot_id") == snapshot_id
            and j.get("status") in {"running", "queued"}
        ),
        None,
    )
    if blocking_job is not None:
        raise HTTPException(
            409,
            "La version est utilisée par un job en cours. Arrêtez le job avant suppression.",
        )

    snapshots.pop(snap_idx)
    kept_jobs = [j for j in jobs if j.get("snapshot_id") != snapshot_id]
    removed_count = len(jobs) - len(kept_jobs)
    sessions[sid]["jobs"] = kept_jobs

    for job in jobs:
        if job.get("snapshot_id") == snapshot_id:
            job_runtime_handles.pop(str(job.get("id", "")), None)

    return {"ok": True, "deleted_jobs": removed_count}


@app.post("/api/session/{sid}/jobs")
def create_job(sid: str, payload: dict):
    if sid not in sessions:
        raise HTTPException(404, "Session not found")
    _poll_jobs(sid)
    snapshots = sessions[sid].setdefault("snapshots", [])
    jobs = sessions[sid].setdefault("jobs", [])
    snapshot_id = str(payload.get("snapshot_id", "") or "")
    snapshot = next((s for s in snapshots if s.get("id") == snapshot_id), None)
    if snapshot is None:
        raise HTTPException(404, "Snapshot not found")

    requested_timeout = int(payload.get("timeout", 0))
    solve_mode = str(payload.get("mode", "balanced") or "balanced").strip().lower()
    request_id = str(payload.get("request_id", "") or "").strip()
    estimate = _estimate_solve_complexity(snapshot.get("school_data", {}), snapshot.get("teacher_assignments", []))
    adaptive_timeout = int(estimate.get("suggested_timeout_seconds", 120))
    effective_timeout = _resolve_mode_timeout(
        solve_mode=solve_mode,
        requested_timeout=requested_timeout,
        adaptive_timeout=adaptive_timeout,
    )
    optimize_soft_constraints, stop_at_first_solution = _solver_flags_for_mode(solve_mode)

    existing_job_ids = {str(j.get("id", "")) for j in jobs}
    job_id = _new_short_id(existing_job_ids, 10)
    now = time.time()
    job = {
        "id": job_id,
        "snapshot_id": snapshot_id,
        "status": "running",
        "mode": solve_mode,
        "request_id": request_id,
        "requested_timeout_seconds": requested_timeout,
        "adaptive_timeout_seconds": adaptive_timeout,
        "effective_timeout_seconds": effective_timeout,
        "optimize_soft_constraints": optimize_soft_constraints,
        "stop_at_first_solution": stop_at_first_solution,
        "created_at": now,
        "started_at": now,
        "finished_at": None,
        "estimate": estimate,
        "result": None,
        "report": None,
    }
    jobs.append(job)

    out_q: multiprocessing.Queue = multiprocessing.Queue()
    proc = multiprocessing.Process(
        target=_run_solver_worker,
        args=({
            "school_data": snapshot.get("school_data", {}),
            "teacher_assignments": snapshot.get("teacher_assignments", []),
            "solve_mode": solve_mode,
            "requested_timeout_seconds": requested_timeout,
            "adaptive_timeout_seconds": adaptive_timeout,
            "effective_timeout_seconds": effective_timeout,
            "optimize_soft_constraints": optimize_soft_constraints,
            "stop_at_first_solution": stop_at_first_solution,
        }, out_q),
        daemon=True,
    )
    proc.start()
    job_runtime_handles[job_id] = {"process": proc, "queue": out_q, "sid": sid}
    return {"job": job}


@app.get("/api/session/{sid}/jobs")
def list_jobs(sid: str):
    if sid not in sessions:
        raise HTTPException(404, "Session not found")
    _poll_jobs(sid)
    return {"jobs": sessions[sid].get("jobs", [])}


@app.get("/api/session/{sid}/jobs/{job_id}")
def get_job(sid: str, job_id: str):
    if sid not in sessions:
        raise HTTPException(404, "Session not found")
    _poll_jobs(sid)
    job = next((j for j in sessions[sid].get("jobs", []) if j.get("id") == job_id), None)
    if job is None:
        raise HTTPException(404, "Job not found")
    return {"job": job}


@app.post("/api/session/{sid}/jobs/{job_id}/cancel")
def cancel_job(sid: str, job_id: str):
    if sid not in sessions:
        raise HTTPException(404, "Session not found")
    job = next((j for j in sessions[sid].get("jobs", []) if j.get("id") == job_id), None)
    if job is None:
        raise HTTPException(404, "Job not found")
    if job.get("status") not in {"running", "queued"}:
        return {"ok": True, "job": job}
    handle = job_runtime_handles.get(job_id)
    if handle and handle.get("process") is not None:
        proc = handle["process"]
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=1)
    job_runtime_handles.pop(job_id, None)
    job["status"] = "cancelled"
    job["finished_at"] = time.time()
    job["result"] = {
        "status": "CANCELLED",
        "solved": False,
        "conflict_summary": "Génération arrêtée par l'utilisateur.",
    }
    job["report"] = _build_job_report(
        outcome="failed",
        reason_code="CANCELLED_BY_USER",
        reason_message="Génération arrêtée par l'utilisateur.",
        summary="Le job a été annulé manuellement.",
        diagnostics={
            "request_id": job.get("request_id"),
            "mode": job.get("mode"),
            "effective_timeout_seconds": job.get("effective_timeout_seconds"),
        },
    )
    return {"ok": True, "job": job}


@app.delete("/api/session/{sid}/jobs/{job_id}")
def delete_job(sid: str, job_id: str):
    if sid not in sessions:
        raise HTTPException(404, "Session not found")
    _poll_jobs(sid)
    jobs = sessions[sid].get("jobs", [])
    idx = next((i for i, j in enumerate(jobs) if j.get("id") == job_id), None)
    if idx is None:
        raise HTTPException(404, "Job not found")
    job = jobs[idx]
    if job.get("status") in {"running", "queued"}:
        raise HTTPException(409, "Le job est en cours. Arrêtez-le avant suppression.")
    jobs.pop(idx)
    job_runtime_handles.pop(job_id, None)
    return {"ok": True}


@app.get("/api/session/{sid}/solve-estimate")
def solve_estimate(sid: str):
    if sid not in sessions:
        raise HTTPException(404, "Session not found")
    sd = sessions[sid]["school_data"]
    ta = sessions[sid]["teacher_assignments"]
    return _estimate_solve_complexity(sd, ta)

# ── File upload ────────────────────────────────────────────────────────────────

@app.post("/api/session/{sid}/upload")
async def upload_file(sid: str, file: UploadFile = File(...)):
    if sid not in sessions:
        raise HTTPException(404, "Session not found")

    suffix = Path(file.filename or "").suffix.lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    if suffix == ".xlsx":
        try:
            from timease.io.excel_import import read_template
            school_data_obj, errors = read_template(tmp_path)
            if school_data_obj and not errors:
                sd_dict = dataclasses.asdict(school_data_obj)
                sessions[sid]["school_data"] = sd_dict
                sessions[sid]["teacher_assignments"] = [
                    {"teacher": ta.teacher, "subject": ta.subject, "school_class": ta.school_class}
                    for ta in school_data_obj.teacher_assignments
                ]
                os.unlink(tmp_path)
                return {
                    "type":        "direct_import",
                    "success":     True,
                    "school_data": sessions[sid]["school_data"],
                    "teacher_assignments": sessions[sid]["teacher_assignments"],
                }
        except Exception:
            pass

    from timease.io.file_parser import extract_content
    text, ftype = extract_content(tmp_path)
    os.unlink(tmp_path)
    return {"type": "text_extract", "content": text, "file_type": ftype}


# ── Solve ──────────────────────────────────────────────────────────────────────

def _format_conflicts_fr(reports: list) -> str:
    """Format ConflictReport list as French markdown for the AI chat."""
    lines: list[str] = []
    for r in reports:
        lines.append(f"**{r.description_fr}**")
        for opt in r.fix_options[:2]:
            lines.append(f"→ {opt.fix_fr}")
        lines.append("")
    return "\n".join(lines).strip()


def _group_unscheduled(unscheduled: list[dict]) -> list[dict]:
    """Group unscheduled sessions by inferred cause category."""
    from collections import defaultdict
    groups: dict[str, list[dict]] = defaultdict(list)
    for u in unscheduled:
        reason = u.get("reason", "").lower()
        if "enseignant" in reason or "teacher" in reason or "qualification" in reason:
            cat = "missing_teacher"
        elif "salle" in reason or "room" in reason or "capacité" in reason:
            cat = "room_unavailable"
        elif "créneau" in reason or "slot" in reason or "domaine" in reason or "domain" in reason:
            cat = "no_valid_slot"
        elif "contrainte" in reason or "constraint" in reason:
            cat = "constraint_conflict"
        else:
            cat = "other"
        groups[cat].append(u)

    label_map = {
        "missing_teacher":   "Enseignant manquant ou non qualifié",
        "room_unavailable":  "Salle indisponible ou trop petite",
        "no_valid_slot":     "Aucun créneau disponible",
        "constraint_conflict": "Conflit de contraintes",
        "other":             "Autres",
    }
    return [
        {"cause": cat, "label": label_map.get(cat, cat), "sessions": items}
        for cat, items in groups.items()
    ]


def _run_solver_worker(payload: dict, out_q: "multiprocessing.Queue") -> None:
    """
    Isolated worker process for long solve jobs.
    Returns a JSON-serializable payload through out_q.
    """
    try:
        from timease.engine.models import (
            Constraint, CurriculumEntry, Room, School, SchoolClass,
            SchoolData, Subject, Teacher, TeacherAssignment,
        )
        from timease.engine.solver import TimetableSolver
        from timease.utils.teacher_colors import teacher_color_map

        sd = payload["school_data"]
        ta = payload["teacher_assignments"]
        timeout = int(payload["effective_timeout_seconds"])
        optimize_soft_constraints = bool(payload.get("optimize_soft_constraints", True))
        stop_at_first_solution = bool(payload.get("stop_at_first_solution", False))
        enforce_room_conflicts = bool(payload.get("enforce_room_conflicts", True))

        school_obj = SchoolData(
            school=School(
                name=sd.get("name", ""),
                academic_year=sd.get("academic_year", ""),
                city=sd.get("city", ""),
            ),
            timeslot_config=_norm_timeslot_config(sd),
            subjects=[Subject(**_norm_subject(s)) for s in sd.get("subjects", [])],
            teachers=[Teacher(**_norm_teacher(t)) for t in sd.get("teachers", [])],
            classes=[SchoolClass(**_norm_class(c)) for c in sd.get("classes", [])],
            rooms=[Room(**_norm_room(r)) for r in sd.get("rooms", [])],
            curriculum=[CurriculumEntry(**_norm_curriculum(e)) for e in sd.get("curriculum", [])],
            constraints=[Constraint(**_norm_constraint(c)) for c in sd.get("constraints", [])],
            teacher_assignments=[
                TeacherAssignment(**_pick(a, ["teacher", "subject", "school_class"]))
                for a in ta
            ],
        )

        validation_errors = school_obj.validate()
        validation_errors.extend(_unsupported_hard_constraints(school_obj.constraints))
        if validation_errors:
            summary = "**Erreurs de validation :**\n" + "\n".join(f"- {e}" for e in validation_errors)
            out_q.put({
                "status": "INFEASIBLE",
                "solved": False,
                "conflict_summary": summary,
                "errors": validation_errors,
            })
            return

        wall_start = time.perf_counter()
        result = TimetableSolver().solve(
            school_obj,
            timeout_seconds=timeout,
            optimize_soft_constraints=optimize_soft_constraints,
            stop_at_first_solution=stop_at_first_solution,
            enforce_room_conflicts=enforce_room_conflicts,
        )
        api_wall_time = round(time.perf_counter() - wall_start, 3)

        if result.solved or result.partial:
            teacher_colors = teacher_color_map([t.name for t in school_obj.teachers])
            unscheduled_grouped = _group_unscheduled(result.unscheduled_sessions)
            status = "OPTIMAL" if result.solved and not result.partial else "PARTIAL"
            out_q.put({
                "status": status,
                "solved": True,
                "assignments": [
                    {
                        "school_class": a.school_class,
                        "subject": a.subject,
                        "teacher": a.teacher,
                        "room": a.room or "",
                        "day": a.day,
                        "start_time": a.start_time,
                        "end_time": a.end_time,
                        "color": teacher_colors.get(a.teacher, "#0d9488"),
                    }
                    for a in result.assignments
                ],
                "solve_time": result.solve_time_seconds,
                "days": [d.name for d in school_obj.timeslot_config.days],
                "soft_results": result.soft_constraint_details,
                "warnings": result.warnings,
                "unscheduled": result.unscheduled_sessions,
                "unscheduled_groups": unscheduled_grouped,
                "diagnostics": {
                    "mode": payload.get("solve_mode", "balanced"),
                    "requested_timeout_seconds": payload.get("requested_timeout_seconds", 0),
                    "adaptive_timeout_seconds": payload.get("adaptive_timeout_seconds", timeout),
                    "effective_timeout_seconds": timeout,
                    "optimize_soft_constraints": optimize_soft_constraints,
                    "stop_at_first_solution": stop_at_first_solution,
                    "enforce_room_conflicts": enforce_room_conflicts,
                    "room_fallback_retry_used": False,
                    "api_wall_time_seconds": api_wall_time,
                },
            })
            return

        raw_reasons = [
            str(c.get("reason", "")).upper()
            for c in (result.conflicts or [])
            if isinstance(c, dict)
        ]
        if any("UNKNOWN" in r for r in raw_reasons):
            out_q.put({
                "status": "TIMEOUT",
                "solved": False,
                "solve_time": result.solve_time_seconds,
                "warnings": result.warnings,
                "conflict_summary": (
                    "Limite de calcul atteinte avant de trouver une solution. "
                    "Essayez de simplifier certaines contraintes dures ou de relancer."
                ),
                "diagnostics": {
                    "mode": payload.get("solve_mode", "balanced"),
                    "requested_timeout_seconds": payload.get("requested_timeout_seconds", 0),
                    "adaptive_timeout_seconds": payload.get("adaptive_timeout_seconds", timeout),
                    "effective_timeout_seconds": timeout,
                    "optimize_soft_constraints": optimize_soft_constraints,
                    "stop_at_first_solution": stop_at_first_solution,
                    "enforce_room_conflicts": enforce_room_conflicts,
                    "room_fallback_retry_used": False,
                    "api_wall_time_seconds": api_wall_time,
                },
            })
            return

        out_q.put({
            "status": "INFEASIBLE",
            "solved": False,
            "conflict_summary": "Aucune solution trouvée avec les données actuelles.",
            "diagnostics": {
                "mode": payload.get("solve_mode", "balanced"),
                "requested_timeout_seconds": payload.get("requested_timeout_seconds", 0),
                "adaptive_timeout_seconds": payload.get("adaptive_timeout_seconds", timeout),
                "effective_timeout_seconds": timeout,
                "optimize_soft_constraints": optimize_soft_constraints,
                "stop_at_first_solution": stop_at_first_solution,
                "enforce_room_conflicts": enforce_room_conflicts,
                "room_fallback_retry_used": False,
                "api_wall_time_seconds": api_wall_time,
            },
        })
    except Exception as exc:
        out_q.put({
            "status": "ERROR",
            "solved": False,
            "errors": [str(exc)],
            "conflict_summary": str(exc),
        })


def _poll_jobs(sid: str) -> None:
    if sid not in sessions:
        return
    now = time.time()
    jobs = sessions[sid].setdefault("jobs", [])
    for job in jobs:
        if job.get("status") not in {"running", "queued"}:
            continue
        handle = job_runtime_handles.get(job["id"])
        if not handle:
            continue
        proc = handle.get("process")
        out_q = handle.get("queue")
        if proc is None or out_q is None:
            continue
        if proc.is_alive():
            continue
        payload = None
        try:
            if not out_q.empty():
                payload = out_q.get_nowait()
        except Exception:
            payload = None

        if payload is None:
            job["status"] = "failed"
            job["report"] = _build_job_report(
                outcome="failed",
                reason_code="WORKER_NO_RESULT",
                reason_message="Le solveur s'est arrêté sans résultat.",
                summary="Le processus de génération s'est terminé sans renvoyer de rapport.",
                diagnostics={
                    "request_id": job.get("request_id"),
                    "mode": job.get("mode"),
                    "effective_timeout_seconds": job.get("effective_timeout_seconds"),
                },
            )
            job["finished_at"] = now
            job_runtime_handles.pop(job["id"], None)
            continue

        job["status"] = str(payload.get("status", "failed")).lower()
        if job["status"] == "optimal":
            job["status"] = "done"
        elif job["status"] == "partial":
            job["status"] = "done"
        elif job["status"] == "timeout":
            job["status"] = "timeout"
        elif job["status"] == "infeasible":
            job["status"] = "failed"
        elif job["status"] == "error":
            job["status"] = "failed"
        job["result"] = payload
        job["report"] = _report_from_worker_payload(payload, job)
        job["finished_at"] = now
        job_runtime_handles.pop(job["id"], None)

        if payload.get("solved"):
            sessions[sid]["timetable_result"] = payload
            sessions[sid]["last_conflict_reports"] = []


@app.post("/api/session/{sid}/solve")
def solve(sid: str, payload: dict = {}):
    if sid not in sessions:
        raise HTTPException(404, "Session not found")

    requested_timeout = int(payload.get("timeout", 0))
    solve_mode = str(payload.get("mode", "balanced") or "balanced").strip().lower()
    request_id = str(payload.get("request_id", "") or "").strip()
    sd      = sessions[sid]["school_data"]
    ta      = sessions[sid]["teacher_assignments"]

    from timease.engine.models import (
        Constraint, CurriculumEntry, Room, School, SchoolClass,
        SchoolData, SessionConfig, Subject, Teacher, TeacherAssignment, TimeslotConfig,
    )
    from timease.engine.solver import TimetableSolver

    try:
        school_obj = SchoolData(
            school=School(
                name=sd.get("name", ""),
                academic_year=sd.get("academic_year", ""),
                city=sd.get("city", ""),
            ),
            timeslot_config=_norm_timeslot_config(sd),
            subjects=[Subject(**_norm_subject(s)) for s in sd.get("subjects", [])],
            teachers=[Teacher(**_norm_teacher(t)) for t in sd.get("teachers", [])],
            classes=[SchoolClass(**_norm_class(c)) for c in sd.get("classes", [])],
            rooms=[Room(**_norm_room(r)) for r in sd.get("rooms", [])],
            curriculum=[CurriculumEntry(**_norm_curriculum(e)) for e in sd.get("curriculum", [])],
            constraints=[Constraint(**_norm_constraint(c)) for c in sd.get("constraints", [])],
            teacher_assignments=[
                TeacherAssignment(**_pick(a, ["teacher", "subject", "school_class"]))
                for a in ta
            ],
        )

        validation_errors = school_obj.validate()
        validation_errors.extend(_unsupported_hard_constraints(school_obj.constraints))
        if validation_errors:
            conflict_summary = "**Erreurs de validation :**\n" + "\n".join(
                f"- {e}" for e in validation_errors
            )
            return {"status": "INFEASIBLE", "solved": False, "conflict_summary": conflict_summary, "errors": validation_errors}

        estimate = _estimate_solve_complexity(sd, ta)
        adaptive_timeout = int(estimate.get("suggested_timeout_seconds", 120))
        effective_timeout = _resolve_mode_timeout(
            solve_mode=solve_mode,
            requested_timeout=requested_timeout,
            adaptive_timeout=adaptive_timeout,
        )
        optimize_soft_constraints, stop_at_first_solution = _solver_flags_for_mode(solve_mode)
        enforce_room_conflicts = _enforce_room_conflicts_for_mode(solve_mode)
        wall_start = time.perf_counter()
        logger.info(
            "Solve request started sid=%s request_id=%s mode=%s requested_timeout=%s adaptive_timeout=%s effective_timeout=%s optimize_soft=%s first_solution=%s",
            sid,
            request_id or "-",
            solve_mode,
            requested_timeout,
            adaptive_timeout,
            effective_timeout,
            optimize_soft_constraints,
            stop_at_first_solution,
        )
        result = TimetableSolver().solve(
            school_obj,
            timeout_seconds=effective_timeout,
            optimize_soft_constraints=optimize_soft_constraints,
            stop_at_first_solution=stop_at_first_solution,
            enforce_room_conflicts=enforce_room_conflicts,
        )
        api_wall_time = round(time.perf_counter() - wall_start, 3)
        logger.info(
            "Solve request finished sid=%s request_id=%s solved=%s partial=%s solve_time=%s api_wall=%s",
            sid,
            request_id or "-",
            result.solved,
            result.partial,
            result.solve_time_seconds,
            api_wall_time,
        )

        if result.solved or result.partial:
            from timease.utils.teacher_colors import teacher_color_map
            teacher_colors = teacher_color_map([t.name for t in school_obj.teachers])
            unscheduled_grouped = _group_unscheduled(result.unscheduled_sessions)
            timetable = {
                "assignments": [
                    {
                        "school_class": a.school_class,
                        "subject":      a.subject,
                        "teacher":      a.teacher,
                        "room":         a.room or "",
                        "day":          a.day,
                        "start_time":   a.start_time,
                        "end_time":     a.end_time,
                        "color":        teacher_colors.get(a.teacher, "#0d9488"),
                    }
                    for a in result.assignments
                ],
                "solve_time":    result.solve_time_seconds,
                "days":          [d.name for d in school_obj.timeslot_config.days],
                "soft_results":  result.soft_constraint_details,
                "warnings":      result.warnings,
                "unscheduled":   result.unscheduled_sessions,
                "unscheduled_groups": unscheduled_grouped,
                "diagnostics": {
                    "request_id": request_id,
                    "mode": solve_mode,
                    "requested_timeout_seconds": requested_timeout,
                    "adaptive_timeout_seconds": adaptive_timeout,
                    "effective_timeout_seconds": effective_timeout,
                    "optimize_soft_constraints": optimize_soft_constraints,
                    "stop_at_first_solution": stop_at_first_solution,
                    "enforce_room_conflicts": enforce_room_conflicts,
                    "room_fallback_retry_used": False,
                    "api_wall_time_seconds": api_wall_time,
                },
            }
            sessions[sid]["timetable_result"] = timetable
            sessions[sid]["last_conflict_reports"] = []
            status = "OPTIMAL" if result.solved and not result.partial else "PARTIAL"
            if status == "PARTIAL":
                sessions[sid]["last_solve_issues"] = {
                    "total_assigned":    len(result.assignments),
                    "total_unscheduled": len(result.unscheduled_sessions),
                    "unscheduled":       [u for u in result.unscheduled_sessions if u.get("subject")],
                    "groups":            unscheduled_grouped,
                }
            else:
                sessions[sid]["last_solve_issues"] = {}
            return {"status": status, "solved": True, **timetable}

        # Timeout (UNKNOWN) — explicit status and guidance
        raw_reasons = [
            str(c.get("reason", "")).upper()
            for c in (result.conflicts or [])
            if isinstance(c, dict)
        ]
        is_timeout = (
            any("UNKNOWN" in r for r in raw_reasons)
            and result.solve_time_seconds >= max(1, effective_timeout - 2)
        )
        if is_timeout:
            summary = (
                "Limite de calcul atteinte avant de trouver une solution. "
                "Essayez de simplifier certaines contraintes dures ou de relancer."
            )
            return {
                "status": "TIMEOUT",
                "solved": False,
                "solve_time": result.solve_time_seconds,
                "request_id": request_id,
                "mode": solve_mode,
                "requested_timeout_seconds": requested_timeout,
                "adaptive_timeout_seconds": adaptive_timeout,
                "effective_timeout_seconds": effective_timeout,
                "optimize_soft_constraints": optimize_soft_constraints,
                "stop_at_first_solution": stop_at_first_solution,
                "enforce_room_conflicts": enforce_room_conflicts,
                "room_fallback_retry_used": False,
                "conflict_summary": summary,
                "warnings": result.warnings,
                "estimate": estimate,
            }

        # Infeasible — run conflict analyzer
        conflict_summary = ""
        structured_reports: list[dict] = []
        try:
            from timease.engine.conflicts import ConflictAnalyzer
            import dataclasses as _dc
            analyzer = ConflictAnalyzer(school_obj)
            reports  = analyzer.analyze()
            conflict_summary = _format_conflicts_fr(reports)
            structured_reports = [_dc.asdict(r) for r in reports]
        except Exception:
            pass

        sessions[sid]["last_conflict_reports"] = structured_reports

        if not conflict_summary:
            if result.conflicts:
                lines = []
                for c in result.conflicts[:5]:
                    reason = c.get("reason", "")
                    cls    = c.get("class", "")
                    subj   = c.get("subject", "")
                    if cls and subj:
                        lines.append(f"- **{cls} / {subj}** : {reason}")
                    else:
                        lines.append(f"- {reason}")
                conflict_summary = "**Sessions impossibles à planifier :**\n" + "\n".join(lines)
            else:
                conflict_summary = "Aucune solution trouvée avec les données actuelles."

        return {
            "status":            "INFEASIBLE",
            "solved":            False,
            "conflict_summary":  conflict_summary,
            "conflict_reports":  structured_reports,
            "diagnostics": {
                "request_id": request_id,
                "mode": solve_mode,
                "requested_timeout_seconds": requested_timeout,
                "adaptive_timeout_seconds": adaptive_timeout,
                "effective_timeout_seconds": effective_timeout,
                "optimize_soft_constraints": optimize_soft_constraints,
                "stop_at_first_solution": stop_at_first_solution,
                "enforce_room_conflicts": enforce_room_conflicts,
                "room_fallback_retry_used": False,
                "api_wall_time_seconds": api_wall_time,
            },
        }

    except Exception as exc:
        return {"status": "ERROR", "solved": False, "errors": [str(exc)], "conflict_summary": str(exc)}


# ── Export ─────────────────────────────────────────────────────────────────────

def _rebuild_school_obj(sd: dict, ta: list[dict]):
    from timease.engine.models import (
        Constraint, CurriculumEntry, Room, School, SchoolClass,
        SchoolData, Subject, Teacher, TeacherAssignment,
    )
    return SchoolData(
        school=School(name=sd.get("name", ""), academic_year=sd.get("academic_year", ""), city=sd.get("city", "")),
        timeslot_config=_norm_timeslot_config(sd),
        subjects=[Subject(**_norm_subject(s)) for s in sd.get("subjects", [])],
        teachers=[Teacher(**_norm_teacher(t)) for t in sd.get("teachers", [])],
        classes=[SchoolClass(**_norm_class(c)) for c in sd.get("classes", [])],
        rooms=[Room(**_norm_room(r)) for r in sd.get("rooms", [])],
        curriculum=[CurriculumEntry(**_norm_curriculum(e)) for e in sd.get("curriculum", [])],
        constraints=[Constraint(**_norm_constraint(c)) for c in sd.get("constraints", [])],
        teacher_assignments=[TeacherAssignment(**_pick(a, ["teacher", "subject", "school_class"])) for a in ta],
    )


@app.get("/api/session/{sid}/export/{format}")
def export(sid: str, format: str):
    if sid not in sessions:
        raise HTTPException(404, "Session not found")
    if not sessions[sid]["timetable_result"]:
        raise HTTPException(400, "No timetable to export — solve first")

    sd  = sessions[sid]["school_data"]
    ta  = sessions[sid]["teacher_assignments"]
    raw = sessions[sid]["timetable_result"]["assignments"]

    from timease.engine.models import Assignment, TimetableResult
    school_obj = _rebuild_school_obj(sd, ta)
    _asgn_keys = {"school_class", "subject", "teacher", "day", "start_time", "end_time", "room"}
    result = TimetableResult(
        solved=True,
        assignments=[Assignment(**{k: v for k, v in a.items() if k in _asgn_keys}) for a in raw],
        solve_time_seconds=sessions[sid]["timetable_result"].get("solve_time", 0),
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format}") as tmp:
        path = tmp.name

    if format == "xlsx":
        from timease.io.excel_export import export_timetable
        export_timetable(result, school_obj, path)
    elif format == "pdf":
        from timease.io.pdf_export import export_pdf
        export_pdf(result, school_obj, path)
    elif format == "docx":
        from timease.io.word_export import export_word
        export_word(result, school_obj, path)
    elif format == "md":
        from timease.io.md_export import export_markdown
        export_markdown(result, school_obj, path)
    else:
        raise HTTPException(400, f"Unknown format: {format}")

    return FileResponse(path, filename=f"emploi_du_temps.{format}")
