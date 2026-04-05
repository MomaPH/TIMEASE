"""Résultats page — dynamic timetable grid and export."""

import reflex as rx

from timease.app.components.layout import page_layout
from timease.app.components.timetable_grid import dynamic_timetable_grid
from timease.app.state import AppState
from timease.app.style import (
    badge_success,
    badge_warning,
    btn_primary,
    card,
    hint_box,
    tab_active,
    tab_group,
    tab_inactive,
)


# ─── Tab bar ────────────────────────────────────────────────────────────────────

def _tab_bar() -> rx.Component:
    tabs = [
        ("Par classe",     "class"),
        ("Par enseignant", "teacher"),
        ("Par salle",      "room"),
        ("Par matière",    "subject"),
    ]
    return rx.box(
        *[
            rx.button(
                label,
                on_click=AppState.set_result_tab(value),
                style=rx.cond(
                    AppState.active_result_tab == value,
                    tab_active,
                    tab_inactive,
                ),
            )
            for label, value in tabs
        ],
        style=tab_group,
    )


# ─── Entity selector ────────────────────────────────────────────────────────────

def _entity_selector() -> rx.Component:
    """Show the right dropdown depending on the active tab."""
    return rx.cond(
        AppState.active_result_tab == "class",
        rx.hstack(
            rx.text("Classe :", size="2", color="var(--gray-9)", white_space="nowrap"),
            rx.select(
                AppState.result_classes_list,
                value=AppState.selected_class,
                on_change=AppState.set_selected_class,
                size="2",
                width="220px",
            ),
            align="center",
            gap="10px",
            margin_bottom="12px",
        ),
        rx.cond(
            AppState.active_result_tab == "teacher",
            rx.hstack(
                rx.text("Enseignant :", size="2", color="var(--gray-9)", white_space="nowrap"),
                rx.select(
                    AppState.result_teachers_list,
                    value=AppState.selected_teacher,
                    on_change=AppState.set_selected_teacher,
                    size="2",
                    width="220px",
                ),
                align="center",
                gap="10px",
                margin_bottom="12px",
            ),
            rx.cond(
                AppState.active_result_tab == "room",
                rx.hstack(
                    rx.text("Salle :", size="2", color="var(--gray-9)", white_space="nowrap"),
                    rx.select(
                        AppState.result_rooms_list,
                        value=AppState.selected_room,
                        on_change=AppState.set_selected_room,
                        size="2",
                        width="220px",
                    ),
                    align="center",
                    gap="10px",
                    margin_bottom="12px",
                ),
                rx.fragment(),  # subject tab — no selector needed
            ),
        ),
    )


# ─── Subject summary tab ─────────────────────────────────────────────────────────

def _render_subject_row(row: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.box(
                    width="10px", height="10px",
                    border_radius="2px",
                    background=row["color"],
                    flex_shrink="0",
                ),
                rx.text(row["subject"], size="2", font_weight="500"),
                align="center",
                gap="6px",
            ),
            padding="10px 12px",
        ),
        rx.table.cell(row["teachers"],       padding="10px 12px", font_size="13px"),
        rx.table.cell(row["hours"].to_string(), padding="10px 12px", font_size="13px"),
        rx.table.cell(row["classes"],        padding="10px 12px", font_size="13px"),
        rx.table.cell(row["days"],           padding="10px 12px", font_size="13px"),
    )


def _subject_tab() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                *[
                    rx.table.column_header_cell(
                        col,
                        padding="10px 12px",
                        font_size="12px",
                        font_weight="500",
                        color="var(--gray-9)",
                    )
                    for col in ["Matière", "Enseignants", "Heures/sem.", "Classes", "Jours"]
                ]
            )
        ),
        rx.table.body(
            rx.foreach(AppState.result_subjects_summary, _render_subject_row),
        ),
        width="100%",
        border="1px solid var(--gray-4)",
        border_radius="10px",
        overflow="hidden",
    )


# ─── Grid area ───────────────────────────────────────────────────────────────────

def _grid_area() -> rx.Component:
    return rx.cond(
        AppState.active_result_tab == "subject",
        _subject_tab(),
        rx.vstack(
            _entity_selector(),
            dynamic_timetable_grid(),
            spacing="0",
            width="100%",
            align="start",
        ),
    )


# ─── Soft constraint panel ───────────────────────────────────────────────────────

def _render_soft_row(item: dict) -> rx.Component:
    """Render one soft-constraint feedback row.
    Handles both {ok, label, pct} and {description, satisfied_pct} formats.
    """
    ok = rx.cond(
        item.contains("ok"),
        item["ok"],
        item.contains("satisfied"),
    )
    label = rx.cond(
        item.contains("label"),
        item["label"],
        rx.cond(item.contains("description"), item["description"], "Contrainte souple"),
    )
    pct_val = rx.cond(
        item.contains("pct"),
        item["pct"].to_string(),
        rx.cond(item.contains("satisfied_pct"), item["satisfied_pct"].to_string(), "?"),
    )

    return rx.hstack(
        rx.cond(
            ok,
            rx.icon("circle_check", size=16, color="var(--green-9)"),
            rx.icon("circle_x",     size=16, color="var(--red-9)"),
        ),
        rx.text(label, size="2", flex="1"),
        rx.badge(
            rx.fragment(pct_val, "%"),
            style=rx.cond(ok, badge_success, badge_warning),
        ),
        align="center",
        width="100%",
        gap="8px",
    )


def _soft_constraints_panel() -> rx.Component:
    return rx.cond(
        AppState.result_soft_details.length() > 0,
        rx.vstack(
            rx.text(
                "Contraintes souples",
                size="2",
                font_weight="500",
                color="var(--gray-11)",
            ),
            rx.foreach(AppState.result_soft_details, _render_soft_row),
            padding="14px 16px",
            background="var(--gray-2)",
            border="1px solid var(--gray-4)",
            border_radius="10px",
            width="100%",
            spacing="2",
            align="start",
        ),
        rx.fragment(),
    )


# ─── Export card ─────────────────────────────────────────────────────────────────

def _export_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(
                "Exporter l'emploi du temps",
                size="2",
                font_weight="500",
                color="var(--gray-11)",
            ),
            rx.hstack(
                rx.checkbox("PDF",   default_checked=True,  size="2"),
                rx.checkbox("Excel", default_checked=False, size="2"),
                rx.checkbox("Word",  default_checked=False, size="2"),
                gap="16px",
            ),
            rx.button(
                rx.icon("download", size=14),
                "Télécharger",
                style=btn_primary,
                size="2",
            ),
            spacing="3",
            align="start",
        ),
        style=card,
        width="100%",
    )


# ─── Empty state ─────────────────────────────────────────────────────────────────

def _empty_state() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.icon("calendar", size=40, color="var(--gray-7)"),
            rx.text(
                "Aucun emploi du temps généré",
                font_weight="500",
                size="3",
                color="var(--gray-11)",
            ),
            rx.text(
                "Configurez vos données et lancez la génération depuis l'espace de travail.",
                size="2",
                color="var(--gray-9)",
                text_align="center",
            ),
            rx.link(
                rx.button("Aller à l'espace de travail", color_scheme="teal", size="2", cursor="pointer"),
                href="/workspace",
            ),
            align="center",
            spacing="3",
        ),
        style=hint_box,
    )


# ─── Page ────────────────────────────────────────────────────────────────────────

def resultats() -> rx.Component:
    """Résultats page at route /resultats."""
    return page_layout(
        rx.vstack(
            # Header
            rx.vstack(
                rx.heading("Résultats", size="5", font_weight="600"),
                rx.text(
                    "Consultez et exportez l'emploi du temps généré.",
                    color="var(--gray-9)",
                    size="2",
                ),
                spacing="1",
                align="start",
                width="100%",
            ),

            # Tab bar
            _tab_bar(),

            # Main content: empty state or grid
            rx.cond(
                AppState.has_timetable,
                rx.vstack(
                    _grid_area(),
                    _soft_constraints_panel(),
                    _export_card(),
                    spacing="4",
                    width="100%",
                ),
                _empty_state(),
            ),

            spacing="4",
            width="100%",
        )
    )
