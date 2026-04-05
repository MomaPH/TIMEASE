"""Main Reflex application entry point for TIMEASE."""

from dotenv import load_dotenv

load_dotenv()

import reflex as rx

from timease.app.state import AppState
from timease.app.pages.index import index
from timease.app.pages.workspace import workspace
from timease.app.pages.resultats import resultats
from timease.app.pages.collaboration import collaboration
from timease.app.pages.collab_teacher import collab_teacher
from timease.app.pages.configuration import configuration
from timease.app.state_collab import CollabTeacherState

app = rx.App(
    theme=rx.theme(
        accent_color="teal",
        appearance="light",  # default, user can toggle
        radius="medium",
    ),
)

app.add_page(index, route="/", title="TIMEASE — Accueil")
app.add_page(workspace, route="/workspace", title="TIMEASE — Espace de travail")
app.add_page(resultats, route="/resultats", title="TIMEASE — Résultats")
app.add_page(collaboration, route="/collaboration", title="TIMEASE — Collaboration")
app.add_page(configuration, route="/configuration", title="TIMEASE — Configuration")
app.add_page(
    collab_teacher,
    route="/collab/[token]",
    title="TIMEASE — Disponibilités",
    on_load=CollabTeacherState.on_load,
)
