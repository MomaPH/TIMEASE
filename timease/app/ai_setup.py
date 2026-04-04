"""Conversational AI assistant for guided TIMEASE school data setup.

Uses the Anthropic Claude API to extract structured school data from
free-form French text messages.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import anthropic

if TYPE_CHECKING:
    from timease.engine.models import SchoolData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt (exact — do not modify without updating tests)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "Tu es l'assistant TIMEASE. Tu extrais des données structurées de messages en français. "
    'Réponds UNIQUEMENT en JSON valide sans backticks: {"message": "ta réponse", '
    '"extracted": null ou objet, "data_type": null ou '
    '"teachers"/"assignments"/"classes"/"rooms"/"curriculum"/"constraints"/"school_info", '
    '"needs_confirmation": true/false, "suggestions": ["suggestion1"]}\n\n'
    "Règles: "
    "'Samba fait maths en 6ème et 4ème' → extracted.assignments: "
    '[{"teacher":"Samba","subject":"Mathématiques","school_class":"6ème"},'
    '{"teacher":"Samba","subject":"Mathématiques","school_class":"4ème"}]. '
    "'pour tout le monde' = toutes les classes connues. "
    "'pas dispo mercredi' = unavailable mercredi:all. "
    "'3h30' = 210 minutes. "
    "Ne devine jamais, demande si ambigu."
)

_MODEL = "claude-sonnet-4-20250514"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SetupResponse:
    """Structured response from the AI setup assistant."""

    message_fr: str
    extracted_data: dict | None
    data_type: str | None
    needs_confirmation: bool
    suggestions: list[str]
    progress: dict


# ---------------------------------------------------------------------------
# Progress helper
# ---------------------------------------------------------------------------

def _compute_progress(current_data: SchoolData | dict | None) -> dict:
    """Return a dict summarising how much of the school data has been filled."""
    if current_data is None:
        return {}
    if hasattr(current_data, "school"):  # SchoolData instance
        return {
            "school_info": bool(
                getattr(current_data.school, "name", None)
            ),
            "teachers": len(getattr(current_data, "teachers", [])),
            "classes": len(getattr(current_data, "classes", [])),
            "rooms": len(getattr(current_data, "rooms", [])),
            "subjects": len(getattr(current_data, "subjects", [])),
            "curriculum": len(getattr(current_data, "curriculum", [])),
            "assignments": len(
                getattr(current_data, "teacher_assignments", [])
            ),
            "constraints": len(getattr(current_data, "constraints", [])),
        }
    if isinstance(current_data, dict):
        result: dict = {}
        for k, v in current_data.items():
            result[k] = len(v) if isinstance(v, list) else bool(v)
        return result
    return {}


# ---------------------------------------------------------------------------
# Assistant
# ---------------------------------------------------------------------------

class SetupAssistant:
    """Conversational assistant that extracts structured school data.

    Args:
        api_key: Anthropic API key. Read from ANTHROPIC_API_KEY env var
                 when not provided explicitly.
    """

    def __init__(self, api_key: str) -> None:
        self.client = anthropic.Anthropic(api_key=api_key)
        self.history: list[dict[str, str]] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_message(
        self,
        user_message: str,
        current_data: SchoolData | dict | None,
        file_content: str | None = None,
    ) -> SetupResponse:
        """Send a user message to Claude and return a structured response.

        Args:
            user_message:  Free-form text from the user (French).
            current_data:  Partial school data already collected, used to
                           compute the progress report.
            file_content:  Optional pre-parsed file content that will be
                           prepended to the user message.

        Returns:
            SetupResponse with the assistant's reply and any extracted data.
        """
        # Prepend file content when provided
        if file_content:
            user_text = f"Fichier envoyé:\n{file_content}\n\n{user_message}"
        else:
            user_text = user_message

        # Build message list (history + new message)
        messages = self.history + [{"role": "user", "content": user_text}]

        raw_json = self._call_api(messages)

        # Update history on success
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": raw_json})

        parsed = self._parse_response(raw_json)
        return SetupResponse(
            message_fr=parsed.get("message", ""),
            extracted_data=parsed.get("extracted"),
            data_type=parsed.get("data_type"),
            needs_confirmation=bool(parsed.get("needs_confirmation", False)),
            suggestions=parsed.get("suggestions", []),
            progress=_compute_progress(current_data),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _call_api(self, messages: list[dict[str, str]]) -> str:
        """Call the Anthropic API and return the raw response text."""
        response = self.client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return response.content[0].text

    def _parse_response(self, raw: str) -> dict[str, Any]:
        """Parse a JSON response string, retrying once on failure."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("JSON parse failed on first attempt, retrying.")

        # Retry: ask the model to output valid JSON
        retry_messages = self.history + [
            {
                "role": "user",
                "content": (
                    "Ta réponse précédente n'était pas du JSON valide. "
                    "Réponds UNIQUEMENT avec du JSON valide, sans texte autour."
                ),
            }
        ]
        try:
            raw2 = self._call_api(retry_messages)
            return json.loads(raw2)
        except (json.JSONDecodeError, Exception) as exc:
            logger.error("JSON parse failed on retry: %s", exc)
            return {
                "message": raw,
                "extracted": None,
                "data_type": None,
                "needs_confirmation": False,
                "suggestions": [],
            }
