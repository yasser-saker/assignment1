# Assessment Scorecard — AI Takeoff Builder Challenge

**Date:** 2026-05-01  
**Evaluator:** Code Review vs. Notion Requirements  
**Overall Score:** **5.5 / 10**

---

## A. Scoring Against Notion Deliverables (1–10)

| # | Deliverable | Required | Actual State | Score | Notes |
|---|-------------|----------|--------------|-------|-------|
| 1 | **Architecture Plan** | Data model, pipeline, eval workflow, deterministic vs AI, risks | `docs/ARCHITECTURE.md` exists but thin (3.5 KB). Code structure shows clean separation (`ingestion/ → extraction/ → output/ → evaluation/`). | **6/10** | Architecture is visible in code more than in the doc. Missing formal data-model diagrams. |
| 2 | **Working Prototype** | Runnable, manifest, gold items, AI predictions, comparison reports, challenge outputs | `run.py` works as CLI. **Only 1 output file exists:** `outputs/TAKEOFF-50/prediction.json`. **Zero evaluation reports** in `outputs/`. Claims in `CANDIDATE_REVIEW_PACKET` about TAKEOFF-28, TAKEOFF-56, TAKEOFF-31, TAKEOFF-36 are **unverified** by files in repo. | **4/10** | The *code* is runnable; the *outputs* are severely lacking for minimum requirements (3 sample + 3–5 challenge). |
| 3 | **README** | Run instructions, tools/models, assumptions, auto vs manual, improvements, limitations | `README.md` is decent (~180 lines). Covers tools, dynamic design, limitations, run commands. Honest about OCR ceiling. | **7/10** | Good clarity. Minor issue: some paths don’t match actual folder structure on disk. |
| 4 | **Short Walkthrough (Video)** | Loom / screen recording, max 10 min | **Not present in repo** (expected external). Cannot evaluate from codebase. | **N/A** | External deliverable; not counted in repo score. |
| 5 | **30-Day Execution Plan** | Backend/evaluation/learning focus, weekly milestones | `docs/30_DAY_PLAN.md` exists with 4-week breakdown, success metrics, resource requirements. | **7/10** | Solid plan. Realistic about needing engineers + API budget. |
| 6 | **CANDIDATE_REVIEW_PACKET.md** | Mandatory: what built, how to run, projects processed, eval results, auto vs manual, tools, limitations, 30-day plan | Exists (~214 lines). Covers all required sections. **However**, claims about processed projects (5 projects, 1,242 items) are **not backed by output files** in the repo. | **6/10** | Well-structured and honest about limitations, but unsubstantiated output claims hurt credibility. |

**Deliverables Average (excluding Video):** **6.0 / 10**

---

## B. Scoring Against Evaluation Criteria (What They Grade On)

| Criterion | Score | Evidence |
|-----------|-------|----------|
| **1. Problem Understanding** | **7/10** | `DynamicRuleExtractor` (~1,106 lines) shows deep understanding of construction schedules, finish legends, equipment tags, and trade classification. `MechanicalParser` and `ElectricalParser` are domain-aware. |
| **2. Data Discipline** | **5/10** | Code *does* separate expected outputs (path guards in `run.py`). **BUT:** API keys are **hardcoded in `src/config.py`** (`OPENAI_API_KEY`, `KIMI_API_KEY`). This is a serious security/ops flaw that contradicts good data discipline. |
| **3. System Design** | **7/10** | Clean modular architecture: `ingestion/` → `extraction/` → `output/` → `evaluation/`. FastAPI backend + React frontend + Docker Compose. **BUT:** 52 one-off scripts at repo root (`extract_schedules.py`, `check_gap.py`, etc.) reveal messy development without consolidation. |
| **4. Structured Outputs** | **6/10** | Output format follows `03_Output_Template.json` schema (project_id, trade_scope, line_items with confidence/source). **BUT:** Only 1 prediction file exists; cannot verify consistency across project types. |
| **5. Evaluation Loop** | **7/10** | `evaluator.py` is genuinely sophisticated: multi-layer fuzzy matching (keyword overlap → equipment tags → critical keywords → length-appropriate ratio), spelling normalization, type validation (diffuser ≠ sink), quantity diff analysis. This is a strength. **BUT:** No `evaluation_report.json` files generated to prove it runs end-to-end. |
| **6. Human Correction Loop** | **3/10** | Mentioned in architecture docs and `CANDIDATE_REVIEW_PACKET`. **Not actually implemented** in code. No `corrections.json`, no review UI, no patch format. |
| **7. AI Judgment** | **6/10** | Smart hybrid approach (rule-based + LLM post-filter + Vision fallback). Good prompt design with JSON mode. **BUT:** Hardcoded API keys show poor judgment. Over-claiming in `.kimi/` files (e.g., "80.2% coverage", "169 items", "production deployed") vs. actual repo state (1 output file) suggests hype over rigor. |
| **8. Honesty / Execution** | **5/10** | `CANDIDATE_REVIEW_PACKET` and `README` are honest about OCR limits and coverage ceiling. **BUT:** `.kimi/PROJECT_MEMORY.md`, `.kimi/PROGRESS.md`, and `PROJECT_REPORT.md` contain **inflated/aspirational claims** (e.g., "TAKEOFF-28: 125 items, 80.2%", "TAKEOFF-36: 57 items", "HTTPS production deploy complete") that are **not reproducible** from the repository. This undermines trust. |

**Criteria Average:** **46 / 80 = 5.75 / 10**

---

## C. Power Points (Strengths)

1. **Real Extraction Engine** — `DynamicRuleExtractor` (~1,100 lines) with generic schedule detection, overlapping-section removal, and trade classification. Not a mock.
2. **Sophisticated Evaluator** — `evaluator.py` implements a genuine 4-layer matching algorithm (keyword overlap → equipment tags → critical keywords → length-appropriate fuzzy ratio) with type-mismatch penalties. This is engineering depth.
3. **OCR Pipeline** — `OCREngine` has a real 6-step preprocessing pipeline (grayscale → DPI rescaling → contrast → sharpen → median filter → adaptive thresholding) plus deskewing via projection-profile angle search.
4. **Modular Codebase** — `src/ingestion/`, `src/extraction/`, `src/output/`, `src/evaluation/` separation is correct and scalable.
5. **Full-Stack GUI** — FastAPI backend with CORS + React frontend with 5 routed pages (Dashboard, Projects, Pipeline, Results, Settings). It exists and is wired.
6. **Docker & Tests** — `docker-compose.yml`, `Dockerfile.backend`, `Dockerfile.frontend`, plus 3 `pytest` test files (`test_ocr_engine.py`, `test_pdf_extractor.py`, `test_ingestion_pipeline.py`).
7. **Honest Limitations** — README and Review Packet clearly state OCR ceiling (~65%), graphics-only items, and time constraints. No false claims of "magic AI."

---

## D. Weak Points (Critical Issues)

1. **Missing Outputs (Minimum Requirements Not Met)**
   - Notion requires: **3 sample projects + 3–5 challenge projects** with generated outputs.
   - Repo contains: **1 prediction file** (`outputs/TAKEOFF-50/prediction.json`).
   - No `evaluation_report.json` for any sample project.
   - **This is the single biggest gap.** The code may work, but the deliverables are incomplete.

2. **Hardcoded Secrets**
   - `src/config.py` lines 15–17 contain plaintext `OPENAI_API_KEY` and `KIMI_API_KEY`.
   - This is a **security failure** and shows poor engineering judgment.

3. **Messy Root Directory**
   - 52 one-off Python scripts at root (`extract_specs.py`, `check_gap.py`, `test_matching5.py`, etc.) that should have been consolidated into `src/` or deleted.
   - Makes the repo look like a scratchpad, not a production-ready prototype.

4. **Inflated Internal Docs**
   - `.kimi/PROJECT_MEMORY.md` claims: "TAKEOFF-28: 125 line items, 80.2% coverage", "TAKEOFF-50: 169 items", "Production deployment complete".
   - These claims are **not reproducible** from the repo files. They appear aspirational or from a different branch/state.

5. **Unimplemented Correction Loop**
   - Notion explicitly asks for a human review/correction loop.
   - The repo mentions it in docs but has **zero code** for capturing corrections or JSON patches.

6. **Frontend Not Pre-Built**
   - `frontend/dist/` is empty or missing; a user must run `npm install && npm run build`.
   - For a "working prototype," the built artifacts should be present or the build must be one-command.

---

## E. Final Verdict

### Overall Score: **5.5 / 10**

### Why 5.5?
- **Code quality & architecture:** 7/10 (solid modular design, real algorithms)
- **Deliverable completeness:** 4/10 (missing outputs, missing evaluation reports, missing challenge results)
- **Professional rigor:** 5/10 (hardcoded secrets, messy root, inflated docs)

### What would raise it to 7–8/10:
1. Add the **missing output files** (regenerate predictions + evaluations for all 3 samples + 3–5 challenges and commit them to `outputs/`).
2. **Remove hardcoded API keys** immediately; use `.env` + `python-dotenv`.
3. **Clean root directory:** delete or move the 52 one-off scripts into `scripts/` or `notebooks/`.
4. **Generate evaluation reports** and commit them so reviewers can see match/miss/extra breakdowns.
5. **Build the frontend** and include `frontend/dist/` or ensure `docker compose up --build` works without manual `npm install`.

### Bottom Line
The **engineering bones are good** — the evaluator, the OCR pipeline, and the rule-based extractor show real backend capability. But the **submission is incomplete** relative to the minimum requirements, and the repo cleanliness/security issues distract from the genuine technical work underneath.
