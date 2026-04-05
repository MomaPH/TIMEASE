"""
AI chat handler for TIMEASE.

Uses the Anthropic Messages API with tool_use to extract school data
from natural-language conversations and return structured JSON.
"""

import anthropic
import os

TOOLS = [
    {
        "name": "save_school_info",
        "description": "Enregistre les informations de l'école",
        "input_schema": {
            "type": "object",
            "properties": {
                "name":              {"type": "string"},
                "city":              {"type": "string"},
                "academic_year":     {"type": "string"},
                "days":              {"type": "array", "items": {"type": "string"}},
                "sessions":          {"type": "array", "items": {"type": "object"}},
                "base_unit_minutes": {"type": "integer"},
            },
        },
    },
    {
        "name": "save_teachers",
        "description": "Enregistre des enseignants",
        "input_schema": {
            "type": "object",
            "properties": {
                "teachers": {"type": "array", "items": {"type": "object"}},
            },
        },
    },
    {
        "name": "save_classes",
        "description": "Enregistre des classes",
        "input_schema": {
            "type": "object",
            "properties": {
                "classes": {"type": "array", "items": {"type": "object"}},
            },
        },
    },
    {
        "name": "save_rooms",
        "description": "Enregistre des salles",
        "input_schema": {
            "type": "object",
            "properties": {
                "rooms": {"type": "array", "items": {"type": "object"}},
            },
        },
    },
    {
        "name": "save_subjects",
        "description": "Enregistre des matières",
        "input_schema": {
            "type": "object",
            "properties": {
                "subjects": {"type": "array", "items": {"type": "object"}},
            },
        },
    },
    {
        "name": "save_assignments",
        "description": "Enregistre des affectations enseignant-matière-classe",
        "input_schema": {
            "type": "object",
            "properties": {
                "assignments": {"type": "array", "items": {"type": "object"}},
            },
        },
    },
    {
        "name": "save_curriculum",
        "description": "Enregistre le programme",
        "input_schema": {
            "type": "object",
            "properties": {
                "curriculum": {"type": "array", "items": {"type": "object"}},
            },
        },
    },
    {
        "name": "save_constraints",
        "description": "Enregistre des contraintes",
        "input_schema": {
            "type": "object",
            "properties": {
                "constraints": {"type": "array", "items": {"type": "object"}},
            },
        },
    },
    {
        "name": "propose_quick_replies",
        "description": "Propose des réponses rapides cliquables",
        "input_schema": {
            "type": "object",
            "properties": {
                "replies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 4,
                },
            },
            "required": ["replies"],
        },
    },
]

SYSTEM_PROMPT = """\
Tu es l'assistant TIMEASE, un consultant expert en emplois du temps scolaires. \
Tu accompagnes les directeurs d'écoles privées en Afrique francophone.

PERSONNALITÉ: Chaleureux, professionnel, rassurant. Tu guides étape par étape, \
UNE question à la fois. Tu résumes ce que tu as compris avant de continuer. \
Tu proposes des solutions quand tu détectes un problème.

PÉRIMÈTRE: Tu ne traites QUE la configuration d'emplois du temps scolaires. \
Si on te demande autre chose: "Je suis spécialisé dans les emplois du temps. \
Comment puis-je vous aider avec votre école ?"

OUTILS: Utilise-les quand l'utilisateur fournit des données claires. \
Résume TOUJOURS avant d'enregistrer. \
Utilise propose_quick_replies après CHAQUE réponse (2-3 options).

FLUX: École → Horaires → Classes → Enseignants (ou fichier) → Affectations → \
Programme → Contraintes → Générer

FICHIERS: Résume clairement avec des puces. Ne montre JAMAIS de données brutes.

RÉCAPITULATIFS après chaque étape:
"✓ École configurée
✓ 14 enseignants
→ Prochaine étape : les salles"

IMPORTANT: "pour tout le monde" = toutes les classes connues. \
Ne devine jamais.\
"""


def process_chat(
    user_message: str,
    file_content: str | None,
    school_data: dict,
    teacher_assignments: list[dict],
    ai_history: list[dict],
) -> dict:
    """Send one user turn to Claude and return the structured response."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

    # Build context summary injected into the system prompt
    parts: list[str] = []
    if school_data.get("name"):
        parts.append(f"École: {school_data['name']}")
    if school_data.get("teachers"):
        parts.append(f"{len(school_data['teachers'])} enseignants")
    if school_data.get("classes"):
        parts.append(f"{len(school_data['classes'])} classes")
    if school_data.get("rooms"):
        parts.append(f"{len(school_data['rooms'])} salles")
    if teacher_assignments:
        parts.append(f"{len(teacher_assignments)} affectations")
    if school_data.get("curriculum"):
        parts.append(f"{len(school_data['curriculum'])} entrées programme")

    context = "Données actuelles: " + " | ".join(parts) if parts else "Aucune donnée."

    full_msg = user_message
    if file_content:
        full_msg = (
            f"Fichier envoyé par l'utilisateur:\n{file_content}\n\n"
            f"Message: {user_message}"
        )

    history = list(ai_history)
    history.append({"role": "user", "content": full_msg})

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        system=SYSTEM_PROMPT + "\n\n" + context,
        tools=TOOLS,
        messages=history,
    )

    text_parts: list[str] = []
    tool_calls: list[dict] = []
    quick_replies: list[str] = []

    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use":
            if block.name == "propose_quick_replies":
                quick_replies = block.input.get("replies", [])
            else:
                tool_calls.append({"name": block.name, "data": block.input})

    # Rebuild history with proper assistant + tool_result turns
    assistant_content = []
    for b in response.content:
        if b.type == "text":
            assistant_content.append({"type": "text", "text": b.text})
        elif b.type == "tool_use":
            assistant_content.append({
                "type": "tool_use",
                "id":   b.id,
                "name": b.name,
                "input": b.input,
            })
    history.append({"role": "assistant", "content": assistant_content})

    for block in response.content:
        if block.type == "tool_use":
            history.append({
                "role": "user",
                "content": [{
                    "type":        "tool_result",
                    "tool_use_id": block.id,
                    "content":     "OK",
                }],
            })

    return {
        "message":             "\n".join(text_parts),
        "tool_calls":          tool_calls,
        "quick_replies":       quick_replies,
        "needs_confirmation":  len(tool_calls) > 0,
        "updated_history":     history,
    }
