"""Programme page — curriculum / course assignments."""

import reflex as rx

from timease.app.components.layout import page_layout


def programme() -> rx.Component:
    """Programme page at route /programme."""
    return page_layout(
        rx.vstack(
            rx.heading("Programme", size="7", color="#0F6E56"),
            rx.text("Définissez le programme scolaire et les affectations.", color="#4a5568"),
            align="start",
            spacing="3",
            width="100%",
        )
    )
