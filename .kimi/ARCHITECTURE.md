# Architecture — AI Takeoff Builder Challenge

**Last Updated:** 2026-04-29  
**Status:** Draft / Design Phase  
**Version:** 0.1

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

**Source:**
- `01_Sample_Projects_With_Expected_Output/TAKEOFF-XX/Project Files/` (3 projects)
- `02_Challenge_Projects_Project_Files_Only/TAKEOFF-XX/Project Files/` (25 projects)

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

### 3. Extraction Engine (LLM-Based)

**Responsibility:** Convert ingested content into structured takeoff line items.

**Approach:**
- Use LLM (GPT-4o or Claude 3.5 Sonnet) with structured output (JSON mode / function calling)
- Process files in context-aware chunks
- Maintain trade/scope context across chunks

**Prompt Strategy:**

#### 3.1 Context Builder
- Assemble project context from all files:
  - Project name, location
  - Scope summary (from SOW)
  - Key trades mentioned
  - Special conditions (from addendums, rules)

#### 3.2 Chunking Strategy
- Text files: chunk by page or logical section (max 4000 tokens per chunk)
- Drawings: one page at a time (image + any available text/OCR)
- Maintain overlap: last 2 lines of previous chunk included as context

#### 3.3 Extraction Prompt Template
```
You are a construction estimator performing a quantity takeoff.

PROJECT CONTEXT:
{project_context}

INPUT (Page {n} of {file_name}):
{page_content}

Extract ALL quantifiable construction line items from this input.
For each item, provide:
- description: clear, specific description
- trade: category (e.g., Demolition, Drywall, Flooring, Painting, Electrical, Plumbing, HVAC, Millwork, Ceilings)
- quantity: numeric value (or null if not determinable)
- unit: SF, LF, EA, CY, etc. (or null)
- confidence: high / medium / low
- source: which file and page/section
- assumptions: any assumptions made
- issues: any uncertainties or missing info

If quantities require calculation from dimensions, calculate them.
If a quantity cannot be determined, note it in issues.
Output as valid JSON array.
```

#### 3.4 Consolidation
- Merge duplicate line items across chunks (same description + trade)
- Sum quantities for identical items
- Flag conflicts (same description, different quantities)

**Data Model (Output):**
```python
class LineItem:
    item_id: str
    description: str
    trade: str
    quantity: Optional[float]
    unit: Optional[str]
    confidence: str  # high, medium, low
    source_files: List[str]
    source_pages: List[int]
    assumptions: List[str]
    issues: List[str]
    
class ProjectOutput:
    project_id: str
    project_name: str
    input_files_used: List[str]
    trade_assumptions: List[str]
    line_items: List[LineItem]
    generated_at: datetime
    model_used: str
    total_line_items: int
    issues_count: int
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
│ CONTEXT BUILDER                    │
│ • Summarize project from SOW       │
│ • Identify trades and scope        │
│ • Note special conditions          │
└────────────────┬───────────────────┘
                 │
                 ▼ ProjectContext object
┌────────────────────────────────────┐
│ CHUNKER                            │
│ • Split into LLM-processable chunks│
│ • Maintain context overlap         │
└────────────────┬───────────────────┘
                 │
                 ▼ Chunks
┌────────────────────────────────────┐
│ LLM EXTRACTION                     │
│ • Structured extraction per chunk  │
│ • JSON output mode                 │
└────────────────┬───────────────────┘
                 │
                 ▼ Raw line items
┌────────────────────────────────────┐
│ CONSOLIDATOR                       │
│ • Merge duplicates                 │
│ • Sum quantities                   │
│ • Flag conflicts                   │
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
| Language | Python 3.11+ | Primary implementation |
| PDF Text | pdfplumber, PyMuPDF | Text and table extraction |
| PDF OCR | pytesseract (local) or Azure DI | Scanned PDF fallback |
| LLM API | OpenAI GPT-4o / Claude 3.5 Sonnet | Extraction and reasoning |
| Data Processing | pandas | Data manipulation |
| String Matching | rapidfuzz | Fuzzy matching for evaluation |
| Data Storage | JSON/JSONL, SQLite | Outputs and intermediate state |
| Testing | pytest | Unit tests for deterministic components |

---

## Directory Structure (Planned)

```
ai-takeoff-builder/
├── .kimi/                          → AI memory files (not for submission)
├── src/
│   ├── __init__.py
│   ├── config.py                   → Configuration, paths, constants
│   ├── models.py                   → Pydantic/dataclass models
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── pdf_extractor.py        → pdfplumber/PyMuPDF wrapper
│   │   ├── ocr_engine.py           → Tesseract/cloud OCR
│   │   ├── file_classifier.py      → Classify input file types
│   │   └── ingestion_pipeline.py   → Orchestrate ingestion
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── context_builder.py      → Build project context
│   │   ├── chunker.py              → Split content for LLM
│   │   ├── prompt_templates.py     → LLM prompt definitions
│   │   ├── llm_client.py           → API client wrapper
│   │   ├── extraction_engine.py    → Run extraction
│   │   └── consolidator.py         → Merge and deduplicate
│   ├── output/
│   │   ├── __init__.py
│   │   └── serializer.py           → JSON output generation
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── expected_loader.py      → Load human expected outputs
│   │   ├── comparator.py           → Fuzzy matching and diff
│   │   └── scoring.py              → Generate evaluation reports
│   └── pipeline/
│       ├── __init__.py
│       └── runner.py               → End-to-end pipeline orchestrator
├── tests/
│   ├── test_ingestion.py
│   ├── test_extraction.py
│   ├── test_evaluation.py
│   └── fixtures/
├── outputs/                        → Generated predictions (gitignored)
├── docs/
│   ├── ARCHITECTURE.md             → This document (moved here)
│   └── 30_DAY_PLAN.md              → Post-hire execution plan
├── data/                           → Symlinks to input datasets (read-only)
├── README.md                       → Run instructions
├── requirements.txt                → Python dependencies
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
