"""Contraintes page — scheduling constraints editor."""

import reflex as rx

from timease.app.components.layout import page_layout


def contraintes() -> rx.Component:
    """Contraintes page at route /contraintes."""
    return page_layout(
        rx.vstack(
            rx.heading("Contraintes", size="7", color="#0F6E56"),
            rx.text("Ajoutez et gérez les contraintes de planification.", color="#4a5568"),
            align="start",
            spacing="3",
            width="100%",
        )
    )
