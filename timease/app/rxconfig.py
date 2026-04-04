"""Reflex configuration for TIMEASE."""

import os
import sys

import reflex as rx

# Make the top-level `timease` package importable when running from this directory.
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

config = rx.Config(
    app_name="timease_app",
    # Override the default "app_name.app_name" module resolution so Reflex
    # imports our flat timease_app.py directly.
    app_module_import="timease_app",
    plugins=[rx.plugins.SitemapPlugin()],
)
