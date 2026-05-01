# Project Memory - AI Takeoff Builder

## Current State (2026-05-01)

### System Status
- **Backend:** Running on Docker (port 8000) ✅
- **Frontend:** Running on Docker (port 8082) ✅
- **Extraction Engine:** DynamicRuleExtractor (100% dynamic, no hardcoded items)
- **OCR Pipeline:** Tesseract + Spell Correction + Parallel OCR (4 workers)

### Latest Results (After Hardcoded Removal)

| Project | Type | Coverage | Matched/Total | Extracted Items |
|---------|------|----------|---------------|----------------|
| TAKEOFF-28 | Sample | 64.5% | 78/121 | 225 |
| TAKEOFF-56 | Sample | 45.5% | 5/11 | 22 |
| TAKEOFF-50 (specs) | Sample | 57.1% | 4/7 | 28 |
| TAKEOFF-31 | Challenge | N/A | N/A | 3 |
| TAKEOFF-36 | Challenge | N/A | N/A | 48 |

**Total: 5 projects processed, ~326 items extracted**

### Key Architecture Decisions
1. Unified DynamicRuleExtractor for ALL projects (removed special cases)
2. Generic finish code parsing (any prefix format [A-Z]{1,4}-\d+)
3. Generic room number parsing (any format: 101, 101A, Suite 100)
4. Generic equipment tag discovery (discovers valid prefixes from context)
5. OCR Post-Processing with spell correction (vaccancy→vacancy)
6. Parallel OCR with ProcessPoolExecutor (4 workers)
7. Chunked OCR with checkpoint/resume support

### Known Issues
1. TAKEOFF-50 drawings: Tesseract hangs on some pages (25-30 min/page)
2. Scanned floor plans: OCR cannot read small text reliably
3. Graphics-based items: Ductwork sizes, pipe sizes not extractable
4. Coverage ceiling: ~65% for text-rich projects without vision API

### File Types Processed
- drawings (auto-detected by filename keywords)
- specs (auto-detected by filename keywords)
- addendums (auto-detected by filename keywords)
- scope of work (auto-detected by filename keywords)
