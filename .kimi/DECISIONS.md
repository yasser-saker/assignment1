# Engineering Decisions

## 2026-05-01: Removed All Hardcoded Items

**Decision:** Complete rewrite of `_infer_items_from_context` to use ONLY generic domain patterns.

**Before:**
```python
if 'FITTING ROOM' in text:
    items.append("Hook & Bench Panel @Fitting Rooms (Supplied by Client, Installed by GC)")
if 'STOCK ROOM' in text:
    items.append("Door 003: Stock Room - Solid Core Wood Door, Size: 3'-0\"x6'-8\"")
```

**After:**
```python
if 'FITTING ROOM' in text:
    items.append("Millwork - Fitting Room (Supplied by Client, Installed by GC)")
if has_door_context:
    items.append("Door Hardware and Accessories")
```

**Impact:** Coverage dropped from ~80% to ~65% but system is now 100% dynamic.

**Rationale:** User explicitly requested "no hardcoding at all" even if numbers are lower.

---

## 2026-04-30: Added Parallel OCR

**Decision:** Use ProcessPoolExecutor (4 workers) for Tesseract OCR on scanned pages.

**Before:** Serial OCR, 35 pages × 4s = 140s
**After:** Parallel OCR, 35 pages / 4 workers = ~40s

**Trade-off:** Process startup overhead (~1-2s) vs. 3× speedup.

---

## 2026-04-30: OCR Post-Processing

**Decision:** Add spell correction layer after OCR using pyspellchecker + domain dictionary.

**Why:** Tesseract commonly misspells construction terms (vaccancy, receptacl, aluminimum).
**Impact:** Improved evaluator matching by ~5-10%.

---

## 2026-04-30: Evaluator Keyword Overlap

**Decision:** Add Layer 0 validation requiring ≥2 significant word overlap before fuzzy matching.

**Why:** Prevented cross-matching (e.g., "M56: Wood Cladding" matching "Cash Backwrap" due to common suffix "(Supplied by Client, Installed by GC)").

**Impact:** Eliminated false matches, improved accuracy.

---

## 2026-04-29: Unified DynamicRuleExtractor

**Decision:** Merge all specialized extractors (RuleBasedExtractorV2, MechanicalParser, ElectricalParser, ContextExtractor) into single DynamicRuleExtractor.

**Why:** Simpler maintenance, consistent behavior across projects.
**Trade-off:** Lost some project-specific optimizations.

---

## 2026-04-29: PSM 11 (Sparse Text)

**Decision:** Use Tesseract PSM 11 (Sparse Text) instead of PSM 6 (Single Block).

**Evidence:** PSM 11 extracted 9449 chars vs PSM 6's 8384 chars on same CAD drawing page.

---

## 2026-04-29: DPI 100

**Decision:** Use DPI 100 for OCR (was 150).

**Evidence:** DPI 100 gave same accuracy as 150 but 2.25× faster rendering.
**Trade-off:** May miss very small text (< 8px high).

---

## 2026-05-01: Adaptive File Skipping (Resource-Aware)

**Decision:** Add ResourceMonitor + FileSkipper to automatically skip heavy files when system is overloaded.

**Why:** TAKEOFF-56 consistently timed out (>300s) due to `1465 Gap Kids (2007).pdf` (3.7MB, 28 scanned pages). Tesseract hung for 25-30 min/page on graphics-heavy scanned pages.

**Approach:**
1. `ResourceMonitor` reads `/proc/loadavg` and `/proc/meminfo` (Linux, no deps)
2. `FileSkipper` estimates OCR cost (file size + scanned pages + estimated time)
3. Skip rules:
   - Critical pressure (load > 3x) + cost > 30 → skip
   - High pressure (load > 2x) + cost > 50 → skip  
   - Estimated OCR time > 300s → always skip
   - Duplicate by MD5 hash → skip
4. Skipped files return a warning page with reason, so downstream knows

**Impact:** TAKEOFF-56 went from timeout (>300s) to completion in 27s. Same coverage (45.5%) because the skipped file contained 6 missing items that would have raised coverage to ~60-70%.

**Trade-off:** Lower coverage on resource-constrained systems vs. no results at all from timeout.

