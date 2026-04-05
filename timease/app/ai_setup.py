"""Conversational AI assistant for guided TIMEASE school data setup.

Uses the Anthropic Claude API with native tool use so responses are natural
French text while structured data is extracted through tool calls.
"""
from __future__ import annotations

import logging
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    {
        "name": "save_school_info",
        "description": "Enregistre les informations de l'école (nom, ville, année scolaire, horaires)",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "city": {"type": "string"},
                "academic_year": {"type": "string"},
                "days": {"type": "array", "items": {"type": "string"}},
                "sessions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "start_time": {"type": "string"},
                            "end_time": {"type": "string"},
                        },
                    },
                },
                "base_unit_minutes": {"type": "integer"},
            },
        },
    },
    {
        "name": "save_teachers",
        "description": "Enregistre un ou plusieurs enseignants",
        "input_schema": {
            "type": "object",
            "properties": {
                "teachers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "subjects": {"type": "array", "items": {"type": "string"}},
                            "max_hours_per_week": {"type": "integer"},
                            "unavailable_slots": {"type": "array", "items": {"type": "object"}},
                        },
                    },
                }
            },
        },
    },
    {
        "name": "save_classes",
        "description": "Enregistre une ou plusieurs classes",
        "input_schema": {
            "type": "object",
            "properties": {
                "classes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "level": {"type": "string"},
                            "student_count": {"type": "integer"},
                        },
                    },
                }
            },
        },
    },
    {
        "name": "save_rooms",
        "description": "Enregistre une ou plusieurs salles",
        "input_schema": {
            "type": "object",
            "properties": {
                "rooms": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "capacity": {"type": "integer"},
                            "types": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                }
            },
        },
    },
    {
        "name": "save_assignments",
        "description": "Enregistre les affectations enseignant-matière-classe",
        "input_schema": {
            "type": "object",
            "properties": {
                "assignments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "teacher": {"type": "string"},
                            "subject": {"type": "string"},
                            "school_class": {"type": "string"},
                        },
                    },
                }
            },
        },
    },
    {
        "name": "save_curriculum",
        "description": "Enregistre le programme (matières, heures par niveau)",
        "input_schema": {
            "type": "object",
            "properties": {
                "curriculum": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "level": {"type": "string"},
                            "subject": {"type": "string"},
                            "total_minutes_per_week": {"type": "integer"},
                            "mode": {"type": "string"},
                            "sessions_per_week": {"type": "integer"},
                            "minutes_per_session": {"type": "integer"},
                            "min_session_minutes": {"type": "integer"},
                            "max_session_minutes": {"type": "integer"},
                        },
                    },
                }
            },
        },
    },
    {
        "name": "save_constraints",
        "description": "Enregistre une contrainte horaire",
        "input_schema": {
            "type": "object",
            "properties": {
                "constraints": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "type": {"type": "string"},
                            "category": {"type": "string"},
                            "priority": {"type": "integer"},
                            "parameters": {"type": "object"},
                            "description_fr": {"type": "string"},
                        },
                    },
                }
            },
        },
    },
    {
        "name": "save_subjects",
        "description": "Enregistre les matières enseignées",
        "input_schema": {
            "type": "object",
            "properties": {
                "subjects": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "short_name": {"type": "string"},
                            "color": {"type": "string"},
                            "required_room_type": {"type": "string"},
                            "needs_room": {"type": "boolean"},
                        },
                    },
                }
            },
        },
    },
    {
        "name": "propose_quick_replies",
        "description": "Propose des réponses rapides cliquables à l'utilisateur",
        "input_schema": {
            "type": "object",
            "properties": {
                "replies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 4,
                }
            },
            "required": ["replies"],
        },
    },
]

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Tu es l'assistant TIMEASE, un consultant expert en emplois du temps scolaires. Tu accompagnes les directeurs d'écoles privées en Afrique francophone.

PERSONNALITÉ:
- Chaleureux, professionnel, rassurant
- Tu guides étape par étape, UNE question à la fois
- Tu résumes ce que tu as compris avant de continuer
- Tu proposes des solutions quand tu détectes un problème
- Tu parles comme un collègue expérimenté

PÉRIMÈTRE:
Tu ne traites QUE la configuration d'emplois du temps scolaires. Si on te demande autre chose, réponds gentiment: "Je suis spécialisé dans les emplois du temps. Comment puis-je vous aider avec votre école ?"

OUTILS:
Tu as des outils pour enregistrer les données. Utilise-les UNIQUEMENT quand l'utilisateur a clairement fourni des données ET que tu les as résumées dans ton message. N'appelle jamais un outil sans avoir d'abord montré à l'utilisateur ce que tu vas enregistrer dans le champ "message".

Utilise TOUJOURS propose_quick_replies après chaque réponse pour offrir 2-3 options cliquables. Exemples:
- Après une question oui/non : ["Oui", "Non, je corrige"]
- Après un résumé de données : ["C'est correct", "Je corrige", "Passer à la suite"]
- Quand tout est prêt : ["Générer l'emploi du temps", "Vérifier d'abord", "Ajouter des contraintes"]
- Quand tu proposes un choix de méthode : ["Envoyer un fichier Excel", "Dicter étape par étape"]

Ne propose JAMAIS plus de 4 options. 2-3 est idéal.

FLUX:
1. "Bienvenue ! Comment s'appelle votre école ?"
2. Après le nom → demande ville et année scolaire
3. Horaires de cours (heure début, pause déjeuner, heure fin)
4. Classes et effectifs
5. Enseignants (proposer import fichier ou dictée)
6. Affectations enseignant-matière-classe
7. Programme (heures par matière et par niveau)
8. Contraintes horaires
9. "Tout est prêt, on génère !"

FICHIERS:
Quand l'utilisateur envoie un fichier, résume clairement ce que tu as trouvé avec des puces, puis propose de confirmer avec les outils.

RÉCAPITULATIFS:
Après chaque étape confirmée, fais un mini-bilan concis avant de passer à la suivante:
"Parfait, on avance bien :
✓ École configurée
✓ 14 enseignants
✓ 4 classes
→ Prochaine étape : les salles. Combien en avez-vous ?"

DÉTECTION DE PROBLÈMES:
Ne bloque pas. Signale et propose une solution:
"J'ai remarqué que [problème]. C'est faisable mais [conséquence]. Voulez-vous continuer ou ajuster ?"
"""

_MODEL = "claude-sonnet-4-20250514"


# ---------------------------------------------------------------------------
# Assistant
# ---------------------------------------------------------------------------

class SetupAssistant:
    """Conversational assistant that extracts structured school data via tool use.

    Args:
        api_key: Anthropic API key.
    """

    def __init__(self, api_key: str) -> None:
        self.client = anthropic.Anthropic(api_key=api_key)
        self.history: list[dict[str, Any]] = []

    def process_message(
        self,
        user_message: str,
        current_data: dict,
        teacher_assignments: list,
        file_content: str | None = None,
    ) -> dict[str, Any]:
        """Send a user message and return a structured result dict.

        Returns:
            {
                "message": str — natural French text for the user,
                "tool_calls": list[{"name": str, "data": dict}],
                "quick_replies": list[str],
                "needs_confirmation": bool,
            }
        """
        # Build a context summary injected into the system prompt
        context = self._build_context(current_data, teacher_assignments)

        # Compose the user message text
        full_message = user_message
        if file_content:
            full_message = (
                f"L'utilisateur a envoyé un fichier. Contenu:\n{file_content}\n\n"
                f"Message: {user_message}"
            )

        self.history.append({"role": "user", "content": full_message})

        response = self.client.messages.create(
            model=_MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT + "\n\n" + context,
            tools=TOOLS,
            messages=self.history,
        )

        # Parse content blocks
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        quick_replies: list[str] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                if block.name == "propose_quick_replies":
                    quick_replies = block.input.get("replies", [])
                else:
                    tool_calls.append({"name": block.name, "data": block.input})

        message_text = "\n".join(text_parts).strip()

        # Store assistant turn in history
        self.history.append({"role": "assistant", "content": response.content})

        # Add batched tool results so the next turn is valid
        tool_result_blocks = [
            {"type": "tool_result", "tool_use_id": block.id, "content": "OK"}
            for block in response.content
            if block.type == "tool_use"
        ]
        if tool_result_blocks:
            self.history.append({"role": "user", "content": tool_result_blocks})

        return {
            "message": message_text,
            "tool_calls": tool_calls,
            "quick_replies": quick_replies,
            "needs_confirmation": len(tool_calls) > 0,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_context(current_data: dict, teacher_assignments: list) -> str:
        """Build a concise context line appended to the system prompt."""
        parts: list[str] = []
        if current_data.get("name"):
            parts.append(f"École: {current_data['name']}")
        teachers = current_data.get("teachers", [])
        if teachers:
            parts.append(f"{len(teachers)} enseignants")
        classes = current_data.get("classes", [])
        if classes:
            names = ", ".join(
                c["name"] if isinstance(c, dict) else str(c) for c in classes
            )
            parts.append(f"{len(classes)} classes: {names}")
        rooms = current_data.get("rooms", [])
        if rooms:
            parts.append(f"{len(rooms)} salles")
        if teacher_assignments:
            parts.append(f"{len(teacher_assignments)} affectations")
        curriculum = current_data.get("curriculum", [])
        if curriculum:
            parts.append(f"{len(curriculum)} entrées de programme")
        if not parts:
            return "État actuel: Aucune donnée configurée."
        return "État actuel: " + " | ".join(parts)


# ---------------------------------------------------------------------------
# Human-readable summary of tool calls (used by the confirm card in the UI)
# ---------------------------------------------------------------------------

def describe_tool_calls(tool_calls: list[dict[str, Any]]) -> str:
    """Return a concise French summary of the data about to be saved."""
    lines: list[str] = []
    for tc in tool_calls:
        name = tc["name"]
        data = tc["data"]
        if name == "save_school_info":
            parts = [data.get("name", "—")]
            if data.get("city"):
                parts.append(data["city"])
            if data.get("academic_year"):
                parts.append(data["academic_year"])
            lines.append("École : " + ", ".join(parts))
        elif name == "save_teachers":
            teachers = data.get("teachers", [])
            preview = ", ".join(t.get("name", "?") for t in teachers[:4])
            suffix = f" +{len(teachers) - 4} autres" if len(teachers) > 4 else ""
            lines.append(f"{len(teachers)} enseignant(s) : {preview}{suffix}")
        elif name == "save_classes":
            classes = data.get("classes", [])
            preview = ", ".join(c.get("name", "?") for c in classes)
            lines.append(f"{len(classes)} classe(s) : {preview}")
        elif name == "save_rooms":
            rooms = data.get("rooms", [])
            preview = ", ".join(r.get("name", "?") for r in rooms)
            lines.append(f"{len(rooms)} salle(s) : {preview}")
        elif name == "save_assignments":
            n = len(data.get("assignments", []))
            lines.append(f"{n} affectation(s) enseignant-matière-classe")
        elif name == "save_curriculum":
            entries = data.get("curriculum", [])
            levels = sorted({e.get("level", "?") for e in entries})
            lines.append(f"{len(entries)} entrée(s) de programme — niveaux : {', '.join(levels)}")
        elif name == "save_subjects":
            subjects = data.get("subjects", [])
            preview = ", ".join(s.get("name", "?") for s in subjects[:5])
            suffix = f" +{len(subjects) - 5} autres" if len(subjects) > 5 else ""
            lines.append(f"{len(subjects)} matière(s) : {preview}{suffix}")
        elif name == "save_constraints":
            n = len(data.get("constraints", []))
            lines.append(f"{n} contrainte(s) horaire(s)")
    return "\n".join(lines) if lines else "Données à enregistrer"
