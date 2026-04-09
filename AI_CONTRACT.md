# TIMEASE — AI Contract (Sprint 1 State)

## Status: Dormant

All AI/chat endpoints and the `ai_chat.py` module have been removed in Sprint 1 ("The Great Deletion").

The `openai` dependency and `OPENAI_API_KEY` environment variable are retained for use in Sprint 3, which will introduce narrow AI features (e.g., conflict explanation, curriculum suggestions). No AI functionality is active in the current codebase.

## What Was Removed

- `timease/api/ai_chat.py` — OpenAI GPT-4o chat layer with tool calling and SSE streaming
- `POST /api/session/{sid}/chat` — non-streaming chat endpoint
- `POST /api/session/{sid}/chat/stream` — SSE streaming chat endpoint
- `POST /api/session/{sid}/apply_pending` — staging/commit layer for AI tool calls
- All frontend chat components (`ChatMessage`, `ChatInput`, `AgentActionPill`)
- All chat state in session management (`ai_history`, `pending_changes`)

## Sprint 3 Planned Scope

_(Not yet started. Details to be defined in Sprint 3 planning.)_

Candidate features:
- Conflict explanation: given an INFEASIBLE result, generate a plain-French explanation
- Curriculum suggestion: propose hours-per-week defaults based on school level
- Data validation hints: surface actionable messages for incomplete form steps

These will be narrow, single-turn, read-only AI calls — not a conversational setup wizard.
