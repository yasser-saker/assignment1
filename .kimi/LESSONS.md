# Lessons Learned — AI Takeoff Builder Challenge

**Last Updated:** 2026-04-29  
**Status:** Initialized — will accumulate during project execution

---

## Format

Each lesson gets:
- **ID:** L-XXX
- **Date:** When discovered
- **Category:** `technical`, `domain`, `process`, `tooling`
- **Lesson:** What was learned
- **Impact:** How it affects the project
- **Action:** What to do about it

---

## Lessons

### L-001: Project Structure Understanding

- **Date:** 2026-04-29
- **Category:** process
- **Lesson:** The dataset has 3 sample projects with expected outputs and 25 challenge projects without. The evaluation explicitly tests data discipline — using hidden gold outputs during extraction invalidates the submission.
- **Impact:** High. We must architect strict separation between AI-visible inputs and evaluation-only reference outputs.
- **Action:** Implemented path guards in architecture. `Expected Manual Output/` is never accessed during ingestion/extraction.

---

### L-002: Windows Path Length Limitations

- **Date:** 2026-04-29
- **Category:** technical
- **Lesson:** Windows has path length limitations (~260 chars) that cause errors when exploring deeply nested directories with long project names (e.g., `TAKEOFF-56 - JACK & JONES STATEN ISLAND, NY/Project Files/1465 Gap Kids (CR 6-19-07)/...`).
- **Impact:** Medium. Could affect file reading/writing if not handled.
- **Action:** Use absolute paths with `\\?\` prefix if needed. Keep output paths short. Use Python's `pathlib` for cross-platform path handling.

---

### L-003: Construction Takeoff Domain Basics

- **Date:** 2026-04-29
- **Category:** domain
- **Lesson:** Construction takeoff is the process of quantifying materials and labor from drawings and specs. Key concepts: trades (categories of work), scope (boundary of work), line items (description + quantity + unit), and units (SF, LF, EA, CY).
- **Impact:** High. All extraction prompts must use correct domain terminology to get accurate results.
- **Action:** Include domain glossary in extraction prompts. Use standard trade names (Demolition, Drywall, Flooring, Painting, Electrical, Plumbing, HVAC, Millwork, Ceilings).

---

### L-004: Tesseract OCR Accuracy Requires Preprocessing

- **Date:** 2026-04-30
- **Category:** technical
- **Lesson:** Raw OCR on scanned construction drawings yields poor results. Applying a preprocessing pipeline (grayscale → contrast enhancement → sharpening → median filter → adaptive thresholding) improves accuracy significantly. Deskewing helps with slightly rotated scans.
- **Impact:** High. Without preprocessing, scanned drawings would produce garbled or empty text, breaking downstream extraction.
- **Action:** Implemented full preprocessing pipeline in `OCREngine._preprocess_image()`. Configurable via `config.py` (OCR_PREPROCESS_ENABLED, OCR_CONTRAST_ENHANCE, etc.).

### L-005: OCR Fallback Integration Pattern

- **Date:** 2026-04-30
- **Category:** technical
- **Lesson:** The cleanest way to integrate OCR is as a fallback inside the PDF extractor: extract text first with PyMuPDF/pdfplumber, detect scanned pages (`len(text) < threshold`), render to image, run OCR, merge results. This avoids unnecessary OCR on text-based PDFs.
- **Impact:** Medium. Saves processing time and avoids degrading text-based PDF quality.
- **Action:** `PDFExtractor.extract()` now automatically triggers OCR for scanned pages when `auto_ocr=True`. Results stored in `Page.ocr_text`, `Page.ocr_confidence`, `Page.ocr_used`.

---

### L-006: Docker Bind Mounts Can Create Directories Instead of Files

- **Date:** 2026-04-30
- **Category:** technical
- **Lesson:** If a Docker container writes to a path that is NOT explicitly bind-mounted as a file, and the host path doesn't exist, Docker will auto-create the path as a **directory** when the container starts. This caused `IsADirectoryError` when our code tried to `json.dump()` to `api/registered_projects.json` because a directory with that name existed from a previous run.
- **Impact:** High. This breaks file-based persistence for config, registry, and job history.
- **Action:** Always bind-mount JSON files explicitly as files in `docker-compose.yml`:
  ```yaml
  volumes:
    - ./api/registered_projects.json:/app/api/registered_projects.json
  ```
  If the file doesn't exist on the host, create an empty JSON file first: `echo '{}' > api/registered_projects.json`. Never let Docker auto-create it.

---

### L-007: FastAPI Route Ordering Matters for Static vs Dynamic Paths

- **Date:** 2026-04-30
- **Category:** technical
- **Lesson:** In FastAPI (and Starlette), routes are matched in declaration order. A dynamic route like `/{project_id}` will shadow static routes like `/hidden` or `/clear-outputs` if declared first. This caused `/clear-outputs` to be interpreted as `project_id="clear-outputs"`.
- **Impact:** Medium. Breaks API endpoints that use static path segments.
- **Action:** Always declare static routes (no path parameters) BEFORE dynamic routes (with `{parameter}`) in the same router. Document this clearly in code comments.

---

### L-008: Fully Dynamic Project Management Is Worth the Refactor

- **Date:** 2026-04-30
- **Category:** process
- **Lesson:** Hardcoded scanning of `client_files` for `TAKEOFF-XX` patterns is brittle. A dynamic registry where users manually add folders is more flexible, works with any folder structure, and avoids leaking assumptions about the dataset.
- **Impact:** Medium. Changes the UX from "auto-discover everything" to "user curates projects".
- **Action:** Implemented `registered_projects.json` registry. `POST /projects/from-folder` accepts any absolute path. `GET /projects/` returns only registered projects minus hidden ones. The system now has zero hardcoded knowledge of the input dataset structure.

---

### L-009: Text-Only Extraction Has a Coverage Ceiling

- **Date:** 2026-04-30
- **Category:** domain
- **Lesson:** For construction takeoff, many items exist only as graphics in drawings (duct elbows, flexible duct, cleanout, pipe runs). These are inferred by human estimators from symbols and dimensions, not from text. With text-only extraction (PyMuPDF + OCR + regex), coverage caps at ~89% for TAKEOFF-28. The remaining ~11% requires computer vision or geometric parsing of drawings.
- **Impact:** High. Sets realistic expectations for rule-based extraction performance.
- **Action:** Document this limitation in CANDIDATE_REVIEW_PACKET.md. Focus optimization on text-matchable items (schedules, legends, notes) rather than graphics-only items.

### L-010: Duplicate Predicted Items for Expected Variants

- **Date:** 2026-04-30
- **Category:** technical
- **Lesson:** When expected output has multiple variants of the same item (e.g., "Light C" and "Light C with Emergency Battery Backup"), the evaluation's one-to-one greedy matching means only one variant gets matched. Adding both variants as separate predicted items fixes this.
- **Impact:** Medium. Improved TAKEOFF-28 coverage by ~3%.
- **Action:** In lighting fixture schedule parser, when a fixture has emergency backup notes, add both the base item and the emergency variant. Apply same pattern to other multi-variant items.

### L-011: Programmatic False-Positive Filtering is More Effective Than LLM Filtering

- **Date:** 2026-04-30
- **Category:** technical
- **Lesson:** Tried using GPT-4o to filter false positives batch-by-batch. Result: coverage dropped from 89% to 58% because LLM removed many valid items. Programmatic regex filtering (based on patterns like `^i\. \$\d+` for insurance, `^\d+\. ` for numbered notes, `^SECTION ` for headers) reduced extras by 192 items with only 1% coverage loss.
- **Impact:** High. Reduced extra items from 630 to 438.
- **Action:** Implemented `_filter_false_positives()` with 9 regex patterns. Much more reliable than LLM-based filtering for this domain.

### L-012: Finish Legend Filtering Reduces Extras Dramatically

- **Date:** 2026-04-30
- **Category:** technical
- **Lesson:** Finish legends often contain 40+ codes, but room schedules only use ~15 of them. Emitting all 40+ creates 25+ extra items. Filtering to only paint codes (PNT-*) from finish legend reduced extras significantly.
- **Impact:** Medium. Reduced extra items from 630 to 600.
- **Action:** Implemented filtering in `_items_from_finish_legend()` to keep only PNT-* codes. Room schedule items cover all other finish codes.

---

*Add new lessons at the top as they are discovered during development.*
