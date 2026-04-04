"""Fixed sidebar navigation component for TIMEASE."""

import reflex as rx

from timease.app.state import AppState


def _nav_item(label: str, href: str) -> rx.Component:
    """Single navigation link with active-page highlight."""
    return rx.link(
        rx.box(
            label,
            padding="0.6em 1em",
            border_radius="6px",
            width="100%",
            font_weight="500",
            background=rx.cond(
                rx.State.router.page.path == href,
                "rgba(15, 110, 86, 0.15)",
                "transparent",
            ),
            color=rx.cond(
                rx.State.router.page.path == href,
                "#0F6E56",
                "inherit",
            ),
            _hover={"background": "rgba(15, 110, 86, 0.08)"},
            transition="background 0.15s",
        ),
        href=href,
        text_decoration="none",
        width="100%",
        display="block",
    )


def sidebar() -> rx.Component:
    """Fixed 240-px sidebar with logo, nav links, and progress bar."""
    return rx.box(
        # Logo row
        rx.hstack(
            rx.box(
                rx.text("T", color="white", font_weight="bold", font_size="1.1em"),
                background="#0F6E56",
                border_radius="50%",
                width="36px",
                height="36px",
                display="flex",
                align_items="center",
                justify_content="center",
            ),
            rx.text(
                "TIMEASE",
                font_weight="700",
                font_size="1.1em",
                color="#0F6E56",
                letter_spacing="0.05em",
            ),
            align="center",
            spacing="2",
            padding_bottom="1.5em",
        ),
        # Navigation links
        rx.vstack(
            _nav_item("Accueil", "/"),
            _nav_item("Configuration", "/configuration"),
            _nav_item("Programme", "/programme"),
            _nav_item("Contraintes", "/contraintes"),
            _nav_item("Générer", "/generer"),
            _nav_item("Résultats", "/resultats"),
            _nav_item("Collaboration", "/collaboration"),
            align="start",
            spacing="1",
            width="100%",
        ),
        # Spacer pushes progress bar to bottom
        rx.box(flex="1"),
        # Progress bar
        rx.vstack(
            rx.hstack(
                rx.text("Progression", font_size="0.75em", color="gray"),
                rx.text(
                    AppState.progress_percent.to_string() + "%",
                    font_size="0.75em",
                    color="#0F6E56",
                    font_weight="600",
                ),
                justify="between",
                width="100%",
            ),
            rx.box(
                rx.box(
                    width=AppState.progress_percent.to_string() + "%",
                    height="100%",
                    background="#0F6E56",
                    border_radius="4px",
                    transition="width 0.3s ease",
                ),
                width="100%",
                height="6px",
                background="#e2e8f0",
                border_radius="4px",
                overflow="hidden",
            ),
            width="100%",
            spacing="1",
        ),
        # Sidebar container styles
        position="fixed",
        top="0",
        left="0",
        height="100vh",
        width="240px",
        padding="1.5em 1em",
        background="white",
        border_right="1px solid #e2e8f0",
        display="flex",
        flex_direction="column",
        z_index="100",
    )
