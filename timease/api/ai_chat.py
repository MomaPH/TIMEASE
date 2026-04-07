"""
AI chat handler for TIMEASE using OpenAI GPT models.

Extracts school data from natural-language conversations and returns structured JSON
using tool calling. Tool calls are auto-applied server-side — no confirmation needed
from the UI.
"""

from dotenv import load_dotenv
load_dotenv()

import dataclasses
import json as _json
import logging
import os
from typing import Generator

import openai

logger = logging.getLogger(__name__)

# ── OpenAI Configuration ───────────────────────────────────────────────────────
OPENAI_MODEL = "gpt-4o"

_openai_client: openai.OpenAI | None = None


def _get_openai_client() -> openai.OpenAI:
    """Return a module-level OpenAI client (lazy singleton)."""
    global _openai_client
    if _openai_client is None:
        _openai_client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    return _openai_client


_SAVE_TOOL_NAMES = {
    "save_school_info", "save_teachers", "save_classes", "save_rooms",
    "save_subjects", "save_curriculum", "save_constraints", "save_assignments",
}

STEP_NAMES: dict[int, str] = {
    0: "École", 1: "Classes", 2: "Enseignants", 3: "Salles",
    4: "Matières", 5: "Affectations", 6: "Programme", 7: "Contraintes",
}

TOOLS = [
    {
        "name": "save_school_info",
        "description": "Enregistre les informations de base de l'école. N'appelle cet outil QU'APRÈS que l'utilisateur ait confirmé (cliqué 'Confirmer' ou répondu 'oui'). Avant d'appeler, affiche toujours un résumé tableau et propose [✅ Confirmer] [✏️ Modifier].",
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
        "description": "Enregistre des enseignants. N'appelle cet outil QU'APRÈS confirmation de l'utilisateur. Avant d'appeler, affiche un tableau récapitulatif et propose [✅ Confirmer] [✏️ Modifier] [➕ Ajouter d'autres]. Le champ 'max_hours_per_week' est optionnel (défaut: 20h si non spécifié).",
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
                            "max_hours_per_week": {"type": "integer", "description": "Optionnel. Nombre max d'heures par semaine. Défaut: 20."},
                        },
                        "required": ["name", "subjects"],
                    },
                },
            },
            "required": ["teachers"],
        },
    },
    {
        "name": "save_classes",
        "description": "Enregistre des classes scolaires. N'appelle cet outil QU'APRÈS confirmation de l'utilisateur. Avant d'appeler, affiche un tableau récapitulatif et propose [✅ Confirmer] [✏️ Modifier].",
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
        "description": "Enregistre des salles. N'appelle cet outil QU'APRÈS confirmation de l'utilisateur. Avant d'appeler, affiche un tableau récapitulatif et propose [✅ Confirmer] [✏️ Modifier].",
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
        "description": "Enregistre des matières. N'appelle cet outil QU'APRÈS confirmation de l'utilisateur. Avant d'appeler, affiche un tableau récapitulatif et propose [✅ Confirmer] [✏️ Modifier].",
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
        "description": "Enregistre les affectations enseignant-matière-classe. N'appelle cet outil QU'APRÈS confirmation. Affiche d'abord un tableau et propose [✅ Confirmer] [✏️ Modifier]. IMPORTANT: utilise TOUJOURS 'school_class' (jamais 'class').",
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
        "description": "Enregistre le programme horaire PAR CLASSE (pas par niveau!). N'appelle cet outil QU'APRÈS confirmation. Affiche d'abord un tableau récapitulatif et propose [✅ Confirmer] [✏️ Modifier]. IMPORTANT: utilise 'school_class' avec le nom exact de la classe (ex: '6ème A', pas juste '6ème').",
        "input_schema": {
            "type": "object",
            "properties": {
                "curriculum": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "school_class":           {"type": "string", "description": "Nom exact de la classe (ex: '6ème A')"},
                            "subject":                {"type": "string"},
                            "total_minutes_per_week": {"type": "integer"},
                            "sessions_per_week":      {"type": "integer"},
                            "minutes_per_session":    {"type": "integer"},
                        },
                        "required": [
                            "school_class",
                            "subject",
                            "total_minutes_per_week",
                            "sessions_per_week",
                            "minutes_per_session",
                        ],
                    },
                },
            },
            "required": ["curriculum"],
        },
    },
    {
        "name": "save_constraints",
        "description": "Enregistre des contraintes de planification. N'appelle cet outil QU'APRÈS confirmation. Affiche d'abord un résumé et propose [✅ Confirmer] [✏️ Modifier].",
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
        "description": "Propose des boutons cliquables. Appelle cet outil dans CHAQUE message qui pose une question ou demande une décision. Toujours inclure au moins [✅ Confirmer] / [✏️ Modifier] pour les résumés, ou des choix spécifiques pour les questions.",
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


_STATIC_SYSTEM_PROMPT = """\
Tu es TIMEASE, un assistant IA expert en emplois du temps scolaires. \
Tu accompagnes les directeurs d'écoles privées en Afrique francophone dans la configuration \
complète de leur emploi du temps.

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
Exemple : {"teacher": "Alice", "subject": "Maths", "school_class": "6ème A"}

**RÈGLE 7bis — Programme (curriculum).**
Le programme se définit PAR CLASSE, pas par niveau! Chaque classe peut avoir des heures \
différentes même au même niveau.
Utilise TOUJOURS `school_class` avec le nom exact de la classe (ex: "6ème A", pas juste "6ème").
Si l'utilisateur mentionne un niveau, demande explicitement pour CHAQUE classe de ce niveau.
Exemple : {"school_class": "6ème A", "subject": "Maths", "total_minutes_per_week": 240, \
"sessions_per_week": 4, "minutes_per_session": 60}

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


def _build_system_prompt(
    school_data: dict,
    teacher_assignments: list[dict],
    conflict_reports: list[dict] | None = None,
    solve_issues: dict | None = None,
) -> list[dict]:
    """Build a context-aware system prompt as a list of content blocks.

    Returns system prompt content for the LLM. The prompt structure is designed
    to be cached — rules and constraint reference never change, enabling
    efficient reuse across calls.
    """

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

    dynamic = f"""{context}

{next_step}
Prochaine étape recommandée : index {next_step_idx}
"""

    # ── Partial solve context (injected after a partial result) ──────────────
    if solve_issues and solve_issues.get("total_unscheduled", 0) > 0:
        unscheduled = solve_issues.get("unscheduled", [])
        groups = solve_issues.get("groups", [])
        cause_steps = {
            "missing_teacher": 2, "room_unavailable": 3,
            "no_valid_slot": 7, "constraint_conflict": 7,
        }
        issues_lines = [
            "\n═══════════════════════════════════════════════════",
            "RÉSULTAT PARTIEL — DERNIÈRE GÉNÉRATION",
            "═══════════════════════════════════════════════════",
            f"{solve_issues.get('total_assigned', 0)} sessions planifiées, "
            f"{solve_issues.get('total_unscheduled', 0)} non planifiée(s).\n",
            "Sessions non planifiées :",
        ]
        for u in unscheduled[:10]:
            parts = [u.get("school_class", ""), u.get("subject", ""), u.get("teacher", "")]
            label = " · ".join(p for p in parts if p)
            reason = u.get("reason", "raison inconnue")
            issues_lines.append(f"  • {label} — {reason}")
        if groups:
            issues_lines.append("\nCauses identifiées :")
            for g in groups:
                step = cause_steps.get(g["cause"])
                step_label = f" → corriger étape {step} ({STEP_NAMES.get(step, '')})" if step else ""
                issues_lines.append(f"  • {g['label']} ({len(g['sessions'])} session(s)){step_label}")
        issues_lines += [
            "\nCOMPORTEMENT REQUIS :",
            "• Explique CHAQUE session non planifiée en français simple (pas de jargon technique).",
            "• Traduis 'No valid placement after domain filtering' par : "
            "'Aucun créneau valide trouvé — toutes les disponibilités ont été éliminées par les contraintes.'",
            "• Identifie la cause probable (enseignant, salle, contrainte horaire).",
            "• Propose des corrections concrètes avec `propose_options`.",
            "• Utilise `set_current_step` vers l'étape à corriger.",
        ]
        dynamic += "\n".join(issues_lines)

    # ── Conflict context (injected after a failed solve) ─────────────────────
    if conflict_reports:
        conflict_lines = [
            "\n═══════════════════════════════════════════════════",
            "RÉSULTAT DU DERNIER ESSAI DE GÉNÉRATION — ÉCHEC",
            "═══════════════════════════════════════════════════",
            "Le solveur n'a PAS trouvé de planning. Voici les conflits détectés :\n",
        ]
        for i, r in enumerate(conflict_reports, 1):
            sev = "🔴 BLOQUANT" if r.get("severity") in ("error", "impossible") else "🟡 AVERTISSEMENT"
            step = r.get("step_to_fix")
            step_label = f" → corriger à l'étape {step} ({STEP_NAMES.get(step, '')})" if step is not None else ""
            conflict_lines.append(f"{i}. {sev} — {r['description_fr']}{step_label}")
            for opt in r.get("fix_options", [])[:2]:
                conflict_lines.append(f"   Fix suggéré : {opt['fix_fr']}")
            conflict_lines.append("")
        conflict_lines += [
            "COMPORTEMENT REQUIS en réponse à ce contexte :",
            "• Explique clairement chaque conflit à l'utilisateur en français simple.",
            "• Pour chaque conflit, indique quelle étape corriger et comment.",
            "• Propose des options concrètes avec `propose_options` pour chaque fix suggéré.",
            "• Utilise `set_current_step` pour guider l'utilisateur vers l'étape à corriger.",
            "• Si plusieurs conflits, commence par le plus bloquant (🔴 en premier).",
        ]
        dynamic += "\n".join(conflict_lines)

    return [
        {
            "type": "text",
            "text": _STATIC_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": dynamic,
        },
    ]


MAX_HISTORY_PAIRS = 20  # keep first 2 + last 38 messages (≈ 20 user/assistant pairs)


def _is_tool_result_msg(msg: dict) -> bool:
    """Check if a message is a user turn containing tool_result blocks."""
    content = msg.get("content")
    if not isinstance(content, list):
        return False
    return any(
        isinstance(b, dict) and b.get("type") == "tool_result"
        for b in content
    )


def _has_tool_use(msg: dict) -> bool:
    """Check if an assistant message contains tool_use blocks."""
    content = msg.get("content")
    if not isinstance(content, list):
        return False
    return any(
        isinstance(b, dict) and b.get("type") == "tool_use"
        for b in content
    )


def stream_chat(
    user_message: str,
    file_content: str | None,
    school_data: dict,
    teacher_assignments: list[dict],
    ai_history: list[dict],
    conflict_reports: list[dict] | None = None,
    solve_issues: dict | None = None,
) -> Generator[dict, None, None]:
    """Stream OpenAI GPT response with full tool calling support.

    Yields:
        {"type": "delta",     "text": "..."}              — streamed text token
        {"type": "tool_call", "name": ..., "input": ..., "id": ...}  — completed tool call
        {"type": "end",       "updated_history": [...]}   — final event
    """
    client = _get_openai_client()
    system_prompt = _build_system_prompt(school_data, teacher_assignments, conflict_reports, solve_issues)

    full_msg = user_message
    if file_content:
        full_msg = (
            f"[Fichier envoyé par l'utilisateur — contenu extrait]\n\n{file_content}\n\n"
            f"---\nMessage accompagnant le fichier: {user_message or '(aucun message)'}"
        )

    history = list(ai_history)
    history.append({"role": "user", "content": full_msg})

    # Convert tools to OpenAI format
    tools_openai = [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            }
        }
        for t in TOOLS
    ]

    # Agentic loop
    MAX_TURNS = 4
    for _turn in range(MAX_TURNS):
        # Build messages for OpenAI API
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)

        has_tool_calls = False
        assistant_text = ""
        tool_calls_data = []

        try:
            stream = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                tools=tools_openai,
                stream=True,
                max_tokens=2048,
            )

            # Accumulate tool calls from stream
            tool_call_buffers: dict[int, dict] = {}

            for chunk in stream:
                delta = chunk.choices[0].delta

                # Handle text content
                if delta.content:
                    assistant_text += delta.content
                    yield {"type": "delta", "text": delta.content}

                # Handle tool calls
                if delta.tool_calls:
                    has_tool_calls = True
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in tool_call_buffers:
                            tool_call_buffers[idx] = {
                                "id": tc_delta.id or "",
                                "name": tc_delta.function.name if tc_delta.function else "",
                                "arguments": "",
                            }
                        if tc_delta.function and tc_delta.function.arguments:
                            tool_call_buffers[idx]["arguments"] += tc_delta.function.arguments

            # Parse completed tool calls
            for tc_buf in tool_call_buffers.values():
                try:
                    args = _json.loads(tc_buf["arguments"])
                    tool_calls_data.append({
                        "id": tc_buf["id"],
                        "name": tc_buf["name"],
                        "input": args,
                    })
                    yield {"type": "tool_call", "name": tc_buf["name"], "input": args, "id": tc_buf["id"]}
                except _json.JSONDecodeError:
                    logger.warning(f"Failed to parse tool arguments: {tc_buf['arguments']}")

        except Exception as e:
            logger.error(f"OpenAI stream error: {e}")
            yield {"type": "end", "updated_history": history}
            return

        # Build assistant message for history
        assistant_msg = {"role": "assistant", "content": assistant_text}
        if has_tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": _json.dumps(tc["input"]),
                    }
                }
                for tc in tool_calls_data
            ]

        history.append(assistant_msg)

        # If no tool calls, we're done
        if not has_tool_calls:
            break

        # Execute tools and build tool results
        tool_results = []
        for tc in tool_calls_data:
            tool_name = tc["name"]
            tool_id = tc["id"]

            # Determine result message
            # (actual execution happens in main.py via _dispatch_tool_calls)
            if tool_name == "trigger_solve":
                result_msg = "Génération de l'emploi du temps demandée."
            elif tool_name in _SAVE_TOOL_NAMES:
                result_msg = f"Données enregistrées: {tool_name}"
            else:
                result_msg = "Outil exécuté avec succès."

            tool_results.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "content": result_msg,
            })

        if tool_results:
            history.extend(tool_results)
        # Loop continues - AI will generate follow-up

    yield {"type": "end", "updated_history": history}



def process_chat(
    user_message: str,
    file_content: str | None,
    school_data: dict,
    teacher_assignments: list[dict],
    ai_history: list[dict],
    conflict_reports: list[dict] | None = None,
    solve_issues: dict | None = None,
) -> dict:
    """Send one user turn to OpenAI and return the structured response.

    Includes an agentic loop (up to MAX_TURNS) so the AI can follow up after
    tool calls with summaries and options.
    """
    client = _get_openai_client()
    system_prompt = _build_system_prompt(school_data, teacher_assignments, conflict_reports, solve_issues)

    full_msg = user_message
    if file_content:
        full_msg = (
            f"[Fichier envoyé par l'utilisateur — contenu extrait]\n\n{file_content}\n\n"
            f"---\nMessage accompagnant le fichier: {user_message or '(aucun message)'}"
        )

    history = list(ai_history)
    history.append({"role": "user", "content": full_msg})

    # Convert tools to OpenAI format
    tools_openai = [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            }
        }
        for t in TOOLS
    ]

    text_parts: list[str] = []
    tool_calls: list[dict] = []

    MAX_TURNS = 4
    for _turn in range(MAX_TURNS):
        # Build messages for OpenAI API
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=tools_openai,
            max_tokens=2048,
        )

        has_tool_calls = False
        assistant_msg = {"role": "assistant"}

        # Extract content and tool calls from response
        if response.choices[0].message.content:
            text = response.choices[0].message.content
            text_parts.append(text)
            assistant_msg["content"] = text
        else:
            assistant_msg["content"] = None

        if response.choices[0].message.tool_calls:
            has_tool_calls = True
            assistant_msg["tool_calls"] = []
            for tc in response.choices[0].message.tool_calls:
                tool_calls.append({
                    "name": tc.function.name,
                    "data": _json.loads(tc.function.arguments),
                    "id": tc.id,
                })
                assistant_msg["tool_calls"].append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                })

        history.append(assistant_msg)

        if not has_tool_calls:
            break

        # Append tool results so AI follows up
        tool_results = []
        for tc in response.choices[0].message.tool_calls or []:
            tool_name = tc.function.name
            if tool_name in _SAVE_TOOL_NAMES:
                result_msg = (
                    "Modifications envoyées pour validation par l'utilisateur.\n"
                    "Maintenant tu DOIS :\n"
                    "1. Afficher un tableau markdown récapitulatif de ce qui sera enregistré après confirmation.\n"
                    "2. Appeler `propose_options` avec [✅ Confirmer] [✏️ Modifier] et les prochaines actions.\n"
                    "NE dis PAS que les données sont déjà enregistrées — elles attendent validation."
                )
            else:
                result_msg = "OK."
            tool_results.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_msg,
            })

        if tool_results:
            history.extend(tool_results)

    return {
        "message":         "\n".join(text_parts),
        "tool_calls":      tool_calls,
        "updated_history": history,
    }
