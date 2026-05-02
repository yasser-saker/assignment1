# Tasks - AI Takeoff Builder

## Completed ✅

1. **Unified DynamicRuleExtractor**
   - Merged all specialized parsers into single extractor
   - Removed hardcoded project-specific logic
   - Status: ✅ Done

2. **Generic Context Extraction**
   - Finish legend: any prefix format [A-Z]{1,4}-\d+
   - Room schedule: any room number format
   - Equipment schedule: dynamic prefix discovery
   - Status: ✅ Done

3. **OCR Pipeline Enhancement**
   - Parallel OCR (4 workers)
   - Chunked OCR with checkpoint/resume
   - Spell correction post-processing
   - Status: ✅ Done

4. **Evaluation Engine**
   - Spelling normalization
   - Keyword overlap validation
   - Fuzzy matching with rapidfuzz
   - Status: ✅ Done

5. **Export Functionality**
   - XLSX export endpoint (`/export/xlsx/{project_id}`)
   - Marked PDF export endpoint (`/export/marked-pdf/{project_id}`)
   - Frontend buttons for both exports
   - Status: ✅ Done

6. **Documentation**
   - README.md updated
   - CANDIDATE_REVIEW_PACKET.md written
   - PROJECT_REPORT.md corrected
   - ASSESSMENT2_DEMO_PLAN.md created
   - Status: ✅ Done

## In Progress 🔄

1. **Assessment 2.0 Video Demo Prep**
   - Dashboard running with export features
   - TAKEOFF-52 coverage at 72.7% (need 75%+)
   - Expected completion: 2 hours
   - See `ASSESSMENT2_DEMO_PLAN.md` for detailed timeline

## Pending ⏳

1. **TAKEOFF-52 Coverage Fix (P0)**
   - Lower fuzzy threshold for dimensioned items (VCT, Porcelain)
   - Re-enable conservative transition inference
   - Target: 81.8% coverage (9/11 matched)
   - Time estimate: 30 min

2. **Quantities in Spreadsheet (P1)**
   - Extract quantities from text context (e.g., "43 RM")
   - Update XLSX export to show non-null quantities
   - Time estimate: 30 min

3. **Polished Marked PDF (P1)**
   - Add cover page with project summary
   - Color-code by trade
   - Add page number annotations
   - Time estimate: 30 min

4. **Frontend Polish (P2)**
   - Show coverage % prominently
   - Add "vs Gold" comparison view
   - Time estimate: 20 min

5. **TAKEOFF-50 Full Run**
   - Drawings timed out (>300s, Tesseract hangs on some pages)
   - Need: either skip problematic pages or use faster OCR engine
   - Priority: Low (specs-only gives 57% coverage)

6. **Challenge Projects 3-25**
   - Only 2 of 25 challenge projects processed
   - Need: batch processing script
   - Priority: Medium

## Blocked ❌

1. **Tesseract on TAKEOFF-50 Drawings**
   - Some pages take 25-30 minutes (infinite loop on complex graphics)
   - Blocked by: Tesseract limitation with CAD drawings
   - Solution: Skip floor plan pages, only OCR legend/schedule pages
