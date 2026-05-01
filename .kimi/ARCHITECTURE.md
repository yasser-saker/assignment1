# Architecture — AI Takeoff Builder Challenge

**Last Updated:** 2026-04-30  
**Status:** Production Deployed  
**Version:** 1.0

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AI Takeoff Builder Pipeline                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Input     │───→│ Ingestion   │───→│ Extraction  │───→│   Output    │  │
│  │   Files     │    │  Engine     │    │   Engine    │    │  Generator  │  │
│  │  (PDFs)     │    │             │    │   (LLM)     │    │             │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘  │
│         │                    │                    │                │        │
│         │                    │                    │                │        │
│         ▼                    ▼                    ▼                ▼        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │ 02_Challenge│    │ Raw Text +  │    │ Structured  │    │  JSON       │  │
│  │ 01_Sample   │    │  Images +   │    │ Line Items  │    │  Output     │  │
│  │             │    │  Metadata   │    │  + QTYs     │    │  per Project│  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘  │
│                                                                   │         │
│                              ┌────────────────────────────────────┘         │
│                              │                                               │
│                              ▼                                               │
│                    ┌─────────────────┐                                       │
│                    │  Evaluation &   │◄──────────────────────────────┐       │
│                    │    Scoring      │                               │       │
│                    │   (Samples)     │                               │       │
│                    └────────┬────────┘                               │       │
│                             │                                        │       │
│                             ▼                                        │       │
│                    ┌─────────────────┐                               │       │
│                    │ Human Review /  │───────────────────────────────┘       │
│                    │ Correction Loop   (feedback for future improvement)     │
│                    └─────────────────┘                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. Input Layer

**Dynamic Project Registry:**
- Projects are **user-added** via `POST /projects/from-folder` with any absolute folder path
- Registry stored in `api/registered_projects.json` (bind-mounted file in Docker)
- No hardcoded scanning of `client_files` or knowledge of `TAKEOFF-XX` naming
- Hidden projects tracked in `hidden_projects.json` (soft-delete, outputs/jobs cleared, source files preserved)
- Restore unhides project and re-adds it to the active list

**Source (Example paths after user adds them):**
- `/app/client_files/01_Sample_Projects_With_Expected_Output/.../TAKEOFF-28/Project Files/` (sample)
- `/app/client_files/02_Challenge_Projects_Project_Files_Only/.../TAKEOFF-31/Project Files/` (challenge)
- Any custom folder path the user provides

**File Types:**
- Construction drawings (multi-page PDF, may be vector or scanned)
- Specifications (text-based PDF)
- Scope of Work (text-based PDF)
- Addendums (text-based PDF)
- Contractor rules/regulations (text-based PDF)
- Breakout drawings (PDF)

**Data Discipline:**
- `Expected Manual Output/` is **NEVER** read during ingestion/extraction
- It is ONLY accessed by the Evaluation component after predictions are generated
- Enforced by directory structure and code (evaluation module checks path guards)

---

### 2. Ingestion Engine

**Responsibility:** Convert PDFs into AI-processable content.

**Modules:**

#### 2.1 PDF Text Extractor
- **Tool:** `pdfplumber` (tables + text) + `PyMuPDF` (fast text + metadata)
- **Output:** Structured text per page, with bounding boxes
- **Use for:** Specs, SOW, addendums, rules (text-based PDFs)

#### 2.2 PDF Image Extractor
- **Tool:** `PyMuPDF` to render pages as images
- **Output:** PNG/JPEG per page
- **Use for:** Construction drawings (may need visual interpretation)

#### 2.3 OCR Engine (Fallback)
- **Tool:** `pytesseract` (local) or cloud OCR (Azure Document Intelligence)
- **Trigger:** When page has <50 extractable text characters (scanned PDF detection)
- **Output:** OCR text with confidence scores

#### 2.4 File Classifier
- Automatically classify each input file:
  - `drawings` → may need OCR + visual analysis
  - `specifications` → text extraction
  - `scope_of_work` → text extraction
  - `addendum` → text extraction
  - `rules` → text extraction (may contain standard costs/rates)
  - `breakout` → text + potential table extraction

**Data Model (Intermediate):**
```python
class IngestedFile:
    file_id: str
    project_id: str
    file_name: str
    file_type: str  # drawing, spec, sow, addendum, rules, breakout, other
    pages: List[Page]
    extracted_at: datetime

class Page:
    page_number: int
    text: str
    has_images: bool
    ocr_used: bool
    ocr_confidence: Optional[float]
    tables: List[Table]

class Table:
    rows: List[List[str]]
    bounding_box: Tuple[float, float, float, float]
```

---

### 3. Extraction Engine (Hybrid: LLM + Vision + Rule-Based)

**Responsibility:** Convert ingested content into structured takeoff line items.

**Architecture (3-Layer Hybrid):**

#### 3.1 StructureClassifier (Local)
- Detects document structure using keyword matching
- Classifies chunks as: `schedule:diffuser`, `schedule:vav`, `spec:paint`, `drawing:plan`, `notes:general`
- Enables targeted LLM prompts per chunk type

#### 3.2 LLMExtractor (GPT-4o)
- Generic prompts that work for ANY project type (no hardcoded regex)
- Targeted prompts based on StructureClassifier output:
  - Schedules: "Extract all diffuser schedule items with tag, CFM, size, manufacturer"
  - Specs: "Extract all HVAC material and equipment items from specification text"
  - Plans: "Extract equipment tags, fixture types, material callouts"
- JSON mode output with `items` array

#### 3.3 VisionExtractor (GPT-4o Vision)
- For scanned drawings with <5000 chars of extractable text
- Converts pages to PNG (2x scale) and sends to vision model
- Extracts: equipment tags, duct sizes, pipe sizes, fixture counts, legend items
- Cost control: max 3 pages per important drawing file

#### 3.4 Rule-Based Fallback
- When LLM API is unavailable (no API key)
- Uses RuleBasedExtractorV2 with static parsers
- Works for TAKEOFF-28 only (project-specific regex)

#### 3.5 Smart Deduplication
- Trade normalization (ceiling→Ceilings, floor→Flooring)
- Fuzzy matching on normalized descriptions
- Subset detection (e.g., "VFD 1" vs "VFD 1-6")

**Results:**
- TAKEOFF-50: 4 → 169 items (42x improvement)
- TAKEOFF-36: 0 → 57 items
- TAKEOFF-31: 0 → 5 items

**Data Model (Output):**
```python
class LineItem:
    description: str
    trade: str
    quantity: Optional[float]
    unit: Optional[str]
    confidence: float  # 0.0 - 1.0
    source_reference: str
```

---

### 4. Output Generator

**Responsibility:** Serialize extraction results to required format.

**Format:** JSON following `03_Output_Template.json` schema

**Enhancements (if justified):**
- Add `project_metadata` section
- Add `processing_stats` (tokens used, processing time, files processed)
- Add `confidence_summary` (count by confidence level per trade)

**Output Path:**
```
outputs/
  TAKEOFF-28/
    prediction.json
    evaluation_report.json (if sample project)
  TAKEOFF-31/
    prediction.json
  ...
```

---

### 5. Evaluation & Scoring (Samples Only)

**Responsibility:** Compare predictions against human expected outputs.

**Input Guard:**
- Only runs for projects in `01_Sample_Projects/`
- Reads `Expected Manual Output/*.xlsx` and `*.pdf` ONLY after predictions are generated

**Comparison Pipeline:**

#### 5.1 Expected Output Ingestion
- Read Excel estimate file into DataFrame
- Extract: description, trade, quantity, unit
- Read PDF markups for additional context

#### 5.2 Fuzzy Matching
- Tool: `rapidfuzz` library (fuzz.ratio, fuzz.token_sort_ratio)
- Match predicted line items to expected line items by description similarity
- Threshold: 80% similarity for match (tunable)
- Fallback: match by trade + unit + approximate quantity

#### 5.3 Classification
For each predicted item:
- **Matched:** Found similar expected item → compare quantity difference
- **Extra:** No matching expected item → potential over-extraction
- **Missing:** Expected item has no predicted match → under-extraction

#### 5.4 Quantity Difference Analysis
- For matched items: `qty_diff = predicted_qty - expected_qty`
- `pct_diff = qty_diff / expected_qty * 100`
- Tolerance thresholds: ±5% (exact), ±10% (close), >10% (significant)

#### 5.5 Scoring Report
```python
class EvaluationReport:
    project_id: str
    matched_items: List[MatchedItem]
    missing_items: List[ExpectedItem]
    extra_items: List[PredictedItem]
    summary: SummaryStats

class SummaryStats:
    total_predicted: int
    total_expected: int
    matched_count: int
    missing_count: int
    extra_count: int
    match_rate: float  # matched / expected
    avg_qty_pct_diff: float
    significant_diffs: int
```

---

### 6. Human Review / Correction Loop

**Concept:** Capture reviewer corrections in a structured format for future improvement.

**Implementation (Prototype):**
- Generate a `corrections_template.json` per project
- Reviewer (human or AI) fills in:
  - Items to add (with source justification)
  - Items to remove (with reason)
  - Items to correct (new quantity/unit/description)
- Store corrections in `outputs/TAKEOFF-XX/corrections.json`

**Future Integration (30-day plan):**
- Use corrections to build fine-tuning dataset
- Improve prompts with common correction patterns
- Add rule-based post-processors for repeated errors

---

## Data Flow Diagram

```
PDF Files
   │
   ▼
┌────────────────────────────────────┐
│ INGESTION ENGINE                   │
│ • Classify file type               │
│ • Extract text (pdfplumber/PyMuPDF)│
│ • OCR fallback for scanned pages   │
│ • Extract tables                   │
└────────────────┬───────────────────┘
                 │
                 ▼ IngestedFile objects
┌────────────────────────────────────┐
│ STRUCTURE CLASSIFIER               │
│ • Detect schedules, specs, plans   │
│ • Classify chunks by type          │
└────────────────┬───────────────────┘
                 │
                 ▼ Classified chunks
       ┌─────────┴─────────┐
       ▼                   ▼
┌──────────────┐   ┌──────────────┐
│ LLM EXTRACTOR│   │VISION EXTRACT│
│ • Schedules  │   │ • Scanned    │
│ • Specs      │   │   drawings   │
│ • Text plans │   │ • Equipment  │
│ • Generic    │   │   tags/sizes │
└──────┬───────┘   └──────┬───────┘
       │                   │
       └─────────┬─────────┘
                 ▼
┌────────────────────────────────────┐
│ SMART DEDUPLICATION                │
│ • Trade normalization              │
│ • Fuzzy matching                   │
│ • Subset detection                 │
└────────────────┬───────────────────┘
                 │
                 ▼ Final line items
┌────────────────────────────────────┐
│ OUTPUT GENERATOR                   │
│ • Serialize to JSON                │
│ • Add metadata and stats           │
└────────────────┬───────────────────┘
                 │
                 ▼ prediction.json
┌────────────────────────────────────┐
│ EVALUATION (Samples Only)          │
│ • Read expected output             │
│ • Fuzzy match descriptions         │
│ • Classify matched/missing/extra   │
│ • Calculate quantity diffs         │
└────────────────┬───────────────────┘
                 │
                 ▼ evaluation_report.json
┌────────────────────────────────────┐
│ CORRECTION LOOP                    │
│ • Generate corrections template    │
│ • Capture reviewer feedback        │
└────────────────────────────────────┘
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | Python 3.12 | Primary implementation |
| PDF Text | pdfplumber, PyMuPDF | Text and table extraction |
| PDF OCR | pytesseract (local) | Scanned PDF fallback |
| LLM API | OpenAI GPT-4o | Text extraction and reasoning |
| Vision API | OpenAI GPT-4o Vision | Scanned drawing extraction |
| Rule-Based | Custom Python parsers | Fallback when LLM unavailable |
| Data Processing | pandas | Data manipulation |
| String Matching | rapidfuzz | Fuzzy matching for evaluation |
| Data Storage | JSON/JSONL | Outputs, registry, config |
| Testing | pytest | Unit tests for deterministic components |
| Frontend | React 19 + Vite + Tailwind CSS | User interface |
| Backend API | FastAPI + Uvicorn | REST API for GUI |
| Reverse Proxy | Nginx (Docker) + Caddy (Host) | API routing + SSL |
| Container | Docker Compose | Full stack orchestration |

---

## Frontend & API Layer

### React Frontend
- **Build Tool:** Vite (dev: 5173, preview: 4173, Docker: Nginx on 80)
- **Styling:** Tailwind CSS
- **Router:** React Router (HashRouter for SPA compatibility)
- **API Client:** Axios with relative base URL (`/api`)
- **Pages:**
  - **Dashboard:** Stats, API status, recent jobs, data management (clear jobs/outputs/all)
  - **Projects:** Dynamic registry management, add custom folders, hide/restore, filters
  - **Pipeline:** Run extraction with real-time progress, stage tracking, live logs
  - **Results:** View predictions, trade filtering, evaluation reports
  - **Settings:** Tabbed config (LLM, OCR, Pipeline, Evaluation, Output)

### FastAPI Backend
- **Entry:** `api/main.py` — CORS enabled for production domain
- **Routers:**
  - `/config` — Dynamic JSON config manager (load/save/reset)
  - `/projects` — Dynamic registry (list, add-from-folder, hide, restore, clear-outputs)
  - `/pipeline` — Run pipeline, custom scripts, get status, get logs
  - `/health` — Health check
- **Registry Files:**
  - `api/registered_projects.json` — User-added projects (bind-mounted as file)
  - `api/hidden_projects.json` — Hidden project IDs
  - `api/dynamic_config.json` — Runtime configuration
  - `api/jobs_history.json` — Pipeline job history
- **Route Ordering:** Static routes (`/`, `/hidden`, `/from-folder`, `/clear-outputs`) declared BEFORE dynamic routes (`/{project_id}`) to prevent FastAPI path shadowing

---

## Directory Structure

```
ai-takeoff-builder/
├── .kimi/                          → AI memory files
├── api/                            → FastAPI backend
│   ├── main.py                     → FastAPI app, CORS
│   ├── models.py                   → Pydantic request/response models
│   ├── config_manager.py           → Dynamic JSON config manager
│   ├── jobs_manager.py             → Pipeline job history
│   ├── dynamic_config.json         → Runtime configuration (bind-mounted)
│   ├── jobs_history.json           → Job records (bind-mounted)
│   ├── registered_projects.json    → Dynamic project registry (bind-mounted)
│   ├── hidden_projects.json        → Hidden project IDs
│   └── routers/
│       ├── config.py               → Config endpoints
│       ├── projects.py             → Project registry, hide/restore, clear
│       └── pipeline.py             → Pipeline runner, status, logs
├── frontend/                       → React GUI
│   ├── src/
│   │   ├── App.jsx                 → Router, layout
│   │   ├── api.js                  → Axios client
│   │   ├── main.jsx                → Entry point
│   │   └── components/
│   │       ├── Dashboard.jsx       → Stats, data management
│   │       ├── Projects.jsx        → Registry, add folders, hide/restore
│   │       ├── Pipeline.jsx        → Run pipeline, progress, logs
│   │       ├── Results.jsx         → View outputs, evaluation
│   │       ├── Settings.jsx        → Tabbed config editor
│   │       └── Layout.jsx          → Navigation
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── src/                            → Python pipeline modules
│   ├── __init__.py
│   ├── config.py                   → Configuration, paths, constants
│   ├── models.py                   → Pydantic/dataclass models
│   ├── ingestion/
│   │   ├── pdf_extractor.py        → pdfplumber/PyMuPDF wrapper
│   │   ├── ocr_engine.py           → Tesseract/cloud OCR
│   │   ├── file_classifier.py      → Classify input file types
│   │   └── ingestion_pipeline.py   → Orchestrate ingestion
│   ├── extraction/
│   │   ├── hybrid_extractor.py     → Main hybrid engine (classifier + LLM + vision)
│   │   ├── vision_extractor.py     → GPT-4o vision for scanned drawings
│   │   ├── rule_based_extractor_v2.py → Project-specific regex parsers (fallback)
│   │   ├── mechanical_parser.py    → HVAC equipment parsers
│   │   ├── electrical_parser.py    → Electrical fixture parsers
│   │   ├── prompt_templates.py     → LLM prompt definitions
│   │   ├── llm_client.py           → API client wrapper
│   │   └── extraction_engine.py    → Orchestrates extraction
│   ├── output/
│   │   └── serializer.py           → JSON output generation
│   └── evaluation/
│       ├── expected_loader.py      → Load human expected outputs
│       ├── comparator.py           → Fuzzy matching and diff
│       └── scoring.py              → Generate evaluation reports
├── tests/                          → pytest unit tests
│   └── test_ocr_engine.py          → 29 OCR tests passing
├── outputs/                        → Generated predictions
├── docs/
│   ├── ARCHITECTURE.md
│   └── 30_DAY_PLAN.md
├── data/                           → Intermediate data
├── client_files/                   → Input PDFs (read-only in Docker)
├── docker-compose.yml              → Full stack orchestration
├── Dockerfile.backend              → Python + Tesseract image
├── Dockerfile.frontend             → Node.js build → Nginx serve
├── nginx.conf                      → Reverse proxy config
├── run.py                          → CLI pipeline runner
├── requirements.txt                → Python dependencies
├── README.md                       → Run instructions
└── CANDIDATE_REVIEW_PACKET.md      → Mandatory submission document
```

---

## Key Design Decisions

1. **Separation of Concerns:** Ingestion, extraction, output, and evaluation are separate modules with clear interfaces
2. **Deterministic Evaluation:** All scoring and comparison is code-based, not AI-based
3. **LLM for Interpretation Only:** LLM extracts and interprets; Python calculates and validates
4. **JSON-First:** All outputs are JSON for easy parsing, comparison, and programmatic analysis
5. **Read-Only Inputs:** Original project files are never modified
6. **Extensible Schema:** Output schema starts with template but can grow with documented fields

---

## Open Architecture Questions

1. Should we use a vector database (e.g., Chroma, FAISS) for semantic search across project files?
   - **Current:** No. Simple chunking is faster for 48h prototype.
   - **Future:** Yes, for cross-project knowledge retrieval.

2. Should we cache LLM responses to save costs during development?
   - **Current:** Yes. Implement disk-based cache (hash of prompt → response).
   - **Reason:** Re-running extraction during development is expensive.

3. How to handle multi-modal input (drawings as images + text)?
   - **Current:** Extract text/OCR first. If drawings have dimensions, use vision-capable LLM (GPT-4o) for image analysis.
   - **Future:** Dedicated drawing analysis pipeline with scale detection.

4. Should we implement retry logic for LLM API failures?
   - **Current:** Yes. Exponential backoff, max 3 retries.
   - **Reason:** API rate limits and transient errors are common.
