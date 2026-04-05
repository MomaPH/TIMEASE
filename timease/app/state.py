"""Global application state for TIMEASE."""

import json
import os
import pathlib
import uuid

from dotenv import load_dotenv

load_dotenv()

import reflex as rx
from pydantic import BaseModel

_COLLAB_DIR = pathlib.Path(__file__).parent.parent.parent / "collab"

_WEEK_DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"]
_DEFAULT_AVAIL = {d: "disponible" for d in _WEEK_DAYS}

class ThemeState(rx.State):
    is_dark: bool = False
    
    def toggle_theme(self):
        self.is_dark = not self.is_dark

class GridCell(BaseModel):
    """One cell in the timetable grid (one day × one time slot)."""

    day: str = ""
    subject: str = ""
    teacher: str = ""
    room: str = ""
    color: str = ""
    school_class: str = ""
    empty: bool = True


class GridRow(BaseModel):
    """One row in the timetable grid (one time slot across all days)."""

    time: str = ""
    cells: list[GridCell] = []


class AppState(rx.State):
    """Central state for the TIMEASE application."""

    # ─── School data ──────────────────────────────────────────────────
    school_data: dict = {}
    teacher_assignments: list[dict] = []

    # ─── Solver ───────────────────────────────────────────────────────
    timetable_result: dict = {}
    is_solving: bool = False
    solve_error: str = ""

    # ─── AI chat ──────────────────────────────────────────────────────
    # All messages carry exactly 4 keys (role, content, data_type, quick_replies).
    chat_messages: list[dict] = [
        {
            "role": "ai",
            "content": (
                "Bienvenue sur TIMEASE ! Je suis votre assistant pour créer l'emploi du temps de votre école. "
                "On commence ? Comment s'appelle votre établissement ?"
            ),
            "data_type": "",
            "quick_replies": ["Mon école s'appelle...", "Voici mon fichier Excel", "J'ai 4 classes"],
        }
    ]
    chat_input: str = ""
    is_ai_loading: bool = False
    pending_tool_calls: list[dict] = []
    ai_history: list[dict] = []

    # ─── UI navigation ────────────────────────────────────────────────
    current_step: int = 1
    active_config_tab: str = "chat"   # "chat" | "forms" | "file"
    active_result_tab: str = "class"
    active_forms_tab: str = "school"  # "school" | "teachers" | "classes" | "rooms"
    selected_class: str = ""
    selected_teacher: str = ""
    selected_room: str = ""

    # ─── File upload ──────────────────────────────────────────────────
    upload_status: str = ""      # "" | "loading" | "success" | "error"
    upload_message: str = ""

    # ─── Programme form ───────────────────────────────────────────────
    form_curriculum: list[dict] = []
    curriculum_save_message: str = ""

    # ─── Constraints form ─────────────────────────────────────────────
    selected_constraint_type: str = ""
    cf_hour: str = "08:00"
    cf_level: str = ""
    cf_day: str = "lundi"
    cf_session: str = ""
    cf_max_hours: int = 3
    cf_subject: str = ""
    cf_days: list[str] = []
    cf_class_name: str = ""
    cf_teacher_name: str = ""
    cf_time: str = "08:00"
    cf_period: str = "Matin"
    cf_priority: int = 5
    cf_subjects: list[str] = []

    # ─── Collaboration ────────────────────────────────────────────────
    collab_links: list[dict] = []
    current_plan: str = "Découverte"

    # ─── School form ──────────────────────────────────────────────────
    form_school_name: str = ""
    form_school_year: str = ""
    form_school_city: str = ""
    form_days: list[str] = ["lundi", "mardi", "mercredi", "jeudi", "vendredi"]
    form_sessions: list[dict] = [
        {"id": 0, "name": "Matin", "start_time": "07:30", "end_time": "12:00"},
        {"id": 1, "name": "Après-midi", "start_time": "13:00", "end_time": "17:30"},
    ]
    form_session_next_id: int = 2
    form_base_unit: str = "30"

    # ─── Teacher dialog ───────────────────────────────────────────────
    show_teacher_dialog: bool = False
    teacher_edit_index: int = -1
    form_teacher_name: str = ""
    form_teacher_subjects: list[str] = []
    form_teacher_max_hours: str = "18"
    form_teacher_avail: dict = dict(_DEFAULT_AVAIL)

    # ─── Class dialog ─────────────────────────────────────────────────
    show_class_dialog: bool = False
    class_edit_index: int = -1
    form_class_name: str = ""
    form_class_level: str = ""
    form_class_count: str = "30"

    # ─── Room dialog ──────────────────────────────────────────────────
    show_room_dialog: bool = False
    room_edit_index: int = -1
    form_room_name: str = ""
    form_room_capacity: str = "40"
    form_room_types: str = "Salle standard"

    # ─── Delete confirmation ──────────────────────────────────────────
    show_delete_dialog: bool = False
    delete_type: str = ""
    delete_index: int = -1

    # =================================================================
    # Computed vars
    # =================================================================

    @rx.var
    def teacher_count(self) -> int:
        return len(self.school_data.get("teachers", []))

    @rx.var
    def class_count(self) -> int:
        return len(self.school_data.get("classes", []))

    @rx.var
    def room_count(self) -> int:
        return len(self.school_data.get("rooms", []))

    @rx.var
    def constraint_count(self) -> int:
        return len(self.school_data.get("constraints", []))

    @rx.var
    def curriculum_count(self) -> int:
        return len(self.school_data.get("curriculum", []))

    @rx.var
    def subject_count(self) -> int:
        return len(self.school_data.get("subjects", []))

    @rx.var
    def assignment_count(self) -> int:
        return len(self.teacher_assignments)

    @rx.var
    def school_name_display(self) -> str:
        return self.school_data.get("name", "") or ""

    @rx.var
    def has_timetable(self) -> bool:
        return bool(self.timetable_result)

    @rx.var
    def progress_percent(self) -> int:
        score = 0
        if self.school_data.get("name"):
            score += 17
        if self.teacher_count > 0:
            score += 17
        if self.class_count > 0:
            score += 17
        if self.room_count > 0:
            score += 17
        if self.school_data.get("curriculum"):
            score += 17
        if self.constraint_count > 0:
            score += 15
        return min(score, 100)

    @rx.var
    def steps_done(self) -> int:
        done = 0
        if self.school_data.get("name"):
            done += 1
        if self.teacher_count > 0:
            done += 1
        if self.class_count > 0:
            done += 1
        if self.room_count > 0:
            done += 1
        if self.curriculum_count > 0:
            done += 1
        return done

    @rx.var
    def school_configured(self) -> int:
        """1 if school info is set, 0 otherwise."""
        return 1 if self.school_data.get("name") else 0

    @rx.var
    def current_suggestions(self) -> list[str]:
        """Last AI message's quick_replies, or defaults."""
        for msg in reversed(self.chat_messages):
            if msg.get("role") == "ai" and msg.get("quick_replies"):
                return list(msg["quick_replies"])
        return ["Mon école s'appelle...", "Voici mon fichier Excel", "J'ai 4 classes"]

    @rx.var
    def can_generate(self) -> bool:
        """True when minimum data for solver is present."""
        return (
            self.class_count > 0
            and self.teacher_count > 0
            and self.assignment_count > 0
            and self.curriculum_count > 0
        )

    @rx.var
    def programme_rows(self) -> list[dict]:
        """Flat list of rows (header / entry / total) for the programme table.

        Using a flat list avoids nested rx.foreach which Reflex cannot type-check
        when the inner iterable comes from a dict value access.
        """
        groups: dict[str, list[dict]] = {}
        order: list[str] = []
        for entry in self.form_curriculum:
            lv = entry.get("level", "")
            if lv not in groups:
                groups[lv] = []
                order.append(lv)
            groups[lv].append(entry)

        _blank: dict = {
            "subject": "", "total_minutes_per_week": "", "mode": "Auto",
            "sessions_per_week": "", "minutes_per_session": "",
            "min_session_minutes": "", "max_session_minutes": "", "_idx": -1,
        }
        rows: list[dict] = []
        for lv in order:
            total = sum(
                int(e.get("total_minutes_per_week", 0) or 0) for e in groups[lv]
            )
            rows.append({**_blank, "_row_type": "header", "level": lv, "total": str(total)})
            for e in groups[lv]:
                rows.append({**e, "_row_type": "entry", "total": ""})
            rows.append({**_blank, "_row_type": "total", "level": lv, "total": str(total)})
        return rows

    @rx.var
    def subjects_list(self) -> list[str]:
        """Subject names available for teacher assignment."""
        subjects = self.school_data.get("subjects", [])
        return [s["name"] if isinstance(s, dict) else s for s in subjects]

    @rx.var
    def teachers_names(self) -> list[str]:
        return [t.get("name", "") for t in self.school_data.get("teachers", [])]

    @rx.var
    def classes_names(self) -> list[str]:
        return [c.get("name", "") for c in self.school_data.get("classes", [])]

    @rx.var
    def levels_list(self) -> list[str]:
        seen: list[str] = []
        for c in self.school_data.get("classes", []):
            lv = c.get("level", "")
            if lv and lv not in seen:
                seen.append(lv)
        return seen

    @rx.var
    def sessions_list(self) -> list[str]:
        return [s.get("name", "") for s in self.school_data.get("sessions", [])]

    @rx.var
    def constraints_indexed(self) -> list[dict]:
        """Constraints list with _idx injected for delete handler."""
        return [
            {
                "_idx": i,
                "id": c.get("id", ""),
                "type": c.get("type", "hard"),
                "category": c.get("category", ""),
                "description_fr": c.get("description_fr", ""),
                "priority": c.get("priority", 10),
            }
            for i, c in enumerate(self.school_data.get("constraints", []))
        ]

    @rx.var
    def cf_priority_label(self) -> str:
        p = self.cf_priority
        if p <= 2:
            return "Peu important"
        if p <= 4:
            return "Normal"
        if p <= 6:
            return "Modéré"
        if p <= 8:
            return "Important"
        return "Essentiel"

    # Per-type constraint counts for the left-panel badges
    @rx.var
    def cnt_h1(self) -> int:
        return sum(1 for c in self.school_data.get("constraints", []) if c.get("category") == "H1")

    @rx.var
    def cnt_h3(self) -> int:
        return sum(1 for c in self.school_data.get("constraints", []) if c.get("category") == "H3")

    @rx.var
    def cnt_h4(self) -> int:
        return sum(1 for c in self.school_data.get("constraints", []) if c.get("category") == "H4")

    @rx.var
    def cnt_h5(self) -> int:
        return sum(1 for c in self.school_data.get("constraints", []) if c.get("category") == "H5")

    @rx.var
    def cnt_h6(self) -> int:
        return sum(1 for c in self.school_data.get("constraints", []) if c.get("category") == "H6")

    @rx.var
    def cnt_h9(self) -> int:
        return sum(1 for c in self.school_data.get("constraints", []) if c.get("category") == "H9")

    @rx.var
    def cnt_s1(self) -> int:
        return sum(1 for c in self.school_data.get("constraints", []) if c.get("category") == "S1")

    @rx.var
    def cnt_s3(self) -> int:
        return sum(1 for c in self.school_data.get("constraints", []) if c.get("category") == "S3")

    @rx.var
    def cnt_s4(self) -> int:
        return sum(1 for c in self.school_data.get("constraints", []) if c.get("category") == "S4")

    @rx.var
    def cnt_s5(self) -> int:
        return sum(1 for c in self.school_data.get("constraints", []) if c.get("category") == "S5")

    @rx.var
    def teachers_table(self) -> list[dict]:
        """Teachers formatted for table display (includes _idx)."""
        rows = []
        for i, t in enumerate(self.school_data.get("teachers", [])):
            rows.append({
                "_idx": i,
                "name": t.get("name", ""),
                "subjects_str": ", ".join(t.get("subjects", [])) or "—",
                "max_hours": str(t.get("max_hours_per_week", "")) + "h",
                "unavail": str(len(t.get("unavailable_slots", []))) + " jour(s)",
            })
        return rows

    @rx.var
    def classes_table(self) -> list[dict]:
        """Classes formatted for table display (includes _idx)."""
        rows = []
        for i, c in enumerate(self.school_data.get("classes", [])):
            rows.append({
                "_idx": i,
                "name": c.get("name", ""),
                "level": c.get("level", "—"),
                "count": str(c.get("student_count", "")),
            })
        return rows

    @rx.var
    def rooms_table(self) -> list[dict]:
        """Rooms formatted for table display (includes _idx)."""
        rows = []
        for i, r in enumerate(self.school_data.get("rooms", [])):
            rows.append({
                "_idx": i,
                "name": r.get("name", ""),
                "capacity": str(r.get("capacity", "")),
                "types": ", ".join(r.get("types", [])) or "—",
            })
        return rows

    @rx.var
    def delete_label(self) -> str:
        """Human-readable label for what is being deleted."""
        mapping = {"teacher": "enseignant", "class": "classe", "room": "salle"}
        return mapping.get(self.delete_type, "élément")

    # =================================================================
    # Timetable result computed vars
    # =================================================================

    @rx.var
    def result_time_slots(self) -> list[str]:
        """Unique sorted start_times from assignments."""
        if not self.timetable_result:
            return []
        times = sorted(set(
            a["start_time"]
            for a in self.timetable_result.get("assignments", [])
        ))
        return times

    @rx.var
    def result_days_list(self) -> list[str]:
        return self.timetable_result.get(
            "days", ["lundi", "mardi", "mercredi", "jeudi", "vendredi"]
        )

    @rx.var
    def result_classes_list(self) -> list[str]:
        if not self.timetable_result:
            return []
        return sorted(set(
            a["school_class"]
            for a in self.timetable_result.get("assignments", [])
        ))

    @rx.var
    def result_teachers_list(self) -> list[str]:
        if not self.timetable_result:
            return []
        return sorted(set(
            a["teacher"]
            for a in self.timetable_result.get("assignments", [])
        ))

    @rx.var
    def result_rooms_list(self) -> list[str]:
        if not self.timetable_result:
            return []
        return sorted(set(
            a["room"]
            for a in self.timetable_result.get("assignments", [])
            if a.get("room")
        ))

    @rx.var
    def filtered_grid_assignments(self) -> list[dict]:
        """Assignments filtered by active tab + selected entity."""
        if not self.timetable_result:
            return []
        assignments = self.timetable_result.get("assignments", [])
        tab = self.active_result_tab
        if tab == "class" and self.selected_class:
            return [a for a in assignments if a["school_class"] == self.selected_class]
        elif tab == "teacher" and self.selected_teacher:
            return [a for a in assignments if a["teacher"] == self.selected_teacher]
        elif tab == "room" and self.selected_room:
            return [a for a in assignments if a.get("room") == self.selected_room]
        return assignments

    @rx.var
    def result_soft_details(self) -> list[dict]:
        if not self.timetable_result:
            return []
        return self.timetable_result.get("soft_details", [])

    @rx.var
    def result_subjects_summary(self) -> list[dict]:
        """Per-subject aggregation for the 'Par matière' tab."""
        if not self.timetable_result:
            return []
        from collections import defaultdict
        summary: dict = defaultdict(lambda: {
            "subject": "", "color": "", "teachers": set(),
            "hours": 0, "classes": set(), "days": set(),
        })
        for a in self.timetable_result.get("assignments", []):
            s = a["subject"]
            summary[s]["subject"] = s
            summary[s]["color"]   = a.get("color", "")
            summary[s]["teachers"].add(a["teacher"])
            summary[s]["hours"]  += 1
            summary[s]["classes"].add(a["school_class"])
            summary[s]["days"].add(a["day"])
        return [
            {
                "subject":  v["subject"],
                "color":    v["color"],
                "teachers": ", ".join(sorted(v["teachers"])),
                "hours":    v["hours"],
                "classes":  ", ".join(sorted(v["classes"])),
                "days":     ", ".join(sorted(v["days"])),
            }
            for v in summary.values()
        ]

    @rx.var
    def grid_rows(self) -> list[GridRow]:
        """Pre-flattened grid data typed as list[GridRow] for rx.foreach."""
        if not self.timetable_result:
            return []
        assignments = self.filtered_grid_assignments
        days  = self.result_days_list
        times = self.result_time_slots
        lookup: dict = {}
        for a in assignments:
            lookup[(a["day"], a["start_time"])] = a
        rows: list[GridRow] = []
        for t in times:
            cells: list[GridCell] = []
            for d in days:
                a = lookup.get((d, t))
                if a:
                    cells.append(GridCell(
                        day=d,
                        subject=a["subject"],
                        teacher=a["teacher"],
                        room=a.get("room", ""),
                        color=a.get("color", "#E2E8F0"),
                        school_class=a.get("school_class", ""),
                        empty=False,
                    ))
                else:
                    cells.append(GridCell(day=d, empty=True))
            rows.append(GridRow(time=t, cells=cells))
        return rows

    # =================================================================
    # Navigation setters
    # =================================================================

    def set_active_config_tab(self, value: str) -> None:
        self.active_config_tab = value
        if value == "forms":
            self._load_school_form()

    def set_forms_tab(self, value: str) -> None:
        self.active_forms_tab = value

    def set_result_tab(self, value: str) -> None:
        self.active_result_tab = value

    def set_selected_class(self, value: str) -> None:
        self.selected_class = value

    def set_selected_teacher(self, value: str) -> None:
        self.selected_teacher = value

    def set_selected_room(self, value: str) -> None:
        self.selected_room = value

    # =================================================================
    # Collaboration
    # =================================================================

    def generate_links(self) -> None:
        """Generate UUID tokens for each teacher and save JSON files."""
        _COLLAB_DIR.mkdir(exist_ok=True)

        teachers = self.school_data.get("teachers", [])
        if not teachers:
            teachers = [
                {"name": "M. Diallo"},
                {"name": "Mme Koné"},
                {"name": "M. Traoré"},
            ]

        school = self.school_data.get("name", "École TIMEASE")
        links: list[dict] = []
        for teacher in teachers:
            name = teacher.get("name", "Enseignant")
            token = str(uuid.uuid4())
            data = {
                "token": token,
                "teacher_name": name,
                "school_name": school,
                "status": "pending",
                "availability": {},
                "preferences": "",
                "has_timetable": False,
                "timetable_assignments": [],
                "preference_feedback": [],
            }
            (_COLLAB_DIR / f"{token}.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=2)
            )
            links.append({
                "teacher": name,
                "token": token,
                "link": f"/collab/{token}",
                "status": "pending",
            })

        self.collab_links = links

    def set_chat_input(self, value: str) -> None:
        self.chat_input = value

    async def send_quick_reply(self, reply: str):
        """Set chat input to reply text and immediately send it."""
        self.chat_input = reply
        async for _ in type(self).send_chat_message(self):
            yield

    # =================================================================
    # Constraint form handlers
    # =================================================================

    def set_selected_constraint_type(self, value: str) -> None:
        self.selected_constraint_type = value
        # Reset shared multi-select fields when switching type
        self.cf_days = []
        self.cf_subjects = []

    def set_cf_hour(self, v: str) -> None:
        self.cf_hour = v

    def set_cf_level(self, v: str) -> None:
        self.cf_level = v

    def set_cf_day(self, v: str) -> None:
        self.cf_day = v

    def set_cf_session(self, v: str) -> None:
        self.cf_session = v

    def set_cf_max_hours(self, v: list) -> None:
        self.cf_max_hours = int(v[0]) if v else 3

    def set_cf_subject(self, v: str) -> None:
        self.cf_subject = v

    def toggle_cf_day(self, day: str, checked: bool) -> None:
        if checked and day not in self.cf_days:
            self.cf_days = [*self.cf_days, day]
        elif not checked:
            self.cf_days = [d for d in self.cf_days if d != day]

    def set_cf_class_name(self, v: str) -> None:
        self.cf_class_name = v

    def set_cf_teacher_name(self, v: str) -> None:
        self.cf_teacher_name = v

    def set_cf_time(self, v: str) -> None:
        self.cf_time = v

    def set_cf_period(self, v: str) -> None:
        self.cf_period = v

    def set_cf_priority(self, v: list) -> None:
        self.cf_priority = int(v[0]) if v else 5

    def toggle_cf_subject(self, subject: str, checked: bool) -> None:
        if checked and subject not in self.cf_subjects:
            self.cf_subjects = [*self.cf_subjects, subject]
        elif not checked:
            self.cf_subjects = [s for s in self.cf_subjects if s != subject]

    def add_constraint(self) -> None:
        """Build and persist a constraint from current cf_* form state."""
        ct = self.selected_constraint_type
        if not ct:
            return
        is_hard = ct.startswith("H")
        params: dict = {}
        description = ""

        if ct == "H1":
            params = {"hour": self.cf_hour}
            description = f"Heure de début des cours : {self.cf_hour}"
        elif ct == "H3":
            session_str = f" ({self.cf_session})" if self.cf_session else ""
            scope = self.cf_level or "Tous niveaux"
            params = {"level": scope, "day": self.cf_day, "session": self.cf_session}
            description = f"{scope} — demi-journée libre : {self.cf_day}{session_str}"
        elif ct == "H4":
            params = {"max_consecutive_hours": self.cf_max_hours}
            description = f"Maximum {self.cf_max_hours} heures consécutives"
        elif ct == "H5":
            days_str = ", ".join(self.cf_days) if self.cf_days else "—"
            params = {"subject": self.cf_subject, "allowed_days": list(self.cf_days)}
            description = f"{self.cf_subject or '—'} doit être placé le(s) : {days_str}"
        elif ct == "H6":
            days_str = ", ".join(self.cf_days) if self.cf_days else "—"
            params = {"subject": self.cf_subject, "forbidden_days": list(self.cf_days)}
            description = f"{self.cf_subject or '—'} interdit le(s) : {days_str}"
        elif ct == "H9":
            params = {
                "class_name": self.cf_class_name,
                "subject": self.cf_subject,
                "teacher": self.cf_teacher_name,
                "day": self.cf_day,
                "time": self.cf_time,
            }
            description = (
                f"Affectation fixe : {self.cf_teacher_name or '—'} — "
                f"{self.cf_subject or '—'} avec {self.cf_class_name or '—'}"
                f" le {self.cf_day} à {self.cf_time}"
            )
        elif ct == "S1":
            params = {
                "teacher": self.cf_teacher_name,
                "period": self.cf_period,
                "priority": self.cf_priority,
            }
            description = (
                f"Préférence horaire : {self.cf_teacher_name or '—'}"
                f" préfère {self.cf_period} (priorité {self.cf_priority})"
            )
        elif ct == "S3":
            params = {"priority": self.cf_priority}
            description = f"Charge quotidienne équilibrée (priorité {self.cf_priority})"
        elif ct == "S4":
            params = {"priority": self.cf_priority}
            description = f"Matières réparties sur la semaine (priorité {self.cf_priority})"
        elif ct == "S5":
            subs_str = ", ".join(self.cf_subjects) if self.cf_subjects else "—"
            params = {"subjects": list(self.cf_subjects), "priority": self.cf_priority}
            description = (
                f"Matières lourdes le matin : {subs_str}"
                f" (priorité {self.cf_priority})"
            )
        else:
            return

        existing = self.school_data.get("constraints", [])
        constraint = {
            "id": f"{ct}_{len(existing) + 1}",
            "type": "hard" if is_hard else "soft",
            "category": ct,
            "description_fr": description,
            "priority": 10 if is_hard else self.cf_priority,
            "parameters": params,
        }
        merged = dict(self.school_data)
        merged["constraints"] = [*existing, constraint]
        self.school_data = merged

    def delete_constraint(self, index: int) -> None:
        """Remove a constraint by index."""
        merged = dict(self.school_data)
        constraints = list(merged.get("constraints", []))
        if 0 <= index < len(constraints):
            constraints.pop(index)
        merged["constraints"] = constraints
        self.school_data = merged

    # =================================================================
    # AI chat handlers
    # =================================================================

    async def handle_chat_key(self, key: str):
        """Trigger send_chat_message when Enter is pressed."""
        if key == "Enter":
            async for _ in type(self).send_chat_message(self):
                yield

    async def send_chat_message(self):
        """Append user message, call AI, append response."""
        if not self.chat_input.strip():
            return

        user_msg = self.chat_input
        self.chat_messages.append({"role": "user", "content": user_msg, "data_type": "", "quick_replies": []})
        self.chat_input = ""
        self.is_ai_loading = True
        yield

        try:
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not api_key:
                self.chat_messages.append({
                    "role": "ai",
                    "content": "Clé API Anthropic non configurée. Ajoutez ANTHROPIC_API_KEY dans le fichier .env",
                    "data_type": "",
                    "quick_replies": [],
                })
                self.is_ai_loading = False
                yield
                return

            from timease.app.ai_setup import SetupAssistant, describe_tool_calls

            assistant = SetupAssistant(api_key=api_key)
            assistant.history = list(self.ai_history)
            response = assistant.process_message(
                user_message=user_msg,
                current_data=self.school_data,
                teacher_assignments=self.teacher_assignments,
            )
            self.ai_history = list(assistant.history)

            if response["message"]:
                self.chat_messages.append({
                    "role": "ai",
                    "content": response["message"],
                    "data_type": "",
                    "quick_replies": response["quick_replies"],
                })

            tool_calls = response["tool_calls"]
            if tool_calls:
                self.pending_tool_calls = tool_calls
                self.chat_messages.append({
                    "role": "confirm",
                    "content": describe_tool_calls(tool_calls),
                    "data_type": "",
                    "quick_replies": [],
                })

        except Exception as exc:
            self.chat_messages.append({
                "role": "ai",
                "content": f"Erreur: {exc}. Réessayez ou utilisez l'onglet Formulaires.",
                "data_type": "",
                "quick_replies": [],
            })

        self.is_ai_loading = False
        yield

    def confirm_extracted_data(self) -> None:
        """Apply all pending tool calls to the school data."""
        if not self.pending_tool_calls:
            return
        for tc in self.pending_tool_calls:
            self._apply_tool_call(tc["name"], tc["data"])
        self.pending_tool_calls = []
        n = self.teacher_count + self.class_count + self.room_count
        self.chat_messages.append({
            "role": "ai",
            "content": "Données enregistrées ! Vous pouvez les vérifier dans le panneau de droite.",
            "data_type": "",
            "quick_replies": ["Continuer la configuration", "Voir ce qui est enregistré"],
        })

    def reject_extracted_data(self) -> None:
        """Discard pending tool calls."""
        self.pending_tool_calls = []
        self.chat_messages.append({
            "role": "ai",
            "content": "D'accord, rien n'a été enregistré. Corrigez et renvoyez-moi les bonnes informations.",
            "data_type": "",
            "quick_replies": [],
        })

    def _apply_tool_call(self, name: str, data: dict) -> None:
        """Merge one tool call's data into school_data / teacher_assignments."""
        merged = dict(self.school_data)
        if name == "save_school_info":
            merged.update({k: v for k, v in data.items() if v is not None})
        elif name in (
            "save_teachers", "save_classes", "save_rooms",
            "save_subjects", "save_curriculum", "save_constraints",
        ):
            key = name.replace("save_", "")
            existing = list(merged.get(key, []))
            existing.extend(data.get(key, []))
            merged[key] = existing
        elif name == "save_assignments":
            existing = list(self.teacher_assignments)
            existing.extend(data.get("assignments", []))
            self.teacher_assignments = existing
        self.school_data = merged

    async def run_generate(self):
        """Trigger CP-SAT solver. Redirects on success, appends error on failure."""
        self.is_solving = True
        yield
        try:
            from timease.engine.models import (
                SchoolData, School, TimeslotConfig, SessionConfig,
                Subject, Teacher, SchoolClass, Room,
                CurriculumEntry, Constraint, TeacherAssignment,
            )
            from timease.engine.solver import TimetableSolver
            sd = self.school_data
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
                        SessionConfig(**s)
                        for s in sd.get("sessions", [{"name": "Matin", "start_time": "08:00", "end_time": "13:00"}])
                    ],
                ),
                subjects=[Subject(**s) for s in sd.get("subjects", [])],
                teachers=[Teacher(**t) for t in sd.get("teachers", [])],
                classes=[SchoolClass(**c) for c in sd.get("classes", [])],
                rooms=[Room(**r) for r in sd.get("rooms", [])],
                curriculum=[CurriculumEntry(**e) for e in sd.get("curriculum", [])],
                constraints=[Constraint(**c) for c in sd.get("constraints", [])],
                teacher_assignments=[
                    TeacherAssignment(**ta) for ta in self.teacher_assignments
                ],
            )
            errors = school_obj.validate()
            if errors:
                self.chat_messages.append({
                    "role": "ai",
                    "content": "Erreurs :\n" + "\n".join(f"• {e}" for e in errors),
                    "data_type": "",
                    "quick_replies": [],
                })
                self.is_solving = False
                yield
                return
            result = TimetableSolver().solve(school_obj, timeout_seconds=120)
            if result.solved:
                subj_colors = {s.name: s.color for s in school_obj.subjects}
                self.timetable_result = {
                    "assignments": [
                        {
                            "school_class": a.school_class,
                            "subject":      a.subject,
                            "teacher":      a.teacher,
                            "room":         a.room or "",
                            "day":          a.day,
                            "start_time":   a.start_time,
                            "end_time":     a.end_time,
                            "color":        subj_colors.get(a.subject, "#E2E8F0"),
                        }
                        for a in result.assignments
                    ],
                    "solve_time": result.solve_time_seconds,
                    "soft_details": (
                        result.soft_constraint_details
                        if hasattr(result, "soft_constraint_details")
                        else []
                    ),
                    "days": sd.get("days", []),
                    "base_unit_minutes": int(sd.get("base_unit_minutes", 30)),
                }
                self.chat_messages.append({
                    "role": "ai",
                    "content": (
                        f"Solution trouvée en {result.solve_time_seconds:.1f}s ! "
                        f"{len(result.assignments)} sessions planifiées."
                    ),
                    "data_type": "",
                    "quick_replies": [],
                })
            else:
                self.chat_messages.append({
                    "role": "ai",
                    "content": "Aucune solution trouvée. Vérifiez vos contraintes.",
                    "data_type": "",
                    "quick_replies": [],
                })
        except Exception as exc:
            import traceback
            traceback.print_exc()
            self.chat_messages.append({
                "role": "ai",
                "content": f"Erreur : {exc}",
                "data_type": "",
                "quick_replies": [],
            })
        finally:
            self.is_solving = False
        yield

    async def handle_chat_file_upload(self, files: list[rx.UploadFile]) -> None:
        """Stub — file-in-chat upload to be implemented in a future session."""

    # =================================================================
    # School form handlers
    # =================================================================

    def set_form_school_name(self, v: str) -> None:
        self.form_school_name = v

    def set_form_school_year(self, v: str) -> None:
        self.form_school_year = v

    def set_form_school_city(self, v: str) -> None:
        self.form_school_city = v

    def set_form_base_unit(self, v: str) -> None:
        self.form_base_unit = v

    def toggle_day(self, day: str, checked: bool) -> None:
        if checked and day not in self.form_days:
            self.form_days = [*self.form_days, day]
        elif not checked:
            self.form_days = [d for d in self.form_days if d != day]

    def add_session(self) -> None:
        sid = self.form_session_next_id
        self.form_sessions = [
            *self.form_sessions,
            {"id": sid, "name": "", "start_time": "08:00", "end_time": "12:00"},
        ]
        self.form_session_next_id = sid + 1

    def remove_session(self, sid: int) -> None:
        self.form_sessions = [s for s in self.form_sessions if s["id"] != sid]

    def update_session_name(self, sid: int, v: str) -> None:
        self.form_sessions = [
            {**s, "name": v} if s["id"] == sid else s for s in self.form_sessions
        ]

    def update_session_start(self, sid: int, v: str) -> None:
        self.form_sessions = [
            {**s, "start_time": v} if s["id"] == sid else s
            for s in self.form_sessions
        ]

    def update_session_end(self, sid: int, v: str) -> None:
        self.form_sessions = [
            {**s, "end_time": v} if s["id"] == sid else s for s in self.form_sessions
        ]

    def save_school_info(self) -> None:
        merged = dict(self.school_data)
        merged["name"] = self.form_school_name.strip()
        merged["academic_year"] = self.form_school_year.strip()
        merged["city"] = self.form_school_city.strip()
        merged["days"] = list(self.form_days)
        merged["sessions"] = [
            {"name": s["name"], "start_time": s["start_time"], "end_time": s["end_time"]}
            for s in self.form_sessions
            if s["name"].strip()
        ]
        merged["base_unit_minutes"] = int(self.form_base_unit or "30")
        self.school_data = merged

    # =================================================================
    # Teacher dialog handlers
    # =================================================================

    def open_teacher_dialog(self, index: int) -> None:
        self.teacher_edit_index = index
        if index == -1:
            self.form_teacher_name = ""
            self.form_teacher_subjects = []
            self.form_teacher_max_hours = "18"
            self.form_teacher_avail = dict(_DEFAULT_AVAIL)
        else:
            teachers = self.school_data.get("teachers", [])
            if 0 <= index < len(teachers):
                t = teachers[index]
                self.form_teacher_name = t.get("name", "")
                self.form_teacher_subjects = list(t.get("subjects", []))
                self.form_teacher_max_hours = str(t.get("max_hours_per_week", 18))
                avail = dict(_DEFAULT_AVAIL)
                for slot in t.get("unavailable_slots", []):
                    d = slot.get("day", "")
                    if d in avail:
                        avail[d] = "impossible"
                self.form_teacher_avail = avail
        self.show_teacher_dialog = True

    def close_teacher_dialog(self) -> None:
        self.show_teacher_dialog = False

    def set_form_teacher_name(self, v: str) -> None:
        self.form_teacher_name = v

    def set_form_teacher_max_hours(self, v: str) -> None:
        self.form_teacher_max_hours = v

    def toggle_teacher_subject(self, subject: str, checked: bool) -> None:
        if checked and subject not in self.form_teacher_subjects:
            self.form_teacher_subjects = [*self.form_teacher_subjects, subject]
        elif not checked:
            self.form_teacher_subjects = [
                s for s in self.form_teacher_subjects if s != subject
            ]

    def set_teacher_avail_day(self, day: str, status: str) -> None:
        avail = dict(self.form_teacher_avail)
        avail[day] = status
        self.form_teacher_avail = avail

    def save_teacher(self) -> None:
        if not self.form_teacher_name.strip():
            return
        unavailable = [
            {"day": d, "start": None, "end": None, "session": "all"}
            for d, status in self.form_teacher_avail.items()
            if status == "impossible"
        ]
        teacher = {
            "name": self.form_teacher_name.strip(),
            "subjects": list(self.form_teacher_subjects),
            "max_hours_per_week": int(self.form_teacher_max_hours or "18"),
            "unavailable_slots": unavailable,
            "preference_weight": 1.0,
        }
        merged = dict(self.school_data)
        teachers = list(merged.get("teachers", []))
        if self.teacher_edit_index == -1:
            teachers.append(teacher)
        elif 0 <= self.teacher_edit_index < len(teachers):
            teachers[self.teacher_edit_index] = teacher
        merged["teachers"] = teachers
        self.school_data = merged
        self.show_teacher_dialog = False

    # =================================================================
    # Class dialog handlers
    # =================================================================

    def open_class_dialog(self, index: int) -> None:
        self.class_edit_index = index
        if index == -1:
            self.form_class_name = ""
            self.form_class_level = ""
            self.form_class_count = "30"
        else:
            classes = self.school_data.get("classes", [])
            if 0 <= index < len(classes):
                c = classes[index]
                self.form_class_name = c.get("name", "")
                self.form_class_level = c.get("level", "")
                self.form_class_count = str(c.get("student_count", 30))
        self.show_class_dialog = True

    def close_class_dialog(self) -> None:
        self.show_class_dialog = False

    def set_form_class_name(self, v: str) -> None:
        self.form_class_name = v

    def set_form_class_level(self, v: str) -> None:
        self.form_class_level = v

    def set_form_class_count(self, v: str) -> None:
        self.form_class_count = v

    def save_class(self) -> None:
        if not self.form_class_name.strip():
            return
        school_class = {
            "name": self.form_class_name.strip(),
            "level": self.form_class_level.strip(),
            "student_count": int(self.form_class_count or "30"),
        }
        merged = dict(self.school_data)
        classes = list(merged.get("classes", []))
        if self.class_edit_index == -1:
            classes.append(school_class)
        elif 0 <= self.class_edit_index < len(classes):
            classes[self.class_edit_index] = school_class
        merged["classes"] = classes
        self.school_data = merged
        self.show_class_dialog = False

    # =================================================================
    # Room dialog handlers
    # =================================================================

    def open_room_dialog(self, index: int) -> None:
        self.room_edit_index = index
        if index == -1:
            self.form_room_name = ""
            self.form_room_capacity = "40"
            self.form_room_types = "Salle standard"
        else:
            rooms = self.school_data.get("rooms", [])
            if 0 <= index < len(rooms):
                r = rooms[index]
                self.form_room_name = r.get("name", "")
                self.form_room_capacity = str(r.get("capacity", 40))
                self.form_room_types = ", ".join(r.get("types", ["Salle standard"]))
        self.show_room_dialog = True

    def close_room_dialog(self) -> None:
        self.show_room_dialog = False

    def set_form_room_name(self, v: str) -> None:
        self.form_room_name = v

    def set_form_room_capacity(self, v: str) -> None:
        self.form_room_capacity = v

    def set_form_room_types(self, v: str) -> None:
        self.form_room_types = v

    def save_room(self) -> None:
        if not self.form_room_name.strip():
            return
        types = [t.strip() for t in self.form_room_types.split(",") if t.strip()]
        room = {
            "name": self.form_room_name.strip(),
            "capacity": int(self.form_room_capacity or "40"),
            "types": types or ["Salle standard"],
        }
        merged = dict(self.school_data)
        rooms = list(merged.get("rooms", []))
        if self.room_edit_index == -1:
            rooms.append(room)
        elif 0 <= self.room_edit_index < len(rooms):
            rooms[self.room_edit_index] = room
        merged["rooms"] = rooms
        self.school_data = merged
        self.show_room_dialog = False

    # =================================================================
    # Delete confirmation handlers
    # =================================================================

    def request_delete(self, dtype: str, index: int) -> None:
        self.delete_type = dtype
        self.delete_index = index
        self.show_delete_dialog = True

    def cancel_delete(self) -> None:
        self.show_delete_dialog = False
        self.delete_type = ""
        self.delete_index = -1

    def confirm_delete(self) -> None:
        merged = dict(self.school_data)
        key_map = {"teacher": "teachers", "class": "classes", "room": "rooms"}
        key = key_map.get(self.delete_type)
        if key:
            items = list(merged.get(key, []))
            if 0 <= self.delete_index < len(items):
                items.pop(self.delete_index)
            merged[key] = items
        self.school_data = merged
        self.show_delete_dialog = False
        self.delete_type = ""
        self.delete_index = -1

    # =================================================================
    # Private helpers
    # =================================================================

    # =================================================================
    # Programme page handlers
    # =================================================================

    _STANDARD_SUBJECTS: list[dict] = [
        {"subject": "Mathématiques", "total": 300, "min": 50, "max": 100},
        {"subject": "Français", "total": 300, "min": 50, "max": 100},
        {"subject": "Anglais", "total": 180, "min": 50, "max": 60},
        {"subject": "Histoire-Géographie", "total": 180, "min": 50, "max": 60},
        {"subject": "Sciences de la Vie et de la Terre", "total": 120, "min": 50, "max": 60},
        {"subject": "Physique-Chimie", "total": 120, "min": 50, "max": 60},
        {"subject": "Éducation Physique et Sportive", "total": 120, "min": 50, "max": 60},
        {"subject": "Informatique", "total": 60, "min": 50, "max": 60},
    ]

    def load_curriculum_form(self) -> None:
        """Load curriculum from school_data into form_curriculum for editing."""
        entries = self.school_data.get("curriculum", [])
        self.form_curriculum = [
            {
                "_idx": i,
                "level": e.get("level", ""),
                "subject": e.get("subject", ""),
                "total_minutes_per_week": str(e.get("total_minutes_per_week", 0) or 0),
                "mode": "Manuel" if e.get("mode", "auto") == "manual" else "Auto",
                "sessions_per_week": str(e.get("sessions_per_week", "") or ""),
                "minutes_per_session": str(e.get("minutes_per_session", "") or ""),
                "min_session_minutes": str(e.get("min_session_minutes", "") or ""),
                "max_session_minutes": str(e.get("max_session_minutes", "") or ""),
            }
            for i, e in enumerate(entries)
        ]
        self.curriculum_save_message = ""

    def update_curriculum_field(self, idx: int, field: str, value: str) -> None:
        """Update a single field of a curriculum entry in the form."""
        curriculum = list(self.form_curriculum)
        if 0 <= idx < len(curriculum):
            entry = dict(curriculum[idx])
            entry[field] = value
            curriculum[idx] = entry
            self.form_curriculum = curriculum

    def save_curriculum(self) -> None:
        """Persist form_curriculum back to school_data."""
        int_fields = {
            "total_minutes_per_week", "sessions_per_week", "minutes_per_session",
            "min_session_minutes", "max_session_minutes",
        }
        entries = []
        for e in self.form_curriculum:
            entry: dict = {}
            for k, v in e.items():
                if k == "_idx":
                    continue
                if k == "mode":
                    entry[k] = "manual" if v == "Manuel" else "auto"
                elif k in int_fields:
                    try:
                        entry[k] = int(v) if str(v).strip() else None
                    except (ValueError, TypeError):
                        entry[k] = None
                else:
                    entry[k] = v
            entries.append(entry)
        merged = dict(self.school_data)
        merged["curriculum"] = entries
        self.school_data = merged
        self.curriculum_save_message = "Programme enregistré avec succès."

    def prefill_standard_curriculum(self) -> None:
        """Pre-populate form_curriculum with a typical French-African school curriculum."""
        levels: list[str] = []
        for cls in self.school_data.get("classes", []):
            lv = cls.get("level", "")
            if lv and lv not in levels:
                levels.append(lv)
        if not levels:
            self.curriculum_save_message = (
                "Configurez d'abord vos classes (onglet Configuration) avant de pré-remplir."
            )
            return
        new_entries: list[dict] = []
        for lv in levels:
            for sub in self._STANDARD_SUBJECTS:
                new_entries.append({
                    "_idx": len(new_entries),
                    "level": lv,
                    "subject": sub["subject"],
                    "total_minutes_per_week": str(sub["total"]),
                    "mode": "Auto",
                    "sessions_per_week": "",
                    "minutes_per_session": "",
                    "min_session_minutes": str(sub["min"]),
                    "max_session_minutes": str(sub["max"]),
                })
        self.form_curriculum = new_entries
        self.curriculum_save_message = (
            f"Programme standard pré-rempli pour {len(levels)} niveau(x). "
            "Cliquez sur « Enregistrer » pour valider."
        )

    # =================================================================
    # File upload handler
    # =================================================================

    async def handle_file_upload(self, files: list[rx.UploadFile]):
        """Handle file upload: TIMEASE template → direct import; other → AI chat."""
        if not files:
            return
        self.upload_status = "loading"
        self.upload_message = ""
        yield

        import os
        import tempfile
        from pathlib import Path

        file = files[0]
        filename: str = getattr(file, "filename", None) or getattr(file, "name", "fichier")
        suffix = Path(filename).suffix.lower()

        try:
            data: bytes = await file.read()

            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(data)
                tmp_path = tmp.name

            try:
                if suffix == ".xlsx":
                    from timease.io.excel_import import read_template
                    school_data_obj, errors = read_template(tmp_path)
                    if school_data_obj is not None:
                        self._populate_from_school_data(school_data_obj)
                        n_t = len(school_data_obj.teachers)
                        n_c = len(school_data_obj.classes)
                        n_a = len(school_data_obj.teacher_assignments)
                        self.upload_status = "success"
                        self.upload_message = (
                            f"{n_t} enseignant(s), {n_c} classe(s), "
                            f"{n_a} affectation(s) importés."
                        )
                        self.active_config_tab = "forms"
                        self._load_school_form()
                        yield
                        return

                # Non-TIMEASE xlsx or other format: extract and send to AI
                from timease.io.file_parser import extract_content
                content, _file_type = extract_content(tmp_path)

                self.chat_messages.append({
                    "role": "user",
                    "content": f"[Fichier joint : {filename}]\n\n{content[:3000]}",
                    "data_type": "",
                    "quick_replies": [],
                })
                self.is_ai_loading = True
                self.upload_status = "success"
                self.upload_message = f"Fichier « {filename} » transmis à l'assistant IA."
                self.active_config_tab = "chat"
                yield

                try:
                    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
                    if api_key:
                        from timease.app.ai_setup import SetupAssistant, describe_tool_calls
                        assistant = SetupAssistant(api_key=api_key)
                        assistant.history = list(self.ai_history)
                        response = assistant.process_message(
                            user_message="Analyse ce fichier et extrais les données de l'école.",
                            current_data=self.school_data,
                            teacher_assignments=self.teacher_assignments,
                            file_content=content,
                        )
                        self.ai_history = list(assistant.history)
                        if response["message"]:
                            self.chat_messages.append({
                                "role": "ai",
                                "content": response["message"],
                                "data_type": "",
                                "quick_replies": response["quick_replies"],
                            })
                        tool_calls = response["tool_calls"]
                        if tool_calls:
                            self.pending_tool_calls = tool_calls
                            self.chat_messages.append({
                                "role": "confirm",
                                "content": describe_tool_calls(tool_calls),
                                "data_type": "",
                                "quick_replies": [],
                            })
                    else:
                        self.chat_messages.append({
                            "role": "ai",
                            "content": (
                                "Fichier reçu. Clé API Anthropic non configurée — "
                                "utilisez l'onglet Formulaires pour saisir vos données."
                            ),
                            "data_type": "",
                            "quick_replies": [],
                        })
                except Exception as ai_exc:
                    self.chat_messages.append({
                        "role": "ai",
                        "content": f"Erreur lors de l'analyse du fichier : {ai_exc}",
                        "data_type": "",
                        "quick_replies": [],
                    })
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        except Exception as exc:
            self.upload_status = "error"
            self.upload_message = f"Erreur : {exc}"

        self.is_ai_loading = False
        yield

    # =================================================================
    # Private helpers
    # =================================================================

    def _populate_from_school_data(self, sd) -> None:
        """Convert SchoolData object to the flat dict used by school_data."""
        self.school_data = {
            "name": sd.school.name,
            "academic_year": sd.school.academic_year,
            "city": sd.school.city,
            "days": list(sd.timeslot_config.days),
            "base_unit_minutes": sd.timeslot_config.base_unit_minutes,
            "sessions": [
                {"name": s.name, "start_time": s.start_time, "end_time": s.end_time}
                for s in sd.timeslot_config.sessions
            ],
            "subjects": [
                {
                    "name": s.name,
                    "short_name": s.short_name,
                    "color": s.color,
                    "required_room_type": s.required_room_type,
                    "needs_room": s.needs_room,
                }
                for s in sd.subjects
            ],
            "teachers": [
                {
                    "name": t.name,
                    "subjects": list(t.subjects),
                    "max_hours_per_week": t.max_hours_per_week,
                    "unavailable_slots": list(t.unavailable_slots),
                    "preference_weight": t.preference_weight,
                }
                for t in sd.teachers
            ],
            "classes": [
                {
                    "name": c.name,
                    "level": c.level,
                    "student_count": c.student_count,
                }
                for c in sd.classes
            ],
            "rooms": [
                {
                    "name": r.name,
                    "capacity": r.capacity,
                    "types": list(r.types),
                }
                for r in sd.rooms
            ],
            "curriculum": [
                {
                    "level": e.level,
                    "subject": e.subject,
                    "total_minutes_per_week": e.total_minutes_per_week,
                    "mode": e.mode,
                    "sessions_per_week": e.sessions_per_week,
                    "minutes_per_session": e.minutes_per_session,
                    "min_session_minutes": e.min_session_minutes,
                    "max_session_minutes": e.max_session_minutes,
                }
                for e in sd.curriculum
            ],
            "constraints": [
                {
                    "id": c.id,
                    "type": c.type,
                    "category": c.category,
                    "description_fr": c.description_fr,
                    "priority": c.priority,
                    "parameters": c.parameters,
                }
                for c in sd.constraints
            ],
        }
        self.teacher_assignments = [
            {
                "teacher": a.teacher,
                "subject": a.subject,
                "school_class": a.school_class,
            }
            for a in sd.teacher_assignments
        ]

    def _load_school_form(self) -> None:
        """Pre-fill school form from existing school_data."""
        self.form_school_name = self.school_data.get("name", "")
        self.form_school_year = self.school_data.get("academic_year", "")
        self.form_school_city = self.school_data.get("city", "")
        saved_days = self.school_data.get("days", [])
        self.form_days = (
            list(saved_days)
            if saved_days
            else ["lundi", "mardi", "mercredi", "jeudi", "vendredi"]
        )
        saved_sessions = self.school_data.get("sessions", [])
        if saved_sessions:
            self.form_sessions = [
                {"id": i, **s} for i, s in enumerate(saved_sessions)
            ]
            self.form_session_next_id = len(saved_sessions)
        self.form_base_unit = str(self.school_data.get("base_unit_minutes", 30))

    def _merge_extracted(self, data: dict | list, data_type: str) -> None:
        """Merge AI-extracted data into school_data / teacher_assignments."""
        merged = dict(self.school_data)
        if data_type == "school_info":
            if isinstance(data, dict):
                info = data.get("school_info", data)
                merged.update(info)
        elif data_type in (
            "teachers", "classes", "rooms", "subjects", "curriculum", "constraints",
        ):
            existing = list(merged.get(data_type, []))
            # If data is a dict (e.g. {"classes": [...]}), extract the list
            if isinstance(data, dict):
                raw_items = data.get(data_type, [])
            else:
                raw_items = data if isinstance(data, list) else [data]
            # Normalize string items to dicts for classes and rooms
            normalized: list = []
            for item in raw_items:
                if data_type == "classes" and isinstance(item, str):
                    normalized.append({"name": item, "level": item, "student_count": 0})
                elif data_type == "rooms" and isinstance(item, str):
                    normalized.append({"name": item, "capacity": 0, "types": ["Standard"]})
                else:
                    normalized.append(item)
            existing.extend(normalized)
            merged[data_type] = existing
        elif data_type == "assignments":
            existing = list(self.teacher_assignments)
            if isinstance(data, dict):
                raw_items = data.get("assignments", [])
            else:
                raw_items = data if isinstance(data, list) else [data]
            existing.extend(item for item in raw_items if isinstance(item, dict))
            self.teacher_assignments = existing
        self.school_data = merged
