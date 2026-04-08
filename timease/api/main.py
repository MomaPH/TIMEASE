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
from fastapi.responses import FileResponse, StreamingResponse
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


# ── In-memory session store ────────────────────────────────────────────────────

sessions: dict[str, dict] = {}


class SessionData(BaseModel):
    school_data: dict = {}
    teacher_assignments: list[dict] = []
    timetable_result: dict = {}
    ai_history: list[dict] = []
    collab_links: list[dict] = []
    last_conflict_reports: list[dict] = []
    last_solve_issues: dict = {}
    pending_changes: list[dict] = []


# ── Merge helper (used by both /merge and chat auto-apply) ─────────────────────

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


def _merge_tool_call(sid: str, tool_name: str, data: dict) -> None:
    """Apply a single AI tool call to the session in-place (upsert or replace)."""
    sd = sessions[sid]["school_data"]
    replace_mode = data.get("replace", False)

    if tool_name == "save_school_info":
        sd.update({k: v for k, v in data.items() if k != "type"})

    elif tool_name == "save_teachers":
        raw = data.get("teachers", [])
        items = [
            {"name": t, "subjects": [], "max_hours_per_week": None}
            if isinstance(t, str) else t
            for t in raw
        ]
        if replace_mode:
            sd["teachers"] = items
        else:
            sd["teachers"] = _upsert(sd.get("teachers", []), items, "name")

    elif tool_name == "save_classes":
        raw = data.get("classes", [])
        items = [
            {"name": c, "level": c, "student_count": 0}
            if isinstance(c, str) else c
            for c in raw
        ]
        if replace_mode:
            sd["classes"] = items
        else:
            sd["classes"] = _upsert(sd.get("classes", []), items, "name")

    elif tool_name == "save_rooms":
        raw = data.get("rooms", [])
        items = [
            {"name": r, "capacity": 30, "types": ["Standard"]}
            if isinstance(r, str) else r
            for r in raw
        ]
        if replace_mode:
            sd["rooms"] = items
        else:
            sd["rooms"] = _upsert(sd.get("rooms", []), items, "name")

    elif tool_name == "save_subjects":
        if replace_mode:
            sd["subjects"] = data.get("subjects", [])
        else:
            sd["subjects"] = _upsert(
                sd.get("subjects", []), data.get("subjects", []), "name"
            )

    elif tool_name == "save_curriculum":
        normalized_curriculum = [
            _norm_curriculum(entry) for entry in data.get("curriculum", [])
        ]
        if replace_mode:
            sd["curriculum"] = normalized_curriculum
        else:
            sd["curriculum"] = _upsert_composite(
                sd.get("curriculum", []), normalized_curriculum, ["school_class", "subject"]
            )

    elif tool_name == "save_constraints":
        if replace_mode:
            sd["constraints"] = data.get("constraints", [])
        else:
            sd["constraints"] = _upsert(
                sd.get("constraints", []), data.get("constraints", []), "id"
            )

    elif tool_name == "save_assignments":
        raw = data.get("assignments", [])
        normalized = []
        for a in raw:
            if isinstance(a, str):
                continue
            entry = {
                "teacher":      a.get("teacher", ""),
                "subject":      a.get("subject", ""),
                "school_class": a.get("school_class") or a.get("class", ""),
            }
            if entry["teacher"] and entry["subject"] and entry["school_class"]:
                normalized.append(entry)
        if replace_mode:
            sessions[sid]["teacher_assignments"] = normalized
        else:
            sessions[sid]["teacher_assignments"] = _upsert_composite(
                sessions[sid]["teacher_assignments"],
                normalized,
                ["teacher", "subject", "school_class"],
            )

    sessions[sid]["school_data"] = sd


# ── Staging layer — preview + commit ──────────────────────────────────────────

_SAVE_TOOLS = {
    "save_school_info", "save_teachers", "save_classes", "save_rooms",
    "save_subjects", "save_curriculum", "save_constraints", "save_assignments",
}

_TOOL_LABELS = {
    "save_school_info":  "Infos école",
    "save_teachers":     "Enseignants",
    "save_classes":      "Classes",
    "save_rooms":        "Salles",
    "save_subjects":     "Matières",
    "save_curriculum":   "Programme horaire",
    "save_constraints":  "Contraintes",
    "save_assignments":  "Affectations enseignants",
}


def _make_preview(tool_name: str, data: dict) -> str:
    """Generate a markdown table preview of what a save tool will write."""
    if tool_name == "save_school_info":
        rows = [(k, str(v)) for k, v in data.items() if v]
        header = "| Champ | Valeur |\n|-------|--------|\n"
        return header + "\n".join(f"| {k} | {v} |" for k, v in rows)

    if tool_name == "save_teachers":
        items = data.get("teachers", [])
        header = "| Nom | Matières | H/sem |\n|-----|----------|-------|\n"
        rows = [
            f"| {t.get('name','?')} | {', '.join(t.get('subjects',[]))} | {t.get('max_hours_per_week','?')} |"
            for t in items
        ]
        return header + "\n".join(rows)

    if tool_name == "save_classes":
        items = data.get("classes", [])
        header = "| Nom | Niveau | Effectif |\n|-----|--------|----------|\n"
        rows = [
            f"| {c.get('name','?')} | {c.get('level','?')} | {c.get('student_count','?')} |"
            for c in items
        ]
        return header + "\n".join(rows)

    if tool_name == "save_rooms":
        items = data.get("rooms", [])
        header = "| Nom | Capacité | Types |\n|-----|----------|-------|\n"
        rows = [
            f"| {r.get('name','?')} | {r.get('capacity','?')} | {', '.join(r.get('types',[]))} |"
            for r in items
        ]
        return header + "\n".join(rows)

    if tool_name == "save_subjects":
        items = data.get("subjects", [])
        header = "| Nom | Abrév. | Salle requise |\n|-----|--------|---------------|\n"
        rows = [
            f"| {s.get('name','?')} | {s.get('short_name','?')} | {s.get('required_room_type') or '—'} |"
            for s in items
        ]
        return header + "\n".join(rows)

    if tool_name == "save_curriculum":
        items = data.get("curriculum", [])
        header = "| Classe | Matière | Min/sem |\n|--------|---------|----------|\n"
        rows = [
            f"| {e.get('school_class','?')} | {e.get('subject','?')} | {e.get('total_minutes_per_week','?')} |"
            for e in items
        ]
        return header + "\n".join(rows)

    if tool_name == "save_constraints":
        items = data.get("constraints", [])
        header = "| ID | Type | Description |\n|----|------|-------------|\n"
        rows = [
            f"| {c.get('id','?')} | {c.get('type','?')} | {c.get('description_fr','?')} |"
            for c in items
        ]
        return header + "\n".join(rows)

    if tool_name == "save_assignments":
        items = data.get("assignments", [])
        header = "| Enseignant | Matière | Classe |\n|------------|---------|--------|\n"
        rows = [
            f"| {a.get('teacher','?')} | {a.get('subject','?')} | {a.get('school_class','?')} |"
            for a in items
        ]
        return header + "\n".join(rows)

    return "(aperçu non disponible)"


def _pending_label(tool_name: str, data: dict) -> str:
    """Short human label: e.g. '3 enseignants', '2 classes'."""
    counts = {
        "save_teachers":    len(data.get("teachers", [])),
        "save_classes":     len(data.get("classes", [])),
        "save_rooms":       len(data.get("rooms", [])),
        "save_subjects":    len(data.get("subjects", [])),
        "save_curriculum":  len(data.get("curriculum", [])),
        "save_constraints": len(data.get("constraints", [])),
        "save_assignments": len(data.get("assignments", [])),
    }
    base = _TOOL_LABELS.get(tool_name, tool_name)
    n = counts.get(tool_name)
    return f"{n} {base.lower()}" if n is not None else base


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


# ── Staging: apply or discard pending changes ─────────────────────────────────

@app.post("/api/session/{sid}/apply_pending")
def apply_pending(sid: str, payload: dict):
    """Commit or discard all staged AI tool calls."""
    if sid not in sessions:
        raise HTTPException(404, "Session not found")
    changes = sessions[sid].get("pending_changes", [])
    applied = 0
    if payload.get("apply", False):
        for change in changes:
            _merge_tool_call(sid, change["tool"], change["input"])
            applied += 1
    sessions[sid]["pending_changes"] = []
    return {"ok": True, "applied": applied}


# ── School data merge (kept for compatibility) ─────────────────────────────────

@app.post("/api/session/{sid}/merge")
def merge_data(sid: str, payload: dict):
    if sid not in sessions:
        raise HTTPException(404, "Session not found")
    _merge_tool_call(sid, payload.get("type", ""), payload.get("data", {}))
    return {"ok": True}


# ── Workload Analysis Tool ─────────────────────────────────────────────────────

def _analyze_workload(sid: str, check_type: str) -> dict:
    """Analyze workload: hours demanded vs teacher/room capacity.

    Returns structured analysis with calculations for the AI to present.
    """
    sd = sessions[sid]["school_data"]
    ta = sessions[sid]["teacher_assignments"]

    classes = sd.get("classes", [])
    teachers = sd.get("teachers", [])
    rooms = sd.get("rooms", [])
    subjects = sd.get("subjects", [])
    curriculum = sd.get("curriculum", [])

    result: dict = {"check_type": check_type, "analyses": [], "warnings": [], "suggestions": []}

    # ── Teacher capacity analysis ──────────────────────────────────────────────
    if check_type in ("teachers", "all"):
        # Calculate hours demanded per subject
        subject_hours: dict[str, int] = {}
        for entry in curriculum:
            subj = entry.get("subject", "")
            minutes = entry.get("total_minutes_per_week", 0)
            hours = minutes / 60
            subject_hours[subj] = subject_hours.get(subj, 0) + hours

        # Calculate teacher capacity per subject
        subject_capacity: dict[str, dict] = {}  # subject -> {teachers: [], total_hours: int}
        for t in teachers:
            max_h = t.get("max_hours_per_week", 18)
            for subj in t.get("subjects", []):
                if subj not in subject_capacity:
                    subject_capacity[subj] = {"teachers": [], "total_hours": 0}
                subject_capacity[subj]["teachers"].append(t.get("name", "?"))
                subject_capacity[subj]["total_hours"] += max_h

        teacher_analysis = []
        for subj in sorted(set(list(subject_hours.keys()) + list(subject_capacity.keys()))):
            demanded = subject_hours.get(subj, 0)
            capacity_info = subject_capacity.get(subj, {"teachers": [], "total_hours": 0})
            capacity = capacity_info["total_hours"]
            teacher_names = capacity_info["teachers"]

            status = "✅" if capacity >= demanded else "❌"
            diff = capacity - demanded

            entry = {
                "subject": subj,
                "hours_demanded": round(demanded, 1),
                "hours_available": capacity,
                "teachers": teacher_names,
                "teacher_count": len(teacher_names),
                "difference": round(diff, 1),
                "status": status,
            }
            teacher_analysis.append(entry)

            if diff < 0:
                needed_teachers = abs(diff) / 18  # assuming 18h/week per teacher
                result["warnings"].append(
                    f"{subj}: déficit de {abs(round(diff, 1))}h/semaine"
                )
                result["suggestions"].append(
                    f"Pour {subj}: recruter {max(1, round(needed_teachers))} enseignant(s) "
                    f"supplémentaire(s) OU réduire le volume horaire"
                )

        result["analyses"].append({
            "type": "teachers",
            "title": "Capacité enseignants par matière",
            "data": teacher_analysis,
        })

    # ── Room capacity analysis ─────────────────────────────────────────────────
    if check_type in ("rooms", "all"):
        # Total class-hours per week
        total_class_hours = sum(
            entry.get("total_minutes_per_week", 0) / 60
            for entry in curriculum
        )

        # Room slots available (assuming 6 days × 7 hours = 42 slots per room)
        days = sd.get("days", [])
        sessions_list = sd.get("sessions", [])
        slots_per_day = 0
        for sess in sessions_list:
            start = sess.get("start_time", "08:00")
            end = sess.get("end_time", "12:00")
            try:
                sh, sm = map(int, start.split(":"))
                eh, em = map(int, end.split(":"))
                duration_min = (eh * 60 + em) - (sh * 60 + sm)
                base_unit = sd.get("base_unit_minutes", 55)
                slots_per_day += duration_min // base_unit
            except (ValueError, AttributeError):
                slots_per_day += 4  # fallback

        total_room_slots = len(rooms) * len(days) * slots_per_day

        room_analysis = {
            "room_count": len(rooms),
            "days": len(days),
            "slots_per_day": slots_per_day,
            "total_slots_available": total_room_slots,
            "total_class_hours_needed": round(total_class_hours, 1),
            "utilization_percent": round((total_class_hours / total_room_slots * 100), 1) if total_room_slots > 0 else 0,
        }

        result["analyses"].append({
            "type": "rooms",
            "title": "Capacité salles",
            "data": room_analysis,
        })

        if total_class_hours > total_room_slots:
            result["warnings"].append(
                f"Salles insuffisantes: {round(total_class_hours)}h demandées vs {total_room_slots}h disponibles"
            )

    # ── Curriculum completeness ────────────────────────────────────────────────
    if check_type in ("curriculum", "all"):
        class_names = {c.get("name", "") for c in classes}
        subject_names = {s.get("name", "") for s in subjects}

        curriculum_by_class: dict[str, set] = {}
        for entry in curriculum:
            cls = entry.get("school_class", "")
            subj = entry.get("subject", "")
            if cls not in curriculum_by_class:
                curriculum_by_class[cls] = set()
            curriculum_by_class[cls].add(subj)

        missing = []
        for cls in class_names:
            cls_subjects = curriculum_by_class.get(cls, set())
            for subj in subject_names:
                if subj not in cls_subjects:
                    missing.append({"class": cls, "subject": subj})

        result["analyses"].append({
            "type": "curriculum",
            "title": "Complétude du programme",
            "data": {
                "classes_count": len(class_names),
                "subjects_count": len(subject_names),
                "curriculum_entries": len(curriculum),
                "expected_entries": len(class_names) * len(subject_names),
                "missing_entries": missing[:20],  # limit for display
            },
        })

        if missing:
            result["warnings"].append(
                f"Programme incomplet: {len(missing)} entrées manquantes"
            )

    return result


# ── Template Generator ─────────────────────────────────────────────────────────

# Standard Senegalese curriculum hours per week
_COLLEGE_CURRICULUM = {
    "Français": 5, "Mathématiques": 5, "Anglais": 3, "Histoire-Géographie": 3,
    "SVT": 2, "Physique-Chimie": 2, "EPS": 2, "Arts plastiques": 1,
    "Éducation civique": 1,
}

_LYCEE_S_CURRICULUM = {
    "Mathématiques": 6, "Physique-Chimie": 5, "SVT": 4, "Français": 4,
    "Anglais": 3, "Histoire-Géographie": 3, "Philosophie": 2, "EPS": 2,
}

_LYCEE_L_CURRICULUM = {
    "Français": 6, "Philosophie": 5, "Histoire-Géographie": 4, "Anglais": 4,
    "Espagnol": 3, "Mathématiques": 3, "EPS": 2, "Arts": 2,
}


def _generate_template(template_type: str, class_count_per_level: int = 1) -> dict:
    """Generate a pre-filled school template.

    Returns data that can be merged into school_data.
    """
    classes = []
    curriculum_entries = []
    subjects = []

    if template_type == "college_standard":
        levels = ["6ème", "5ème", "4ème", "3ème"]
        curriculum_def = _COLLEGE_CURRICULUM
    elif template_type == "lycee_s":
        levels = ["2nde", "1ère S", "Tle S"]
        curriculum_def = _LYCEE_S_CURRICULUM
    elif template_type == "lycee_l":
        levels = ["2nde", "1ère L", "Tle L"]
        curriculum_def = _LYCEE_L_CURRICULUM
    elif template_type == "lycee_mixte":
        levels = ["2nde", "1ère S", "1ère L", "Tle S", "Tle L"]
        curriculum_def = {**_LYCEE_S_CURRICULUM, **_LYCEE_L_CURRICULUM}
    else:
        levels = ["CP", "CE1", "CE2", "CM1", "CM2"]
        curriculum_def = {"Français": 8, "Mathématiques": 5, "Éveil": 3, "EPS": 2}

    # Generate subjects
    colors = ["#3b82f6", "#ef4444", "#22c55e", "#f59e0b", "#8b5cf6",
              "#ec4899", "#06b6d4", "#84cc16", "#f97316"]
    for i, (subj_name, _) in enumerate(curriculum_def.items()):
        subjects.append({
            "name": subj_name,
            "short_name": subj_name[:4].upper(),
            "color": colors[i % len(colors)],
            "needs_room": True,
        })

    # Generate classes
    suffixes = "ABCDE"[:class_count_per_level]
    for level in levels:
        for suffix in suffixes:
            class_name = f"{level} {suffix}" if class_count_per_level > 1 else level
            classes.append({
                "name": class_name,
                "level": level,
                "student_count": 35,
            })

            # Generate curriculum for this class
            for subj_name, hours in curriculum_def.items():
                # Skip series-specific subjects for wrong classes
                if "S" in class_name and subj_name in ["Espagnol", "Arts"]:
                    continue
                if "L" in class_name and subj_name == "SVT":
                    continue

                curriculum_entries.append({
                    "school_class": class_name,
                    "subject": subj_name,
                    "total_minutes_per_week": hours * 60,
                    "sessions_per_week": hours,
                    "minutes_per_session": 55,
                })

    return {
        "template_type": template_type,
        "classes": classes,
        "subjects": subjects,
        "curriculum": curriculum_entries,
        "days": ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"],
        "sessions": [
            {"name": "Matin", "start_time": "08:00", "end_time": "12:30"},
            {"name": "Après-midi", "start_time": "15:00", "end_time": "17:00"},
        ],
        "base_unit_minutes": 55,
    }


def _dispatch_tool_calls(
    sid: str,
    tool_calls: list[dict],
    *,
    input_key: str = "data",
) -> dict:
    """Process AI tool calls: stage saves, apply metadata, return summary.

    ``input_key`` adapts to different schemas — ``process_chat`` uses "data",
    ``stream_chat`` uses "input".
    """
    saved_types: list[str] = []
    pending: list[dict] = []
    trigger_generation = False
    proposed_options: list[dict] = []
    set_step: int | None = None
    workload_analysis: dict | None = None
    template_data: dict | None = None

    for tc in tool_calls:
        name = tc["name"]
        data = tc[input_key]
        if name == "trigger_generation":
            trigger_generation = True
        elif name == "propose_options":
            proposed_options = data.get("options", [])
        elif name == "set_current_step":
            set_step = data.get("step")
        elif name == "analyze_workload":
            check_type = data.get("check_type", "all")
            workload_analysis = _analyze_workload(sid, check_type)
        elif name == "suggest_template":
            template_type = data.get("template_type", "college_standard")
            class_count = data.get("class_count_per_level", 1)
            template_data = _generate_template(template_type, class_count)
        elif name in _SAVE_TOOLS:
            pending.append({
                "tool":    name,
                "input":   data,
                "preview": _make_preview(name, data),
                "label":   _pending_label(name, data),
            })
            saved_types.append(name)
        else:
            _merge_tool_call(sid, name, data)

    if pending:
        sessions[sid]["pending_changes"] = (
            sessions[sid].get("pending_changes", []) + pending
        )

    # Fallback: inject default options if AI forgot to call propose_options
    if not proposed_options and pending:
        # Save tools were called but no options provided → add confirm/modify
        proposed_options = [
            {"label": "✅ Confirmer", "value": "Confirmer"},
            {"label": "✏️ Modifier", "value": "Je veux modifier"},
        ]

    return {
        "pending":            pending,
        "trigger_generation": trigger_generation,
        "options":            proposed_options,
        "set_step":           set_step,
        "saved_types":        saved_types,
        "workload_analysis":  workload_analysis,
        "template_data":      template_data,
    }


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
        conflict_reports=sessions[sid].get("last_conflict_reports") or None,
        solve_issues=sessions[sid].get("last_solve_issues") or None,
    )

    dispatch = _dispatch_tool_calls(sid, result["tool_calls"], input_key="data")
    sessions[sid]["ai_history"] = result["updated_history"]

    return {
        "message":            result["message"],
        "data_saved":         False,   # not yet — pending review
        "pending_changes":    dispatch["pending"],
        "trigger_generation": dispatch["trigger_generation"],
        "options":            dispatch["options"],
        "set_step":           dispatch["set_step"],
        "saved_types":        dispatch["saved_types"],
        "ai_history":         result["updated_history"],
    }


# ── AI chat (streaming SSE) ────────────────────────────────────────────────────

@app.post("/api/session/{sid}/chat/stream")
async def chat_stream(sid: str, payload: dict):
    """Send one chat turn to Claude; stream the response as SSE events."""
    if sid not in sessions:
        raise HTTPException(404, "Session not found")

    from timease.api.ai_chat import stream_chat

    provided_history = payload.get("ai_history")
    ai_history = (
        provided_history
        if provided_history is not None
        else sessions[sid]["ai_history"]
    )

    def _generate():
        tool_calls_buf: list[dict] = []
        updated_history: list[dict] = []

        for event in stream_chat(
            user_message=payload.get("message", ""),
            file_content=payload.get("file_content"),
            school_data=sessions[sid]["school_data"],
            teacher_assignments=sessions[sid]["teacher_assignments"],
            ai_history=ai_history,
            conflict_reports=sessions[sid].get("last_conflict_reports") or None,
            solve_issues=sessions[sid].get("last_solve_issues") or None,
        ):
            if event["type"] == "delta":
                yield f"data: {json.dumps({'type': 'delta', 'text': event['text']})}\n\n"

            elif event["type"] == "tool_call":
                tool_calls_buf.append(event)
                yield f"data: {json.dumps({'type': 'tool_start', 'name': event['name']})}\n\n"

            elif event["type"] == "end":
                updated_history = event["updated_history"]

                dispatch = _dispatch_tool_calls(
                    sid, tool_calls_buf, input_key="input",
                )
                sessions[sid]["ai_history"] = updated_history

                done_payload = {
                    "type":               "done",
                    "data_saved":         False,   # not yet — pending review
                    "pending_changes":    dispatch["pending"],
                    "trigger_generation": dispatch["trigger_generation"],
                    "options":            dispatch["options"],
                    "set_step":           dispatch["set_step"],
                    "saved_types":        dispatch["saved_types"],
                    "workload_analysis":  dispatch.get("workload_analysis"),
                    "template_data":      dispatch.get("template_data"),
                    "ai_history":         updated_history,
                }
                yield f"data: {json.dumps(done_payload)}\n\n"

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":       "keep-alive",
        },
    )


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
                "days":          sd.get("days", []),
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
