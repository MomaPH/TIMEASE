"""Page layout wrapper that includes the sidebar."""

import reflex as rx

from timease.app.components.sidebar import sidebar


def page_layout(*content: rx.Component) -> rx.Component:
    """Wrap page content with the fixed sidebar on the left."""
    return rx.hstack(
        sidebar(),
        rx.box(
            *content,
            margin_left="240px",
            padding="2em",
            min_height="100vh",
            width="100%",
            background="#f8fafc",
            flex="1",
        ),
        align="start",
        spacing="0",
        width="100%",
    )
