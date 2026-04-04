"""Global application state for TIMEASE."""

import reflex as rx


class AppState(rx.State):
    """Central state for the TIMEASE application."""

    # School data
    school_data: dict = {}  # Serialized SchoolData
    teacher_assignments: list[dict] = []

    # Solver
    timetable_result: dict = {}
    is_solving: bool = False
    solve_error: str = ""

    # AI chat
    chat_messages: list[dict] = []  # [{role: "ai"|"user", content: "..."}]
    chat_input: str = ""

    # UI state
    current_step: int = 1  # 1-5
    active_config_tab: str = "chat"  # "chat" | "forms" | "file"
    active_result_tab: str = "class"  # "class" | "teacher" | "room" | "subject"
    selected_class: str = ""
    selected_teacher: str = ""
    selected_room: str = ""

    # Collaboration
    collab_links: list[dict] = []  # [{teacher, token, status}]

    # Plan limits
    current_plan: str = "Découverte"

    @rx.var
    def teacher_count(self) -> int:
        """Number of teachers in school_data."""
        return len(self.school_data.get("teachers", []))

    @rx.var
    def class_count(self) -> int:
        """Number of classes in school_data."""
        return len(self.school_data.get("classes", []))

    @rx.var
    def room_count(self) -> int:
        """Number of rooms in school_data."""
        return len(self.school_data.get("rooms", []))

    @rx.var
    def constraint_count(self) -> int:
        """Number of constraints in school_data."""
        return len(self.school_data.get("constraints", []))

    @rx.var
    def progress_percent(self) -> int:
        """
        Completion progress 0-100.

        Each of these 6 sections is worth ~17%:
        school info, teachers, classes, rooms, curriculum, constraints.
        """
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
            score += 15  # brings total to 100
        return min(score, 100)
