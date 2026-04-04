"""Configuration page — school setup via AI chat, forms, or file upload."""

import reflex as rx

from timease.app.components.layout import page_layout


def configuration() -> rx.Component:
    """Configuration page at route /configuration."""
    return page_layout(
        rx.vstack(
            rx.heading("Configuration", size="7", color="#0F6E56"),
            rx.text("Configurez les données de votre école.", color="#4a5568"),
            align="start",
            spacing="3",
            width="100%",
        )
    )
