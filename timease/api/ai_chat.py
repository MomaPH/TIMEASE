"""
AI chat handler for TIMEASE.

Supports both Anthropic Claude and OpenAI GPT models with tool_use to extract
school data from natural-language conversations and return structured JSON.
Tool calls are auto-applied server-side — no confirmation needed from the UI.
"""

from dotenv import load_dotenv
load_dotenv()

import json as _json
import logging
import os
from typing import Generator, Literal

import anthropic
import openai

logger = logging.getLogger(__name__)

# ── Provider configuration ─────────────────────────────────────────────────────
AIProvider = Literal["anthropic", "openai"]
DEFAULT_PROVIDER: AIProvider = "openai"  # OpenAI is now the default

# Model mappings
MODELS = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o",
}

_anthropic_client: anthropic.Anthropic | None = None
_openai_client: openai.OpenAI | None = None


def _get_anthropic_client() -> anthropic.Anthropic:
    """Return a module-level Anthropic client (lazy singleton)."""
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    return _anthropic_client


def _get_openai_client() -> openai.OpenAI:
    """Return a module-level OpenAI client (lazy singleton)."""
    global _openai_client
    if _openai_client is None:
        _openai_client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    return _openai_client


def get_ai_provider() -> AIProvider:
    """Get current AI provider from environment or default."""
    provider = os.environ.get("AI_PROVIDER", DEFAULT_PROVIDER).lower()
    if provider in ("anthropic", "openai"):
        return provider  # type: ignore
    return DEFAULT_PROVIDER


def set_ai_provider(provider: AIProvider) -> None:
    """Set the AI provider (for runtime switching)."""
    os.environ["AI_PROVIDER"] = provider


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
        "description": "Enregistre des enseignants. N'appelle cet outil QU'APRÈS confirmation de l'utilisateur. Avant d'appeler, affiche un tableau récapitulatif et propose [✅ Confirmer] [✏️ Modifier] [➕ Ajouter d'autres].",
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
        "description": "Enregistre le programme horaire. N'appelle cet outil QU'APRÈS confirmation. Affiche d'abord un tableau récapitulatif et propose [✅ Confirmer] [✏️ Modifier].",
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
                            "sessions_per_week":      {"type": "integer"},
                            "minutes_per_session":    {"type": "integer"},
                        },
                        "required": [
                            "level",
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

    Returns a list suitable for Anthropic's ``system`` parameter.
    The first block (static rules) is marked with ``cache_control`` so that
    Anthropic can cache it across calls — the rules and constraint reference
    never change, saving ~90% of input cost on the static portion.
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


def _sanitize_history(history: list[dict]) -> list[dict]:
    """Remove orphaned tool_use messages that lack corresponding tool_result.

    The Anthropic API requires that every tool_use block is immediately
    followed by a user message containing the matching tool_result.
    If the frontend sends corrupted history (e.g., from localStorage),
    we strip those orphaned messages to prevent 400 errors.
    """
    if not history:
        return []

    sanitized: list[dict] = []
    i = 0
    while i < len(history):
        msg = history[i]

        # If this is an assistant message with tool_use, check for matching tool_result
        if msg.get("role") == "assistant" and _has_tool_use(msg):
            # Next message must be a user message with tool_result
            if i + 1 < len(history):
                next_msg = history[i + 1]
                if next_msg.get("role") == "user" and _is_tool_result_msg(next_msg):
                    # Valid pair — keep both
                    sanitized.append(msg)
                    sanitized.append(next_msg)
                    i += 2
                    continue
            # Orphaned tool_use — skip it
            logger.warning("Skipping orphaned tool_use message at index %d", i)
            i += 1
            continue

        # Regular message — keep it
        sanitized.append(msg)
        i += 1

    return sanitized


def _convert_history_for_openai(history: list[dict]) -> list[dict]:
    """Convert Anthropic-style history to OpenAI format.

    Anthropic uses: {"role": "user/assistant", "content": [{"type": "text", "text": "..."}]}
    OpenAI uses:    {"role": "user/assistant", "content": "..."}

    Also converts tool_use/tool_result to OpenAI's tool_calls/tool format.
    """
    converted = []
    i = 0
    while i < len(history):
        msg = history[i]
        role = msg.get("role", "user")
        content = msg.get("content", "")

        # Handle string content directly
        if isinstance(content, str):
            converted.append({"role": role, "content": content})
            i += 1
            continue

        # Handle list content (Anthropic style)
        if isinstance(content, list):
            # Check for tool_use blocks (assistant with tools)
            tool_uses = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]
            text_blocks = [b for b in content if isinstance(b, dict) and b.get("type") == "text"]

            if tool_uses and role == "assistant":
                # Convert to OpenAI tool_calls format
                text_content = " ".join(b.get("text", "") for b in text_blocks).strip() or None
                tool_calls = []
                for tu in tool_uses:
                    tool_calls.append({
                        "id": tu.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": tu.get("name", ""),
                            "arguments": _json.dumps(tu.get("input", {})),
                        }
                    })
                converted.append({
                    "role": "assistant",
                    "content": text_content,
                    "tool_calls": tool_calls,
                })

                # Look for corresponding tool_result in next message
                if i + 1 < len(history):
                    next_msg = history[i + 1]
                    if next_msg.get("role") == "user" and _is_tool_result_msg(next_msg):
                        next_content = next_msg.get("content", [])
                        for tr in next_content:
                            if isinstance(tr, dict) and tr.get("type") == "tool_result":
                                converted.append({
                                    "role": "tool",
                                    "tool_call_id": tr.get("tool_use_id", ""),
                                    "content": str(tr.get("content", "")),
                                })
                        i += 2
                        continue
                i += 1
                continue

            # Check for tool_result blocks (user with tool results) — already handled above
            if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
                # Skip — should have been handled with the preceding tool_use
                i += 1
                continue

            # Regular text blocks
            text = " ".join(
                b.get("text", "") if isinstance(b, dict) else str(b)
                for b in content
            ).strip()
            if text:
                converted.append({"role": role, "content": text})
            i += 1
            continue

        i += 1

    return converted


def _convert_tools_for_openai(tools: list[dict]) -> list[dict]:
    """Convert Anthropic tool definitions to OpenAI function format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            }
        }
        for t in tools
    ]


def _truncate_history(history: list[dict]) -> list[dict]:
    """Trim history to stay within context limits.

    Keeps the first 2 messages (initial greeting exchange) and the most
    recent messages, up to ``MAX_HISTORY_PAIRS * 2`` total messages.
    Never cuts between a tool_use assistant message and its tool_result
    user message — the tail always starts at a plain user message.
    """
    # First sanitize to remove any orphaned tool_use messages
    history = _sanitize_history(history)

    max_msgs = MAX_HISTORY_PAIRS * 2
    if len(history) <= max_msgs:
        return history
    head = history[:2]
    # Find a safe cut point: walk forward from the naive cut until we
    # hit a plain user message (not a tool_result). This ensures we
    # never orphan a tool_result from its preceding tool_use.
    cut = len(history) - (max_msgs - 2)
    while cut < len(history):
        msg = history[cut]
        if msg.get("role") == "user" and not _is_tool_result_msg(msg):
            break
        cut += 1
    tail = history[cut:]
    return head + tail


def stream_chat(
    user_message: str,
    file_content: str | None,
    school_data: dict,
    teacher_assignments: list[dict],
    ai_history: list[dict],
    conflict_reports: list[dict] | None = None,
    solve_issues: dict | None = None,
) -> Generator[dict, None, None]:
    """Stream AI response (Anthropic or OpenAI), yielding structured event dicts.

    Yields:
        {"type": "delta",     "text": "..."}              — streamed text token
        {"type": "tool_call", "name": ..., "input": ..., "id": ...}  — completed tool call
        {"type": "end",       "updated_history": [...]}   — final event
    """
    provider = get_ai_provider()

    # Route to provider-specific implementation
    if provider == "openai":
        yield from _stream_chat_openai(
            user_message, file_content, school_data, teacher_assignments,
            ai_history, conflict_reports, solve_issues
        )
    else:
        yield from _stream_chat_anthropic(
            user_message, file_content, school_data, teacher_assignments,
            ai_history, conflict_reports, solve_issues
        )


def _stream_chat_anthropic(
    user_message: str,
    file_content: str | None,
    school_data: dict,
    teacher_assignments: list[dict],
    ai_history: list[dict],
    conflict_reports: list[dict] | None = None,
    solve_issues: dict | None = None,
) -> Generator[dict, None, None]:
    """Stream Anthropic Claude response."""
    client = _get_anthropic_client()
    system_prompt = _build_system_prompt(school_data, teacher_assignments, conflict_reports, solve_issues)

    full_msg = user_message
    if file_content:
        full_msg = (
            f"[Fichier envoyé par l'utilisateur — contenu extrait]\n\n{file_content}\n\n"
            f"---\nMessage accompagnant le fichier: {user_message or '(aucun message)'}"
        )

    history = _truncate_history(list(ai_history))
    history.append({"role": "user", "content": full_msg})

    # ── Agentic loop: keep calling the API until AI returns text-only ──────────
    # Max 4 iterations to prevent infinite loops
    MAX_TURNS = 4
    for _turn in range(MAX_TURNS):
        tool_input_bufs: dict[int, dict] = {}
        assistant_content: list[dict] = []
        has_tool_calls = False

        try:
            with client.messages.stream(
                model="claude-sonnet-4-20250514",
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
                            has_tool_calls = True
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
            # Flush incomplete tool blocks (aborted stream)
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

        # Append this turn's assistant message to history
        history.append({"role": "assistant", "content": assistant_content})

        if not has_tool_calls:
            # Pure text response — conversation turn complete
            break

        # Append tool_result turns so AI sees the outcome and MUST follow up
        tool_result_content = []
        for b in assistant_content:
            if b.get("type") == "tool_use":
                # Rich instruction forces AI to generate summary + options next turn
                tool_name = b["name"]
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
                tool_result_content.append({
                    "type":        "tool_result",
                    "tool_use_id": b["id"],
                    "content":     result_msg,
                })

        if tool_result_content:
            history.append({"role": "user", "content": tool_result_content})
        # Loop → AI will generate the follow-up with summary + options

    yield {"type": "end", "updated_history": history}


def _stream_chat_openai(
    user_message: str,
    file_content: str | None,
    school_data: dict,
    teacher_assignments: list[dict],
    ai_history: list[dict],
    conflict_reports: list[dict] | None = None,
    solve_issues: dict | None = None,
) -> Generator[dict, None, None]:
    """Stream OpenAI GPT response.

    Note: OpenAI's tool calling is simplified here - we don't use tools
    for now to avoid complexity. Just use text responses.
    """
    client = _get_openai_client()
    system_prompt = _build_system_prompt(school_data, teacher_assignments, conflict_reports, solve_issues)

    full_msg = user_message
    if file_content:
        full_msg = (
            f"[Fichier envoyé par l'utilisateur — contenu extrait]\n\n{file_content}\n\n"
            f"---\nMessage accompagnant le fichier: {user_message or '(aucun message)'}"
        )

    # Convert Anthropic-style history to OpenAI format
    history = _truncate_history(list(ai_history))
    history_openai = _convert_history_for_openai(history)

    # Add user message
    history_openai.append({"role": "user", "content": full_msg})

    # Prepend system message
    messages = [{"role": "system", "content": system_prompt}] + history_openai

    try:
        stream = client.chat.completions.create(
            model=MODELS["openai"],
            messages=messages,
            stream=True,
            max_tokens=2048,
        )

        full_response = ""
        for chunk in stream:
            if chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                full_response += text
                yield {"type": "delta", "text": text}

        # Convert back to Anthropic format for history
        history.append({
            "role": "assistant",
            "content": [{"type": "text", "text": full_response}]
        })

        yield {"type": "end", "updated_history": history}

    except Exception as e:
        logger.error(f"OpenAI stream error: {e}")
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
    """Send one user turn to Claude and return the structured response.

    Now includes an agentic loop (up to MAX_TURNS) matching stream_chat,
    so the AI can follow up after tool calls with summaries and options.
    """
    client = _get_anthropic_client()
    system_prompt = _build_system_prompt(school_data, teacher_assignments, conflict_reports, solve_issues)

    full_msg = user_message
    if file_content:
        full_msg = (
            f"[Fichier envoyé par l'utilisateur — contenu extrait]\n\n{file_content}\n\n"
            f"---\nMessage accompagnant le fichier: {user_message or '(aucun message)'}"
        )

    history = _truncate_history(list(ai_history))
    history.append({"role": "user", "content": full_msg})

    text_parts: list[str] = []
    tool_calls: list[dict] = []

    MAX_TURNS = 4
    for _turn in range(MAX_TURNS):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            tools=TOOLS,
            messages=history,
        )

        has_tool_calls = False
        assistant_content: list[dict] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                has_tool_calls = True
                tool_calls.append({"name": block.name, "data": block.input, "id": block.id})
                assistant_content.append({
                    "type": "tool_use", "id": block.id,
                    "name": block.name, "input": block.input,
                })

        history.append({"role": "assistant", "content": assistant_content})

        if not has_tool_calls:
            break

        # Append tool_result turns so AI follows up
        tool_result_content = []
        for block in response.content:
            if block.type == "tool_use":
                if block.name in _SAVE_TOOL_NAMES:
                    result_msg = (
                        "Modifications envoyées pour validation par l'utilisateur.\n"
                        "Maintenant tu DOIS :\n"
                        "1. Afficher un tableau markdown récapitulatif de ce qui sera enregistré après confirmation.\n"
                        "2. Appeler `propose_options` avec [✅ Confirmer] [✏️ Modifier] et les prochaines actions.\n"
                        "NE dis PAS que les données sont déjà enregistrées — elles attendent validation."
                    )
                else:
                    result_msg = "OK."
                tool_result_content.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_msg,
                })

        if tool_result_content:
            history.append({"role": "user", "content": tool_result_content})

    return {
        "message":         "\n".join(text_parts),
        "tool_calls":      tool_calls,
        "updated_history": history,
    }
