"""Fixed sidebar navigation component for TIMEASE."""
import reflex as rx

from timease.app.state import AppState
from timease.app.style import *

_NAV_ITEMS = [
    ("home", "Accueil", "/"),
    ("layout_dashboard", "Espace de travail", "/workspace"),
    ("calendar", "Résultats", "/resultats"),
    ("users", "Collaboration", "/collaboration"),
]


def _nav_item(icon: str, label: str, href: str) -> rx.Component:
    """Single nav row with icon, label, and active highlight."""
    is_active = rx.State.router.page.path == href
    return rx.link(
        rx.hstack(
            rx.icon(
                icon,
                size=16,
                color=rx.cond(is_active, rx.color("teal", 11), rx.color("gray", 10)),
            ),
            rx.text(
                label,
                size="2",
                font_weight=rx.cond(is_active, "500", "400"),
                color=rx.cond(is_active, rx.color("teal", 11), rx.color("gray", 10)),
            ),
            padding="8px 12px",
            border_radius=INPUT_RADIUS,
            width="100%",
            background=rx.cond(is_active, rx.color("teal", 3), "transparent"),
            _hover={"background": rx.cond(is_active, rx.color("teal", 3), rx.color("gray", 3))},
            cursor="pointer",
            spacing="2",
            align="center",
        ),
        href=href,
        text_decoration="none",
        width="100%",
        display="block",
    )


def sidebar() -> rx.Component:
    """Fixed sidebar with nav links and dark-mode toggle."""
    return rx.box(
        # Logo row
        rx.hstack(
            rx.box(
                rx.text("T", color="white", font_weight="600", font_size="16px"),
                style=sidebar_logo_circle,
            ),
            rx.text("TIMEASE", style=sidebar_brand_text),
            align="center",
            spacing="2",
            padding_bottom="20px",
        ),
        # Nav links
        rx.vstack(
            *[_nav_item(icon, label, href) for icon, label, href in _NAV_ITEMS],
            align="start",
            spacing="1",
            width="100%",
        ),
        # Spacer
        rx.box(flex="1"),
        # Progress
        rx.vstack(
            rx.hstack(
                rx.text("Progression", size="1", color=rx.color("gray", 9)),
                rx.text(
                    AppState.progress_percent,
                    "%",
                    size="1",
                    color=rx.color("teal", 9),
                    font_weight="500",
                ),
                justify="between",
                width="100%",
            ),
            rx.progress(
                value=AppState.progress_percent,
                color_scheme="teal",
                width="100%",
            ),
            spacing="1",
            width="100%",
        ),
        # Dark mode toggle
        rx.hstack(
            rx.icon("sun", size=16, color="var(--gray-8)"),
            rx.color_mode.switch(size="1", color_scheme="teal"),
            rx.icon("moon", size=16, color="var(--gray-8)"),
            align="center",
            gap="8px",
            padding_top="12px",
        ),
        style=sidebar_style,
        z_index="100",
    )
