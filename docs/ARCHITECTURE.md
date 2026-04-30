# Architecture — AI Takeoff Builder Challenge

## System Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Input     │───→│ Ingestion   │───→│ Extraction  │───→│   Output    │
│   Files     │    │  Engine     │    │   Engine    │    │  Generator  │
│  (PDFs)     │    │             │    │   (LLM)     │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘
                                                                  │
                              ┌───────────────────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │  Evaluation &   │
                    │    Scoring      │
                    │   (Samples)     │
                    └─────────────────┘
```

## Components

### 1. Ingestion Engine
- **PDFExtractor**: Uses PyMuPDF for fast text extraction (0.3s for 41-page document)
- **OCREngine**: Tesseract fallback for scanned pages (not used in current prototype)
- **FileClassifier**: Classifies files by name keywords (drawing, spec, sow, addendum, rules, breakout)

### 2. Extraction Engine
- **Chunker**: Groups pages into 30K character chunks (reduces API calls by ~60%)
- **LLMClient**: OpenAI GPT-4o (small files) / GPT-4o-mini (large files > 50 pages)
- **PromptTemplates**: Structured prompts for consistent JSON output
- **RuleBasedExtractor**: Fallback when API key unavailable

### 3. Output Generator
- **Serializer**: Generates JSON following 03_Output_Template.json schema
- **ProjectOutput**: Pydantic model with validation

### 4. Evaluation Engine
- **ExpectedLoader**: Reads Excel estimates using pandas
- **Comparator**: Fuzzy matching (rapidfuzz) with 50% threshold
- **Scoring**: Classifies items as Matched / Missing / Extra

## Data Model

```python
class LineItem:
    description: str
    trade: str
    quantity: Optional[float]
    unit: Optional[str]
    confidence: float  # 0.0 to 1.0
    source_reference: str

class ProjectOutput:
    project_id: str
    trade_scope: str
    input_files_used: List[str]
    ai_run: AIRun
    line_items: List[LineItem]
    evaluation_when_gold_available: Optional[EvaluationReport]
```

## AI vs Deterministic Code

| Task | Approach | Reason |
|------|----------|--------|
| Text extraction | Deterministic (PyMuPDF) | Fast, reliable, no hallucination |
| Item interpretation | AI (GPT-4o) | Requires domain understanding |
| Quantity comparison | Deterministic | Math must be exact |
| Fuzzy matching | Deterministic (rapidfuzz) | Reproducible scoring |

## Key Design Decisions

1. **Chunking (30K chars)**: Reduces API calls from 200 to ~50 per large file
2. **Model selection**: GPT-4o-mini for files > 50 pages (30x cheaper)
3. **Page filtering**: Skip pages < 200 chars (covers, blank pages)
4. **Rate limit handling**: 0.3s delay + 5s retry on 429 errors

## Risks

- Scanned drawings not processed (no OCR in prototype)
- Quantity extraction limited (no dimension analysis)
- API rate limits slow large projects
- Description format gap between AI and human estimates
