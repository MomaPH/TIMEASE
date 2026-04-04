"""Landing page for TIMEASE."""

import reflex as rx

from timease.app.components.layout import page_layout


def _feature_card(icon: str, title: str, description: str) -> rx.Component:
    """One feature highlight card."""
    return rx.box(
        rx.vstack(
            rx.text(icon, font_size="2em"),
            rx.text(title, font_weight="700", font_size="1.05em", color="#0F6E56"),
            rx.text(description, color="#4a5568", font_size="0.9em", text_align="center"),
            align="center",
            spacing="2",
        ),
        padding="1.5em",
        border_radius="12px",
        background="white",
        border="1px solid #e2e8f0",
        flex="1",
        min_width="200px",
        text_align="center",
        box_shadow="0 1px 4px rgba(0,0,0,0.06)",
    )


def index() -> rx.Component:
    """Landing page at route /."""
    return page_layout(
        rx.vstack(
            # Hero section
            rx.vstack(
                rx.heading(
                    "TIMEASE",
                    size="9",
                    color="#0F6E56",
                    font_weight="800",
                    letter_spacing="-0.02em",
                ),
                rx.text(
                    "Générez vos emplois du temps en quelques minutes",
                    font_size="1.3em",
                    color="#4a5568",
                    text_align="center",
                    max_width="520px",
                ),
                rx.text(
                    "Conçu pour les écoles privées francophones. "
                    "Simple, rapide, et intelligent.",
                    font_size="0.95em",
                    color="#718096",
                    text_align="center",
                    max_width="420px",
                ),
                align="center",
                spacing="3",
                padding_bottom="1em",
            ),
            # Feature cards
            rx.hstack(
                _feature_card(
                    "🤖",
                    "Configuration par IA",
                    "Décrivez votre école en langage naturel. "
                    "L'IA configure automatiquement vos données.",
                ),
                _feature_card(
                    "👥",
                    "Collaboration enseignants",
                    "Partagez un lien sécurisé avec chaque enseignant "
                    "pour recueillir leurs disponibilités.",
                ),
                _feature_card(
                    "📄",
                    "Export multi-format",
                    "Exportez vos emplois du temps en PDF, Word, Excel "
                    "ou Markdown en un clic.",
                ),
                spacing="4",
                wrap="wrap",
                width="100%",
                justify="center",
            ),
            # CTA button
            rx.link(
                rx.button(
                    "Commencer gratuitement",
                    size="3",
                    background="#0F6E56",
                    color="white",
                    border_radius="8px",
                    padding="0.75em 2em",
                    font_weight="600",
                    cursor="pointer",
                    _hover={"background": "#0a5a46"},
                ),
                href="/configuration",
                text_decoration="none",
            ),
            align="center",
            spacing="6",
            padding_top="4em",
            width="100%",
        )
    )
