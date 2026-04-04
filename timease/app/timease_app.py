"""Main Reflex application entry point for TIMEASE."""

import reflex as rx

from timease.app.pages.index import index
from timease.app.pages.configuration import configuration
from timease.app.pages.programme import programme
from timease.app.pages.contraintes import contraintes
from timease.app.pages.generer import generer
from timease.app.pages.resultats import resultats
from timease.app.pages.collaboration import collaboration

app = rx.App(
    theme=rx.theme(accent_color="teal"),
)

app.add_page(index, route="/", title="TIMEASE — Accueil")
app.add_page(configuration, route="/configuration", title="TIMEASE — Configuration")
app.add_page(programme, route="/programme", title="TIMEASE — Programme")
app.add_page(contraintes, route="/contraintes", title="TIMEASE — Contraintes")
app.add_page(generer, route="/generer", title="TIMEASE — Générer")
app.add_page(resultats, route="/resultats", title="TIMEASE — Résultats")
app.add_page(collaboration, route="/collaboration", title="TIMEASE — Collaboration")
