"""Dynamic timetable grid — renders from AppState.grid_rows via rx.foreach."""

import reflex as rx

from timease.app.state import AppState, GridCell, GridRow
from timease.app.style import (
    timetable_cell,
    timetable_cell_info,
    timetable_cell_subject,
    timetable_header,
    timetable_time_col,
)


# ─── Cell renderers ─────────────────────────────────────────────────────────────

def _free_cell() -> rx.Component:
    return rx.box(
        min_height="52px",
        background="var(--gray-2)",
        border_radius="4px",
        width="100%",
    )


def _filled_cell(cell: GridCell) -> rx.Component:
    """Colored cell; line2/line3 adapt to the active tab."""
    line2 = rx.cond(
        AppState.active_result_tab == "class",
        cell.teacher,
        cell.school_class,
    )
    line3 = rx.cond(
        AppState.active_result_tab == "room",
        cell.teacher,
        cell.room,
    )

    return rx.box(
        rx.vstack(
            rx.text(cell.subject, style=timetable_cell_subject),
            rx.text(line2,        style=timetable_cell_info),
            rx.text(line3,        style=timetable_cell_info),
            spacing="0",
            align="start",
        ),
        background=cell.color,
        opacity="0.92",
        padding="4px 6px",
        border_radius="4px",
        font_size="11px",
        line_height="1.35",
        min_height="52px",
        width="100%",
    )


def render_cell(cell: GridCell) -> rx.Component:
    return rx.table.cell(
        rx.cond(
            cell.empty,
            _free_cell(),
            _filled_cell(cell),
        ),
        padding="3px",
    )


def render_row(row: GridRow) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            row.time,
            style={
                **timetable_time_col,
                "border_right": "1px solid var(--gray-4)",
                "padding": "8px 8px 8px 4px",
                "white_space": "nowrap",
            },
        ),
        rx.foreach(row.cells, render_cell),
    )


# ─── Public component ────────────────────────────────────────────────────────────

def dynamic_timetable_grid() -> rx.Component:
    """
    Timetable grid driven by AppState.grid_rows and AppState.result_days_list.
    Uses rx.foreach — no Python-level dict lookups on reactive state.
    """
    return rx.box(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell(
                        "",
                        style={
                            **timetable_header,
                            "width": "64px",
                            "background": "var(--gray-2)",
                        },
                    ),
                    rx.foreach(
                        AppState.result_days_list,
                        lambda d: rx.table.column_header_cell(
                            d,
                            style={
                                **timetable_header,
                                "background": "var(--gray-2)",
                            },
                        ),
                    ),
                )
            ),
            rx.table.body(
                rx.foreach(AppState.grid_rows, render_row),
            ),
            width="100%",
            border="1px solid var(--gray-4)",
            border_radius="10px",
            overflow="hidden",
        ),
        overflow_x="auto",
        width="100%",
    )
