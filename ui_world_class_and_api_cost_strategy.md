# TIMEASE — Réconciliation stricte: objectifs produit, architecture réelle, UX “world-class”, coût Anthropic

Ce document remplace la version précédente avec une règle stricte: **aucune recommandation sans ancrage dans le code ou les docs du repo**.

## 1) Faits vérifiés dans le projet (source-of-truth)

## Produit / objectifs

- Cible: écoles privées francophones Afrique, UX en français (`CLAUDE.md`).
- Phase 2 active: human-in-the-loop, coût API maîtrisé, UX premium, robustesse stream (`CLAUDE.md`, `task.md`, `CONTEXT.md`).
- Règle explicite: éviter appels Anthropic pour erreurs mathématiques structurelles (`CLAUDE.md`).

## Architecture

- Frontend Next.js 16 + React 19 (`frontend/`).
- Backend FastAPI (`timease/api/main.py`).
- Chat SSE: endpoint `POST /api/session/{sid}/chat/stream` + événements `delta`, `tool_start`, `done` (`main.py`, `frontend/lib/api.ts`).
- Solve synchrone HTTP `POST /api/session/{sid}/solve` (`main.py`).
- Sessions backend en mémoire (`sessions: dict[...]`) (`main.py`).

## Chat IA / coût

- Modèle réellement appelé en code: `claude-3-5-haiku-latest` (`timease/api/ai_chat.py`, `stream_chat()` et `process_chat()`).
- Prompt caching déjà activé sur bloc système statique via `cache_control: {"type": "ephemeral"}` (`_build_system_prompt()`).
- Troncature historique existante (`_truncate_history`, `MAX_HISTORY_PAIRS=20`) (`ai_chat.py`).

## UX actuelle vérifiée

- Gatekeeping côté UI déjà branché: `validateHourBarriers()`, panel erreurs, bouton “Demander à l’IA” (`StepPanel.tsx`, `validation.ts`, `ValidationErrorPanel.tsx`).
- SSE streaming visuel déjà présent: curseur, “thinking”, pill outil (`workspace/page.tsx`, `ChatMessage.tsx`, `AgentActionPill`).
- Staging de modifications IA déjà présent (`pending_changes`, apply/reject) (`main.py`, `workspace/page.tsx`).
- **Stop stream non implémenté**: `onStop={undefined}` (`workspace/page.tsx`).

## Solve / conflits

- `solve` renvoie `INFEASIBLE` + `conflict_reports` structurés sans lancer automatiquement un appel IA backend (`main.py`).
- MAIS le frontend déclenche `autoTrigger(...)` après échec/partiel (`workspace/page.tsx`) — important pour coût/contrôle.

## 2) Conflits entre ambitions “world-class” et architecture actuelle

## A. Contrôle utilisateur

- Objectif: stop immédiat de génération/réponse.
- Réalité: pas d’AbortController branché dans `sendChatStream`; UI a un bouton stop prévu mais non câblé.
- Impact: non-conforme à “User control and freedom”.

## B. Coût API et détachement LLM

- Objectif: ne pas consommer tokens sur erreurs déterministes.
- Réalité: gatekeeping présent (bien), mais autoTrigger après solve partiel/échec relance automatiquement l’IA.
- Impact: risque de coût non nécessaire en boucle d’essais.

## C. Fiabilité de perception

- Objectif: états explicites de bout en bout.
- Réalité: bons signaux en chat, mais pas d’état “interrompu” officiel ni reprise explicite.

## D. Alignement doc vs code

- `KNOW.md` mentionne parfois Sonnet, mais code exécute Haiku.
- Risque: décisions produit/coût basées sur une hypothèse erronée.

## 3) Plan “world-class” compatible avec l’architecture existante (sans guess)

## P0 — Corrections bloquantes (priorité absolue)

1. **Implémenter Stop SSE réellement**
- Front: ajouter `AbortController` dans `sendChatStream()` (`frontend/lib/api.ts`) et exposer une méthode d’annulation.
- Front: brancher `onStop` dans `workspace/page.tsx` + état local “stream annulé”.
- UX: afficher message français explicite (“Génération interrompue.”).
- Aucun changement moteur solver requis.

2. **Supprimer les appels IA automatiques post-solve (ou les rendre opt-in)**
- Remplacer `autoTrigger(...)` automatique après `PARTIAL` / `INFEASIBLE` par:
  - affichage deterministic des `conflict_reports`/`unscheduled_groups` déjà fournis;
  - bouton explicite “Demander à l’IA”.
- Conforme à la règle Phase 2 de détachement LLM.

3. **Corriger le check de barrière horaire**
- `validateHourBarriers` utilise seuil `requestedHours > schoolHours * 0.95` tout en disant “dépasse”.
- Ajuster le wording ou la règle pour cohérence stricte.

## P1 — Renforcement premium sans casser l’architecture

4. **État système unifié**
- Introduire un mini-state machine frontend: `idle | streaming | solving | interrupted | error`.
- Mapper visuellement ces états dans l’en-tête chat et le panel résumé.

5. **Fiabiliser l’édition de tableaux chat**
- `ChatMessage.tsx` mélange clés `(rowIdx-colIdx)` et clés basées sur `position.line/column`.
- Unifier le schéma de clé pour garantir que l’édition se reflète lors de confirmation.

6. **A11y clavier réelle (WCAG 2.2 focus visible)**
- Vérifier tous boutons interactifs (chips, apply/reject, stop, edit/regenerate, upload) avec focus visible constant.
- Ajouter `aria-live` sur zones de statut streaming.

## P2 — Coût API: descendre sans sacrifier fiabilité

7. **Exploiter au maximum ce qui existe déjà**
- Garder Haiku par défaut (déjà en place).
- Conserver prompt cache statique (déjà en place).
- Conserver troncature historique (déjà en place).

8. **Ajouter métriques coût/tokens factuelles**
- Logger côté backend, par requête chat:
  - taille historique envoyée;
  - nombre de messages avant/après troncature;
  - model utilisé.
- Ajouter, si dispo SDK/réponse, usage tokens exacts par appel.
- Sans métrique, impossible de piloter “.001”.

9. **Token budget guardrail**
- Avant appel Anthropic: budget max par tour (ex: mode “micro” vs “normal”).
- Si dépassement: résumer davantage `ai_history` côté serveur avant envoi.

10. **Rendre l’IA réellement optionnelle sur chemins déterministes**
- Solve/validation/errors courants d’abord en UI/native reports.
- IA uniquement sur demande utilisateur.

## 4) Coût cible “$0.001” — borne réaliste, sans promesse non vérifiable

Avec les tarifs Anthropic observés (ex. Haiku 4.5 pricing public), $0.001/tour nécessite des tours **très courts**.
Le repo actuel n’expose pas encore des métriques tokens complètes; on ne peut donc pas affirmer un coût réel actuel sans instrumentation.

Conclusion stricte:
- **Possible** pour micro-interactions courtes.
- **Non garanti** pour tours longs (fichier importé, diagnostics complexes) sans budget/token guardrails.

## 5) Matrice “objectif projet -> action technique sûre”

- “Ne pas ping Anthropic pour erreurs math” (`CLAUDE.md`)
  - Action: supprimer autoTrigger post-solve, garder bouton opt-in IA.

- “Ne jamais casser SSE streams” (`CLAUDE.md`)
  - Action: abort contrôlé côté frontend uniquement; pas de changement protocole SSE backend.

- “UX premium concierge” (`task.md` phase 2.3)
  - Action: état visible unifié + actions robustes + a11y focus + table edits fiables.

- “Qualité/fiabilité”
  - Action: tests ciblés frontend + backend sur stop stream, conflict display, ask-AI opt-in path.

## 6) Changements à NE PAS faire (hors scope archi actuel)

- Ne pas déplacer engine vers dépendances web.
- Ne pas introduire Celery dans ce lot (Phase 2.6 dédiée).
- Ne pas promettre réduction coût absolue sans métriques tokens instrumentées.

## 7) Références internes utilisées

- `CLAUDE.md`
- `KNOW.md`
- `CONTEXT.md`
- `task.md`
- `timease/api/main.py`
- `timease/api/ai_chat.py`
- `frontend/lib/api.ts`
- `frontend/app/workspace/page.tsx`
- `frontend/components/StepPanel.tsx`
- `frontend/lib/validation.ts`
- `frontend/components/ValidationErrorPanel.tsx`
- `frontend/components/ChatMessage.tsx`

## 8) Références externes (méthodologie UX/coût)

- Anthropic pricing: https://www.anthropic.com/pricing
- Anthropic prompt caching: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- Anthropic token counting: https://docs.anthropic.com/en/docs/build-with-claude/token-counting
- Anthropic batch processing: https://docs.anthropic.com/en/docs/build-with-claude/batch-processing
- NN/g response times: https://www.nngroup.com/articles/response-times-3-important-limits/
- NN/g heuristics: https://www.nngroup.com/articles/ten-usability-heuristics/
- WCAG 2.2 focus visible: https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html
