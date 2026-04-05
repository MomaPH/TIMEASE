"""Forms tab — École / Enseignants / Classes / Salles sub-tabs."""

import reflex as rx

from timease.app.state import AppState

_WEEK_DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"]

# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _label(text: str) -> rx.Component:
    return rx.text(text, size="1", color=rx.color("gray", 9), font_weight="500", margin_bottom="2px")


def _section_heading(text: str) -> rx.Component:
    return rx.text(text, size="2", font_weight="600", color=rx.color("gray", 11), margin_bottom="8px", margin_top="16px")


def _empty_table_row(colspan: int, message: str) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.text(message, color=rx.color("gray", 8), size="2", text_align="center"),
            col_span=colspan,
            padding="24px",
        )
    )


def _action_btn(icon: str, label: str, on_click, color: str = "gray") -> rx.Component:
    return rx.button(
        rx.icon(icon, size=14),
        label,
        variant="ghost",
        size="1",
        color_scheme=color,
        cursor="pointer",
        on_click=on_click,
    )


# ─────────────────────────────────────────────────────────────────────────────
# École sub-tab
# ─────────────────────────────────────────────────────────────────────────────

def _day_checkbox(day: str) -> rx.Component:
    return rx.hstack(
        rx.checkbox(
            checked=AppState.form_days.contains(day),
            on_change=AppState.toggle_day(day),
            color_scheme="teal",
        ),
        rx.text(day.capitalize(), size="2"),
        align="center",
        gap="6px",
    )


def _session_row(session: dict) -> rx.Component:
    """One editable session row in the schedule grid."""
    return rx.hstack(
        rx.input(
            value=session["name"],
            on_change=AppState.update_session_name(session["id"]),
            placeholder="Nom (ex: Matin)",
            size="2",
            flex="1",
        ),
        rx.el.input(
            type="time",
            value=session["start_time"],
            on_change=AppState.update_session_start(session["id"]),
            style={
                "font_size": "13px",
                "padding": "4px 8px",
                "border": "1px solid var(--gray-5)",
                "border_radius": "6px",
                "background": rx.color("gray", 1),
                "color": rx.color("gray", 12),
                "width": "130px",
            },
        ),
        rx.el.input(
            type="time",
            value=session["end_time"],
            on_change=AppState.update_session_end(session["id"]),
            style={
                "font_size": "13px",
                "padding": "4px 8px",
                "border": "1px solid var(--gray-5)",
                "border_radius": "6px",
                "background": rx.color("gray", 1),
                "color": rx.color("gray", 12),
                "width": "130px",
            },
        ),
        rx.icon_button(
            rx.icon("x", size=14),
            on_click=AppState.remove_session(session["id"]),
            variant="ghost",
            color_scheme="red",
            size="1",
            cursor="pointer",
        ),
        gap="8px",
        align="center",
        width="100%",
        padding="6px 0",
        border_bottom="1px solid var(--gray-3)",
    )


def _school_tab() -> rx.Component:
    return rx.vstack(
        # ── Informations générales ─────────────────────────────────
        _section_heading("Informations générales"),
        rx.hstack(
            rx.vstack(
                _label("Nom de l'école"),
                rx.input(
                    value=AppState.form_school_name,
                    on_change=AppState.set_form_school_name,
                    placeholder="Lycée Saint-Joseph",
                    size="2",
                    width="100%",
                ),
                align="start",
                flex="2",
                spacing="1",
            ),
            rx.vstack(
                _label("Année scolaire"),
                rx.input(
                    value=AppState.form_school_year,
                    on_change=AppState.set_form_school_year,
                    placeholder="2026-2027",
                    size="2",
                    width="100%",
                ),
                align="start",
                flex="1",
                spacing="1",
            ),
            rx.vstack(
                _label("Ville"),
                rx.input(
                    value=AppState.form_school_city,
                    on_change=AppState.set_form_school_city,
                    placeholder="Abidjan",
                    size="2",
                    width="100%",
                ),
                align="start",
                flex="1",
                spacing="1",
            ),
            gap="12px",
            width="100%",
            align="end",
        ),

        # ── Jours actifs ──────────────────────────────────────────
        _section_heading("Jours actifs"),
        rx.hstack(
            *[_day_checkbox(day) for day in _WEEK_DAYS],
            flex_wrap="wrap",
            gap="12px",
        ),

        # ── Sessions ──────────────────────────────────────────────
        _section_heading("Sessions horaires"),
        rx.hstack(
            rx.text("Nom", size="1", color=rx.color("gray", 9), flex="1"),
            rx.text("Début", size="1", color=rx.color("gray", 9), width="130px"),
            rx.text("Fin", size="1", color=rx.color("gray", 9), width="130px"),
            rx.box(width="32px"),
            gap="8px",
            padding_bottom="4px",
        ),
        rx.vstack(
            rx.foreach(AppState.form_sessions, _session_row),
            width="100%",
            spacing="0",
        ),
        rx.button(
            rx.icon("plus", size=14),
            "Ajouter une session",
            variant="ghost",
            color_scheme="teal",
            size="2",
            on_click=AppState.add_session,
            cursor="pointer",
            margin_top="4px",
        ),

        # ── Unité de base ─────────────────────────────────────────
        _section_heading("Unité de base"),
        rx.hstack(
            rx.vstack(
                _label("Durée minimale d'un créneau"),
                rx.select.root(
                    rx.select.trigger(placeholder="30 minutes"),
                    rx.select.content(
                        rx.select.item("15 minutes", value="15"),
                        rx.select.item("30 minutes", value="30"),
                        rx.select.item("60 minutes", value="60"),
                    ),
                    value=AppState.form_base_unit,
                    on_change=AppState.set_form_base_unit,
                    size="2",
                ),
                spacing="1",
                align="start",
            ),
            align="end",
        ),

        # ── Save ──────────────────────────────────────────────────
        rx.box(
            rx.button(
                rx.icon("save", size=14),
                "Enregistrer",
                color_scheme="teal",
                size="2",
                on_click=AppState.save_school_info,
                cursor="pointer",
            ),
            margin_top="16px",
        ),

        align="start",
        width="100%",
        spacing="2",
        padding="4px 0",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Teacher dialog
# ─────────────────────────────────────────────────────────────────────────────

def _avail_select(day: str) -> rx.Component:
    return rx.hstack(
        rx.text(day.capitalize(), size="2", width="88px", color=rx.color("gray", 11)),
        rx.select.root(
            rx.select.trigger(),
            rx.select.content(
                rx.select.item("Disponible", value="disponible"),
                rx.select.item("Pas idéal", value="pas_ideal"),
                rx.select.item("Impossible", value="impossible"),
            ),
            value=AppState.form_teacher_avail[day],
            on_change=AppState.set_teacher_avail_day(day),
            size="2",
            width="160px",
        ),
        align="center",
        gap="8px",
    )


def _subject_checkbox(subject: str) -> rx.Component:
    return rx.hstack(
        rx.checkbox(
            checked=AppState.form_teacher_subjects.contains(subject),
            on_change=AppState.toggle_teacher_subject(subject),
            color_scheme="teal",
        ),
        rx.text(subject, size="2"),
        align="center",
        gap="6px",
    )


def teacher_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.cond(
                    AppState.teacher_edit_index == -1,
                    "Ajouter un enseignant",
                    "Modifier l'enseignant",
                )
            ),
            rx.vstack(
                # Nom
                rx.vstack(
                    _label("Nom"),
                    rx.input(
                        value=AppState.form_teacher_name,
                        on_change=AppState.set_form_teacher_name,
                        placeholder="Ex: M. Diallo",
                        size="2",
                        width="100%",
                        auto_focus=True,
                    ),
                    align="start",
                    width="100%",
                    spacing="1",
                ),
                # Heures max
                rx.vstack(
                    _label("Heures max / semaine"),
                    rx.input(
                        value=AppState.form_teacher_max_hours,
                        on_change=AppState.set_form_teacher_max_hours,
                        type="number",
                        min="1",
                        max="40",
                        size="2",
                        width="120px",
                    ),
                    align="start",
                    spacing="1",
                ),
                # Matières
                rx.vstack(
                    _label("Matières enseignées"),
                    rx.cond(
                        AppState.subject_count == 0,
                        rx.text(
                            "Aucune matière configurée. Utilisez l'IA ou ajoutez via l'onglet Programme.",
                            size="1",
                            color=rx.color("gray", 8),
                            font_style="italic",
                        ),
                        rx.vstack(
                            rx.foreach(AppState.subjects_list, _subject_checkbox),
                            align="start",
                            spacing="1",
                            flex_wrap="wrap",
                        ),
                    ),
                    align="start",
                    width="100%",
                    spacing="1",
                ),
                # Disponibilités
                rx.vstack(
                    _label("Disponibilités par jour"),
                    rx.vstack(
                        *[_avail_select(day) for day in _WEEK_DAYS],
                        spacing="2",
                        align="start",
                    ),
                    align="start",
                    width="100%",
                    spacing="1",
                ),
                # Buttons
                rx.hstack(
                    rx.dialog.close(
                        rx.button(
                            "Annuler",
                            variant="soft",
                            color_scheme="gray",
                            size="2",
                            cursor="pointer",
                            on_click=AppState.close_teacher_dialog,
                        )
                    ),
                    rx.button(
                        "Enregistrer",
                        color_scheme="teal",
                        size="2",
                        cursor="pointer",
                        on_click=AppState.save_teacher,
                    ),
                    justify="end",
                    gap="8px",
                    margin_top="8px",
                    width="100%",
                ),
                align="start",
                width="100%",
                spacing="4",
            ),
            max_width="520px",
        ),
        open=AppState.show_teacher_dialog,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Teachers sub-tab
# ─────────────────────────────────────────────────────────────────────────────

def _teacher_row(row: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(row["name"], size="2", font_weight="500")),
        rx.table.cell(rx.text(row["subjects_str"], size="2", color=rx.color("gray", 10))),
        rx.table.cell(rx.text(row["max_hours"], size="2")),
        rx.table.cell(rx.text(row["unavail"], size="2", color=rx.color("gray", 9))),
        rx.table.cell(
            rx.hstack(
                _action_btn("pencil", "Modifier", AppState.open_teacher_dialog(row["_idx"])),
                _action_btn("trash_2", "Supprimer", AppState.request_delete("teacher", row["_idx"]), "red"),
                gap="4px",
            )
        ),
        _hover={"background": rx.color("gray", 2)},
    )


def _teachers_tab() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.button(
                rx.icon("plus", size=14),
                "Ajouter un enseignant",
                color_scheme="teal",
                size="2",
                cursor="pointer",
                on_click=AppState.open_teacher_dialog(-1),
            ),
            justify="end",
            width="100%",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    *[
                        rx.table.column_header_cell(
                            col,
                            background=rx.color("gray", 2),
                            padding="8px 12px",
                            font_size="12px",
                            color=rx.color("gray", 9),
                            font_weight="500",
                        )
                        for col in ["Nom", "Matières", "Heures max", "Indisponibilités", "Actions"]
                    ]
                )
            ),
            rx.table.body(
                rx.cond(
                    AppState.teacher_count == 0,
                    _empty_table_row(5, "Aucun enseignant. Cliquez sur « Ajouter » pour commencer."),
                    rx.foreach(AppState.teachers_table, _teacher_row),
                )
            ),
            width="100%",
            border="1px solid var(--gray-4)",
            border_radius="10px",
            overflow="hidden",
        ),
        align="start",
        width="100%",
        spacing="3",
        padding="4px 0",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Class dialog
# ─────────────────────────────────────────────────────────────────────────────

def class_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.cond(
                    AppState.class_edit_index == -1,
                    "Ajouter une classe",
                    "Modifier la classe",
                )
            ),
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        _label("Nom de la classe"),
                        rx.input(
                            value=AppState.form_class_name,
                            on_change=AppState.set_form_class_name,
                            placeholder="6ème A",
                            size="2",
                            auto_focus=True,
                        ),
                        align="start",
                        spacing="1",
                        flex="1",
                    ),
                    rx.vstack(
                        _label("Niveau"),
                        rx.input(
                            value=AppState.form_class_level,
                            on_change=AppState.set_form_class_level,
                            placeholder="6ème",
                            size="2",
                        ),
                        align="start",
                        spacing="1",
                        flex="1",
                    ),
                    rx.vstack(
                        _label("Effectif"),
                        rx.input(
                            value=AppState.form_class_count,
                            on_change=AppState.set_form_class_count,
                            type="number",
                            min="1",
                            placeholder="30",
                            size="2",
                            width="80px",
                        ),
                        align="start",
                        spacing="1",
                    ),
                    gap="12px",
                    width="100%",
                    align="end",
                ),
                rx.hstack(
                    rx.dialog.close(
                        rx.button(
                            "Annuler",
                            variant="soft",
                            color_scheme="gray",
                            size="2",
                            cursor="pointer",
                            on_click=AppState.close_class_dialog,
                        )
                    ),
                    rx.button(
                        "Enregistrer",
                        color_scheme="teal",
                        size="2",
                        cursor="pointer",
                        on_click=AppState.save_class,
                    ),
                    justify="end",
                    gap="8px",
                    margin_top="8px",
                    width="100%",
                ),
                align="start",
                width="100%",
                spacing="4",
            ),
            max_width="480px",
        ),
        open=AppState.show_class_dialog,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Classes sub-tab
# ─────────────────────────────────────────────────────────────────────────────

def _class_row(row: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(row["name"], size="2", font_weight="500")),
        rx.table.cell(rx.text(row["level"], size="2", color=rx.color("gray", 10))),
        rx.table.cell(rx.text(row["count"], size="2")),
        rx.table.cell(
            rx.hstack(
                _action_btn("pencil", "Modifier", AppState.open_class_dialog(row["_idx"])),
                _action_btn("trash_2", "Supprimer", AppState.request_delete("class", row["_idx"]), "red"),
                gap="4px",
            )
        ),
        _hover={"background": rx.color("gray", 2)},
    )


def _classes_tab() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.button(
                rx.icon("plus", size=14),
                "Ajouter une classe",
                color_scheme="teal",
                size="2",
                cursor="pointer",
                on_click=AppState.open_class_dialog(-1),
            ),
            justify="end",
            width="100%",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    *[
                        rx.table.column_header_cell(
                            col,
                            background=rx.color("gray", 2),
                            padding="8px 12px",
                            font_size="12px",
                            color=rx.color("gray", 9),
                            font_weight="500",
                        )
                        for col in ["Nom", "Niveau", "Effectif", "Actions"]
                    ]
                )
            ),
            rx.table.body(
                rx.cond(
                    AppState.class_count == 0,
                    _empty_table_row(4, "Aucune classe. Cliquez sur « Ajouter » pour commencer."),
                    rx.foreach(AppState.classes_table, _class_row),
                )
            ),
            width="100%",
            border="1px solid var(--gray-4)",
            border_radius="10px",
            overflow="hidden",
        ),
        align="start",
        width="100%",
        spacing="3",
        padding="4px 0",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Room dialog
# ─────────────────────────────────────────────────────────────────────────────

def room_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.cond(
                    AppState.room_edit_index == -1,
                    "Ajouter une salle",
                    "Modifier la salle",
                )
            ),
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        _label("Nom de la salle"),
                        rx.input(
                            value=AppState.form_room_name,
                            on_change=AppState.set_form_room_name,
                            placeholder="Salle 101",
                            size="2",
                            auto_focus=True,
                        ),
                        align="start",
                        spacing="1",
                        flex="1",
                    ),
                    rx.vstack(
                        _label("Capacité"),
                        rx.input(
                            value=AppState.form_room_capacity,
                            on_change=AppState.set_form_room_capacity,
                            type="number",
                            min="1",
                            placeholder="40",
                            size="2",
                            width="80px",
                        ),
                        align="start",
                        spacing="1",
                    ),
                    gap="12px",
                    width="100%",
                    align="end",
                ),
                rx.vstack(
                    _label("Types (séparés par virgule)"),
                    rx.input(
                        value=AppState.form_room_types,
                        on_change=AppState.set_form_room_types,
                        placeholder="Salle standard, Laboratoire",
                        size="2",
                        width="100%",
                    ),
                    rx.text(
                        "Ex: Salle standard, Laboratoire, Salle informatique",
                        size="1",
                        color=rx.color("gray", 8),
                    ),
                    align="start",
                    width="100%",
                    spacing="1",
                ),
                rx.hstack(
                    rx.dialog.close(
                        rx.button(
                            "Annuler",
                            variant="soft",
                            color_scheme="gray",
                            size="2",
                            cursor="pointer",
                            on_click=AppState.close_room_dialog,
                        )
                    ),
                    rx.button(
                        "Enregistrer",
                        color_scheme="teal",
                        size="2",
                        cursor="pointer",
                        on_click=AppState.save_room,
                    ),
                    justify="end",
                    gap="8px",
                    margin_top="8px",
                    width="100%",
                ),
                align="start",
                width="100%",
                spacing="4",
            ),
            max_width="480px",
        ),
        open=AppState.show_room_dialog,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Rooms sub-tab
# ─────────────────────────────────────────────────────────────────────────────

def _room_row(row: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(row["name"], size="2", font_weight="500")),
        rx.table.cell(rx.text(row["capacity"], size="2")),
        rx.table.cell(rx.text(row["types"], size="2", color=rx.color("gray", 10))),
        rx.table.cell(
            rx.hstack(
                _action_btn("pencil", "Modifier", AppState.open_room_dialog(row["_idx"])),
                _action_btn("trash_2", "Supprimer", AppState.request_delete("room", row["_idx"]), "red"),
                gap="4px",
            )
        ),
        _hover={"background": rx.color("gray", 2)},
    )


def _rooms_tab() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.button(
                rx.icon("plus", size=14),
                "Ajouter une salle",
                color_scheme="teal",
                size="2",
                cursor="pointer",
                on_click=AppState.open_room_dialog(-1),
            ),
            justify="end",
            width="100%",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    *[
                        rx.table.column_header_cell(
                            col,
                            background=rx.color("gray", 2),
                            padding="8px 12px",
                            font_size="12px",
                            color=rx.color("gray", 9),
                            font_weight="500",
                        )
                        for col in ["Nom", "Capacité", "Types", "Actions"]
                    ]
                )
            ),
            rx.table.body(
                rx.cond(
                    AppState.room_count == 0,
                    _empty_table_row(4, "Aucune salle. Cliquez sur « Ajouter » pour commencer."),
                    rx.foreach(AppState.rooms_table, _room_row),
                )
            ),
            width="100%",
            border="1px solid var(--gray-4)",
            border_radius="10px",
            overflow="hidden",
        ),
        align="start",
        width="100%",
        spacing="3",
        padding="4px 0",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Delete confirmation (alert dialog)
# ─────────────────────────────────────────────────────────────────────────────

def delete_confirm_dialog() -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Confirmer la suppression"),
            rx.alert_dialog.description(
                "Supprimer cet ",
                AppState.delete_label,
                " ? Cette action est irréversible.",
                size="2",
            ),
            rx.flex(
                rx.alert_dialog.cancel(
                    rx.button(
                        "Annuler",
                        variant="soft",
                        color_scheme="gray",
                        size="2",
                        cursor="pointer",
                        on_click=AppState.cancel_delete,
                    )
                ),
                rx.alert_dialog.action(
                    rx.button(
                        "Supprimer",
                        color_scheme="red",
                        size="2",
                        cursor="pointer",
                        on_click=AppState.confirm_delete,
                    )
                ),
                gap="8px",
                justify="end",
                margin_top="16px",
            ),
        ),
        open=AppState.show_delete_dialog,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def forms_tab() -> rx.Component:
    """Complete forms tab with sub-tabs and all dialogs."""
    return rx.fragment(
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("École", value="school"),
                rx.tabs.trigger("Enseignants", value="teachers"),
                rx.tabs.trigger("Classes", value="classes"),
                rx.tabs.trigger("Salles", value="rooms"),
                margin_bottom="16px",
            ),
            rx.tabs.content(
                _school_tab(),
                value="school",
                width="100%",
            ),
            rx.tabs.content(
                _teachers_tab(),
                value="teachers",
                width="100%",
            ),
            rx.tabs.content(
                _classes_tab(),
                value="classes",
                width="100%",
            ),
            rx.tabs.content(
                _rooms_tab(),
                value="rooms",
                width="100%",
            ),
            value=AppState.active_forms_tab,
            on_change=AppState.set_forms_tab,
            width="100%",
        ),
        # Dialogs rendered outside tabs so they overlay correctly
        teacher_dialog(),
        class_dialog(),
        room_dialog(),
        delete_confirm_dialog(),
    )
