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
import os
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="TIMEASE API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
    ],
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
    return {
        "id":             d.get("id") or str(uuid.uuid4())[:8],
        "type":           d.get("type", "hard"),
        "category":       d.get("category", ""),
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


class SessionData(BaseModel):
    school_data: dict = {}
    teacher_assignments: list[dict] = []
    timetable_result: dict = {}
    last_conflict_reports: list[dict] = []
    last_solve_issues: dict = {}


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


@app.post("/api/session/{sid}/solve")
def solve(sid: str, payload: dict = {}):
    if sid not in sessions:
        raise HTTPException(404, "Session not found")

    timeout = int(payload.get("timeout", 120))
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
        if validation_errors:
            conflict_summary = "**Erreurs de validation :**\n" + "\n".join(
                f"- {e}" for e in validation_errors
            )
            return {"status": "INFEASIBLE", "solved": False, "conflict_summary": conflict_summary, "errors": validation_errors}

        result = TimetableSolver().solve(school_obj, timeout_seconds=timeout)

        if result.solved or result.partial:
            subj_colors = {s.name: s.color for s in school_obj.subjects}
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
                        "color":        subj_colors.get(a.subject, "#0d9488"),
                    }
                    for a in result.assignments
                ],
                "solve_time":    result.solve_time_seconds,
                "days":          [d.name for d in school_obj.timeslot_config.days],
                "soft_results":  result.soft_constraint_details,
                "warnings":      result.warnings,
                "unscheduled":   result.unscheduled_sessions,
                "unscheduled_groups": unscheduled_grouped,
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
