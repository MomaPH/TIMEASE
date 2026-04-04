"""Collaboration page — teacher availability links."""

import reflex as rx

from timease.app.components.layout import page_layout


def collaboration() -> rx.Component:
    """Collaboration page at route /collaboration."""
    return page_layout(
        rx.vstack(
            rx.heading("Collaboration", size="7", color="#0F6E56"),
            rx.text(
                "Partagez des liens avec les enseignants pour recueillir leurs disponibilités.",
                color="#4a5568",
            ),
            align="start",
            spacing="3",
            width="100%",
        )
    )
