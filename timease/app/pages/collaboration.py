"""Collaboration page — teacher availability links."""

import reflex as rx

from timease.app.components.layout import page_layout
from timease.app.state import AppState
from timease.app.style import (
    badge_neutral,
    badge_success,
    badge_warning,
    btn_primary,
    card,
    card_table_wrapper,
    hint_box,
)


# ─── Per-row component (used with rx.foreach) ──────────────────────────────────

def _teacher_row(row: dict) -> rx.Component:
    """One teacher row: name | link | copy | status badge."""
    status_badge = rx.cond(
        row["status"] == "completed",
        rx.badge("Complété",  style=badge_success),
        rx.cond(
            row["status"] == "pending",
            rx.badge("En attente", style=badge_warning),
            rx.badge("Non envoyé", style=badge_neutral),
        ),
    )

    return rx.hstack(
        rx.text(
            row["teacher"],
            font_weight="500",
            size="2",
            width="140px",
            flex_shrink="0",
            color="var(--gray-12)",
        ),
        rx.code(
            row["link"],
            size="1",
            color="var(--gray-10)",
            flex="1",
            overflow="hidden",
            text_overflow="ellipsis",
            white_space="nowrap",
        ),
        rx.button(
            rx.icon("copy", size=13),
            "Copier",
            variant="ghost",
            size="1",
            cursor="pointer",
            color="var(--teal-9)",
            flex_shrink="0",
            on_click=rx.set_clipboard(row["link"]),
        ),
        status_badge,
        align="center",
        gap="12px",
        padding="10px 14px",
        border_bottom="1px solid var(--gray-4)",
        width="100%",
        _hover={"background": "var(--gray-2)"},
    )


# ─── Table header ──────────────────────────────────────────────────────────────

def _table_header() -> rx.Component:
    return rx.hstack(
        rx.text("Enseignant",          size="1", color="var(--gray-9)", font_weight="500", width="140px", flex_shrink="0"),
        rx.text("Lien de disponibilité", size="1", color="var(--gray-9)", font_weight="500", flex="1"),
        rx.text("",                    size="1", width="80px"),
        rx.text("Statut",              size="1", color="var(--gray-9)", font_weight="500"),
        padding="8px 14px",
        border_bottom="1px solid var(--gray-5)",
        background="var(--gray-2)",
        border_radius="10px 10px 0 0",
        gap="12px",
        align="center",
        width="100%",
    )


# ─── Page ─────────────────────────────────────────────────────────────────────

def collaboration() -> rx.Component:
    """Collaboration page at route /collaboration."""
    return page_layout(
        rx.vstack(
            # Header
            rx.vstack(
                rx.heading("Collaboration", size="5", font_weight="600"),
                rx.text(
                    "Partagez des liens avec les enseignants pour recueillir leurs disponibilités.",
                    color="var(--gray-9)",
                    size="2",
                ),
                spacing="1",
                align="start",
                width="100%",
            ),

            # Action bar
            rx.hstack(
                rx.button(
                    rx.icon("link", size=14),
                    "Générer les liens",
                    on_click=AppState.generate_links,
                    color_scheme="teal",
                    size="2",
                    cursor="pointer",
                ),
                rx.button(
                    rx.icon("send", size=14),
                    "Envoyer par email",
                    variant="outline",
                    size="2",
                    cursor="pointer",
                ),
                gap="8px",
            ),

            # Links card
            rx.cond(
                AppState.collab_links.length() == 0,
                # Empty state
                rx.box(
                    rx.vstack(
                        rx.icon("users", size=36, color="var(--gray-7)"),
                        rx.text(
                            "Aucun lien généré",
                            font_weight="500",
                            size="3",
                            color="var(--gray-11)",
                        ),
                        rx.text(
                            "Cliquez sur « Générer les liens » pour créer un lien unique par enseignant.",
                            size="2",
                            color="var(--gray-9)",
                            text_align="center",
                        ),
                        align="center",
                        spacing="2",
                    ),
                    style=hint_box,
                ),
                # Populated table
                rx.box(
                    _table_header(),
                    rx.foreach(AppState.collab_links, _teacher_row),
                    style=card_table_wrapper,
                ),
            ),

            # Legend
            rx.hstack(
                rx.hstack(
                    rx.box(width="10px", height="10px", background="var(--green-9)", border_radius="50%"),
                    rx.text("Complété",  size="1", color="var(--gray-9)"),
                    gap="4px", align="center",
                ),
                rx.hstack(
                    rx.box(width="10px", height="10px", background="var(--amber-9)", border_radius="50%"),
                    rx.text("En attente", size="1", color="var(--gray-9)"),
                    gap="4px", align="center",
                ),
                rx.hstack(
                    rx.box(width="10px", height="10px", background="var(--gray-7)", border_radius="50%"),
                    rx.text("Non envoyé", size="1", color="var(--gray-9)"),
                    gap="4px", align="center",
                ),
                gap="16px",
            ),

            spacing="4",
            width="100%",
        )
    )
