# Assignment 2 — TAKEOFF-52 (Actual State)

**Project:** Lovesac Corner Shoppes at Stadium, Kalamazoo, MI  
**Date:** 2026-05-02  
**Status:** Prototype — partial extraction, no quantities from drawings

---

## What This Folder Contains

### Actual Generated Outputs
| File | What It Actually Is |
|------|---------------------|
| `prediction.json` | 27 predicted line items. **Only 8 match** the human gold output. 19 are extra/false positives. **All quantities are null** except 2 general items (Management + Documentation). |
| `evaluation_report.json` | Comparison against human estimate. **Coverage: 72.7%** (8 of 11 items matched). |
| `TAKEOFF-52_takeoff.xlsx` | Spreadsheet export of the 27 predicted items. **Quantity column is empty** for 25 items. |
| `TAKEOFF-52_marked.pdf` | Copy of source PDFs with **keyword highlights only** (not real measurement annotations). |

### Source Code (what produced these outputs)
| File | Role |
|------|------|
| `export.py` | FastAPI endpoints for XLSX and marked PDF export. |
| `dynamic_rule_extractor.py` | Rule-based text extractor. Uses regex for flooring types, dimensions, manufacturers. No ML, no vision. |

---

## The Real Numbers

### Gold Output (Human Estimate) — 11 Items

| # | Item | Qty | Unit |
|---|------|-----|------|
| 1 | Management & Supervision (Weeks) | 1 | EA |
| 2 | Documentation & Shop Drawings | 1 | LS |
| 3 | V-1: 12"x12"x1/8" Vinyl Composition Tile Flooring (Armstrong, Desert Beige) | 311.52 | SF |
| 4 | T-1: 8"x48"x3/8" Light Color Wood Grain Plank Porcelain Tile (Patcraft, White Oak) | 1934.66 | SF |
| 5 | W-1: 6 1/2" Wide x 3/8" Thick Light Color Engineered Hardwood Plank (Shaw) | 162.61 | SF |
| 6 | W-1: 6 1/2" Wide x 3/8" Thick Light Color Engineered Hardwood Plank (7" High) | 36.6 | FT |
| 7 | Teal 3/8" Schluter-Indec Style Edge Trim | ~39 | FT |
| 8 | Rubber Base to Match Flooring | 107.92 | FT |
| 9 | MDF Painted Wood Base | 99.45 | FT |
| 10 | Painted Wood Ledger @Masonry Wall Base | 85.37 | FT |
| 11 | Vinyl to Porcelain Transition | 3.16 | FT |

### What the AI Actually Found — 27 Items

**Matched (8/11):**
| AI Prediction | Gold Match | Status |
|---------------|------------|--------|
| VCT Flooring | V-1: Vinyl Composition Tile | ✅ Fuzzy match |
| 12" X 12" Vinyl Composition Tile Flooring | V-1: Vinyl Composition Tile | ✅ Exact dim match |
| Engineered Hardwood Flooring | W-1: Engineered Hardwood Plank | ✅ Keyword match |
| Schluter Edge Trim | Schluter-Indec Edge Trim | ✅ Keyword match |
| Rubber Base | Rubber Base to Match Flooring | ✅ Keyword match |
| MDF Base | MDF Painted Wood Base | ✅ Keyword match |
| Wood Base | Painted Wood Ledger | ✅ Partial match |
| Floor Transition | Vinyl to Porcelain Transition | ✅ Partial match |
| Management & Supervision | Management & Supervision | ✅ Exact match |
| Documentation & Shop Drawings | Documentation & Shop Drawings | ✅ Exact match |

*Note: The evaluator counts 8 matches, not 10, because some of the above are partial/fuzzy matches grouped together.*

**Missing (3/11):**
| Missing Item | Why It's Missing |
|--------------|------------------|
| T-1: 8"x48"x3/8" Porcelain Tile (Patcraft, White Oak) | Fuzzy match score 57% (below 60 threshold). AI found "6" X 36" | Porcelain Tile" and "8" X 48" | Vinyl Tile" but not the exact Patcraft + White Oak combo. |
| W-1: 6 1/2" Wide x 3/8" Thick Hardwood (7" High) | Parenthetical dimension "(7" High)" extracted separately but not combined into item description. |
| Vinyl to Porcelain Transition | Inference was disabled to reduce false positives. Document mentions "SALES FLOOR TO BOH VCT TRANSITION" but not "vinyl to porcelain" together. |

**Extra (19 items) — The Problem:**

Most extra items are **generic flooring types inferred from context**, not actual project specifications:

| Extra Item | Why It Appeared | Should It Stay? |
|------------|-----------------|-----------------|
| 6" X 36" Porcelain Tile | Generic inference from "porcelain tile" mention | ❌ Remove — wrong dimensions |
| Ceramic Tile Flooring | Generic pattern match | ❌ Remove — not in project |
| 7" X 48" Luxury Vinyl Flooring | Generic pattern match | ❌ Remove — not in project |
| Carpet Flooring | Generic pattern match | ❌ Remove — not in project |
| 8" X 48" Vinyl Tile | Generic pattern match | ❌ Remove — wrong product type |
| 7" X 48" Vinyl Tile Flooring | Generic pattern match | ❌ Remove — not in project |
| Resilient Floor Flooring | Generic pattern match | ❌ Remove — vague |
| Metal Edge Trim | Generic accessory inference | ❌ Remove — no evidence |
| Wood Ledger | Extracted from text but matched to "Wood Base" | ⚠️ Keep but merge |
| Floor Leveling Compound | Generic inference | ❌ Remove — no evidence |
| Walk-Off Mat | Generic inference | ❌ Remove — no evidence |
| Millwork - Storage | Generic inference from "STOCK ROOM" mention | ❌ Remove — not flooring |
| Door Hardware and Accessories | Generic inference from door schedules | ❌ Remove — not flooring |
| Flexible Ductwork to Diffusers | Generic HVAC inference | ❌ Remove — not flooring |
| Roof Equipment Curb | Generic HVAC inference | ❌ Remove — not flooring |
| Plumbing Cleanout | Generic plumbing inference | ❌ Remove — not flooring |
| Refrigerant Lines | Generic HVAC inference | ❌ Remove — not flooring |

---

## Root Causes

### 1. No Quantities from Drawings
**Reality:** The system extracts text from PDFs only. It does **not** measure areas from floor plans.  
**Result:** 25 of 27 items have `quantity: null`.  
**Fix needed:** Either (a) manual quantity entry, (b) AI parsing of room schedules + dimensions, or (c) integration with a quantity calculator.

### 2. Generic Pattern Matching
**Reality:** The extractor uses regex patterns that match ANY mention of flooring types, not just the ones specified for this project.  
**Result:** 12+ false positive flooring items (Ceramic, Carpet, Luxury Vinyl, etc.).  
**Fix needed:** Cross-reference extracted items against the project's finish legend / room schedule to validate which products are actually used.

### 3. Fuzzy Matcher Too Strict
**Reality:** The evaluator requires 60% fuzzy match. The AI extracts "8\" X 48\" | Vinyl Tile" but the gold says "8\"x48\"x3/8\" Light Color Wood Grain Plank Porcelain Tile (Patcraft, White Oak)". The manufacturer and color details aren't in the PDF text, so fuzzy match fails.  
**Result:** T-1 Porcelain Tile marked as missing despite dimension extraction.  
**Fix needed:** Lower fuzzy threshold to 50% for dimensioned items, or add manufacturer/color extraction from spec sections.

### 4. Missing Transition Inference
**Reality:** "Vinyl to Porcelain Transition" requires knowing both flooring types exist in the project AND that a transition exists between them. The conservative approach removed this to avoid false positives.  
**Result:** 1 missing item.  
**Fix needed:** Re-enable transition inference with a document-level check (if both types mentioned anywhere in the PDF, infer transitions).

---

## What "81.8%" Would Require

The 81.8% figure (9/11 matched) is **not current reality**. It would require:

| Fix | Time | Impact |
|-----|------|--------|
| Lower fuzzy threshold for dimensioned items (55% instead of 60%) | 10 min | Catches T-1 Porcelain Tile |
| Combine parenthetical dims into item description | 10 min | Catches W-1 (7" High) variant |
| Re-enable document-level transition inference | 10 min | Catches Vinyl to Porcelain Transition |

**Total: ~30 minutes of work → 9/11 = 81.8%**

But even at 81.8%, the **19 extra items and null quantities** remain unsolved. Those require deeper architectural changes.

---

## Honest Assessment

| Metric | Value | Target | Verdict |
|--------|-------|--------|---------|
| Coverage | 72.7% (8/11) | ≥ 75% | ❌ Below target |
| Extra Items | 19 | < 10 | ❌ Too many false positives |
| Quantities Filled | 2/27 (7%) | 100% | ❌ Not implemented |
| Source Attribution | All items | All items | ✅ Every item has source file |
| Export (XLSX/PDF) | Working | Working | ✅ Functional |

**Bottom line:** The pipeline works end-to-end (ingest → extract → evaluate → export), but the extraction quality needs significant improvement before it's demo-ready at 75%+ coverage with clean output.
