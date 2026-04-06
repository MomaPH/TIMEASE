# TIMEASE Clarification Questions
**Date:** 2026-04-06
**Context:** Issues found during comprehensive audit that require your input

---

## ❓ Question 1: Anthropic Model Selection

**Context:**
Your code uses `claude-3-5-haiku-20241022` but logs show a 404 error:
```
anthropic.NotFoundError: Error code: 404 -
{'error': {'type': 'not_found_error', 'message': 'model: claude-3-5-haiku-latest'}}
```

**Your Anthropic SDK:** v0.89.0 (latest as of April 2026)

**Question:**
Which Claude model should the AI chat use for the conversational assistant?

**Options:**
1. **claude-3-5-sonnet-20241022** (most capable, recommended for complex tasks)
2. **claude-3-7-sonnet-20250219** (newest Sonnet if available in your region)
3. **claude-3-5-haiku-20241022** (current code - but getting 404)
4. **claude-3-opus-20240229** (highest quality, slower/expensive)
5. **Other** (please specify the exact model ID)

**Impact:** AI chat streaming is completely broken until this is fixed.

**My Recommendation:**
Use `claude-3-5-sonnet-20241022` (stable, well-tested, good balance of speed/quality). The Haiku model might not be available in your API tier or region.

---

## ❓ Question 2: Node.js Upgrade Path

**Context:**
- Current: Node.js v18.19.1
- Required by Next.js 16.2.2: >= v20.9.0
- npm shows EBADENGINE warnings

**Question:**
Do you want to upgrade Node.js, or should we downgrade Next.js to match Node 18?

**Options:**
1. **Upgrade Node.js to v20 LTS** (recommended - get latest features)
2. **Downgrade Next.js to 14.x** (compatible with Node 18)
3. **Keep as-is** (works but with warnings)

**Recommendation:**
Upgrade to Node 20.x using `nvm` or system package manager. Next.js 16 has significant performance improvements with Turbopack that work best on Node 20+.

**Command to upgrade (if using nvm):**
```bash
nvm install 20
nvm use 20
nvm alias default 20
```

**Impact:** Low risk - all code should work on Node 20. Build times may improve.

---

## ❓ Question 3: Uncommitted Changes Strategy

**Context:**
7 files modified, 3 new files untracked:
```
M  README.md
M  frontend/components/StepPanel.tsx
M  frontend/next.config.ts
M  frontend/package-lock.json
M  scripts/dev.sh
M  timease/api/ai_chat.py
M  timease/api/main.py
?? frontend/components/ChatInput.tsx
?? frontend/components/CodeBlock.tsx
?? frontend/components/ValidationErrorPanel.tsx
```

**Question:**
What should we do with these changes?

**Options:**
1. **Commit them** as "Phase 2.3/2.4 completion" (if they're finished work)
2. **Stash them** (if they're experimental/incomplete)
3. **Review individually** (you want to inspect before deciding)
4. **Leave as-is** (you're actively working on them)

**My Recommendation:**
Based on CONTEXT.md saying Phase 2.3-2.4 are complete (✅), these should be committed. But I want your confirmation first.

---

## ❓ Question 4: Development Logs Retention

**Context:**
The `logs/dev/` directory has 20+ log files from backend/frontend runs, taking ~180KB.

**Question:**
Should we:

**Options:**
1. **Add `logs/` to .gitignore and delete existing logs** (clean slate)
2. **Add `logs/` to .gitignore but keep existing logs** (for your reference)
3. **Keep logs tracked in git** (not recommended - sensitive data risk)
4. **Create a logs retention policy** (e.g., keep last 7 days, auto-rotate)

**My Recommendation:**
Option 1 - Add `logs/` to `.gitignore` and delete old logs. Create `.gitkeep` to preserve the directory structure.

**Risk if not fixed:**
Accidentally committing logs could expose:
- API keys in stack traces
- Internal file paths
- Session data
- Debug information

---

## ❓ Question 5: Type Checking Integration

**Context:**
Project uses type hints everywhere but `mypy` is not installed.

**Question:**
Should we add static type checking to your development workflow?

**Options:**
1. **Yes - add mypy + run in CI/pre-commit** (strict mode)
2. **Yes - add mypy but run manually only** (optional)
3. **No - type hints are for IDE only** (current state)

**Recommendation:**
Option 1. Add to `pyproject.toml`:
```toml
[project.optional-dependencies]
dev = ["mypy>=1.8", "pytest>=8.0"]

[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

**Benefit:** Catch type errors before runtime (especially important for Phase 2.5 mypyc compilation).

---

## ❓ Question 6: Docstring Print Statements

**Context:**
`conflicts.py` has example code in its docstring that uses `print()`:

```python
"""
Usage::

    analyzer = ConflictAnalyzer(school_data)
    reports  = analyzer.analyze()
    for r in reports:
        print(r.description_fr)  # ❌ Violates "no print in library code"
        for opt in r.fix_options:
            print(" →", opt.fix_fr)
"""
```

**Question:**
How should we fix the example code?

**Options:**
1. **Replace with logging** (consistent with project rules)
   ```python
   logger.info(r.description_fr)
   ```

2. **Use proper CLI pattern** (if this is meant for a CLI tool)
   ```python
   # In a CLI script (not library):
   for r in reports:
       console.print(r.description_fr)
   ```

3. **Keep print() in docstring** (it's just documentation, not real code)

**My Recommendation:**
Option 1 - Update the example to use logging, teaching the correct pattern. Docstrings are often copy-pasted by developers.

---

## 📋 Summary of Decisions Needed

| # | Issue | Urgency | Default Action |
|---|-------|---------|----------------|
| 1 | Claude model name | 🔴 HIGH | Use `claude-3-5-sonnet-20241022` |
| 2 | Node.js version | 🟡 MEDIUM | Upgrade to Node 20 |
| 3 | Uncommitted changes | 🟢 LOW | Commit them |
| 4 | Logs retention | 🟡 MEDIUM | Add to .gitignore + delete |
| 5 | Type checking | 🟢 LOW | Add mypy to dev deps |
| 6 | Docstring prints | 🟢 LOW | Replace with logging |

---

## 🎯 What I'll Do If You Approve All Defaults

1. ✅ Fix Claude model → `claude-3-5-sonnet-20241022`
2. ✅ Add `logs/` to `.gitignore` + clean old logs
3. ✅ Replace print() with logging in docstring
4. ✅ Add mypy to dev dependencies
5. ✅ Commit working changes with proper message
6. ⚠️ **Document Node.js upgrade** (but not auto-upgrade - requires your system)

---

**Please respond with:**
- "Approve all defaults" (I'll apply fixes 1-5 automatically)
- Or specific answers for each question
- Or "wait" if you need time to review
