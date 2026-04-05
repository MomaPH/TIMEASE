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
                    "maxItems": 6,
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
    {
        "name": "set_current_step",
        "description": (
            "Avance le panneau de formulaire de l'interface vers une étape spécifique. "
            "Appelle cet outil IMMÉDIATEMENT après avoir enregistré des données pour une étape, "
            "pour synchroniser l'interface avec la conversation. "
            "Étapes: 0=École, 1=Classes, 2=Enseignants, 3=Salles, 4=Matières, "
            "5=Affectations, 6=Programme, 7=Contraintes, 8=Résumé."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "step": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 8,
                    "description": "Index de l'étape à afficher (0-8)",
                },
            },
            "required": ["step"],
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

    # ── Step index mapping ───────────────────────────────────────────────────
    step_map = {
        "école": 0, "classes": 1, "enseignants": 2, "salles": 3,
        "matières": 4, "affectations": 5, "programme": 6,
    }
    next_step_idx = next(
        (step_map[k] for k, v in checklist.items() if not v),
        8,  # summary if all done
    )

    prompt = f"""Tu es TIMEASE, un assistant IA expert en emplois du temps scolaires. \
Tu accompagnes les directeurs d'écoles privées en Afrique francophone dans la configuration \
complète de leur emploi du temps.

{context}

{next_step}

═══════════════════════════════════════════════════
RÈGLES DE COMPORTEMENT — OBLIGATOIRES
═══════════════════════════════════════════════════

**RÈGLE 1 — UNE seule question à la fois.**
Ne pose jamais deux questions dans le même message. Choisis la question la plus importante \
pour cette étape. Attends toujours la réponse avant d'en poser une autre.

**RÈGLE 2 — Toujours proposer des options interactives.**
À CHAQUE fois que tu poses une question avec des choix possibles (oui/non, sélection de \
valeur, confirmation), appelle `propose_options` avec 2 à 5 boutons cliquables.
Exemples où tu DOIS proposer des options :
• Confirmation : [✅ Oui, c'est correct] [✏️ Modifier] [➕ Ajouter d'autres]
• Jours de cours : [Lundi à Vendredi] [Lundi à Samedi] [Personnaliser]
• Sessions : [Matin + Après-midi] [Matin seulement] [Personnaliser]
• Unité de base : [30 minutes] [45 minutes] [60 minutes] [Autre]
• Avancement : [➡️ Étape suivante] [🔄 Modifier cette étape] [⏭️ Passer]
• Validation finale : [🚀 Générer l'emploi du temps] [📝 Revoir les données]

**RÈGLE 3 — Valider avant d'enregistrer.**
Avant d'appeler un outil de sauvegarde, affiche un résumé de ce que tu vas enregistrer \
et demande confirmation avec `propose_options` : [✅ Confirmer] [✏️ Modifier].
EXCEPTION : si l'utilisateur a déjà confirmé explicitement ou cliqué sur "Confirmer", \
enregistre directement sans redemander.

**RÈGLE 4 — Proactif après chaque étape.**
Après confirmation et enregistrement :
a) Affiche "✓ [données] enregistrées."
b) Appelle `set_current_step` avec l'index de la prochaine étape incomplète.
c) Pose immédiatement la première question de la prochaine étape avec `propose_options`.
Ne laisse JAMAIS l'utilisateur sans une question ou action suivante claire.

Mapping étapes: 0=École, 1=Classes, 2=Enseignants, 3=Salles, 4=Matières, \
5=Affectations, 6=Programme, 7=Contraintes, 8=Résumé
Prochaine étape recommandée : index {next_step_idx}

**RÈGLE 5 — Format de résumé par étape.**
Avant de valider une étape, présente les données sous forme de tableau markdown :
```
| Champ | Valeur |
|-------|--------|
| Nom   | ...    |
```
Puis propose : [✅ Confirmer] [✏️ Modifier une entrée]

**RÈGLE 6 — Upsert transparent.**
Envoyer la même entité (même nom) met à jour, pas de doublon. Si l'utilisateur corrige \
une info, renvoie l'entrée complète corrigée. Dis-le clairement : "J'ai mis à jour X."

**RÈGLE 7 — Affectations.**
Utilise TOUJOURS `school_class` (jamais `class`).
Exemple : {{"teacher": "Alice", "subject": "Maths", "school_class": "6ème A"}}

**RÈGLE 8 — Fichiers importés.**
Quand un fichier est envoyé :
1. Extrais TOUTES les données (école, classes, enseignants, salles, matières, \
affectations, programme, contraintes).
2. Enregistre tout en une seule passe avec les outils.
3. Appelle `set_current_step` vers la première étape incomplète.
4. Affiche un tableau récapitulatif de ce qui a été trouvé vs ce qui manque.
5. Pose immédiatement la première question pour compléter ce qui manque, \
avec `propose_options`.

**RÈGLE 9 — Génération.**
Quand l'utilisateur demande de générer ET que toutes les cases sont ✅ :
appelle `trigger_generation` ET `set_current_step` avec step=8.
Si des cases sont ❌, explique précisément ce qui manque et propose des options pour \
le compléter maintenant.

**RÈGLE 10 — Style.**
• Tableaux markdown pour les résumés et données.
• Gras pour les éléments importants, listes pour les étapes.
• Emojis modérés pour signaler le statut (✅ ❌ ✓ ⚙️ 📋).
• Jamais de JSON brut visible. Jamais de blocs de code pour des données simples.
• Réponses concises — une idée par message.

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


from typing import Generator


def stream_chat(
    user_message: str,
    file_content: str | None,
    school_data: dict,
    teacher_assignments: list[dict],
    ai_history: list[dict],
) -> Generator[dict, None, None]:
    """Stream Claude's response, yielding structured event dicts.

    Yields:
        {"type": "delta",     "text": "..."}              — streamed text token
        {"type": "tool_call", "name": ..., "input": ..., "id": ...}  — completed tool call
        {"type": "end",       "updated_history": [...]}   — final event
    """
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

    # Buffer for assembling tool_use input JSON
    tool_input_bufs: dict[int, dict] = {}  # index → {"id","name","json_buf"}
    assistant_content: list[dict] = []

    import json as _json

    try:
        with client.messages.stream(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=system_prompt,
            tools=TOOLS,
            messages=history,
        ) as stream:
            for event in stream:
                etype = event.type

                if etype == "content_block_start":
                    block = event.content_block
                    if block.type == "text":
                        assistant_content.append({"type": "text", "text": ""})
                    elif block.type == "tool_use":
                        tool_input_bufs[event.index] = {
                            "id":       block.id,
                            "name":     block.name,
                            "json_buf": "",
                        }
                        assistant_content.append({
                            "type":  "tool_use",
                            "id":    block.id,
                            "name":  block.name,
                            "input": {},
                        })

                elif etype == "content_block_delta":
                    delta = event.delta
                    if delta.type == "text_delta":
                        for b in reversed(assistant_content):
                            if b["type"] == "text":
                                b["text"] += delta.text
                                break
                        yield {"type": "delta", "text": delta.text}

                    elif delta.type == "input_json_delta":
                        if event.index in tool_input_bufs:
                            tool_input_bufs[event.index]["json_buf"] += delta.partial_json

                elif etype == "content_block_stop":
                    if event.index in tool_input_bufs:
                        buf = tool_input_bufs.pop(event.index)
                        try:
                            parsed = _json.loads(buf["json_buf"]) if buf["json_buf"] else {}
                        except Exception:
                            parsed = {}
                        for b in assistant_content:
                            if b.get("type") == "tool_use" and b.get("id") == buf["id"]:
                                b["input"] = parsed
                                break
                        yield {"type": "tool_call", "name": buf["name"], "input": parsed, "id": buf["id"]}
    finally:
        # Flush any tool blocks that never received content_block_stop (aborted streams)
        for buf in tool_input_bufs.values():
            try:
                parsed = _json.loads(buf["json_buf"]) if buf["json_buf"] else {}
            except Exception:
                parsed = {}
            for b in assistant_content:
                if b.get("type") == "tool_use" and b.get("id") == buf["id"]:
                    b["input"] = parsed
                    break
            yield {"type": "tool_call", "name": buf["name"], "input": parsed, "id": buf["id"]}

    # Build updated history with tool_result turns
    history.append({"role": "assistant", "content": assistant_content})
    for b in assistant_content:
        if b.get("type") == "tool_use":
            history.append({
                "role": "user",
                "content": [{
                    "type":        "tool_result",
                    "tool_use_id": b["id"],
                    "content":     "OK — données enregistrées.",
                }],
            })

    yield {"type": "end", "updated_history": history}


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
