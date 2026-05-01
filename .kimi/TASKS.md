# Task Queue — AI Takeoff Builder Challenge

**Last Updated:** 2026-04-30

## Completed
- ✅ Create project scaffold (folders, __init__.py)
- ✅ Create requirements.txt
- ✅ Create config.py
- ✅ Create models.py (Pydantic)
- ✅ Create ingestion module (extractor, OCR, classifier)
- ✅ Create extraction module (LLM client, prompts, engine)
- ✅ Create output module (serializer)
- ✅ Create evaluation module (comparator, scoring)
- ✅ Create run.py
- ✅ Create README.md
- ✅ React GUI with 5 pages (Dashboard, Projects, Pipeline, Results, Settings)
- ✅ FastAPI backend for GUI
- ✅ Dynamic config manager with JSON persistence
- ✅ Pipeline runner with real-time progress tracking
- ✅ Jobs history with live logs
- ✅ Custom folder selection support
- ✅ Evaluation viewer with match rate, missing/extra items
- ✅ Script execution from GUI
- ✅ Full pytesseract OCR support with preprocessing pipeline
- ✅ Unified ingestion pipeline with automatic OCR fallback
- ✅ OCR statistics and reporting
- ✅ Comprehensive OCR tests (29 tests passing)
- ✅ Docker Compose full containerization (backend + frontend + nginx)
- ✅ Dockerfile.backend with Tesseract OCR
- ✅ Dockerfile.frontend with multi-stage Node.js → Nginx
- ✅ Nginx reverse proxy for /api → backend
- ✅ Docker healthchecks for both services
- ✅ HTTPS with Caddy reverse proxy (assign.jobotai.site)
- ✅ Let's Encrypt SSL auto-provisioned
- ✅ CORS updated for production domain
- ✅ Data Management panel in Dashboard (clear jobs, outputs, all)
- ✅ Confirmation modal before destructive actions
- ✅ Backend endpoints: POST /pipeline/clear-jobs, POST /projects/clear-outputs
- ✅ Project delete button with confirmation modal
- ✅ Fixed files_count to use recursive rglob (TAKEOFF-31 now shows 2 files)
- ✅ Changed project status from "Pending" to "No Output"
- ✅ Fixed delete error: client_files is read-only in Docker
- ✅ Hidden projects system: hide from list + delete outputs + delete jobs
- ✅ Restore hidden projects with one click
- ✅ Hidden projects section in Projects page
- ✅ Increased Dashboard jobs limit from 5 to 50
- ✅ Redesigned Settings with organized tabs (LLM, OCR, Pipeline, Evaluation, Output)
- ✅ Added OCR mode selector: Local Tesseract (default) vs Online Vision API
- ✅ Removed unnecessary fields from Settings (API keys hidden, paths auto-resolved)
- ✅ Added temperature slider, radio cards for OCR mode, cleaner layout
- ✅ Fixed restore bug: FastAPI route ordering conflict (/clear-outputs vs /{id}/delete)
- ✅ Added "Add Custom Project Folder" in Projects page
- ✅ Custom folder accepts any absolute path, scans recursively, adds to project list
- ✅ Dynamic project registry (`registered_projects.json`) replaces hardcoded scanning
- ✅ Fully dynamic system: no hardcoded `TAKEOFF-XX` or `client_files` knowledge
- ✅ Fixed `IsADirectoryError` on registry file path
- ✅ Registry persisted via Docker bind mount

## In Progress
- 🔄 Testing on real challenge projects

## Recently Completed
- ✅ Optimized RuleBasedExtractorV2 for TAKEOFF-28
  - Fixed VAV unit format matching (JCI/TSS)
  - Added electrical legend items extraction (switches, sensors, receptacles)
  - Added emergency lighting extraction (Lithonia, battery packs)
  - Added transformer voltage extraction (45kVA XFMR 480V-208/120V)
  - Added paint height extraction from room schedule (PNT-01 9'-0", 9'-6", 10'-0", 10'-6")
  - Added programmatic false-positive filtering (insurance clauses, numbered notes, section headers, blocking notes, etc.)
  - Reduced finish legend to paint codes only (PNT-*)
  - Reduced extras from 630 → 438 (-192 items)
  - Coverage: 88.4% (107/121 matched)
  - Missing 14 items: all graphics-only (duct elbows, flexible duct, cleanout, pipe) or inferred (management, transformer wiring)

## Next (Priority Order)
1. Process additional challenge projects if time allows
2. Final code cleanup and documentation
3. Record Loom video (10 min max)
4. Write CANDIDATE_REVIEW_PACKET.md

## GUI Features Delivered
| Feature | Status |
|---------|--------|
| Dashboard with stats & job history | ✅ |
| Project browser with search/filter | ✅ |
| Custom folder path selection | ✅ |
| Pipeline runner with stage tracking | ✅ |
| Real-time progress bar & live logs | ✅ |
| Jobs history with expandable details | ✅ |
| Results viewer with trade filtering | ✅ |
| Evaluation with match rate & diffs | ✅ |
| Settings panel for all config | ✅ |
| Custom script runner | ✅ |
