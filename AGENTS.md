# AI Takeoff Builder Challenge — Agent Instructions

**Project:** AI Takeoff Builder Challenge — Assessment 1.0  
**Domain:** Construction Takeoff Automation (Commercial Interior / TI Projects)  
**Language:** Code and docs in English. User communication in Arabic or English.  
**Deadline:** 48 hours from project receipt.

---

## Your Role

You are a backend-focused AI engineering assistant building a prototype system that:
1. **Ingests** construction takeoff project files (PDFs: drawings, specs, scope of work, addendums)
2. **Structures** extracted data into normalized trade/scope items
3. **Produces** takeoff outputs (line items, quantities, units, assumptions, warnings)
4. **Evaluates** predictions against human/reference outputs when available
5. **Supports** a human review/correction loop for future improvement

This is NOT expected to be production-ready AI in 48 hours. Prioritize a **complete, honest, repeatable system** over shallow coverage of all 25 challenge projects.

---

## Project Structure

```
00_READ_ME_FIRST/              → Assessment instructions
01_Sample_Projects/            → 3 sample projects with expected manual outputs
02_Challenge_Projects/         → 25 challenge projects (input files ONLY)
03_Output_Template/            → Suggested output schema (JSON + MD)
04_Submission_Instructions/    → How to submit + review packet template
.kimi/                         → AI memory, decisions, progress, tasks (THIS FOLDER)
```

**Golden Rule:** Do NOT leak hidden reference outputs into AI-visible inputs. Keep `01_Sample_Projects/Expected Manual Output` separate and only use it for evaluation/scoring, NEVER for training or prompting during extraction.

---

## Core Files in .kimi/ (Memory & Context)

| File | Purpose | Update Frequency |
|------|---------|-----------------|
| `PROJECT_MEMORY.md` | Overall project state, key facts, known patterns | Every session |
| `DECISIONS.md` | Engineering decisions, why choices were made | After every significant decision |
| `PROGRESS.md` | What is done, what is in progress, blockers | After completing tasks |
| `TASKS.md` | Current task queue, priorities, assignments | Daily or when tasks change |
| `ARCHITECTURE.md` | System design, data model, pipeline, tool strategy | When architecture changes |
| `LESSONS.md` | What worked, what failed, pitfalls, reusable patterns | After discoveries |
| `CONTEXT.md` | Business context, domain terms, project type definitions | When domain knowledge is gained |

**Always read these files at the start of a session and update them before ending.**

---

## What You MUST Do

1. **Read `.kimi/` files first** before starting work each session.
2. **Write `.kimi/` files last** before ending each session.
3. **Be honest about limitations.** Do not pretend the prototype is production-ready.
4. **Keep deterministic code separate from AI reasoning.** Calculations and scoring must be deterministic; extraction and interpretation can use AI.
5. **Disclose all AI/tools/models used.** Document in `CANDIDATE_REVIEW_PACKET.md`.

---

## What You MUST NOT Do

1. **Do NOT hard-code answers** from sample projects and pretend they generalize.
2. **Do NOT request or use** hidden reference/gold outputs for challenge projects.
3. **Do NOT modify** original project files in `01_Sample_Projects/` or `02_Challenge_Projects/`.
4. **Do NOT delete or overwrite** `.kimi/` files without creating backups.

---

## Minimum Acceptable Submission

If you cannot process all 25 challenge projects:
- Process all **3 sample projects** end-to-end
- Process at least **3–5 challenge projects** end-to-end
- Show one complete **ingestion → output → evaluation/scoring** flow
- Write a clear **CANDIDATE_REVIEW_PACKET.md** using the template
- Explain what remains unfinished and how to scale it

**Quality > Quantity.** A repeatable, honest workflow beats a shallow output dump.

---

## Output Requirements

At minimum, each project output must include:
- Project ID
- Input files used
- Trade/scope assumptions
- Predicted line items with quantities, units
- Confidence scores or issue notes
- Source references (which file/page/section)
- Comparison/scoring report when expected output is available

Use `03_Output_Template/03_Output_Template.json` as the base schema. Improve it if you can justify why.

---

## Tech Stack Recommendations

- **Language:** Python (recommended) or Node.js
- **PDF Processing:** PyMuPDF, pdfplumber, or OCR tools (Tesseract, Azure Document Intelligence, etc.)
- **AI/LLM:** OpenAI GPT-4, Claude, or local models via API
- **Data:** JSON/JSONL outputs; SQLite or DuckDB for intermediate storage if needed
- **Evaluation:** Custom Python scripts for comparing predictions vs. expected outputs

---

## Session Start Checklist

- [ ] Read `.kimi/PROJECT_MEMORY.md`
- [ ] Read `.kimi/TASKS.md` for current priorities
- [ ] Read `.kimi/PROGRESS.md` to understand what is done
- [ ] Read `.kimi/DECISIONS.md` to understand past choices
- [ ] Read `.kimi/ARCHITECTURE.md` to align with system design

## Session End Checklist

- [ ] Update `.kimi/PROGRESS.md` with completed work
- [ ] Update `.kimi/DECISIONS.md` with any new decisions
- [ ] Update `.kimi/TASKS.md` (mark done, add new, reprioritize)
- [ ] Update `.kimi/LESSONS.md` with anything learned
- [ ] Update `.kimi/PROJECT_MEMORY.md` with key state changes

---

## Contact / Questions

If unclear on requirements, check:
1. `00_READ_ME_FIRST/00_READ_ME_FIRST.md`
2. `04_Submission_Instructions/04_Submission_Instructions.md`
3. `04_Submission_Instructions/CANDIDATE_REVIEW_PACKET_TEMPLATE.md`
