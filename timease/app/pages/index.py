"""Landing page for TIMEASE."""

import reflex as rx

from timease.app.components.layout import page_layout
from timease.app.style import *


def _feature_card(icon: str, title: str, description: str) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.icon(icon, size=28, color=rx.color("teal", 9)),
            rx.text(title, font_weight="600", size="3", color=rx.color("gray", 12)),
            rx.text(description, color=rx.color("gray", 9), size="2", text_align="center"),
            align="center",
            spacing="2",
        ),
        padding="24px",
        border_radius="12px",
        background=rx.color("gray", 2),
        border="1px solid var(--gray-4)",
        flex="1",
        min_width="200px",
        text_align="center",
    )


def index() -> rx.Component:
    """Landing page at route /."""
    return page_layout(
        rx.vstack(
            # Hero
            rx.vstack(
                rx.heading(
                    "TIMEASE",
                    size="9",
                    color=rx.color("teal", 9),
                    font_weight="800",
                    letter_spacing="-0.02em",
                ),
                rx.text(
                    "Générez vos emplois du temps en quelques minutes",
                    size="4",
                    color=rx.color("gray", 11),
                    text_align="center",
                    max_width="520px",
                ),
                rx.text(
                    "Conçu pour les écoles privées francophones. Simple, rapide, intelligent.",
                    size="2",
                    color=rx.color("gray", 9),
                    text_align="center",
                    max_width="420px",
                ),
                align="center",
                spacing="3",
                padding_bottom="16px",
            ),
            # Feature cards
            rx.hstack(
                _feature_card("bot", "Configuration par IA", "Décrivez votre école en langage naturel. L'IA configure automatiquement vos données."),
                _feature_card("users", "Collaboration enseignants", "Partagez un lien sécurisé avec chaque enseignant pour recueillir leurs disponibilités."),
                _feature_card("file_down", "Export multi-format", "Exportez vos emplois du temps en PDF, Word, Excel ou Markdown en un clic."),
                gap="16px",
                flex_wrap="wrap",
                width="100%",
                justify="center",
            ),
            # CTA
            rx.link(
                rx.button(
                    "Commencer gratuitement",
                    color_scheme="teal",
                    size="3",
                    cursor="pointer",
                ),
                href="/configuration",
                text_decoration="none",
            ),
            align="center",
            spacing="6",
            padding_top="48px",
            width="100%",
        )
    )
