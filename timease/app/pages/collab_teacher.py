"""Teacher-facing collaboration page at /collab/[token]. No sidebar, mobile-first."""

import reflex as rx

from timease.app.state_collab import (
    CollabTeacherState,
    _AVAIL_DAYS,
    _AVAIL_SLOTS,
)
from timease.app.style import (
    avail_available,
    avail_impossible,
    avail_not_ideal,
    btn_primary,
    hint_box,
)

# ─── Availability grid ──────────────────────────────────────────────────────────

def _avail_cell(day: str, slot: str) -> rx.Component:
    """Single clickable availability cell."""
    key = f"{day}_{slot}"
    val = CollabTeacherState.availability[key]

    bg = rx.cond(
        val == "disponible", "var(--green-3)",
        rx.cond(val == "non_idéal", "var(--amber-3)", "var(--red-3)"),
    )
    fg = rx.cond(
        val == "disponible", "var(--green-11)",
        rx.cond(val == "non_idéal", "var(--amber-11)", "var(--red-11)"),
    )
    lbl = rx.cond(
        val == "disponible", "✓",
        rx.cond(val == "non_idéal", "~", "✗"),
    )

    return rx.box(
        rx.text(lbl, size="1", font_weight="700"),
        background=bg,
        color=fg,
        padding="5px 0",
        text_align="center",
        border_radius="4px",
        cursor="pointer",
        min_width="38px",
        min_height="28px",
        display="flex",
        align_items="center",
        justify_content="center",
        on_click=CollabTeacherState.toggle_cell(key),
        _hover={"opacity": "0.8", "transform": "scale(0.97)"},
        transition="all 0.12s ease",
    )


def _avail_grid() -> rx.Component:
    """Days × slots availability matrix."""
    return rx.box(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell(
                        "",
                        padding="6px 8px",
                        font_size="11px",
                        color="var(--gray-8)",
                        width="52px",
                    ),
                    *[
                        rx.table.column_header_cell(
                            day[:3],  # "Lun", "Mar", etc.
                            padding="6px 4px",
                            font_size="11px",
                            font_weight="500",
                            color="var(--gray-11)",
                            text_align="center",
                        )
                        for day in _AVAIL_DAYS
                    ],
                )
            ),
            rx.table.body(
                *[
                    rx.table.row(
                        rx.table.cell(
                            slot,
                            padding="4px 8px 4px 0",
                            font_size="10px",
                            color="var(--gray-8)",
                            white_space="nowrap",
                        ),
                        *[
                            rx.table.cell(
                                _avail_cell(day, slot),
                                padding="3px",
                            )
                            for day in _AVAIL_DAYS
                        ],
                    )
                    for slot in _AVAIL_SLOTS
                ]
            ),
            width="100%",
            border="1px solid var(--gray-4)",
            border_radius="10px",
            overflow="hidden",
        ),
        overflow_x="auto",
        width="100%",
    )


def _avail_legend() -> rx.Component:
    items = [
        ("var(--green-3)", "var(--green-11)", "✓", "Disponible"),
        ("var(--amber-3)", "var(--amber-11)", "~", "Pas idéal"),
        ("var(--red-3)",   "var(--red-11)",   "✗", "Impossible"),
    ]
    return rx.hstack(
        *[
            rx.hstack(
                rx.box(
                    rx.text(icon, size="1", font_weight="700", color=fg),
                    background=bg,
                    padding="2px 8px",
                    border_radius="4px",
                ),
                rx.text(label, size="1", color="var(--gray-9)"),
                gap="4px",
                align="center",
            )
            for bg, fg, icon, label in items
        ],
        gap="14px",
        flex_wrap="wrap",
    )


# ─── Before-timetable form ──────────────────────────────────────────────────────

def _availability_form() -> rx.Component:
    return rx.vstack(
        rx.text(
            "Cliquez sur chaque créneau pour indiquer votre disponibilité.",
            size="2",
            color="var(--gray-9)",
        ),
        _avail_grid(),
        _avail_legend(),

        # Free text preferences
        rx.vstack(
            rx.text("Préférences ou contraintes spécifiques", size="2", font_weight="500", color="var(--gray-11)"),
            rx.text_area(
                value=CollabTeacherState.preferences,
                on_change=CollabTeacherState.set_preferences,
                placeholder="Ex : Je préfère ne pas enseigner le vendredi après-midi...",
                rows="4",
                width="100%",
                border="1px solid var(--gray-5)",
                border_radius="8px",
                font_size="13px",
                resize="vertical",
            ),
            spacing="2",
            width="100%",
            align="start",
        ),

        # Submit
        rx.button(
            rx.icon("send", size=14),
            "Soumettre mes disponibilités",
            on_click=CollabTeacherState.submit,
            style=btn_primary,
            size="3",
            width="100%",
        ),

        spacing="4",
        width="100%",
        align="start",
    )


# ─── After-timetable view ───────────────────────────────────────────────────────

def _stat_card(icon: str, value: rx.Var, label: str) -> rx.Component:
    return rx.vstack(
        rx.icon(icon, size=20, color="var(--teal-9)"),
        rx.text(value, font_size="22px", font_weight="700", color="var(--gray-12)"),
        rx.text(label, size="1", color="var(--gray-9)", text_align="center"),
        align="center",
        padding="14px 20px",
        background="var(--gray-2)",
        border="1px solid var(--gray-4)",
        border_radius="10px",
        flex="1",
        spacing="1",
    )


def _timetable_view() -> rx.Component:
    return rx.vstack(
        # Stats row
        rx.hstack(
            _stat_card("clock",     CollabTeacherState.stat_hours, "Heures/sem."),
            _stat_card("calendar",  CollabTeacherState.stat_days,  "Jours actifs"),
            _stat_card("coffee",    CollabTeacherState.stat_free,  "Créneaux libres"),
            gap="12px",
            width="100%",
        ),

        # Timetable grid (populated once solver assigns this teacher's courses)
        rx.text(
            "Votre emploi du temps",
            size="3",
            font_weight="500",
            color="var(--gray-11)",
        ),
        rx.box(
            rx.text(
                "L'emploi du temps détaillé sera disponible après la génération.",
                size="2",
                color="var(--gray-9)",
            ),
            padding="24px",
            background="var(--gray-2)",
            border="1px dashed var(--gray-5)",
            border_radius="10px",
            width="100%",
            text_align="center",
        ),

        # Preference feedback
        rx.vstack(
            rx.text("Retour sur vos préférences", size="2", font_weight="500", color="var(--gray-11)"),
            rx.cond(
                CollabTeacherState.preference_feedback.length() == 0,
                rx.text("Aucun retour disponible.", size="2", color="var(--gray-8)"),
                rx.vstack(
                    rx.foreach(
                        CollabTeacherState.preference_feedback,
                        lambda item: rx.hstack(
                            rx.icon("check", size=14, color="var(--green-9)"),
                            rx.text(item, size="2"),
                            gap="6px",
                            align="center",
                        ),
                    ),
                    spacing="2",
                    align="start",
                ),
            ),
            spacing="2",
            align="start",
            width="100%",
        ),

        # Download PDF
        rx.button(
            rx.icon("download", size=14),
            "Télécharger mon emploi du temps (PDF)",
            variant="outline",
            size="2",
            cursor="pointer",
            width="100%",
        ),

        spacing="4",
        width="100%",
        align="start",
    )


# ─── Success confirmation ───────────────────────────────────────────────────────

def _success_banner() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.icon("circle_check", size=40, color="var(--green-9)"),
            rx.text(
                "Disponibilités soumises !",
                font_weight="600",
                size="4",
                color="var(--gray-12)",
            ),
            rx.text(
                "Merci. L'administrateur sera notifié. Vous pouvez fermer cette page.",
                size="2",
                color="var(--gray-9)",
                text_align="center",
            ),
            align="center",
            spacing="3",
        ),
        padding="40px 24px",
        background="var(--green-2)",
        border="1px solid var(--green-6)",
        border_radius="12px",
        text_align="center",
        width="100%",
    )


# ─── Error state ───────────────────────────────────────────────────────────────

def _error_view() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.icon("circle_x", size=36, color="var(--red-9)"),
            rx.text(
                "Lien invalide",
                font_weight="600",
                size="4",
                color="var(--gray-12)",
            ),
            rx.text(
                CollabTeacherState.error_msg,
                size="2",
                color="var(--gray-9)",
                text_align="center",
            ),
            align="center",
            spacing="3",
        ),
        style=hint_box,
    )


# ─── Page ─────────────────────────────────────────────────────────────────────

def collab_teacher() -> rx.Component:
    """Teacher availability page — no sidebar, mobile-first, no auth required."""
    return rx.box(
        rx.box(
            rx.vstack(
                # Header
                rx.vstack(
                    rx.hstack(
                        rx.box(
                            rx.text("T", color="white", font_weight="700", font_size="18px"),
                            width="36px",
                            height="36px",
                            border_radius="50%",
                            background="var(--teal-9)",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                            flex_shrink="0",
                        ),
                        rx.vstack(
                            rx.text(
                                CollabTeacherState.teacher_name,
                                font_weight="600",
                                size="4",
                                color="var(--gray-12)",
                            ),
                            rx.text(
                                CollabTeacherState.school_name,
                                size="2",
                                color="var(--gray-9)",
                            ),
                            spacing="0",
                            align="start",
                        ),
                        gap="10px",
                        align="center",
                        width="100%",
                    ),
                    rx.divider(),
                    spacing="3",
                    width="100%",
                ),

                # Main content — switches between error / success / before / after
                rx.cond(
                    ~CollabTeacherState.loaded,
                    _error_view(),
                    rx.cond(
                        CollabTeacherState.submitted,
                        _success_banner(),
                        rx.cond(
                            CollabTeacherState.has_timetable,
                            _timetable_view(),
                            _availability_form(),
                        ),
                    ),
                ),

                spacing="5",
                width="100%",
                align="start",
            ),
            max_width="600px",
            margin="0 auto",
            padding="24px 16px 48px 16px",
            width="100%",
        ),
        min_height="100vh",
        background="var(--gray-1)",
        width="100%",
    )
