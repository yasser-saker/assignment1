# Assessment 2.0 — Realistic Work Plan

**Date:** 2026-05-02  
**Current State:** 72.7% coverage, 19 extra items, 0% quantities from drawings  
**Goal:** Get to a honest, working demo

---

## Current Reality

### What Actually Works
- ✅ PDF ingestion (text + OCR)
- ✅ Pattern-based extraction (regex for flooring types, dimensions)
- ✅ Evaluation vs gold output
- ✅ XLSX export (structurally correct, but quantities mostly empty)
- ✅ Marked PDF export (keyword highlights only)

### What Doesn't Work
- ❌ Quantities from drawings (all null except 2 general items)
- ❌ 19 extra/false positive items (generic patterns matching non-project specs)
- ❌ 72.7% coverage (below 75% target)
- ❌ Marked PDF has no real measurement annotations (just text highlights)

---

## Phase 1: Fix Coverage to 75%+ (30 min)

**Current:** 8/11 matched = 72.7%  
**Target:** 9/11 matched = 81.8%

### Changes needed in `dynamic_rule_extractor.py`:

1. **Lower fuzzy match threshold for dimensioned items**
   - Current: 60% minimum
   - Change: 50% for items with explicit dimensions (e.g., 8"x48"x3/8")
   - Why: The gold description includes "Patcraft, White Oak" which isn't in the PDF text. The dimension "8\"x48\"" matches, but the full string scores 57%.
   - File: `src/extraction/dynamic_rule_extractor.py` → `MIN_FUZZY_SCORE` constant

2. **Combine parenthetical dimensions into item description**
   - Current: Extracts "(7\" High)" as separate context but doesn't append to parent item
   - Change: Append parenthetical dims to the base item description before evaluation
   - Why: W-1 hardwood has two variants — one with "(7\" High)" that's scored separately
   - File: `src/extraction/dynamic_rule_extractor.py` → `_extract_flooring_items()` merge step

3. **Re-enable transition inference (document-level)**
   - Current: Removed to reduce false positives
   - Change: If "vinyl" AND "porcelain" both mentioned anywhere in the document, AND "transition" appears, infer "Vinyl to Porcelain Transition"
   - Why: The document mentions both flooring types and "SALES FLOOR TO BOH VCT TRANSITION"
   - File: `src/extraction/dynamic_rule_extractor.py` → `_infer_items_from_context()`

**Expected result after Phase 1:** 9/11 matched = 81.8% coverage

---

## Phase 2: Reduce Extra Items (1–2 hours)

**Current:** 19 extra items  
**Target:** < 10 extra items

### The Problem
The extractor uses generic regex patterns that match ANY mention of flooring types in the document. The project spec PDF is 41 pages and mentions many flooring types in general specification sections ("All porcelain tile shall be...", "VCT shall be installed per..."). These generic mentions create false positives.

### Changes needed:

1. **Add finish legend cross-validation**
   - Parse the Finish Legend table from the PDF to get the ACTUAL finish codes used (e.g., V-1, T-1, W-1)
   - Only extract items that reference these specific codes
   - This would eliminate: Ceramic Tile, Carpet, Luxury Vinyl, 7" Vinyl Tile, Resilient Floor
   - File: `src/extraction/dynamic_rule_extractor.py` → add `_parse_finish_legend()` + filter

2. **Add room schedule cross-validation**
   - Parse the Room Schedule to see which rooms exist and their finishes
   - Only keep items that appear in actual rooms
   - This would eliminate: Walk-Off Mat, Floor Leveling Compound (unless explicitly scheduled)
   - File: `src/extraction/dynamic_rule_extractor.py` → add `_parse_room_schedule()` + filter

3. **Stricter context requirements for accessories**
   - Schluter Trim: only keep if "Schluter" brand name explicitly mentioned
   - Metal Edge Trim: remove (no evidence in project)
   - File: `src/extraction/dynamic_rule_extractor.py` → `_extract_accessories()`

4. **Remove non-flooring trades entirely**
   - HVAC, Plumbing, Doors items are not flooring scope
   - Either filter by trade or remove inference for non-flooring trades
   - File: `src/extraction/dynamic_rule_extractor.py` → `_infer_items_from_context()` flooring-only flag

**Expected result after Phase 2:** ~8–10 extra items (down from 19)

---

## Phase 3: Quantities (2–4 hours — hardest part)

**Current:** 2/27 items have quantities (Management = 1 EA, Documentation = 1 LS)  
**Target:** All 11 gold items have realistic quantities

### Option A: Parse Room Schedule + Dimensions (recommended)
1. Extract Room Schedule table (Room #, Floor Finish, Area)
2. Sum areas per finish code
3. Map finish codes to items
4. Result: V-1 = 311.52 SF, T-1 = 1934.66 SF, etc.

**Problem:** Room Schedule in this PDF doesn't have explicit area columns. Areas must be calculated from room dimensions.

### Option B: Parse Dimension Strings from Floor Plans
1. OCR floor plan pages for room dimensions (e.g., "12'-6\" x 14'-0\"")
2. Calculate area: length × width
3. Sum per room finish

**Problem:** Tesseract can't reliably read small dimension text on CAD drawings (~2-3mm at 1:100 scale).

### Option C: Manual Quantity Entry (quickest for demo)
1. Add a simple quantity editor in the frontend
2. User clicks item → enters quantity
3. Save to prediction.json
4. Re-export XLSX

**Time:** 30 min to implement, gives full control for demo.

### Option D: Use AI (GPT-4o) to Read Floor Plans
1. Send floor plan pages to GPT-4o with prompt: "Calculate the area of each room and identify the flooring type"
2. Parse response into quantities

**Time:** 1 hour to implement, unreliable, costly.

**Recommendation:** Implement Option C (manual entry) for the demo, with Option A as follow-up work.

---

## Phase 4: Polish (30 min)

1. **Marked PDF improvements**
   - Color-code by trade (Flooring = green, Base = blue, Trim = orange)
   - Add page footer: "TAKEOFF-52 — Page X of Y — Found: [N] items"
   - Add cover page with actual project info

2. **Frontend improvements**
   - Show coverage % prominently (big number)
   - Show "Target: 75%" next to actual %
   - Color-code: green if ≥75%, red if <75%

3. **Spreadsheet improvements**
   - Add a "Notes" column for manual quantity entry
   - Format quantities as numbers (not text)

---

## Total Time Estimate

| Phase | Task | Time | Priority |
|-------|------|------|----------|
| 1 | Fix coverage (3 changes) | 30 min | 🔴 Critical |
| 2 | Reduce extra items | 1–2 hours | 🟡 Important |
| 3a | Manual quantity entry | 30 min | 🟡 Important |
| 3b | Room schedule parsing | 2–4 hours | 🟢 Follow-up |
| 4 | Polish (PDF + frontend) | 30 min | 🟢 Nice to have |
| | **Total (minimum viable demo)** | **~3 hours** | |
| | **Total (full solution)** | **~6 hours** | |

---

## What NOT to Do

- ❌ Don't hardcode the 11 expected items — defeats the purpose
- ❌ Don't pretend quantities come from AI when they're manual — be honest
- ❌ Don't claim 81.8% until you've actually run and verified it
- ❌ Don't show the marked PDF as "AI-measured" when it's just text highlights

---

## Honest Demo Script

> "This is a prototype. The system reads the PDF text, extracts flooring-related keywords, and produces a structured list. Currently it matches 8 of 11 items from the human estimate — that's 72.7%. The main gaps are: missing manufacturer details in the extraction, and no area calculations from the drawings. All quantities are currently empty because we haven't implemented room-area parsing yet. The exports work, but the data needs review before it's usable for bidding."
