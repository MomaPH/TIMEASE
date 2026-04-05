"""State for the teacher-facing collaboration page (/collab/[token])."""

import json
import logging
import pathlib

import reflex as rx

_COLLAB_DIR = pathlib.Path(__file__).parent.parent.parent / "collab"

_AVAIL_DAYS  = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
_AVAIL_SLOTS = [
    "07:30", "08:30", "09:30", "10:30", "11:30",
    "13:30", "14:30", "15:30", "16:30",
]
_AVAIL_CYCLE = {
    "disponible": "non_idéal",
    "non_idéal":  "impossible",
    "impossible":  "disponible",
}
_DEFAULT_AVAIL: dict[str, str] = {
    f"{d}_{s}": "disponible"
    for d in _AVAIL_DAYS
    for s in _AVAIL_SLOTS
}

logger = logging.getLogger(__name__)


class CollabTeacherState(rx.State):
    """State for the teacher availability form."""

    collab_token: str = ""
    teacher_name: str = ""
    school_name: str = ""
    status: str = "pending"
    availability: dict = dict(_DEFAULT_AVAIL)
    preferences: str = ""
    has_timetable: bool = False
    timetable_assignments: list[dict] = []
    preference_feedback: list[str] = []
    loaded: bool = False
    error_msg: str = ""
    submitted: bool = False

    # Computed stats (set in on_load when has_timetable is True)
    stat_hours: int = 0
    stat_days: int = 0
    stat_free: int = 0

    # =================================================================
    # Lifecycle
    # =================================================================

    def on_load(self) -> None:
        """Load collab data from JSON file on page mount."""
        token = self.router.page.params.get("token", "")
        self.collab_token = token

        # Reset to defaults
        self.availability = dict(_DEFAULT_AVAIL)
        self.submitted = False
        self.error_msg = ""

        json_path = _COLLAB_DIR / f"{token}.json"
        if not json_path.exists():
            self.error_msg = f"Lien invalide ou expiré."
            self.loaded = False
            logger.warning("Collab token not found: %s", token)
            return

        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.teacher_name = data.get("teacher_name", "")
            self.school_name  = data.get("school_name", "")
            self.status       = data.get("status", "pending")
            self.preferences  = data.get("preferences", "")
            self.has_timetable = data.get("has_timetable", False)
            self.timetable_assignments = data.get("timetable_assignments", [])
            self.preference_feedback   = data.get("preference_feedback", [])

            # Merge stored availability on top of defaults
            stored = data.get("availability", {})
            merged = dict(_DEFAULT_AVAIL)
            merged.update({k: v for k, v in stored.items() if k in merged})
            self.availability = merged

            # Compute stats when timetable exists
            if self.has_timetable:
                assignments = self.timetable_assignments
                unique_days = {a.get("day", "") for a in assignments}
                total_slots = len(_AVAIL_DAYS) * len(_AVAIL_SLOTS)
                self.stat_hours = len(assignments)
                self.stat_days  = len(unique_days)
                self.stat_free  = total_slots - len(assignments)

            self.loaded = True
        except Exception as exc:
            self.error_msg = "Erreur lors du chargement des données."
            self.loaded = False
            logger.exception("Failed to load collab token %s: %s", token, exc)

    # =================================================================
    # Event handlers
    # =================================================================

    def toggle_cell(self, key: str) -> None:
        """Cycle availability for one (day, slot) cell."""
        current = self.availability.get(key, "disponible")
        self.availability = {**self.availability, key: _AVAIL_CYCLE.get(current, "disponible")}

    def set_preferences(self, value: str) -> None:
        self.preferences = value

    def submit(self) -> None:
        """Persist availability + preferences to JSON file."""
        if not self.collab_token:
            return
        json_path = _COLLAB_DIR / f"{self.collab_token}.json"
        if not json_path.exists():
            self.error_msg = "Impossible de sauvegarder : lien introuvable."
            return
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            data["availability"] = dict(self.availability)
            data["preferences"]  = self.preferences
            data["status"]       = "completed"
            json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
            self.status    = "completed"
            self.submitted = True
        except Exception as exc:
            self.error_msg = "Erreur lors de la sauvegarde."
            logger.exception("Failed to save collab token %s: %s", self.collab_token, exc)
