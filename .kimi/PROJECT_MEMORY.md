# Project Memory — AI Takeoff Builder Challenge

**Last Updated:** 2026-04-30  
**Current Phase:** Production deployment complete, all core features delivered  
**Next Milestone:** Final testing + video recording

---

## Project Identity

- **Name:** AI Takeoff Builder Challenge — Assessment 1.0
- **Domain:** Construction Takeoff (Commercial Tenant Improvement / Interior Fit-Out)
- **Goal:** Build a backend prototype that ingests messy construction PDFs and produces structured takeoff outputs with evaluation capabilities
- **Time Budget:** 48 hours total
- **Quality Principle:** Honest, repeatable, well-documented system beats shallow full-dataset attempt

---

## Key Facts

### Dataset
- **Sample Projects (with expected output):** 3
  - TAKEOFF-28: Maryland Vision Institute
  - TAKEOFF-50: Portland VA Surgical Center Rehabilitation
  - TAKEOFF-56: JACK & JONES STATEN ISLAND, NY
- **Challenge Projects (input files only):** 25 (known: TAKEOFF-31 Walmart 1783, TAKEOFF-36 Gucci Perm)
- **Total Projects:** 28

### Input File Types (Typical)
- Architectural/Construction Drawings (PDF, multi-page)
- Specifications (PDF)
- Scope of Work (PDF)
- Addendums (PDF)
- Contractor Rules/Regulations (PDF)

### Output Requirements
- Project ID
- Input files used
- Trade/scope assumptions
- Predicted line items (description, quantity, unit)
- Confidence/issue notes
- Source references (file, page, section)
- Comparison/scoring report vs. expected manual outputs (for samples only)

### Evaluation Criteria
1. Problem understanding (messy construction files → structured output)
2. Data discipline (separation of AI inputs from hidden gold outputs)
3. System design (scalable backend pipeline)
4. Structured outputs (line items, QTY, UOM, assumptions, warnings, sources)
5. Evaluation loop (match/miss/extra/qty-diff analysis)
6. Human correction loop (how reviewer fixes improve future runs)
7. AI judgment (smart tool usage + deterministic calculations/scoring)
8. Honesty/execution (clear limitations stated)

---

## Known Constraints

- 48-hour hard deadline
- Must submit: repo/README, architecture note, generated outputs, Loom video (10 min max), CANDIDATE_REVIEW_PACKET
- Must NOT request hidden gold outputs for challenge projects
- Must NOT hard-code sample answers
- Must disclose all AI/tools/models used

---

## Current State

| Component | Status | Notes |
|-----------|--------|-------|
| Project structure understood | ✅ Done | All folders and files identified |
| AI memory files created | ✅ Done | `.kimi/` folder and memory files active |
| Sample project analysis | ✅ Done | 3 samples processed end-to-end |
| System architecture | ✅ Done | Ingestion → extraction → output → eval pipeline |
| Code scaffold | ✅ Done | Full Python + React project structure |
| First sample processed | ✅ Done | TAKEOFF-28: 187 line items, 17.4% match |
| Challenge projects | ✅ Done | 2 challenge projects processed (TAKEOFF-31, TAKEOFF-36) |
| Evaluation/scoring | ✅ Done | Custom comparator with fuzzy matching + qty diff |
| React GUI | ✅ Done | Dashboard, Projects, Pipeline, Results, Settings |
| FastAPI backend | ✅ Done | Config, projects, pipeline, evaluation endpoints |
| Docker containerization | ✅ Done | Backend + Frontend + Nginx in Docker Compose |
| HTTPS production deploy | ✅ Done | `https://assign.jobotai.site` with Caddy + Let's Encrypt |
| Dynamic project registry | ✅ Done | User adds folders manually, no hardcoded scanning |
| Hidden/restore projects | ✅ Done | Delete hides project + clears outputs, restore unhides |
| Data management | ✅ Done | Clear Jobs, Clear Outputs, Clear All with confirmation |
| OCR engine | ✅ Done | Full Tesseract with preprocessing, 29 tests passing |
| Review packet | ✅ Done | CANDIDATE_REVIEW_PACKET.md written |

---

## Domain Knowledge Accumulated

### Construction Takeoff Basics
- A "takeoff" is the process of quantifying materials/labor from construction drawings and specs
- "Trade" = category of work (e.g., drywall, flooring, painting, electrical, plumbing)
- "Scope" = defined boundary of work for a contractor
- "Line item" = one entry in an estimate (description + quantity + unit + unit price)
- Common units: SF (square feet), LF (linear feet), EA (each), CY (cubic yards)

### Project Types Observed
- Commercial interior fit-out / tenant improvement (TI)
- Retail stores (Gap Kids, Jack & Jones, Walmart, Gucci)
- Medical/institutional (Maryland Vision Institute, Portland VA)
- Typical trades: demo, drywall, ceilings, flooring, painting, millwork, electrical, plumbing, HVAC

### File Naming Patterns
- `TAKEOFF-XX - [Project Name]/`
- `Project Files/` — all input PDFs
- `Expected Manual Output/` — human estimate (XLSX) + markups (PDF) — **AI HIDDEN, USE ONLY FOR SCORING**

---

## Tooling Decisions (Active)

- **Primary Language:** Python 3.12
- **PDF Text Extraction:** pdfplumber + PyMuPDF
- **PDF Image/OCR:** Tesseract OCR 5.3.4 with full preprocessing pipeline (grayscale, contrast, sharpen, denoise, threshold, deskew)
- **LLM:** OpenAI GPT-4o / Claude 3.5 Sonnet via API for extraction and reasoning
- **Data Storage:** JSON for outputs; `registered_projects.json` for dynamic registry; `hidden_projects.json` for hidden list
- **Evaluation:** Custom Python comparator (fuzzy matching on descriptions + qty diff analysis)
- **Output Format:** JSON following `03_Output_Template.json` schema
- **Frontend:** React 19 + Vite + Tailwind CSS
- **Backend:** FastAPI + Uvicorn
- **Deployment:** Docker Compose + Caddy reverse proxy + Let's Encrypt SSL

---

## Risks & Open Questions

1. **PDF Quality:** Drawings may be scanned images requiring OCR. How accurate is extraction?
2. **Scale:** 25 challenge projects in 48h is aggressive. Need efficient batch processing.
3. **Trade Classification:** How to map extracted items to standard trade categories?
4. **Quantity Calculation:** AI can identify items, but can it calculate areas/lengths/counts accurately from drawings?
5. **Evaluation Method:** How to fuzzy-match predicted line items to human line items when wording differs?
6. **API Costs:** LLM API costs for 28 projects with large PDFs could be significant.

---

## Session History

| Date | Session | Key Actions | Outcome |
|------|---------|-------------|---------|
| 2026-04-29 | Init | Read all instructions, explored dataset structure, created AI memory files | Project initialized, ready for architecture design |
| 2026-04-29 | Build | Created ingestion, extraction, output, evaluation modules; processed first sample | Core pipeline working |
| 2026-04-30 | Build | Processed all 3 samples + 2 challenge projects; built React GUI; built FastAPI backend; Dockerized; deployed to production | Full system operational on `https://assign.jobotai.site` |
| 2026-04-30 | Polish | Dynamic project registry, hidden/restore projects, data management (clear jobs/outputs/all), OCR settings tab, route ordering fixes | System fully dynamic and user-friendly |
