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

*Add new lessons at the top as they are discovered during development.*
