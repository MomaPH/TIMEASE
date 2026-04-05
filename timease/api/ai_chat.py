"""
AI chat handler for TIMEASE.

Uses the Anthropic Messages API with tool_use to extract school data
from natural-language conversations and return structured JSON.
Tool calls are auto-applied server-side — no confirmation needed from the UI.
"""

from dotenv import load_dotenv
load_dotenv()

import anthropic
import os

TOOLS = [
    {
        "name": "save_school_info",
        "description": "Enregistre les informations de base de l'école (nom, ville, année, jours, sessions, unité de base). Appelle cet outil dès que tu as suffisamment d'infos — tu peux compléter plus tard.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name":              {"type": "string"},
                "city":              {"type": "string"},
                "academic_year":     {"type": "string"},
                "days":              {"type": "array", "items": {"type": "string"}},
                "sessions":          {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name":       {"type": "string"},
                            "start_time": {"type": "string"},
                            "end_time":   {"type": "string"},
                        },
                    },
                },
                "base_unit_minutes": {"type": "integer"},
            },
        },
    },
    {
        "name": "save_teachers",
        "description": "Enregistre des enseignants avec leurs matières et heures max.",
        "input_schema": {
            "type": "object",
            "properties": {
                "teachers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name":               {"type": "string"},
                            "subjects":           {"type": "array", "items": {"type": "string"}},
                            "max_hours_per_week": {"type": "integer"},
                        },
                    },
                },
            },
            "required": ["teachers"],
        },
    },
    {
        "name": "save_classes",
        "description": "Enregistre des classes scolaires.",
        "input_schema": {
            "type": "object",
            "properties": {
                "classes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name":          {"type": "string"},
                            "level":         {"type": "string"},
                            "student_count": {"type": "integer"},
                        },
                    },
                },
            },
            "required": ["classes"],
        },
    },
    {
        "name": "save_rooms",
        "description": "Enregistre des salles de classe.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rooms": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name":     {"type": "string"},
                            "capacity": {"type": "integer"},
                            "types":    {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
            },
            "required": ["rooms"],
        },
    },
    {
        "name": "save_subjects",
        "description": "Enregistre des matières enseignées.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subjects": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name":               {"type": "string"},
                            "short_name":         {"type": "string"},
                            "color":              {"type": "string"},
                            "required_room_type": {"type": "string"},
                            "needs_room":         {"type": "boolean"},
                        },
                    },
                },
            },
            "required": ["subjects"],
        },
    },
    {
        "name": "save_assignments",
        "description": "Enregistre les affectations enseignant-matière-classe. IMPORTANT: utilise TOUJOURS 'school_class' (pas 'class') pour le nom de la classe.",
        "input_schema": {
            "type": "object",
            "properties": {
                "assignments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "teacher":      {"type": "string"},
                            "subject":      {"type": "string"},
                            "school_class": {"type": "string"},
                        },
                        "required": ["teacher", "subject", "school_class"],
                    },
                },
            },
            "required": ["assignments"],
        },
    },
    {
        "name": "save_curriculum",
        "description": "Enregistre le programme (heures par semaine par niveau et matière).",
        "input_schema": {
            "type": "object",
            "properties": {
                "curriculum": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "level":                  {"type": "string"},
                            "subject":                {"type": "string"},
                            "total_minutes_per_week": {"type": "integer"},
                            "mode":                   {"type": "string", "enum": ["auto", "manual"]},
                        },
                        "required": ["level", "subject", "total_minutes_per_week"],
                    },
                },
            },
            "required": ["curriculum"],
        },
    },
    {
        "name": "save_constraints",
        "description": "Enregistre des contraintes de planification.",
        "input_schema": {
            "type": "object",
            "properties": {
                "constraints": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id":             {"type": "string"},
                            "type":           {"type": "string", "enum": ["hard", "soft"]},
                            "category":       {"type": "string"},
                            "description_fr": {"type": "string"},
                            "priority":       {"type": "integer"},
                            "parameters":     {"type": "object"},
                        },
                        "required": ["type", "category", "description_fr"],
                    },
                },
            },
            "required": ["constraints"],
        },
    },
    {
        "name": "propose_options",
        "description": "Propose des choix cliquables à l'utilisateur quand tu as besoin d'une décision précise. Utilise cet outil APRÈS avoir posé ta question dans ton message texte. Maximum 5 options.",
        "input_schema": {
            "type": "object",
            "properties": {
                "options": {
                    "type": "array",
                    "maxItems": 5,
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string", "description": "Texte affiché sur le bouton"},
                            "value": {"type": "string", "description": "Valeur envoyée quand l'utilisateur clique"},
                        },
                        "required": ["label", "value"],
                    },
                },
            },
            "required": ["options"],
        },
    },
    {
        "name": "trigger_generation",
        "description": "Déclenche automatiquement la génération de l'emploi du temps. Appelle cet outil UNIQUEMENT quand l'utilisateur demande explicitement de générer et que toutes les données obligatoires sont présentes (école, classes, enseignants, salles, matières, affectations, programme).",
        "input_schema": {
            "type": "object",
            "properties": {
                "ready": {"type": "boolean", "description": "Toujours true quand tu appelles cet outil"},
            },
            "required": ["ready"],
        },
    },
]


def _build_system_prompt(
    school_data: dict,
    teacher_assignments: list[dict],
) -> str:
    """Build a context-aware system prompt reflecting current session state."""

    # ── What's filled ────────────────────────────────────────────────────────
    sd = school_data
    classes    = sd.get("classes",    [])
    teachers   = sd.get("teachers",   [])
    rooms      = sd.get("rooms",      [])
    subjects   = sd.get("subjects",   [])
    curriculum = sd.get("curriculum", [])
    constraints= sd.get("constraints",[])
    days       = sd.get("days",       [])
    sessions   = sd.get("sessions",   [])
    ta         = teacher_assignments

    # ── Checklist ────────────────────────────────────────────────────────────
    checklist = {
        "école":         bool(sd.get("name") and days and sessions),
        "classes":       len(classes)    > 0,
        "enseignants":   len(teachers)   > 0,
        "salles":        len(rooms)      > 0,
        "matières":      len(subjects)   > 0,
        "affectations":  len(ta)         > 0,
        "programme":     len(curriculum) > 0,
    }
    ready = all(checklist.values())

    # ── Context block injected into the prompt ────────────────────────────────
    check_lines = "\n".join(
        f"  {'✅' if v else '❌'} {k}"
        for k, v in checklist.items()
    )
    context = f"""
ÉTAT ACTUEL DE LA SESSION:
{check_lines}
{'✅ PRÊT À GÉNÉRER' if ready else '⏳ Configuration incomplète'}

Données détaillées:
- École: {sd.get('name', 'non définie')} | Ville: {sd.get('city', '?')} | Année: {sd.get('academic_year', '?')}
- Jours: {', '.join(days) if days else 'non définis'} | Sessions: {len(sessions)} | Unité: {sd.get('base_unit_minutes', '?')} min
- Classes ({len(classes)}): {', '.join(c.get('name','?') for c in classes[:8]) if classes else 'aucune'}
- Enseignants ({len(teachers)}): {', '.join(t.get('name','?') for t in teachers[:8]) if teachers else 'aucun'}
- Salles ({len(rooms)}): {', '.join(r.get('name','?') for r in rooms[:6]) if rooms else 'aucune'}
- Matières ({len(subjects)}): {', '.join(s.get('name','?') for s in subjects[:8]) if subjects else 'aucune'}
- Affectations: {len(ta)} enregistrées
- Programme: {len(curriculum)} entrées
- Contraintes: {len(constraints)} enregistrées
"""

    # ── Next recommended step ─────────────────────────────────────────────────
    if not checklist["école"]:
        next_step = "**Prochaine étape → École** : demande le nom, la ville, l'année scolaire, les jours de cours, les sessions (matin/après-midi avec horaires), l'unité de base."
    elif not checklist["classes"]:
        next_step = "**Prochaine étape → Classes** : demande les noms des classes, niveaux (6ème, 5ème…) et effectifs."
    elif not checklist["enseignants"]:
        next_step = "**Prochaine étape → Enseignants** : demande les noms, matières enseignées et heures max/semaine."
    elif not checklist["salles"]:
        next_step = "**Prochaine étape → Salles** : demande les noms, capacités et types (standard, laboratoire…)."
    elif not checklist["matières"]:
        next_step = "**Prochaine étape → Matières** : demande les noms, abréviations, et si certaines nécessitent une salle spécialisée."
    elif not checklist["affectations"]:
        next_step = "**Prochaine étape → Affectations** : pour chaque matière de chaque classe, assigne un enseignant. Utilise les données déjà enregistrées."
    elif not checklist["programme"]:
        next_step = "**Prochaine étape → Programme** : demande les heures par semaine pour chaque matière à chaque niveau."
    else:
        next_step = "**Configuration complète !** Propose à l'utilisateur d'ajouter des contraintes (optionnel) ou de générer directement."

    prompt = f"""Tu es TIMEASE, un assistant IA expert en emplois du temps scolaires. \
Tu accompagnes les directeurs d'écoles privées en Afrique francophone.

Tu peux répondre à n'importe quelle question — tu es un assistant généraliste — \
mais tu guides activement la configuration de l'emploi du temps étape par étape.

{context}

{next_step}

═══════════════════════════════════════════════════
COMPORTEMENT OBLIGATOIRE
═══════════════════════════════════════════════════

1. **UNE question à la fois.** Ne pose jamais deux questions dans le même message. \
Pose la question la plus importante, attends la réponse.

2. **Proactif.** Après chaque enregistrement, résume ce qui vient d'être sauvegardé \
en une ligne (ex: "✓ 3 enseignants enregistrés"), puis guide vers la prochaine étape.

3. **Valide avant d'enregistrer.** Si une info clé manque (ex: `school_class` vide \
dans une affectation), pose une question de clarification. Ne devine jamais un champ obligatoire.

4. **Affectations** : utilise TOUJOURS `school_class` (jamais `class`). \
Exemple correct: {{"teacher": "Alice", "subject": "Maths", "school_class": "6ème"}}.

5. **Choix interactifs.** Quand tu proposes des options (oui/non, choix de valeur), \
utilise l'outil `propose_options` pour créer des boutons cliquables. \
Exemples: confirmer des heures, choisir entre matin/après-midi, valider un résumé.

6. **Génération.** Quand l'utilisateur demande de générer ET que toutes les cases \
sont ✅, appelle `trigger_generation`. Sinon, explique ce qui manque.

7. **Fichiers.** Quand l'utilisateur envoie un fichier, extrais toutes les données \
possibles en une seule fois (école, classes, enseignants, matières, affectations, \
programme, contraintes), enregistre-les toutes, puis affiche un résumé clair \
avec ce qui a été trouvé et ce qui manque encore.

8. **Style markdown.** Utilise des tableaux pour les résumés, du gras pour les \
éléments importants, des listes pour les étapes. Jamais de JSON brut visible.

═══════════════════════════════════════════════════
CONTRAINTES SUPPORTÉES PAR LE SOLVEUR
═══════════════════════════════════════════════════

Dures (type: "hard"):
• start_time — heure min de début (param: hour "HH:MM")
• day_off — jour/session bloqué (params: day, session "all"|nom_session)
• subject_on_days — matière limitée à certains jours (params: subject, days [])
• subject_not_on_days — matière exclue de jours (params: subject, days [])
• subject_not_last_slot — pas en dernier créneau (params: subject)
• max_consecutive — max heures consécutives (params: max_hours)
• min_break_between — pause min entre sessions (params: minutes)
• fixed_assignment — session fixée (params: class, subject, day, start_time)
• teacher_day_off — congé enseignant (params: teacher, preferred_day_off)

Souples (type: "soft", priority 1–10):
• teacher_time_preference — préférence horaire (params: teacher, preferred_session)
• balanced_daily_load — charge équilibrée par jour
• subject_spread — même matière pas 2x/jour
• heavy_subjects_morning — matières difficiles le matin (params: subjects [])
• teacher_compact_schedule — minimiser les trous
• same_room_for_class — classe concentrée dans une salle
• no_subject_back_to_back — éviter consécutif même matière
• light_last_day — peu de cours le dernier jour
• teacher_day_off — préférence congé (params: teacher, preferred_day_off)
"""
    return prompt


def process_chat(
    user_message: str,
    file_content: str | None,
    school_data: dict,
    teacher_assignments: list[dict],
    ai_history: list[dict],
) -> dict:
    """Send one user turn to Claude and return the structured response."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

    system_prompt = _build_system_prompt(school_data, teacher_assignments)

    full_msg = user_message
    if file_content:
        full_msg = (
            f"[Fichier envoyé par l'utilisateur — contenu extrait]\n\n{file_content}\n\n"
            f"---\nMessage accompagnant le fichier: {user_message or '(aucun message)'}"
        )

    history = list(ai_history)
    history.append({"role": "user", "content": full_msg})

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        system=system_prompt,
        tools=TOOLS,
        messages=history,
    )

    text_parts: list[str] = []
    tool_calls: list[dict] = []

    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use":
            tool_calls.append({"name": block.name, "data": block.input, "id": block.id})

    # Rebuild history with proper assistant + tool_result turns
    assistant_content = []
    for b in response.content:
        if b.type == "text":
            assistant_content.append({"type": "text", "text": b.text})
        elif b.type == "tool_use":
            assistant_content.append({
                "type":  "tool_use",
                "id":    b.id,
                "name":  b.name,
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
                    "content":     "OK — données enregistrées.",
                }],
            })

    return {
        "message":         "\n".join(text_parts),
        "tool_calls":      tool_calls,
        "updated_history": history,
    }
