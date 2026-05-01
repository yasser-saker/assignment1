# Progress Report

## Completed (2026-05-01)

### Core Extraction (100% Dynamic)
- [x] Unified DynamicRuleExtractor (works across ALL projects)
- [x] Removed ALL hardcoded project-specific items
- [x] Generic finish legend parsing (any prefix format [A-Z]{1,4}-\d+)
- [x] Generic room schedule parsing (any room number format)
- [x] Generic equipment schedule parsing (discovers prefixes dynamically from context)
- [x] Enhanced mechanical parser (flexible diffuser/VAV/RTU formats)
- [x] Enhanced electrical parser (multi-letter lighting tags: LF-1, LT-01)
- [x] Trade classifier (keyword-based scoring, no hardcoded mappings)
- [x] False positive filter (regex-based, ~80-90 false positives removed per run)

### OCR Pipeline
- [x] Tesseract OCR with PSM 11 (Sparse Text)
- [x] OCR post-processing with spell correction (pyspellchecker + domain dictionary)
- [x] Construction domain dictionary (150+ terms)
- [x] Parallel OCR (4 workers, ProcessPoolExecutor)
- [x] Chunked OCR with checkpoint/resume
- [x] Smart region detection (OpenCV-based contour detection)
- [x] DPI optimization (100 for detection, 200 for focused crops)
- [x] **Adaptive file skipping** based on system resources and file traits
- [x] **ResourceMonitor** (reads /proc/loadavg, /proc/meminfo on Linux)
- [x] **FileSkipper** (skips heavy scanned PDFs when system overloaded)
- [x] Duplicate file detection by content hash (prevents re-processing same files)
- [x] Cost estimation (file size + scanned pages + estimated OCR time)

### Evaluation Engine
- [x] Fuzzy matching with rapidfuzz
- [x] Equipment tag extraction validation
- [x] Critical keyword validation
- [x] Spelling normalization (vaccancy→vacancy, receptacl→receptacle)
- [x] Keyword overlap validation (prevents cross-matching on common suffixes)

### Infrastructure
- [x] Docker Compose deployment
- [x] FastAPI backend with health check
- [x] React frontend
- [x] CLI runner (run.py)
- [x] Comprehensive README.md
- [x] CANDIDATE_REVIEW_PACKET.md
- [x] PROJECT_REPORT.md (updated with correct numbers)

## Results Summary

| Project | Type | Coverage | Matched/Total | Extracted |
|---------|------|----------|---------------|-----------|
| TAKEOFF-28 | Sample | 64.5% | 78/121 | 225 |
| TAKEOFF-56 | Sample | 45.5% | 5/11 | 18 |
| TAKEOFF-50 (specs) | Sample | 57.1% | 4/7 | 28 |
| TAKEOFF-31 | Challenge | N/A | N/A | 3 |
| TAKEOFF-36 | Challenge | N/A | N/A | 48 |

**Note:** TAKEOFF-56 scanned PDF (`1465 Gap Kids (2007).pdf`, 28 pages scanned) was auto-skipped
due to critical system pressure (load 4.3x). This caused 6 missing millwork/door items.
With the scanned PDF, coverage would likely be ~60-70% (estimated from manual analysis).

**Total: 5 projects processed, ~326 items extracted**

## Known Limitations

1. **OCR on Scanned Floor Plans** (Critical)
   - Floor plan text is ~2-3mm high at 1:100 scale
   - Tesseract cannot reliably read text smaller than ~10px
   - Some TAKEOFF-50 pages take 25-30 minutes per page (Tesseract hangs)
   - Impact: 30-40% of items on scanned architectural drawings are missed

2. **Graphics-Based Items** (Critical)
   - Ductwork sizes, pipe sizes, conduit runs are drawn as lines/graphics
   - No text to extract
   - Impact: All ductwork items (6" Dia, 8"x8", etc.) are missed

3. **Coverage Ceiling** (Moderate)
   - Realistic ceiling: ~65% for text-rich projects
   - ~45% for scanned-heavy projects
   - Without vision API or manual review, cannot exceed this

## What Was Removed (Hardcoded Items)

- ❌ Project-specific item injection (exact expected output strings)
- ❌ Fixed finish code prefixes (was 20 specific codes: PNT-, CL-, LVT-)
- ❌ Fixed room number format (was 3-digit only)
- ❌ Fixed equipment prefixes (was RTU/AC/EF/VAV only)
- ❌ Fixed lighting tags (was single letter A-Z only)
- ❌ Fixed door descriptions with exact sizes
- ❌ Fixed millwork descriptions (Hook & Bench, Cash Backwrap)
- ❌ Unconditional General items injection (was injected for ALL projects)

## Next Steps (If Continuing)

- [ ] Vision API integration (GPT-4o) for floor plans
- [ ] Object detection for graphics-based items (YOLO/segmentation)
- [ ] GPU acceleration for OCR (Tesseract doesn't support GPU, need EasyOCR/PaddleOCR)
- [ ] Database storage for intermediate results (SQLite/DuckDB)
- [ ] Process remaining challenge projects (currently only 2 of 25 processed)
