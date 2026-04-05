"""Workspace page — AI chat (left) + accordion data panels (right)."""

import reflex as rx

from timease.app.components.forms_tab import (
    _school_tab,
    _teachers_tab,
    _classes_tab,
    _rooms_tab,
    teacher_dialog,
    class_dialog,
    room_dialog,
    delete_confirm_dialog,
)
from timease.app.components.layout import page_layout
from timease.app.state import AppState
from timease.app.style import (
    CARD_RADIUS,
    SECTION_GAP,
    chat_confirm_card,
    chat_container,
    chat_input_bar,
    chat_messages_area,
    chat_msg_ai,
    chat_msg_user,
    chat_suggestion_bar,
)


# ─────────────────────────────────────────────────────────────────────────────
# Chat message rendering
# ─────────────────────────────────────────────────────────────────────────────

def _render_message(msg: dict) -> rx.Component:
    """Render one chat message — user bubble, AI bubble, or confirm card."""
    return rx.cond(
        msg["role"] == "user",
        rx.box(
            rx.text(msg["content"], size="2"),
            style=chat_msg_user,
            margin_bottom="8px",
        ),
        rx.cond(
            msg["role"] == "confirm",
            rx.box(
                rx.hstack(
                    rx.icon("check_check", size=14, color=rx.color("teal", 9)),
                    rx.text(
                        "À confirmer",
                        font_weight="600",
                        size="2",
                        color=rx.color("teal", 11),
                    ),
                    gap="6px",
                    align="center",
                    margin_bottom="10px",
                ),
                rx.box(
                    rx.text(
                        msg["content"],
                        size="2",
                        color=rx.color("gray", 11),
                        white_space="pre-wrap",
                        line_height="1.7",
                    ),
                    background=rx.color("teal", 2),
                    border_radius="8px",
                    padding="10px 14px",
                    margin_bottom="12px",
                ),
                rx.hstack(
                    rx.button(
                        rx.icon("check", size=14),
                        "Confirmer",
                        color_scheme="teal",
                        size="2",
                        on_click=AppState.confirm_extracted_data,
                        cursor="pointer",
                    ),
                    rx.button(
                        rx.icon("x", size=14),
                        "Corriger",
                        variant="outline",
                        size="2",
                        on_click=AppState.reject_extracted_data,
                        cursor="pointer",
                    ),
                    gap="8px",
                ),
                style=chat_confirm_card,
                border_left="3px solid var(--teal-8)",
                margin_bottom="8px",
            ),
            rx.box(
                rx.text(msg["content"], size="2"),
                rx.cond(
                    msg["quick_replies"].to(list[str]).length() > 0,
                    rx.hstack(
                        rx.foreach(
                            msg["quick_replies"].to(list[str]),
                            lambda reply: rx.button(
                                reply,
                                size="1",
                                variant="outline",
                                color_scheme="teal",
                                border_radius="16px",
                                cursor="pointer",
                                on_click=AppState.send_quick_reply(reply),
                            ),
                        ),
                        gap="6px",
                        flex_wrap="wrap",
                        margin_top="8px",
                    ),
                    rx.fragment(),
                ),
                style=chat_msg_ai,
                margin_bottom="8px",
            ),
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Chat panel (left, 60%)
# ─────────────────────────────────────────────────────────────────────────────

def _chat_panel() -> rx.Component:
    return rx.box(
        # Message area
        rx.box(
            rx.vstack(
                rx.foreach(AppState.chat_messages, _render_message),
                align="stretch",
                spacing="0",
                width="100%",
            ),
            rx.cond(
                AppState.is_ai_loading,
                rx.box(
                    rx.hstack(
                        rx.spinner(size="1", color=rx.color("teal", 9)),
                        rx.text("TIMEASE réfléchit…", size="1", color=rx.color("gray", 9)),
                        gap="8px",
                        align="center",
                    ),
                    background=rx.color("gray", 3),
                    padding="8px 14px",
                    border_radius="12px 12px 12px 3px",
                    display="inline-block",
                    margin_left="0",
                    margin_bottom="8px",
                ),
                rx.fragment(),
            ),
            style=chat_messages_area,
        ),
        # Generate button — visible only when data is sufficient
        rx.cond(
            AppState.can_generate,
            rx.box(
                rx.button(
                    rx.icon("zap", size=16),
                    "Générer l'emploi du temps",
                    color_scheme="teal",
                    size="3",
                    on_click=AppState.run_generate,
                    loading=AppState.is_solving,
                    cursor="pointer",
                    width="100%",
                ),
                padding="8px 16px",
                border_top="1px solid var(--teal-4)",
                background=rx.color("teal", 1),
            ),
            rx.fragment(),
        ),
        # Suggestion chips — driven by last AI quick_replies
        rx.hstack(
            rx.foreach(
                AppState.current_suggestions,
                lambda s: rx.badge(
                    s,
                    variant="surface",
                    color_scheme="teal",
                    cursor="pointer",
                    size="1",
                    on_click=AppState.send_quick_reply(s),
                ),
            ),
            style=chat_suggestion_bar,
        ),
        # Input bar with paperclip upload
        rx.hstack(
            rx.upload(
                rx.icon("paperclip", size=18, color=rx.color("gray", 8), cursor="pointer", flex_shrink="0"),
                id="workspace_upload",
                accept={
                    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    ".csv": "text/csv",
                    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    ".txt": "text/plain",
                },
                multiple=False,
                on_drop=AppState.handle_file_upload(
                    rx.upload_files(upload_id="workspace_upload")
                ),
            ),
            rx.input(
                value=AppState.chat_input,
                on_change=AppState.set_chat_input,
                on_key_down=AppState.handle_chat_key,
                placeholder="Décrivez votre école, vos enseignants…",
                size="3",
                variant="surface",
                width="100%",
            ),
            rx.button(
                rx.icon("send", size=16),
                on_click=AppState.send_chat_message,
                color_scheme="teal",
                size="3",
                flex_shrink="0",
                loading=AppState.is_ai_loading,
                cursor="pointer",
            ),
            style=chat_input_bar,
        ),
        style=chat_container,
        width="100%",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Accordion item helpers
# ─────────────────────────────────────────────────────────────────────────────

def _acc_header(label: str, count_var: rx.Var, done_var: rx.Var) -> rx.Component:
    return rx.hstack(
        rx.text(label, size="2", font_weight="500"),
        rx.badge(
            count_var,
            color_scheme=rx.cond(done_var, "teal", "gray"),
            variant="soft",
            size="1",
        ),
        rx.cond(
            done_var,
            rx.icon("check", size=14, color=rx.color("teal", 9)),
            rx.fragment(),
        ),
        gap="8px",
        align="center",
        width="100%",
    )


def _assignment_row(a: dict) -> rx.Component:
    return rx.hstack(
        rx.text(a["teacher"], size="2", flex="1"),
        rx.text(a["subject"], size="2", color=rx.color("gray", 9), flex="1"),
        rx.text(a.get("class_name", ""), size="2", color=rx.color("gray", 9), flex="1"),
        padding="6px 0",
        border_bottom="1px solid var(--gray-3)",
        width="100%",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Right accordion panel (40%)
# ─────────────────────────────────────────────────────────────────────────────

def _accordion_panel() -> rx.Component:
    return rx.box(
        rx.accordion.root(
            rx.accordion.item(
                header=_acc_header(
                    "École",
                    AppState.school_configured,
                    AppState.school_configured > 0,
                ),
                content=_school_tab(),
                value="school",
            ),
            rx.accordion.item(
                header=_acc_header(
                    "Enseignants",
                    AppState.teacher_count,
                    AppState.teacher_count > 0,
                ),
                content=_teachers_tab(),
                value="teachers",
            ),
            rx.accordion.item(
                header=_acc_header(
                    "Classes",
                    AppState.class_count,
                    AppState.class_count > 0,
                ),
                content=_classes_tab(),
                value="classes",
            ),
            rx.accordion.item(
                header=_acc_header(
                    "Salles",
                    AppState.room_count,
                    AppState.room_count > 0,
                ),
                content=_rooms_tab(),
                value="rooms",
            ),
            rx.accordion.item(
                header=_acc_header(
                    "Affectations",
                    AppState.assignment_count,
                    AppState.assignment_count > 0,
                ),
                content=rx.cond(
                    AppState.assignment_count > 0,
                    rx.vstack(
                        rx.hstack(
                            rx.text("Enseignant", size="1", color=rx.color("gray", 9), flex="1", font_weight="500"),
                            rx.text("Matière", size="1", color=rx.color("gray", 9), flex="1", font_weight="500"),
                            rx.text("Classe", size="1", color=rx.color("gray", 9), flex="1", font_weight="500"),
                            width="100%",
                            padding_bottom="4px",
                            border_bottom="1px solid var(--gray-4)",
                        ),
                        rx.foreach(AppState.teacher_assignments, _assignment_row),
                        width="100%",
                        spacing="0",
                        padding="4px 0",
                    ),
                    rx.text(
                        "Aucune affectation. Décrivez-les à l'assistant IA.",
                        size="2",
                        color=rx.color("gray", 8),
                        padding="8px 0",
                    ),
                ),
                value="assignments",
            ),
            rx.accordion.item(
                header=_acc_header(
                    "Programme",
                    AppState.curriculum_count,
                    AppState.curriculum_count > 0,
                ),
                content=rx.text(
                    "Décrivez le programme (matières, heures par semaine) à l'assistant IA.",
                    size="2",
                    color=rx.color("gray", 8),
                    padding="8px 0",
                ),
                value="programme",
            ),
            rx.accordion.item(
                header=_acc_header(
                    "Contraintes",
                    AppState.constraint_count,
                    AppState.constraint_count > 0,
                ),
                content=rx.text(
                    "Décrivez vos contraintes horaires à l'assistant IA.",
                    size="2",
                    color=rx.color("gray", 8),
                    padding="8px 0",
                ),
                value="contraintes",
            ),
            collapsible=True,
            width="100%",
            type="single",
        ),
        width="40%",
        flex_shrink="0",
        overflow_y="auto",
        max_height="85vh",
        border="1px solid var(--gray-4)",
        border_radius=CARD_RADIUS,
        padding="4px",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Page
# ─────────────────────────────────────────────────────────────────────────────

def workspace() -> rx.Component:
    """Workspace page at route /workspace."""
    return page_layout(
        rx.fragment(
            rx.vstack(
                rx.heading("Espace de travail", size="5", font_weight="600"),
                rx.text(
                    "Configurez et générez votre emploi du temps",
                    color=rx.color("gray", 9),
                    size="2",
                ),
                rx.hstack(
                    rx.box(_chat_panel(), width="60%", flex_shrink="0"),
                    _accordion_panel(),
                    gap=SECTION_GAP,
                    width="100%",
                    align_items="flex-start",
                ),
                spacing="4",
                width="100%",
            ),
            teacher_dialog(),
            class_dialog(),
            room_dialog(),
            delete_confirm_dialog(),
        )
    )
