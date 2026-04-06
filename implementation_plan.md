# Phase 2 Detailed Implementation Prompts (For Coding AI)

This document contains a sequence of highly structured, strict prompts designed to go directly into an agentic coding AI.

## Global Quality Control Rule
> [!CRITICAL]
> **Clean & Polish After Every Step**: After completing each task, ALWAYS perform a cleanup pass:
> - Run linters and fix warnings (`npm run lint`, `mypy`, etc.)
> - Run tests and fix any breakages (`pytest`, `npm test`)
> - Remove unused imports, variables, and dead code
> - Update TypeScript types to be strict and accurate
> - Verify the build succeeds without warnings
> - Update documentation (docstrings, comments) for modified code
> 
> **Do NOT proceed to the next task while errors, warnings, or technical debt remain.**
> This prevents error accumulation and maintains high code quality throughout the project.

## User Review Required
> [!IMPORTANT]
> The prompts below match the final Master Analysis document. Review the tasks and copy the **entire prompt block** to paste into your coding AI sequentially.

---

## 1. System Prompt (Context Initialization)
**Why execute this?** To align the AI on tech stack boundaries, strict formatting rules, and the new Phase 2 architecture.

```markdown
**Context:**
You are an elite Staff Engineer tasked with upgrading `TIMEASE`, a B2B SaaS timetable generator for private African schools. Operations are critical and must be flawless.

**The Tech Stack:**
- **Backend:** Python 3.12+, FastAPI (REST + SSE), Google OR-Tools (CP-SAT), SQLAlchemy (Postgres/RLS), Celery + Redis.
- **Frontend:** Next.js 16 (App Router), React 19, Tailwind CSS v4.

**Strict Global Rules:**
1. Read `CLAUDE.md` and `KNOW.md` thoroughly before any code changes.
2. Architecture Boundary: The engine (`timease/engine`) must NEVER import from FastAPI (`timease/api`).
3. Localization: ALL user-facing UI text, toast messages, and docstring user summaries must be in French. Internal code docstrings must be in English.
4. Types: Enforce strict Python typing (`typing` module) across every new function.
5. Testing: Create localized `pytest` tests for every new feature you touch.
6. **Clean & Polish**: After completing each subtask, run linters, fix tests, remove dead code, and verify the build succeeds before moving forward.
7. Acknowledge these instructions and await exactly the first task before executing any code.
```

---

## 2. Phase 2.1: Code Abstraction Removal (Deprecating Auto Mode)
**Why execute this?** Teachers and classes are pre-negotiated by human administration. The algorithm shouldn't try to assign them. 

```markdown
**Task:** Strip out the hypothetical "Auto Mode" and the entire Python Greedy pre-assignment phase.

**Execution Steps:**
1. Update `timease/engine/models.py`. Remove the `mode` field from `CurriculumEntry`. Assume 100% strictly manual assignments. 
2. In `timease/engine/solver.py`, completely delete the Python "Greedy pre-assignment" loop that autonomously assigns teachers to subjects. 
3. Remove unused helper logic scoring teachers based on capacity.
4. Update `tests/test_solver.py` to remove any tests expecting autonomous teacher matching.
5. **Cleanup Pass**: Run `pytest tests/` and `mypy timease/` to verify no breakages. Remove any unused imports.

**Constraints:** 
Ensure the CP-SAT engine handles strict `CurriculumEntry.teacher` definitions directly.
```

---

## 3. Phase 2.2: Advanced Solver Optimization (Time limits)
**Why execute this?** To force CP-SAT to output the most beautiful schedule possible without freezing the server for 10 hours proving optimality.

```markdown
**Task:** Push Soft Constraints (S1-S5) into the CP-SAT objective function with strict 30-second logic bounds.

**Execution Steps:**
1. In `timease/engine/solver.py`, integrate existing S1-S5 post-solve metrics directly into the CP-SAT model using `model.Maximize()`.
2. Add a hard timeout to the solver parameters: `solver.parameters.max_time_in_seconds = 30`.
3. Update return logic so that if the solver reaches `MAX_TIME` but found *any* feasible schedule during the 30 seconds, it returns that schedule natively.
4. **Cleanup Pass**: Run `pytest tests/test_solver.py` to ensure timeout doesn't break tests. Verify no infinite loops or hangs.

**Constraints:** Do NOT let the solver run open-ended. 
```

---

## 4. Phase 2.3: The Premium AI Experience (Agentic Concierge)
**Why execute this?** Visualizing tool work and allowing inline editing changes the AI from a sluggish text generator to an enterprise concierge.

```markdown
**Task:** Upgrade the Next.js chat interface (`frontend/app/workspace` and `ChatMessage.tsx`) to behave like a premium SaaS assistant. 

**Execution Steps:**
1. **Transparent Tool UX:** Build an `<AgentActionPill />` component utilizing Tailwind v4 micro-animations. When the backend streams a tool start, render a pulsing pill stating what is happening in French.
2. **Inline Editable Recap Tables:** In the `ChatMessage.tsx` markdown renderer, if the AI outputs an array of data awaiting confirmation (`[✅ Confirmer]`), make the rendered table cells `<input>` fields or `contentEditable` so the user can natively fix AI math hallucinations without typing a prompt. 
3. **Streaming Polish:** Implement a custom blinking text cursor block `▍` that attaches to the end of the SSE stream.
4. **Cleanup Pass**: Run `npm run build` to verify TypeScript errors are resolved. Test the UI manually to ensure smooth interactions.
```

---

## 5. Phase 2.4: UI Gatekeeping & Detaching the LLM
**Why execute this?** Prevent UI loops from burning Anthropic tokens on trivial mathematical failures.

```markdown
**Task:** Build strict pre-solver UI validation barriers and detach the `ConflictAnalyzer` from automatic LLM consumption.

**Execution Steps:**
1. In the Next.js `StepPanel.tsx`, add reactive logic that sums total requested teacher hours vs available school hours. If requested > available, immediately disable the Generate button.
2. Modify `POST /api/session/{sid}/solve`. When `INFEASIBLE`, return the `ConflictAnalyzer` French report natively via HTTP 400. Do NOT invoke the AI chat stream.
3. Add a *"Demander à l'IA de m'aider"* button below the React error UI that triggers the LLM only if pressed explicitly by the user, sending pruned context.
4. **Cleanup Pass**: Test solve endpoint with invalid data. Verify error UI displays correctly. Run `npm run build` and backend tests.
```

---

## 6. Phase 2.5: Compiling Diagnosis Bottlenecks (mypyc)
**Why execute this?** To exponentially speed up the pure Python logic Loops natively.

```markdown
**Task:** Implement C-compilation using `mypyc`.

**Execution Steps:**
1. Add `mypy` to the root `pyproject.toml`.
2. Ensure `timease/engine/conflicts.py` has 100% strict Python type mappings.
3. Create a `build_ext.py` script at the project root importing `mypyc.build.mypycify` targeting `conflicts.py`.
4. Modify `start.sh` to compile before booting the API.
5. **Cleanup Pass**: Run `mypy --strict timease/engine/conflicts.py` to verify no type errors. Benchmark performance improvement. Verify compiled module works correctly.
```

---

## 7. Phase 2.6: Asynchronous Queue & Security (Hosting/Collab)
**Why execute this?** Stop network timeouts on massive schedules, enforce RLS silos, and stage admin approvals.

```markdown
**Task:** Decouple CP-SAT using Celery, force Postgres RLS, and secure the Teacher Collab Portal.

**Execution Steps (Celery/DB):**
1. Add `celery` and `redis` to `pyproject.toml`. Wrap the `solver_run` invocation in a `@celery.task`.
2. Refactor `POST /solve` to dispatch the task to Celery and return a `task_id`. Let Next.js poll this via a progress ring.
3. Inject raw SQL into the SQLAlchemy setup: `ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;`. Enforce `SET LOCAL app.current_tenant = :id`.
4. **Cleanup Pass**: Test Celery worker starts correctly. Verify RLS policies work with test queries. Run full test suite.

**Execution Steps (Collab Portal Staging):**
1. When a teacher submits availability via `/api/collab/{token}/availability`, do NOT immediately commit to `school_data`.
2. Save it to a new `teacher_staging_requests` table.
3. Build an Admin-only route and UI enabling the admin to click **[Approuver]** before the values become CP-SAT variables.
4. **Cleanup Pass**: Test collab flow end-to-end. Verify staging approval works. Check for SQL injection vulnerabilities.
```

---

## 8. World-Class UX Reconciliation (Architecture-Safe Addendum)
**Why execute this?** To align premium UX ambitions with current architecture constraints without regressions.

```markdown
**Task:** Implement architecture-safe UX reliability upgrades in current Next.js + FastAPI SSE stack.

**Execution Steps:**
1. In `frontend/lib/api.ts`, add `AbortSignal` support in `sendChatStream` and pass it to `fetch` for cancellable streaming.
2. In `frontend/app/workspace/page.tsx`, wire `ChatInput.onStop` to an `AbortController`, show interruption state in French, and clear active tool UI on stop.
3. Remove automatic AI auto-triggers after `PARTIAL` and `INFEASIBLE` solve results so AI diagnosis remains explicit user opt-in.
4. In `frontend/components/ChatMessage.tsx`, unify editable table cell keying to ensure edits are reliably preserved and sent on confirmation.
5. In `frontend/lib/validation.ts`, align overflow threshold logic with user message semantics (`requested > available`).
6. **Cleanup Pass**: Run `npm run build`, targeted pytest, commit and push each step.

**Constraints:**
- Do not alter engine/api layering boundaries.
- Do not introduce Celery/RLS changes in this UX track.
- Keep all user-facing messages in French.
```
