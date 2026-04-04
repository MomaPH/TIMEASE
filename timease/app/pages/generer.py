"""Générer page — trigger the CP-SAT solver."""

import reflex as rx

from timease.app.components.layout import page_layout


def generer() -> rx.Component:
    """Générer page at route /generer."""
    return page_layout(
        rx.vstack(
            rx.heading("Générer", size="7", color="#0F6E56"),
            rx.text("Lancez la génération automatique de l'emploi du temps.", color="#4a5568"),
            align="start",
            spacing="3",
            width="100%",
        )
    )
