# TIMEASE Architectural Analysis (Master Document)

> [!NOTE]
> This analysis aggregates every single operational, architectural, and business-logic decision we have discussed. It serves as the definitive roadmap for deploying the Phase 2, human-in-the-loop TIMEASE application for African private schools.

---

## 1. Product Philosophy: Absolute Human Authority

**The Pivot:** TIMEASE must embrace a 100% **"Manual" / "All-or-Nothing"** paradigm.
- The Engine must assume every teacher, class, and subject is pre-negotiated by human contracts. The Phase 1 Python "Greedy Assignment" (Auto mode) algorithm is a false abstraction and must be fully deprecated.
- The schedule must accommodate 100% of these manual requests to be valid. Dropping sessions via algorithmic compromise is unacceptable in a real school.
- If the human constraints clash mathematically, the system must forcefully halt (`INFEASIBLE`) and demand human resolution. By acting as an unyielding logical boundary, the software commands absolute trust and forces necessary administrative choices.

---

## 2. Advanced Solver Optimization (Soft Constraints S1-S5)

Converting S1-S5 (like teacher time preferences or balanced daily loads) from post-solve grading to native CP-SAT `model.Maximize()` forces CP-SAT to output the most aesthetically pleasing schedule possible, rather than just the first valid one.

> [!WARNING]
> **The Risk:** CP-SAT can find a valid schedule in 5 seconds, but proving it is the *mathematically optimal* schedule can take 10 hours. It will hang indefinitely.

- **Mitigation (Strict Time Limits):** Set `solver.parameters.max_time_in_seconds = 30`. Tell CP-SAT to maximize the soft constraints to create a beautiful schedule, but force it to return the *best schedule it found within 30 seconds*.
- **A/B Testing Updates:** Never refactor `timease/engine/solver.py` directly. Instead, create `solver_v2.py`. Use deterministic locked data files (like `real_school_dakar_LOCKED.json`) to regression test V2 parallel to V1 before deprecating V1.

---

## 3. Python Bottleneck Compilation (Cython / mypyc)

Currently, the `ConflictAnalyzer` iteratively removes constraints in Python with timeouts to test `INFEASIBLE` limits. As schools scale, this pure-Python loop will heavily bottleneck the API.

> [!TIP]
> Compile bottleneck Python scripts into C extensions for massive performance gains without touching C++ OR-Tools.

Since your `CLAUDE.md` explicitly enforces strict type hints, leverage **mypyc** (or Cython) to compile files like `conflicts.py` directly into C extensions. This maintains Python readability for developers but dramatically accelerates the constraint triage loops, bringing them closer to native C++ speeds.

---

## 4. UI Gatekeeping & Detaching the LLM (API Optimization)

The frontend is the absolute gatekeeper for API costs. Relying on Anthropic's Claude to resolve simple human math errors (e.g., allocating 50 teaching hours for a 40-hour week) is financially catastrophic.

- **Frontend Feasibility Bars:** Prevent users from advancing to the solver (Step 8) if their allocated teacher hours exceed physical school hours. Basic mathematics should *never* touch the solver or the LLM.
- **Deterministic Fix Option Rendering:** On an `INFEASIBLE` wall, the backend `ConflictAnalyzer` returns structured, French recommendations. The UI must map this JSON explicitly to React components, deliberately detaching Anthropic from summarizing standard errors.
- **Opt-in LLM Calls:** Only trigger the Claude API if the user clicks an explicit *"Demander à l'IA de m'aider"* (Ask AI) button on complex errors. Send strictly the truncated JSON data surrounding the isolated conflicting parameter, saving thousands of payload tokens.

---

## 5. The Premium AI Experience (Agentic Concierge)

The AI layer must feel less like a "chatbot" and more like an executive assistant. B2B trust hinges on how premium the software "thinks."

- **Transparent Tool-Call Visuals:** Replicate the Claude/Perplexity UI. Show a sleek, pulsing `<AgentActionPill />` component that says *"Validation des matières..."* or *"Analyse des contraintes..."*. The transparency makes the AI feel powerful and deliberate rather than sluggish.
- **Inline AI Mispull Corrections:** When the AI summarizes a table of schedules, if it hallucinates a data point, the user should not have to type a correction prompt. The Recap Tables must be **editable spreadsheets**. The user clicks the erroneous cell, fixes the number, and *then* clicks `✅ Confirmer`.
- **The Streaming Polish:** Ensure SSE Markdown streams smoothly, implementing a custom blinking cursor `▍` at the tail of the stream to give a "live intelligence" feel.

---

## 6. Cloud Infrastructure Strategy (Hosting Celery)

Massive CP-SAT solves will exceed Next.js/FastAPI 60-second timeouts. The solve process must be decoupled to a background queue (Celery/Redis) using WebSockets/SSE to stream progress to the frontend.

**The Hosting Problem:** Serverless providers (like Vercel) forcefully terminate background workers. You cannot host Celery on Vercel. 
**The Solution (Micro-Services Split):** 
1. Deploy your Next.js Frontend to **Vercel** for the fastest global CDN caching and React rendering.
2. Deploy your FastAPI Backend + Celery + PostgreSQL to a PaaS like **Render.com**. Render natively supports long-lived "Background Workers," meaning you do not need intensive Linux/DevOps expertise to keep your Celery queue alive.

---

## 7. Data Localization & Compliance (Senegal CDP)

Because school timetables include sensitive teacher names and availability, you fall under the Senegalese **Commission de Protection des Données Personnelles (CDP)** (Law No. 2008-12).

**Legal Strategy:**
There is **no strict legal mandate** requiring you to physically host servers inside Senegal. Because you are deploying the backend on Render, you should elect to host the PostgreSQL database in the **European Union** (e.g., Frankfurt region). The EU's GDPR is globally recognized by the CDP as providing "sufficient protection" for cross-border data transfers, keeping you fully legally compliant.

---

## 8. Collaboration Staging & Security

- **Admin Interaction Portal:** Teacher availability submissions from the public URL must route to a "Staging Table" in PostgreSQL. The School Administrator dashboard provides a UI to review, modify, and explicitly **[Approve]** these availabilities before they convert into hard CP-SAT constraints (H8).
- **Postgres Row-Level Security (RLS):** Transitioning away from SQLite demands robust data silos. An `ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;` query bound by JWT tenant models ensures mathematical proof that Data Leaks between rival schools cannot occur.
