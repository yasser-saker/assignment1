# System Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Input Layer                                  │
│  PDF Files (Drawings, Specs, Addendums, Scope of Work)              │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      Ingestion Pipeline                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ File         │  │ PDF Text     │  │ OCR Fallback             │  │
│  │ Classifier   │→ │ Extraction   │→ │ (Parallel Tesseract)     │  │
│  │ (filename)   │  │ (PyMuPDF)    │  │ + Spell Correction       │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    Context Extraction Layer                          │
│  ┌────────────────┐  ┌───────────────┐  ┌────────────────────────┐  │
│  │ Finish Legend   │  │ Room Schedule │  │ Equipment Schedule     │  │
│  │ (any prefix)    │  │ (any format)  │  │ (dynamic discovery)    │  │
│  └────────────────┘  └───────────────┘  └────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                   Dynamic Extraction Engine                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  DynamicRuleExtractor (Unified - ALL projects)               │   │
│  │  ├── ScheduleDetector (pattern-based header detection)       │   │
│  │  ├── GenericRowParser (equipment tag extraction)             │   │
│  │  ├── MechanicalParser (HVAC items)                          │   │
│  │  ├── ElectricalParser (Electrical items)                    │   │
│  │  ├── TradeClassifier (keyword scoring)                      │   │
│  │  └── _infer_items_from_context (generic domain patterns)    │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    Post-Processing Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ False        │  │ Deduplicate  │  │ LLM Filter (optional)    │  │
│  │ Positive     │→ │ (exact +     │→ │ (GPT-4o-mini batch)      │  │
│  │ Filter       │  │ fuzzy match) │  │                          │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      Output Layer                                    │
│  prediction.json → Evaluation → CANDIDATE_REVIEW_PACKET.md          │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Design Principles

### 1. 100% Dynamic (No Hardcoding)
- No project-specific item injection
- No fixed finish code prefixes
- No fixed room number formats
- No fixed equipment tags
- Generic inference based on domain keywords

### 2. Deterministic + AI Hybrid
- Deterministic: calculations, pattern matching, trade classification
- AI: LLM post-filter for false positive removal (optional)
- Separation ensures reproducibility

### 3. Modular Architecture
- Each parser is independent
- Can add new parsers without modifying existing ones
- Trade classifier is pluggable

## Data Flow

1. **File Classification**: `FileClassifier.classify(filename)` → drawing/spec/sow/addendum/other
2. **Text Extraction**: `PDFExtractor.extract()` → Page objects (text + OCR)
3. **Context Building**: `ContextExtractor.extract_all(pages)` → finish_legend, room_schedule, equipment_schedule
4. **Item Extraction**: `DynamicRuleExtractor.extract_from_project(ingested_files)` → List[LineItem]
5. **Filtering**: `_filter_false_positives()` + `_deduplicate()` + optional LLM filter
6. **Output**: `ProjectOutput` → JSON file
7. **Evaluation**: `Evaluator.evaluate()` → EvaluationReport

## Technology Choices

| Component | Technology | Why |
|-----------|-----------|-----|
| PDF Text | PyMuPDF | Fast, reliable text extraction |
| OCR | Tesseract | Free, configurable PSM modes |
| Spell Check | pyspellchecker | Fast, offline, domain dictionary |
| Fuzzy Match | rapidfuzz | Fast C++ implementation |
| Backend | FastAPI | Async, OpenAPI docs |
| Frontend | React + Vite | Modern, fast build |
| Deployment | Docker Compose | Simple, reproducible |

## Performance Characteristics

| Operation | Time | Bottleneck |
|-----------|------|------------|
| Text extraction (1500 pages) | ~30s | PyMuPDF |
| OCR (1 page, DPI 100) | ~4s | Tesseract |
| Parallel OCR (35 pages, 4 workers) | ~40s | Tesseract |
| Extraction (all rules) | ~5s | Pattern matching |
| Evaluation (121 items) | ~1s | Fuzzy matching |
| **Total (specs only)** | **~1 min** | Text extraction |
| **Total (with OCR)** | **~10-15 min** | OCR |

## Known Bottlenecks

1. **Tesseract on CAD drawings**: Some pages take 25-30 min (complex graphics)
2. **Memory**: Large PDF rendering (8M pixels cap)
3. **ProcessPoolExecutor**: Startup overhead for small batches
