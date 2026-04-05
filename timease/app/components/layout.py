"""Page layout wrapper — sidebar on left, content on right."""

import reflex as rx

from timease.app.components.sidebar import sidebar
from timease.app.style import *


def page_layout(*content: rx.Component) -> rx.Component:
    """Wrap page content with the fixed sidebar."""
    return rx.hstack(
        sidebar(),
        rx.box(
            *content,
            style=page_container,
            width="100%",
            flex="1",
        ),
        align="start",
        spacing="0",
        width="100%",
    )
