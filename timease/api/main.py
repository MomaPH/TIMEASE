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
        "max_hours_per_week": int(d.get("max_hours_per_week", 20)),
        "unavailable_slots":  d.get("unavailable_slots", []),
        "preference_weight":  float(d.get("preference_weight", 1.0)),
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
    return {
        "level":                  d.get("level", ""),
        "subject":                d.get("subject", ""),
        "total_minutes_per_week": int(d.get("total_minutes_per_week", 60)),
        "mode":                   d.get("mode", "auto"),
        "sessions_per_week":      d.get("sessions_per_week"),
        "minutes_per_session":    d.get("minutes_per_session"),
        "min_session_minutes":    d.get("min_session_minutes"),
        "max_session_minutes":    d.get("max_session_minutes"),
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


# ── In-memory session store ────────────────────────────────────────────────────

sessions: dict[str, dict] = {}


class SessionData(BaseModel):
    school_data: dict = {}
    teacher_assignments: list[dict] = []
    timetable_result: dict = {}
    ai_history: list[dict] = []
    collab_links: list[dict] = []


# ── Merge helper (used by both /merge and chat auto-apply) ─────────────────────

def _merge_tool_call(sid: str, tool_name: str, data: dict) -> None:
    """Apply a single AI tool call to the session in-place."""
    sd = sessions[sid]["school_data"]

    if tool_name == "save_school_info":
        sd.update({k: v for k, v in data.items() if k != "type"})

    elif tool_name == "save_teachers":
        existing  = sd.get("teachers", [])
        new_items = data.get("teachers", [])
        sd["teachers"] = existing + [
            {"name": t, "subjects": [], "max_hours_per_week": 20}
            if isinstance(t, str) else t
            for t in new_items
        ]

    elif tool_name == "save_classes":
        existing  = sd.get("classes", [])
        new_items = data.get("classes", [])
        sd["classes"] = existing + [
            {"name": c, "level": c, "student_count": 0}
            if isinstance(c, str) else c
            for c in new_items
        ]

    elif tool_name == "save_rooms":
        existing  = sd.get("rooms", [])
        new_items = data.get("rooms", [])
        sd["rooms"] = existing + [
            {"name": r, "capacity": 30, "types": ["Standard"]}
            if isinstance(r, str) else r
            for r in new_items
        ]

    elif tool_name == "save_subjects":
        existing  = sd.get("subjects", [])
        new_items = data.get("subjects", [])
        sd["subjects"] = existing + new_items

    elif tool_name == "save_curriculum":
        existing  = sd.get("curriculum", [])
        new_items = data.get("curriculum", [])
        sd["curriculum"] = existing + new_items

    elif tool_name == "save_constraints":
        existing  = sd.get("constraints", [])
        new_items = data.get("constraints", [])
        sd["constraints"] = existing + new_items

    elif tool_name == "save_assignments":
        existing = sessions[sid]["teacher_assignments"]
        raw = data.get("assignments", [])
        normalized = []
        for a in raw:
            if isinstance(a, str):
                continue
            # Normalize field aliases the AI may send
            entry = {
                "teacher":      a.get("teacher", ""),
                "subject":      a.get("subject", ""),
                # Accept both "school_class" and "class"
                "school_class": a.get("school_class") or a.get("class", ""),
            }
            if entry["teacher"] and entry["subject"] and entry["school_class"]:
                normalized.append(entry)
        sessions[sid]["teacher_assignments"] = existing + normalized

    sessions[sid]["school_data"] = sd


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


# ── School data merge (kept for compatibility) ─────────────────────────────────

@app.post("/api/session/{sid}/merge")
def merge_data(sid: str, payload: dict):
    if sid not in sessions:
        raise HTTPException(404, "Session not found")
    _merge_tool_call(sid, payload.get("type", ""), payload.get("data", {}))
    return {"ok": True}


# ── AI chat ────────────────────────────────────────────────────────────────────

@app.post("/api/session/{sid}/chat")
async def chat(sid: str, payload: dict):
    """Send one chat turn to Claude, auto-apply tool calls, return message."""
    if sid not in sessions:
        raise HTTPException(404, "Session not found")

    from timease.api.ai_chat import process_chat

    # Frontend may send its locally-stored ai_history (survives backend restart)
    provided_history = payload.get("ai_history")
    ai_history = (
        provided_history
        if provided_history is not None
        else sessions[sid]["ai_history"]
    )

    result = process_chat(
        user_message=payload.get("message", ""),
        file_content=payload.get("file_content"),
        school_data=sessions[sid]["school_data"],
        teacher_assignments=sessions[sid]["teacher_assignments"],
        ai_history=ai_history,
    )

    # Auto-apply data tool calls; handle special tools separately
    saved_types: list[str] = []
    trigger_generation = False
    proposed_options: list[dict] = []

    for tc in result["tool_calls"]:
        if tc["name"] == "trigger_generation":
            trigger_generation = True
        elif tc["name"] == "propose_options":
            proposed_options = tc["data"].get("options", [])
        else:
            _merge_tool_call(sid, tc["name"], tc["data"])
            saved_types.append(tc["name"])

    sessions[sid]["ai_history"] = result["updated_history"]

    return {
        "message":            result["message"],
        "data_saved":         len(saved_types) > 0,
        "trigger_generation": trigger_generation,
        "options":            proposed_options,
        "saved_types": saved_types,
        "ai_history":  result["updated_history"],
    }


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
            timeslot_config=TimeslotConfig(
                days=sd.get("days", ["lundi", "mardi", "mercredi", "jeudi", "vendredi"]),
                base_unit_minutes=int(sd.get("base_unit_minutes", 30)),
                sessions=[
                    SessionConfig(**_pick(s, ["name", "start_time", "end_time"]))
                    for s in sd.get("sessions", [
                        {"name": "Matin",      "start_time": "08:00", "end_time": "12:00"},
                        {"name": "Après-midi", "start_time": "14:00", "end_time": "17:00"},
                    ])
                ],
            ),
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
                "solve_time":               result.solve_time_seconds,
                "days":                     sd.get("days", []),
                "soft_results":             result.soft_constraint_details,
                "warnings":                 result.warnings,
                "unscheduled":              result.unscheduled_sessions,
            }
            sessions[sid]["timetable_result"] = timetable
            status = "OPTIMAL" if result.solved and not result.partial else "PARTIAL"
            return {"status": status, "solved": True, **timetable}

        # Infeasible — run conflict analyzer
        conflict_summary = ""
        try:
            from timease.engine.conflicts import ConflictAnalyzer
            analyzer = ConflictAnalyzer(school_obj)
            reports  = analyzer.analyze()
            conflict_summary = _format_conflicts_fr(reports)
        except Exception:
            pass

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
            "status":           "INFEASIBLE",
            "solved":           False,
            "conflict_summary": conflict_summary,
        }

    except Exception as exc:
        return {"status": "ERROR", "solved": False, "errors": [str(exc)], "conflict_summary": str(exc)}


# ── Export ─────────────────────────────────────────────────────────────────────

def _rebuild_school_obj(sd: dict, ta: list[dict]):
    from timease.engine.models import (
        Constraint, CurriculumEntry, Room, School, SchoolClass,
        SchoolData, SessionConfig, Subject, Teacher, TeacherAssignment, TimeslotConfig,
    )
    return SchoolData(
        school=School(name=sd.get("name", ""), academic_year=sd.get("academic_year", ""), city=sd.get("city", "")),
        timeslot_config=TimeslotConfig(
            days=sd.get("days", []),
            base_unit_minutes=int(sd.get("base_unit_minutes", 30)),
            sessions=[SessionConfig(**_pick(s, ["name", "start_time", "end_time"])) for s in sd.get("sessions", [])],
        ),
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


# ── Collaboration ──────────────────────────────────────────────────────────────

_COLLAB_DIR = Path("collab")


@app.post("/api/session/{sid}/collab/generate")
def generate_collab_links(sid: str):
    if sid not in sessions:
        raise HTTPException(404, "Session not found")

    teachers = sessions[sid]["school_data"].get("teachers", [])
    links: list[dict] = []
    _COLLAB_DIR.mkdir(exist_ok=True)

    for t in teachers:
        token = uuid.uuid4().hex[:8]
        name  = t["name"] if isinstance(t, dict) else str(t)
        (_COLLAB_DIR / f"{token}.json").write_text(
            json.dumps({
                "teacher":      name,
                "school":       sessions[sid]["school_data"].get("name", ""),
                "submitted":    False,
                "availability": {},
                "preferences":  "",
            }, ensure_ascii=False)
        )
        links.append({"teacher": name, "token": token, "status": "non_envoye"})

    sessions[sid]["collab_links"] = links
    return {"links": links}


@app.get("/api/collab/{token}")
def get_collab(token: str):
    p = _COLLAB_DIR / f"{token}.json"
    if not p.exists():
        raise HTTPException(404, "Token not found")
    return json.loads(p.read_text())


@app.post("/api/collab/{token}/availability")
def submit_availability(token: str, payload: dict):
    p = _COLLAB_DIR / f"{token}.json"
    if not p.exists():
        return {"ok": True}
    data = json.loads(p.read_text())
    data["availability"] = payload.get("availability", {})
    data["submitted"]    = True
    p.write_text(json.dumps(data, ensure_ascii=False))
    return {"ok": True}
