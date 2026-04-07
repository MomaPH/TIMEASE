# TIMEASE Resume Context

**Last Updated:** 2026-04-07
**Active Phase:** 2.5 — OpenAI Migration + Class-Based Curriculum ✅

## Current Work

### Completed in this session

1. **Removed Claude/Anthropic Support**
   - Removed `anthropic` dependency from pyproject.toml
   - Removed `/api/ai/provider` endpoints
   - Removed provider toggle from Sidebar.tsx
   - OpenAI GPT-4o is now sole AI provider
   - Cost savings: ~27% less than Claude Sonnet

2. **Class-Based Curriculum Model (BREAKING)**
   - Changed `CurriculumEntry.level` → `CurriculumEntry.school_class`
   - Curriculum now specifies hours per individual class, not per level
   - Updated models.py, solver.py, conflicts.py, ai_chat.py, excel_import.py
   - Migrated all JSON data files
   - Sample data expanded: 41 → 82 curriculum entries

3. **Teacher Hours Optional**
   - `max_hours_per_week` defaults to 20h if not specified

4. **All Tests Fixed**
   - All 249 tests passing
   - Updated test fixtures for new data model
   - Frontend builds successfully

### Validation

- `uv run pytest tests/ -q` → 249 passed ✅
- `cd frontend && npm run build` ✅
- Git commit and push ✅

## Next Steps

1. **Test AI chat end-to-end** - Verify OpenAI tool calling works
2. **Fix propose_options display** - Ensure clickable buttons appear
3. **Test curriculum workflow** - Verify class-based curriculum via AI setup

## Known Issues

- `propose_options` tool may not display clickable buttons (needs verification)
- Pre-commit warning about deprecated pytest stage (cosmetic)
- `uv run pytest -q tests/test_solver.py tests/test_conflicts.py tests/test_io.py` ✅ (68 passed)

## Architecture Notes

- Design inspired by Linear, Stripe, Vercel
- Single accent color (indigo #6366f1) used sparingly
- Neutral zinc palette for text and backgrounds
- System fonts for optimal performance
- No external dependencies (no Google Fonts, no CDN)

## BREAKS in Timetable — Implementation Plan

Currently, breaks are extracted from `schoolData.sessions` if:
- `is_break: true` flag is set, OR
- name contains "pause" or "récréation"

To fully implement breaks:

1. **Backend**: In school setup (step 0), add UI to mark certain sessions as breaks
2. **Solver**: Already respects unavailable slots — breaks should be naturally excluded
3. **Export**: PDF/Excel exports should include break rows in output

## File Quick Reference

| Purpose | Path |
|---------|------|
| Design system CSS | `frontend/app/globals.css` |
| Sidebar component | `frontend/components/Sidebar.tsx` |
| Client layout | `frontend/components/ClientLayout.tsx` |
| Home page | `frontend/app/page.tsx` |
| Results page | `frontend/app/results/page.tsx` |
| Timetable grid | `frontend/components/TimetableGrid.tsx` |
| Types | `frontend/lib/types.ts` |

## Remaining Next Steps

1. **Phase 2.5** — mypyc on `timease/engine/conflicts.py`
2. **Phase 2.6** — Celery/Redis async solve + Postgres RLS
3. **Breaks UI** — Add explicit break configuration in school setup wizard
4. **A11y pass** — focus-visible, aria-live audit
