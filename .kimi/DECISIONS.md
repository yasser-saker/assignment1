# Decision Log — AI Takeoff Builder Challenge

**Format:** Each decision gets an ID (DEC-XXX), date, context, decision, rationale, and status (Active / Reversed / Superseded).

---

## DEC-011: React + FastAPI GUI

- **Date:** 2026-04-30
- **Context:** Need a user-friendly interface to control the system, manage config, run pipeline, and view results
- **Decision:** Build React frontend (Vite) + FastAPI backend wrapping existing Python code
- **Rationale:** React is modern and fast with rich component ecosystem. FastAPI integrates seamlessly with existing Python backend. CORS allows separate frontend/backend during development.
- **Status:** Active

**GUI Architecture:**
```
React Frontend (Port 5173/4173)
  ├── Dashboard (stats, overview)
  ├── Projects (list, filter, view details)
  ├── Pipeline (run extraction, custom scripts)
  ├── Results (view outputs, evaluation reports)
  └── Settings (LLM config, paths, thresholds)
         ↑↓ (REST API + CORS)
FastAPI Backend (Port 8000)
  ├── /config (dynamic settings manager via JSON file)
  ├── /projects (scan client_files directories)
  ├── /pipeline (run scripts, track status, logs)
  └── /health
         ↑↓
Existing Python Backend
```

---

## DEC-001: AI Memory File Structure

- **Date:** 2026-04-29
- **Context:** Need to maintain consistency across AI sessions for a complex 48-hour project
- **Decision:** Create `.kimi/` folder with 7 memory files (PROJECT_MEMORY, DECISIONS, PROGRESS, TASKS, ARCHITECTURE, LESSONS, CONTEXT) plus root AGENTS.md
- **Rationale:** Separated concerns allow focused updates; AGENTS.md provides session start/end protocols; .kimi/ files are deep context
- **Status:** Active

---

## DEC-002: Primary Programming Language

- **Date:** 2026-04-29
- **Context:** Need to choose between Python and Node.js for backend pipeline
- **Decision:** Use Python 3.11+
- **Rationale:** Rich ecosystem for PDF processing (pdfplumber, PyMuPDF), data science (pandas, numpy), and LLM integration (openai, anthropic SDKs). Better for numerical quantity calculations.
- **Status:** Active (Tentative — can revisit if strong Node.js advantage emerges)

---

## DEC-003: PDF Extraction Strategy

- **Date:** 2026-04-29
- **Context:** Input files are construction PDFs (drawings, specs, SOW). Some may be scanned images.
- **Decision:** Two-tier approach: (1) pdfplumber/PyMuPDF for text-based PDFs, (2) OCR (Tesseract or cloud API) for scanned/image-based PDFs
- **Rationale:** Text-based extraction is faster and cheaper. OCR is fallback for scanned drawings. Need to detect which method per file.
- **Status:** Active (Tentative — will validate on first sample project)

---

## DEC-004: LLM Usage Strategy

- **Date:** 2026-04-29
- **Context:** Need AI for interpreting construction content and extracting structured data
- **Decision:** Use LLM API (OpenAI GPT-4o or Claude 3.5 Sonnet) for extraction and reasoning; keep all calculations and scoring in deterministic Python code
- **Rationale:** LLMs excel at understanding messy, domain-specific text. Calculations and comparisons must be deterministic and auditable.
- **Status:** Active

---

## DEC-005: Output Schema

- **Date:** 2026-04-29
- **Context:** Assessment provides `03_Output_Template.json` as suggested structure
- **Decision:** Start with provided template, extend if needed with documented justification
- **Rationale:** Meeting the spec is priority; extensions only if they add clear value and are explained in review packet
- **Status:** Active

---

## DEC-006: Evaluation Approach

- **Date:** 2026-04-29
- **Context:** Need to compare AI predictions against human expected outputs for sample projects
- **Decision:** Build custom Python comparator with: (a) fuzzy string matching on line item descriptions, (b) quantity difference analysis, (c) classification into matched/missing/extra
- **Rationale:** Simple exact matching will fail due to wording differences. Fuzzy matching (e.g., rapidfuzz) handles description variations. Quantity diff shows accuracy.
- **Status:** Active (Tentative — design detailed after first sample analysis)

---

## DEC-007: Data Discipline — Gold Output Separation

- **Date:** 2026-04-29
- **Context:** Assessment explicitly tests whether AI inputs leak from hidden reference outputs
- **Decision:** Strict separation: `01_Sample_Projects/*/Expected Manual Output/` is NEVER read during ingestion/extraction. It is ONLY read during the evaluation/scoring phase after predictions are generated.
- **Rationale:** This is an explicit evaluation criterion. Violating it invalidates the submission.
- **Status:** Active

---

## DEC-008: Project Processing Priority

- **Date:** 2026-04-29
- **Context:** 48 hours, 28 projects. Cannot do all with high quality.
- **Decision:** Process ALL 3 sample projects first (to build and validate pipeline), then process 3–5 challenge projects minimum. If time allows, process more.
- **Rationale:** Sample projects have expected outputs, allowing us to build and tune the evaluation loop. Challenge projects test generalization. Quality of system matters more than quantity of outputs.
- **Status:** Active

---

## DEC-009: Repository Structure

- **Date:** 2026-04-29
- **Context:** Need organized codebase for submission
- **Decision:** Create top-level project structure:
  ```
  /src/              → Python source code
  /src/ingestion/    → PDF extraction modules
  /src/extraction/   → LLM prompting and output generation
  /src/evaluation/   → Comparison and scoring
  /src/pipeline/     → Orchestration / main runner
  /api/              → FastAPI backend for GUI
  /frontend/         → React GUI
  /outputs/          → Generated outputs (gitignored or committed)
  /data/             → Symlinks or references to project files (read-only)
  /tests/            → Unit tests for deterministic components
  /docs/             → Architecture notes, 30-day plan
  README.md          → Run instructions
  requirements.txt   → Python dependencies
  ```
- **Rationale:** Clean separation of concerns, easy for reviewers to navigate, supports testing and documentation requirements.
- **Status:** Active

---

## DEC-010: Human Correction Loop Design

- **Date:** 2026-04-29
- **Context:** Assessment asks for a human review/correction loop concept
- **Decision:** Implement as a structured diff + correction format: reviewer sees prediction vs. expected (for samples) or reviews prediction directly (for challenges), submits corrections as JSON patch, system stores corrections for potential future fine-tuning or prompt improvement.
- **Rationale:** Full active learning in 48h is unrealistic. A structured correction capture mechanism demonstrates the concept and shows how it would improve future runs.
- **Status:** Active (Tentative — will refine after first evaluation)

---

*End of decision log. Add new decisions at the top with the next DEC-XXX ID.*
