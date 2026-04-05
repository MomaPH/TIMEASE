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

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="TIMEASE API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",  # Next.js fallback port
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# ── Model normalization helpers ────────────────────────────────────────────────
# The AI and frontend may send field names that differ from the engine's dataclass
# field names. These helpers remap aliases and drop unknown keys so that
# direct **unpacking into dataclasses never raises TypeError.

def _pick(d: dict, keys: list[str]) -> dict:
    """Return only the keys that exist in the target dataclass."""
    return {k: v for k, v in d.items() if k in keys}


def _norm_subject(d: dict) -> dict:
    out = {
        "name":       d.get("name", ""),
        "short_name": d.get("short_name") or d.get("name", "")[:4].upper(),
        "color":      d.get("color", "#0d9488"),
        "required_room_type": d.get("required_room_type") or d.get("room_type"),
        "needs_room": d.get("needs_room", True),
    }
    return out


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
    import uuid as _uuid
    return {
        "id":             d.get("id") or str(_uuid.uuid4())[:8],
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


# ── Session management ─────────────────────────────────────────────────────────


@app.post("/api/session")
def create_session():
    """Create a new empty session and return its ID."""
    sid = uuid.uuid4().hex[:12]
    sessions[sid] = SessionData().model_dump()
    return {"session_id": sid}


@app.get("/api/session/{sid}")
def get_session(sid: str):
    """Return the full session state."""
    if sid not in sessions:
        raise HTTPException(404, "Session not found")
    return sessions[sid]


# ── School data CRUD ───────────────────────────────────────────────────────────


@app.post("/api/session/{sid}/merge")
def merge_data(sid: str, payload: dict):
    """
    Merge AI-extracted data into the session.

    payload: {"type": str, "data": dict}
    """
    if sid not in sessions:
        raise HTTPException(404, "Session not found")

    dtype = payload.get("type", "")
    data  = payload.get("data", {})
    sd    = sessions[sid]["school_data"]

    if dtype in ("save_school_info", "school_info"):
        sd.update({k: v for k, v in data.items() if k != "type"})

    elif dtype in ("save_teachers", "teachers"):
        existing  = sd.get("teachers", [])
        new_items = data.get("teachers", [])
        sd["teachers"] = existing + [
            {"name": t, "subjects": [], "max_hours_per_week": 30}
            if isinstance(t, str) else t
            for t in new_items
        ]

    elif dtype in ("save_classes", "classes"):
        existing  = sd.get("classes", [])
        new_items = data.get("classes", [])
        sd["classes"] = existing + [
            {"name": c, "level": c, "student_count": 0}
            if isinstance(c, str) else c
            for c in new_items
        ]

    elif dtype in ("save_rooms", "rooms"):
        existing  = sd.get("rooms", [])
        new_items = data.get("rooms", [])
        sd["rooms"] = existing + [
            {"name": r, "capacity": 0, "types": ["Standard"]}
            if isinstance(r, str) else r
            for r in new_items
        ]

    elif dtype in ("save_subjects", "subjects"):
        existing  = sd.get("subjects", [])
        new_items = data.get("subjects", [])
        sd["subjects"] = existing + new_items

    elif dtype in ("save_curriculum", "curriculum"):
        existing  = sd.get("curriculum", [])
        new_items = data.get("curriculum", [])
        sd["curriculum"] = existing + new_items

    elif dtype in ("save_constraints", "constraints"):
        existing  = sd.get("constraints", [])
        new_items = data.get("constraints", [])
        sd["constraints"] = existing + new_items

    elif dtype in ("save_assignments", "assignments"):
        existing = sessions[sid]["teacher_assignments"]
        sessions[sid]["teacher_assignments"] = (
            existing + data.get("assignments", [])
        )

    sessions[sid]["school_data"] = sd
    return {"ok": True}


# ── AI chat ────────────────────────────────────────────────────────────────────


@app.post("/api/session/{sid}/chat")
async def chat(sid: str, payload: dict):
    """Send one chat turn to Claude and return the structured response."""
    if sid not in sessions:
        raise HTTPException(404, "Session not found")

    from timease.api.ai_chat import process_chat

    result = process_chat(
        user_message=payload.get("message", ""),
        file_content=payload.get("file_content"),
        school_data=sessions[sid]["school_data"],
        teacher_assignments=sessions[sid]["teacher_assignments"],
        ai_history=sessions[sid]["ai_history"],
    )

    sessions[sid]["ai_history"] = result["updated_history"]

    return {
        "message":            result["message"],
        "tool_calls":         result["tool_calls"],
        "quick_replies":      result["quick_replies"],
        "needs_confirmation": result["needs_confirmation"],
    }


# ── File upload ────────────────────────────────────────────────────────────────


@app.post("/api/session/{sid}/upload")
async def upload_file(sid: str, file: UploadFile = File(...)):
    """Accept a file, attempt direct import or fall back to text extraction."""
    if sid not in sessions:
        raise HTTPException(404, "Session not found")

    suffix = Path(file.filename or "").suffix.lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    # Try direct TIMEASE template import for .xlsx only (openpyxl doesn't read .xls)
    if suffix == ".xlsx":
        try:
            from timease.io.excel_import import read_template

            school_data_obj, errors = read_template(tmp_path)
            if school_data_obj and not errors:
                sd_dict = dataclasses.asdict(school_data_obj)
                sessions[sid]["school_data"] = sd_dict
                sessions[sid]["teacher_assignments"] = [
                    {
                        "teacher":      ta.teacher,
                        "subject":      ta.subject,
                        "school_class": ta.school_class,
                    }
                    for ta in school_data_obj.teacher_assignments
                ]
                os.unlink(tmp_path)
                return {
                    "type":        "direct_import",
                    "success":     True,
                    "school_data": sessions[sid]["school_data"],
                }
        except Exception:
            pass

    # Fallback: extract text for AI
    from timease.io.file_parser import extract_content

    text, ftype = extract_content(tmp_path)
    os.unlink(tmp_path)
    return {"type": "text_extract", "content": text, "file_type": ftype}


# ── Solve ──────────────────────────────────────────────────────────────────────


@app.post("/api/session/{sid}/solve")
def solve(sid: str, payload: dict = {}):
    """Run the CP-SAT solver and store the result."""
    if sid not in sessions:
        raise HTTPException(404, "Session not found")

    timeout = int(payload.get("timeout", 120))
    sd      = sessions[sid]["school_data"]
    ta      = sessions[sid]["teacher_assignments"]

    from timease.engine.models import (
        Constraint,
        CurriculumEntry,
        Room,
        School,
        SchoolClass,
        SchoolData,
        SessionConfig,
        Subject,
        Teacher,
        TeacherAssignment,
        TimeslotConfig,
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
                days=sd.get("days", [
                    "lundi", "mardi", "mercredi", "jeudi", "vendredi",
                ]),
                base_unit_minutes=int(sd.get("base_unit_minutes", 30)),
                sessions=[
                    SessionConfig(**_pick(s, ["name", "start_time", "end_time"]))
                    for s in sd.get("sessions", [
                        {"name": "Matin", "start_time": "08:00", "end_time": "13:00"},
                    ])
                ],
            ),
            subjects=[Subject(**_norm_subject(s)) for s in sd.get("subjects", [])],
            teachers=[Teacher(**_norm_teacher(t)) for t in sd.get("teachers", [])],
            classes=[SchoolClass(**_norm_class(c)) for c in sd.get("classes", [])],
            rooms=[Room(**_norm_room(r)) for r in sd.get("rooms", [])],
            curriculum=[CurriculumEntry(**_norm_curriculum(e)) for e in sd.get("curriculum", [])],
            constraints=[Constraint(**_norm_constraint(c)) for c in sd.get("constraints", [])],
            teacher_assignments=[TeacherAssignment(**_pick(a, ["teacher", "subject", "school_class"])) for a in ta],
        )

        validation_errors = school_obj.validate()
        if validation_errors:
            return {"status": "INFEASIBLE", "solved": False, "errors": validation_errors}

        result = TimetableSolver().solve(school_obj, timeout_seconds=timeout)

        if result.solved:
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
                "solve_time": result.solve_time_seconds,
                "days": sd.get("days", []),
            }
            sessions[sid]["timetable_result"] = timetable
            return {"status": "OPTIMAL", "solved": True, **timetable}

        return {"status": "INFEASIBLE", "solved": False, "message": "Aucune solution trouvée"}

    except Exception as exc:
        return {"status": "ERROR", "solved": False, "errors": [str(exc)]}


# ── Export ─────────────────────────────────────────────────────────────────────


def _rebuild_school_obj(sd: dict, ta: list[dict]):
    from timease.engine.models import (
        Constraint,
        CurriculumEntry,
        Room,
        School,
        SchoolClass,
        SchoolData,
        SessionConfig,
        Subject,
        Teacher,
        TeacherAssignment,
        TimeslotConfig,
    )
    return SchoolData(
        school=School(
            name=sd.get("name", ""),
            academic_year=sd.get("academic_year", ""),
            city=sd.get("city", ""),
        ),
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
    """Export the solved timetable in the requested format."""
    if sid not in sessions:
        raise HTTPException(404, "Session not found")
    if not sessions[sid]["timetable_result"]:
        raise HTTPException(400, "No timetable to export — solve first")

    sd  = sessions[sid]["school_data"]
    ta  = sessions[sid]["teacher_assignments"]
    raw = sessions[sid]["timetable_result"]["assignments"]

    from timease.engine.models import Assignment, TimetableResult

    school_obj = _rebuild_school_obj(sd, ta)
    _assignment_keys = {"school_class", "subject", "teacher", "day", "start_time", "end_time", "room"}
    result = TimetableResult(
        solved=True,
        assignments=[Assignment(**{k: v for k, v in a.items() if k in _assignment_keys}) for a in raw],
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
    """Generate a token for each teacher's availability form."""
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
    """Submit a teacher's availability."""
    p = _COLLAB_DIR / f"{token}.json"
    if not p.exists():
        # Silently accept if token doesn't exist yet (stub mode)
        return {"ok": True}
    data = json.loads(p.read_text())
    data["availability"] = payload.get("availability", {})
    data["submitted"]    = True
    p.write_text(json.dumps(data, ensure_ascii=False))
    return {"ok": True}
