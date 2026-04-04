"""Résultats page — view and export the generated timetable."""

import reflex as rx

from timease.app.components.layout import page_layout


def resultats() -> rx.Component:
    """Résultats page at route /resultats."""
    return page_layout(
        rx.vstack(
            rx.heading("Résultats", size="7", color="#0F6E56"),
            rx.text("Consultez et exportez l'emploi du temps généré.", color="#4a5568"),
            align="start",
            spacing="3",
            width="100%",
        )
    )
