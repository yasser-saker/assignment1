# AI Takeoff Builder Challenge

Backend prototype for automated construction takeoff extraction from PDF project files.

## What It Does

This system reads construction project PDFs (drawings, specifications, scope of work, addendums) and extracts structured takeoff line items including:
- Description of work
- Trade category (Electrical, HVAC, Drywall, etc.)
- Quantity and unit (SF, LF, EA, etc.)
- Confidence score
- Source reference

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set OpenAI API key (required for LLM extraction)
export OPENAI_API_KEY="your-key-here"  # Linux/Mac
set OPENAI_API_KEY=your-key-here       # Windows
```

## Usage

### Run on a Single Project

```bash
python run.py --project-id TAKEOFF-28 --input-dir "path/to/project/files" --use-llm
```

### Run Evaluation (Sample Projects Only)

```python
from src.evaluation.evaluator import Evaluator

evaluator = Evaluator(fuzzy_threshold=50)
report = evaluator.evaluate(
    "outputs/TAKEOFF-28/TAKEOFF-28_prediction.json",
    "path/to/expected/estimate.xlsx"
)
print(report.overall_notes)
```

## Project Structure

```
src/
  ingestion/       PDF text extraction and file classification
  extraction/      LLM-based line item extraction
  output/          JSON output generation
  evaluation/      Comparison and scoring against expected outputs
outputs/           Generated predictions (one folder per project)
docs/              Architecture notes and 30-day plan
tests/             Unit tests
```

## Tools Used

| Tool | Purpose |
|------|---------|
| Python 3.11+ | Core language |
| PyMuPDF | Fast PDF text extraction |
| OpenAI GPT-4o | AI extraction engine |
| OpenAI GPT-4o-mini | Cost-effective extraction for large files |
| rapidfuzz | Fuzzy string matching for evaluation |
| pandas | Excel reading for expected outputs |
| pydantic | Data validation |

## Performance

| Metric | Value |
|--------|-------|
| Projects processed | 5 (3 sample + 2 challenge) |
| Total line items | 1,242 |
| Average processing time | 5-15 min per project |
| File size handled | Up to 1,544 pages |

## Evaluation Results

| Project | Expected | Predicted | Match Rate |
|---------|----------|-----------|------------|
| TAKEOFF-28 | 121 | 187 | 17.4% |
| TAKEOFF-50 | 7 | 688 | 57.1% |
| TAKEOFF-56 | 11 | 216 | 36.4% |

## Known Limitations

- Scanned drawings not processed (OCR not implemented)
- Quantity extraction limited (no drawing dimension analysis)
- Description format differs from human estimates
- API rate limits slow large projects

## License

Assessment project — not for production use.
