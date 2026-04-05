"""Configuration page — school setup via AI chat, forms, or file import."""

import reflex as rx

from timease.app.components.forms_tab import forms_tab
from timease.app.components.layout import page_layout
from timease.app.state import AppState
from timease.app.style import *


# ─────────────────────────────────────────────────────────────────────────────
# Tab bar
# ─────────────────────────────────────────────────────────────────────────────

def _tab_btn(label: str, value: str) -> rx.Component:
    is_active = AppState.active_config_tab == value
    return rx.button(
        label,
        on_click=AppState.set_active_config_tab(value),
        background=rx.cond(is_active, rx.color("teal", 9), "transparent"),
        color=rx.cond(is_active, "white", rx.color("gray", 9)),
        border=rx.cond(
            is_active,
            "1px solid transparent",
            "1px solid var(--gray-5)",
        ),
        border_radius=INPUT_RADIUS,
        padding="6px 16px",
        font_size="14px",
        font_weight=rx.cond(is_active, "500", "400"),
        cursor="pointer",
        _hover={"opacity": "0.85"},
    )


def _tab_bar() -> rx.Component:
    return rx.hstack(
        _tab_btn("Conversation IA", "chat"),
        _tab_btn("Formulaires", "forms"),
        _tab_btn("Import fichier", "file"),
        gap="8px",
        margin_bottom="16px",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Chat message rendering
# ─────────────────────────────────────────────────────────────────────────────

def _render_message(msg: dict) -> rx.Component:
    """Render one chat message — user bubble, AI bubble, or confirm card."""
    return rx.cond(
        msg["role"] == "user",
        # ── User message ──────────────────────────────────────────────
        rx.box(
            rx.text(msg["content"], size="2"),
            style=chat_msg_user,
            margin_bottom="8px",
        ),
        rx.cond(
            msg["role"] == "confirm",
            # ── Confirmation card ─────────────────────────────────────
            rx.box(
                rx.text(
                    "Données extraites",
                    font_weight="500",
                    size="2",
                    margin_bottom="6px",
                ),
                rx.box(
                    rx.text(
                        "Type : ",
                        size="1",
                        color=rx.color("gray", 9),
                        display="inline",
                    ),
                    rx.badge(
                        msg["data_type"],
                        color_scheme="teal",
                        variant="soft",
                        size="1",
                    ),
                    margin_bottom="6px",
                ),
                rx.box(
                    rx.text(msg["content"], size="1", color=rx.color("gray", 9)),
                    background=rx.color("gray", 2),
                    border_radius="6px",
                    padding="8px 10px",
                    margin_bottom="10px",
                    font_family="monospace",
                    white_space="pre-wrap",
                    word_break="break-all",
                ),
                rx.hstack(
                    rx.button(
                        "Confirmer",
                        color_scheme="teal",
                        size="2",
                        on_click=AppState.confirm_extracted_data,
                        cursor="pointer",
                    ),
                    rx.button(
                        "Corriger",
                        variant="outline",
                        size="2",
                        on_click=AppState.reject_extracted_data,
                        cursor="pointer",
                    ),
                    gap="8px",
                ),
                style=chat_confirm_card,
                border_left="3px solid var(--teal-9)",
                margin_bottom="8px",
            ),
            # ── AI message ────────────────────────────────────────────
            rx.box(
                rx.text(msg["content"], size="2"),
                style=chat_msg_ai,
                margin_bottom="8px",
            ),
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Chat tab
# ─────────────────────────────────────────────────────────────────────────────

def _chat_tab() -> rx.Component:
    return rx.box(
        # ── Message area ─────────────────────────────────────────────
        rx.box(
            rx.vstack(
                rx.foreach(AppState.chat_messages, _render_message),
                align="stretch",
                spacing="0",
                width="100%",
            ),
            rx.cond(
                AppState.is_ai_loading,
                rx.hstack(
                    rx.spinner(size="2"),
                    rx.text(
                        "TIMEASE réfléchit…",
                        size="1",
                        color=rx.color("gray", 8),
                    ),
                    padding="8px 12px",
                    align="center",
                    gap="8px",
                ),
                rx.fragment(),
            ),
            style=chat_messages_area,
        ),
        # ── Suggestion chips ─────────────────────────────────────────
        rx.hstack(
            rx.badge(
                "Ajouter des enseignants",
                variant="surface",
                color_scheme="teal",
                cursor="pointer",
                size="1",
                on_click=AppState.set_chat_input("Ajouter des enseignants"),
            ),
            rx.badge(
                "Configurer les classes",
                variant="surface",
                color_scheme="teal",
                cursor="pointer",
                size="1",
                on_click=AppState.set_chat_input("Configurer les classes"),
            ),
            rx.badge(
                "Importer un fichier Excel",
                variant="surface",
                color_scheme="teal",
                cursor="pointer",
                size="1",
                on_click=AppState.set_chat_input("Importer un fichier Excel"),
            ),
            style=chat_suggestion_bar,
        ),
        # ── Input bar ────────────────────────────────────────────────
        rx.hstack(
            rx.icon(
                "paperclip",
                size=18,
                color=rx.color("gray", 8),
                cursor="pointer",
                flex_shrink="0",
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
        # ── Container ────────────────────────────────────────────────
        style=chat_container,
        width="100%",
    )


# ─────────────────────────────────────────────────────────────────────────────
# File import tab
# ─────────────────────────────────────────────────────────────────────────────

def _file_tab() -> rx.Component:
    return rx.box(
        # ── Drop zone ─────────────────────────────────────────────────
        rx.upload(
            rx.vstack(
                rx.icon("cloud_upload", size=36, color=rx.color("teal", 8)),
                rx.text(
                    "Glissez un fichier ici ou cliquez pour sélectionner",
                    size="2",
                    color=rx.color("gray", 11),
                    font_weight="500",
                ),
                rx.text(
                    "Formats acceptés : .xlsx, .csv, .docx, .txt",
                    size="1",
                    color=rx.color("gray", 8),
                ),
                align="center",
                spacing="2",
                padding="40px 24px",
                width="100%",
            ),
            id="timease_upload",
            accept={
                ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ".csv": "text/csv",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ".txt": "text/plain",
            },
            multiple=False,
            on_drop=AppState.handle_file_upload(
                rx.upload_files(upload_id="timease_upload")
            ),
            style=upload_dropzone,
        ),
        # ── Status message ────────────────────────────────────────────
        rx.cond(
            AppState.upload_status == "loading",
            rx.hstack(
                rx.spinner(size="2"),
                rx.text("Traitement en cours…", size="2", color=rx.color("gray", 9)),
                padding_top="12px",
                align="center",
                gap="8px",
            ),
            rx.cond(
                AppState.upload_status == "success",
                rx.box(
                    rx.hstack(
                        rx.icon("circle_check", size=16, color=rx.color("teal", 9)),
                        rx.text(AppState.upload_message, size="2", color=rx.color("teal", 11)),
                        align="center",
                        gap="6px",
                    ),
                    style=upload_status_success,
                ),
                rx.cond(
                    AppState.upload_status == "error",
                    rx.box(
                        rx.hstack(
                            rx.icon("circle_alert", size=16, color=rx.color("red", 9)),
                            rx.text(AppState.upload_message, size="2", color=rx.color("red", 11)),
                            align="center",
                            gap="6px",
                        ),
                        style=upload_status_error,
                    ),
                    rx.fragment(),
                ),
            ),
        ),
        # ── Help notes ────────────────────────────────────────────────
        rx.vstack(
            rx.hstack(
                rx.icon("table", size=14, color=rx.color("teal", 8)),
                rx.text(
                    "Modèle Excel TIMEASE (.xlsx) : import direct et complet des données.",
                    size="1",
                    color=rx.color("gray", 9),
                ),
                align="center",
                gap="6px",
            ),
            rx.hstack(
                rx.icon("file_text", size=14, color=rx.color("gray", 7)),
                rx.text(
                    "Autres formats (.csv, .docx, .txt) : transmis à l'assistant IA.",
                    size="1",
                    color=rx.color("gray", 9),
                ),
                align="center",
                gap="6px",
            ),
            padding_top="12px",
            spacing="1",
        ),
        width="100%",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Right sidebar — data summary
# ─────────────────────────────────────────────────────────────────────────────

def _data_card(
    title: str,
    subtitle: rx.Var,
    completed: rx.Var,
) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(title, font_weight="500", size="2", color=rx.color("gray", 12)),
            rx.cond(
                completed,
                rx.badge("✓", color_scheme="teal", size="1", variant="soft"),
                rx.fragment(),
            ),
            justify="between",
            width="100%",
        ),
        rx.text(subtitle, size="1", color=rx.color("gray", 9), margin_top="2px"),
        rx.text(
            "modifier",
            size="1",
            color=rx.color("teal", 9),
            cursor="pointer",
            margin_top="4px",
            on_click=AppState.set_active_config_tab("forms"),
            _hover={"text_decoration": "underline"},
        ),
        style=data_card,
        border_left=rx.cond(
            completed,
            "3px solid var(--teal-9)",
            "3px solid var(--gray-5)",
        ),
    )


def _data_sidebar() -> rx.Component:
    school_done = AppState.school_name_display != ""
    return rx.box(
        rx.heading("Données collectées", size="3", font_weight="500", margin_bottom="4px"),
        rx.hstack(
            rx.text(
                AppState.steps_done,
                " sur 5 étapes",
                size="1",
                color=rx.color("gray", 9),
            ),
            rx.text(
                AppState.progress_percent,
                "%",
                size="1",
                color=rx.color("teal", 9),
                font_weight="500",
            ),
            justify="between",
            margin_top="4px",
            margin_bottom="8px",
        ),
        rx.progress(
            value=AppState.progress_percent,
            color_scheme="teal",
            margin_bottom="16px",
            width="100%",
        ),
        _data_card(
            "École",
            rx.cond(school_done, AppState.school_name_display, "Non configuré"),
            school_done,
        ),
        _data_card(
            "Enseignants",
            rx.cond(
                AppState.teacher_count > 0,
                rx.el.span(AppState.teacher_count, " enseignant(s)"),
                rx.el.span("Aucun"),
            ),
            AppState.teacher_count > 0,
        ),
        _data_card(
            "Classes",
            rx.cond(
                AppState.class_count > 0,
                rx.el.span(AppState.class_count, " classe(s)"),
                rx.el.span("Aucune"),
            ),
            AppState.class_count > 0,
        ),
        _data_card(
            "Salles",
            rx.cond(
                AppState.room_count > 0,
                rx.el.span(AppState.room_count, " salle(s)"),
                rx.el.span("Aucune"),
            ),
            AppState.room_count > 0,
        ),
        _data_card(
            "Programme",
            rx.cond(
                AppState.curriculum_count > 0,
                rx.el.span(AppState.curriculum_count, " entrée(s)"),
                rx.el.span("Non configuré"),
            ),
            AppState.curriculum_count > 0,
        ),
        _data_card(
            "Affectations",
            rx.cond(
                AppState.assignment_count > 0,
                rx.el.span(AppState.assignment_count, " affectation(s)"),
                rx.el.span("Aucune"),
            ),
            AppState.assignment_count > 0,
        ),
        width=RIGHT_PANEL_WIDTH,
        flex_shrink="0",
        padding=CARD_PADDING,
        background=rx.color("gray", 2),
        border="1px solid var(--gray-4)",
        border_radius=CARD_RADIUS,
        height="fit-content",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Page
# ─────────────────────────────────────────────────────────────────────────────

def configuration() -> rx.Component:
    """Configuration page at route /configuration."""
    return page_layout(
        rx.vstack(
            rx.heading("Configuration", size="5", font_weight="600"),
            rx.text(
                "Configurez les données de votre école",
                color=rx.color("gray", 9),
                size="2",
            ),
            rx.hstack(
                # Left — input area
                rx.box(
                    _tab_bar(),
                    rx.cond(
                        AppState.active_config_tab == "chat",
                        _chat_tab(),
                        rx.cond(
                            AppState.active_config_tab == "forms",
                            forms_tab(),
                            _file_tab(),
                        ),
                    ),
                    flex="1",
                    min_width="0",
                ),
                # Right — data summary
                _data_sidebar(),
                gap=SECTION_GAP,
                width="100%",
                align_items="flex-start",
            ),
            spacing="4",
            width="100%",
        )
    )
