# AI Takeoff Builder - Construction Document Extraction System

## Overview

This system automatically extracts construction takeoff line items from project files (PDFs: drawings, specs, scope of work, addendums) using dynamic rule-based extraction with OCR fallback for scanned documents.

**Key Features:**
- **100% Dynamic Extraction** - No hardcoded project-specific items
- **Unified Extractor** - Single `DynamicRuleExtractor` works across all projects
- **OCR with Post-Processing** - Tesseract OCR + spell correction + parallel processing
- **Smart File Classification** - Detects file types (drawing, spec, addendum) automatically
- **Evaluation Engine** - Fuzzy matching against expected outputs with spelling normalization

## Architecture

```
PDF Files → Ingestion Pipeline → Context Extraction → Dynamic Rules → Line Items → Output
                ↓                      ↓                ↓
            OCR Fallback      Finish Legend      Schedule Detection
            (Parallel)        Room Schedule      Trade Classification
                              Equipment          False Positive Filter
```

## Tech Stack

- **Backend:** Python 3.12, FastAPI
- **PDF Processing:** PyMuPDF, pdfplumber
- **OCR:** Tesseract (PSM 11, OEM 3), pyspellchecker
- **Frontend:** React + Vite
- **Deployment:** Docker Compose

## Quick Start

### 1. Start Services

```bash
docker compose up -d
```

- Backend: http://localhost:8000
- Frontend: http://localhost:8082
- API Docs: http://localhost:8000/docs

### 2. Run Extraction via CLI

```bash
# Activate virtual environment
source venv/bin/activate

# Run on a project (specs only for speed)
python run.py \
  --project-id TAKEOFF-50 \
  --input-dir "client_files/01_Sample_Projects_With_Expected_Output/TAKEOFF-50 - Portland VA Surgical Center Rehabilitation/Project Files/Specifications"

# Run with evaluation (requires expected output)
python run.py \
  --project-id TAKEOFF-28 \
  --input-dir "client_files/01_Sample_Projects_With_Expected_Output/TAKEOFF-28 - Maryland Vision Institute/Project Files" \
  --evaluate \
  --expected-dir "client_files/01_Sample_Projects_With_Expected_Output/TAKEOFF-28 - Maryland Vision Institute/Expected Manual Output"
```

### 3. Run Extraction via API

```bash
curl -X POST http://localhost:8000/api/extract \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "TAKEOFF-28",
    "input_dir": "client_files/01_Sample_Projects_With_Expected_Output/TAKEOFF-28 - Maryland Vision Institute/Project Files"
  }'
```

## Project Structure

```
├── api/                          # FastAPI backend
│   ├── main.py                   # API entry point
│   └── routers/                  # API routes
├── src/                          # Core extraction logic
│   ├── extraction/
│   │   ├── dynamic_rule_extractor.py   # Unified extractor (ALL projects)
│   │   ├── context_extractor.py        # Finish legend, room schedule, equipment
│   │   ├── mechanical_parser.py        # HVAC items
│   │   ├── electrical_parser.py        # Electrical items
│   │   └── ...
│   ├── ingestion/
│   │   ├── pdf_extractor.py            # PDF text + OCR
│   │   ├── ocr_engine.py               # Tesseract wrapper
│   │   ├── ocr_post_processor.py       # Spell correction
│   │   ├── parallel_ocr.py             # Multi-process OCR
│   │   └── chunked_ocr.py              # Checkpoint/resume OCR
│   ├── evaluation/
│   │   └── evaluator.py                # Fuzzy match evaluation
│   └── models.py                       # Data models
├── outputs/                      # Generated predictions
├── tests/                        # Unit tests
├── client_files/                 # Input projects
│   ├── 01_Sample_Projects/       # 3 sample projects with expected output
│   └── 02_Challenge_Projects/    # 2 challenge projects
├── frontend/                     # React frontend
├── run.py                        # CLI runner
└── docker-compose.yml
```

## Dynamic Extraction Design

### What Makes It Dynamic?

1. **Generic Schedule Detection** - Detects ANY schedule type by header patterns:
   - `DIFFUSERS?.*SCHEDULE`, `VAV.*SCHEDULE`, `LIGHTING.*SCHEDULE`, etc.
   
2. **Flexible Tag Parsing** - Accepts any equipment tag format:
   - `RTU-1`, `AC-01`, `VAV-A`, `Light-A`, etc.
   
3. **Adaptive Context Extraction**:
   - Finish codes: `PNT-01`, `CL-02`, `LVT-03`, `PAINT-A`, etc.
   - Room numbers: `101`, `101A`, `A-1`, `Suite 100`
   
4. **Domain Inference** - Generic patterns (NOT hardcoded items):
   - Flooring transitions between detected types
   - Millwork from room type keywords
   - HVAC from spec section keywords
   
5. **Trade Classification** - Keyword-based scoring:
   - `diffuser` → HVAC, `receptacle` → Electrical, `tile` → Flooring

### What Was Removed (Previously Hardcoded)

- ❌ Project-specific item injection (`_infer_items_from_context` had exact expected output strings)
- ❌ Fixed finish code prefixes (was 20 specific codes)
- ❌ Fixed room number format (was 3-digit only)
- ❌ Fixed equipment prefixes (was RTU/AC/EF/VAV only)
- ❌ Fixed lighting tags (was single letter only)

## Performance Benchmarks

| Project | Coverage | Matched/Total | Notes |
|---------|----------|---------------|-------|
| TAKEOFF-28 | 64.5% | 78/121 | Best - rich text data |
| TAKEOFF-56 | 45.5% | 5/11 | Scanned pages, OCR limits |
| TAKEOFF-50 (specs) | 57.1% | 4/7 | Drawings timed out (>300s) |

**OCR Performance:**
- DPI 100: ~4.2s/page average
- Parallel OCR: ~1 min for 104 scanned pages (4 workers)
- Total spec pages (1544): ~30s (no OCR needed)

## Limitations & Honest Assessment

1. **Scanned Floor Plans** - OCR cannot reliably read small text on CAD floor plans (text ~2-3mm high at 1:100 scale)
2. **Graphics-Based Items** - Ductwork sizes, pipe sizes drawn as graphics (not text) are not extractable
3. **Time Constraints** - Full project with 100+ scanned pages takes 10-15 minutes
4. **Coverage Ceiling** - Without vision API or manual review, ~60-65% is realistic ceiling for text-rich projects

## Configuration

Key settings in `src/config.py`:

```python
OCR_DPI = 100                    # DPI for rendering scanned pages
OCR_DEFAULT_PSM = 11             # Tesseract PSM mode (Sparse Text)
MIN_TEXT_CHARS_FOR_NON_SCANNED = 50  # Threshold for OCR trigger
```

## Development

```bash
# Run tests
pytest tests/

# Run specific test
pytest tests/test_ingestion_pipeline.py -v

# Format code
black src/ api/ tests/
```

## License

Internal project for AI Takeoff Builder Challenge.
