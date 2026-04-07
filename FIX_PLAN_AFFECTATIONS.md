# Fix Plan: Affectations, Options Display & Curriculum Model

**Date:** 2026-04-07
**Issues Reported:**
1. ❌ Affectations validation not checking properly (checklist stuck)
2. ❌ `propose_options` appearing as plain text instead of clickable buttons
3. ❌ Curriculum model wrong: should be hours per (class+subject), NOT per teacher
4. ℹ️ Teacher max_hours_per_week should be optional

---

## Issue Analysis

### 1. **Affectations Validation Not Checking** 🔴 CRITICAL

**Current behavior:**
- Line 138-140 in `frontend/lib/types.ts`:
  ```typescript
  const allAssigned = curriculum.length === 0 || curriculum.every(c => {
    const cls4level = classes.filter(cl => (cl.level || cl.name) === c.level)
    return cls4level.length === 0 || cls4level.every(cl => pairSet.has(`${cl.name}__${c.subject}`))
  })
  ```
- This checks if every curriculum entry has assignments for all classes at that level
- **Problem:** When user provides data, curriculum might exist but assignments are empty
- Result: Checklist shows "Toutes les affectations renseignées" as ❌ even when they are provided

**Root cause:**
- Validation logic assumes curriculum is PRIMARY source of truth
- But curriculum is just "hours per level+subject" (e.g., "6ème needs 4h Math")
- Assignments are SEPARATE: "Teacher X teaches Math to Class 6A"
- The logic correctly validates IF curriculum exists, BUT:
  - If curriculum has 0 entries → `allAssigned = true` (line 138)
  - This is wrong! We need both curriculum AND assignments to be complete

**Evidence:**
User says "affectations do not check" → likely means checklist item stays red/unchecked

---

### 2. **Options Not Appearing as Buttons** 🔴 CRITICAL

**Expected behavior:**
- AI calls `propose_options` tool
- Frontend receives `options: [{label: "✅ Confirmer", value: "confirm"}, ...]`
- ChatMessage.tsx lines 300-312 render clickable buttons

**Current implementation:**
- `propose_options` tool exists (ai_chat.py line 266)
- Main.py line 448-449 extracts options from tool calls
- Main.py line 472 returns `"options": proposed_options`
- Frontend should receive this in streaming response

**Problem identified:**
Looking at the streaming code, I see:
- `_dispatch_tool_calls()` returns options
- But in `_generate()` (main.py line 562), the SSE stream yields:
  ```python
  for event in stream_chat(...):
      if event["type"] == "text":
          yield f"data: {json.dumps({'type': 'text', 'content': event['content']})}\n\n"
      elif event["type"] == "tool_call":
          # ... dispatch tools
  ```
- **Missing:** No code to yield `options` from tool dispatch result!
- The options are computed but NEVER sent to frontend via SSE stream

**Why options appear as plain text:**
- AI mentions options in its text message (e.g., "Choisissez: ✅ Confirmer ou ✏️ Modifier")
- But `propose_options` tool result is lost
- Frontend never receives the structured `options` array
- Only the text description appears

---

### 3. **Curriculum Model Wrong** 🟡 MEDIUM

**Current model (WRONG):**
```
Curriculum: hours per (level + subject)
  - 6ème Math: 4h/week
  - 5ème Français: 5h/week

Teacher: has max_hours_per_week
  - M. Dupont: 20h/week max
  - Mme Martin: 18h/week max

Assignments: teacher → class+subject
  - M. Dupont teaches Math to 6A
```

**User's documents specify:**
```
Curriculum should be: hours per (CLASS + subject)
  - 6A Math: 4h/week
  - 6B Math: 4h/week
  - 5A Français: 5h/week

NOT: 6ème level Math: 4h total
```

**Why this matters:**
- Different classes in same level might have different hours
- E.g., 6A might have 4h Math, 6B might have 3h Math (bilingual section)
- Current model forces all 6ème classes to have same hours per subject
- This is too restrictive!

**Current code assumption:**
- `CurriculumEntry.level` (line 212 in models.py)
- `save_curriculum` tool uses `level` field (ai_chat.py line 221)
- Validation checks `cl.level === c.level` (types.ts line 108)

**Fix needed:**
- Change curriculum from (level, subject) → (class, subject)
- OR: Keep level-based curriculum but allow per-class overrides
- OR: Make curriculum optional and derive from assignments

---

### 4. **Teacher Hours Should Be Optional** 🟢 LOW

**Current:**
- `save_teachers` requires `max_hours_per_week` (ai_chat.py line 115)
- Backend defaults to 20 if missing (main.py line 316)

**User wants:**
- Optional field
- Only validate if provided
- Don't force teachers to specify max hours

**Impact:**
- Low priority (has sensible default)
- Easy fix: remove from `required` array in tool schema

---

## Fix Strategy

### Priority 1: Fix Options Display (Immediate UX issue)

**Root cause:** SSE stream doesn't send `options` to frontend

**Fix location:** `timease/api/main.py` lines 540-585 (`/chat/stream` endpoint)

**Current code:**
```python
def _generate():
    for event in stream_chat(...):
        if event["type"] == "text":
            yield f"data: {json.dumps({'type': 'text', ...})}\n\n"
        elif event["type"] == "tool_call":
            res = _dispatch_tool_calls(...)
            # res contains 'options' but we don't send it!
```

**Fix:**
```python
def _generate():
    for event in stream_chat(...):
        if event["type"] == "text":
            yield f"data: {json.dumps({'type': 'text', ...})}\n\n"
        elif event["type"] == "tool_call":
            res = _dispatch_tool_calls(...)

            # NEW: Send options to frontend if present
            if res.get("options"):
                yield f"data: {json.dumps({
                    'type': 'options',
                    'options': res['options']
                })}\n\n"

            # Send pending changes, set_step, etc.
```

**Frontend update:** `frontend/app/workspace/page.tsx` lines 200-220
```typescript
// In handleSend(), SSE event processing:
if (data.type === 'options') {
  setMessages(prev => {
    const next = [...prev]
    const last = next[next.length - 1]
    if (last && last.role === 'ai') {
      last.options = data.options  // ✅ Attach to last AI message
    }
    return next
  })
}
```

---

### Priority 2: Fix Affectations Validation

**Problem:** Checklist logic is correct BUT might have edge case

**Investigation needed:**
1. Check if curriculum entries are being created correctly
2. Check if assignments are being populated
3. Add debug logging to see what `pairSet` contains vs what curriculum expects

**Likely fix:** Frontend validation is fine, backend might not be saving data properly

**Alternative:** Simplify checklist to just check:
```typescript
const allAssigned = assignments.length > 0 && curriculum.length > 0
```

But this is too loose. Better approach:

**New validation (more explicit):**
```typescript
const allAssigned = curriculum.length === 0 || (() => {
  // For each curriculum entry
  for (const curr of curriculum) {
    // Find all classes at this level
    const classesAtLevel = classes.filter(cl =>
      (cl.level || cl.name) === curr.level
    )

    // Each class must have an assignment for this subject
    for (const cls of classesAtLevel) {
      const key = `${cls.name}__${curr.subject}`
      if (!pairSet.has(key)) {
        console.log(`Missing assignment: ${cls.name} → ${curr.subject}`)
        return false
      }
    }
  }
  return true
})()
```

Add logging to debug what's missing!

---

### Priority 3: Curriculum Model Change (Breaking change)

**Two approaches:**

#### Option A: Keep level-based, add class overrides
- Keep `CurriculumEntry.level`
- Add optional `CurriculumOverride.class_name`
- More complex but backward compatible

#### Option B: Switch to class-based curriculum (RECOMMENDED)
- Change `CurriculumEntry.level` → `CurriculumEntry.school_class`
- Update AI tool schema
- Update frontend validation
- Simpler mental model: "This class needs X hours of Y subject"

**I recommend Option B** because:
1. Simpler to understand
2. Matches user's documents exactly
3. More flexible (different classes can have different hours)
4. Easier to validate (direct class → subject → hours mapping)

**Changes needed:**
1. `timease/engine/models.py` line 212: `level: str` → `school_class: str`
2. `timease/api/ai_chat.py` line 221: `"level"` → `"school_class"`
3. `frontend/lib/types.ts` line 108: Check against `class` not `level`
4. Update system prompt to instruct AI to use class names not levels

---

### Priority 4: Make Teacher Hours Optional

**Simple fix:**
1. Remove `max_hours_per_week` from `required` in tool schema (ai_chat.py line 117)
2. Keep default of 20 in backend (main.py line 316)
3. Update UI to show "Non spécifié" if missing

---

## Implementation Order

1. ✅ **Fix options display** (30 min)
   - Update SSE stream in main.py
   - Update frontend to receive options events
   - Test with both OpenAI and Claude

2. ✅ **Add debug logging for affectations** (15 min)
   - Log what curriculum expects vs what assignments provide
   - Identify exact mismatch

3. ✅ **Make teacher hours optional** (10 min)
   - One-line change in tool schema

4. ⚠️ **Decide on curriculum model** (USER INPUT NEEDED)
   - Option A: Keep level-based
   - Option B: Switch to class-based
   - This affects data structure and AI behavior

5. ✅ **Implement chosen curriculum model** (1-2 hours depending on choice)
   - Update models
   - Update tools
   - Update frontend validation
   - Update system prompt
   - Test thoroughly

6. ✅ **Test end-to-end** (30 min)
   - Fresh session
   - AI-assisted setup
   - Verify all checkboxes turn green
   - Verify generate button works

---

## What I Think (My Recommendation)

### On Curriculum Model:

**Switch to class-based curriculum (Option B)** because:

1. ✅ **Matches your documents exactly**
   - You said: "documents give number of hours per subject per class"
   - Current model: hours per subject per LEVEL
   - This mismatch causes confusion

2. ✅ **More flexible**
   - Different classes in same grade can have different hours
   - E.g., 6A (regular): 4h Math, 6B (bilingual): 3h Math + 2h Math in English
   - Level-based model can't handle this

3. ✅ **Simpler validation**
   - Check: Does 6A have a teacher assigned for Math? YES/NO
   - vs: Does every 6ème class have Math assigned? (requires lookup)

4. ✅ **Easier for AI to understand**
   - "6A needs 4 hours of Math per week" is clearer than
   - "All 6ème classes need 4 hours total of Math distributed somehow"

5. ⚠️ **Slight data entry overhead**
   - If you have 10 classes at 6ème level, you enter 10 curriculum entries instead of 1
   - BUT: AI can help by asking "Apply to all 6ème classes?" and duplicating

**Trade-off:**
- More entries to input initially
- But more accurate, more flexible, easier to validate

### On Options Display:

**This is a bug, must fix.** The `propose_options` tool is being called but results are lost. This breaks the entire conversational UX.

### On Affectations Check:

**Probably just needs debug logging** to see what's mismatched. Validation logic looks correct.

---

## Questions for You

Before I implement, please confirm:

1. **Curriculum model change:**
   - [ ] **Option A:** Keep level-based curriculum (current)
   - [ ] **Option B:** Switch to class-based curriculum (RECOMMENDED)
   - [ ] **Option C:** Make both work (level-based with per-class overrides)

2. **If Option B (class-based):**
   - Should AI offer to "apply to all classes at this level" when setting curriculum?
   - Or should it always ask per-class?

3. **Teacher hours:**
   - Confirm: make `max_hours_per_week` fully optional? (default 20h if not specified)
   - Or: keep it required but allow entering "0" to mean "unlimited"?

4. **Options display:**
   - This is clearly a bug - proceed with fix immediately? (Yes/No)

5. **Testing priority:**
   - Should I fix options display FIRST so you can test it live?
   - Or fix all issues together in one batch?

---

## Estimated Time

- Options display fix: **30 minutes**
- Teacher hours optional: **10 minutes**
- Debug affectations: **15 minutes**
- Curriculum model switch (if Option B): **2 hours**
- Testing: **30 minutes**

**Total: 3-4 hours** depending on curriculum decision

---

**Ready to proceed?** Please answer the questions above and I'll implement immediately.
