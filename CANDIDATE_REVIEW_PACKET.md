# Candidate Review Packet — AI Takeoff Builder Challenge

**Date:** 2026-04-29  
**Candidate:** [Your Name]  
**Project:** AI Takeoff Builder — Assessment 1.0

---

## 1. Plain-English Summary

I built a backend prototype that automatically reads construction project PDFs (drawings, specifications, scope of work, addendums) and extracts structured takeoff line items (description, trade, quantity, unit, confidence).

The system uses:
- **PyMuPDF** for fast PDF text extraction
- **OpenAI GPT-4o / GPT-4o-mini** for AI-powered extraction
- **Rule-based fallback** when AI is unavailable
- **Chunked processing** to handle large files efficiently

**What it does:** Upload PDFs → Extract text → AI identifies line items → Output JSON

---

## 2. How To Run It

```bash
# Install dependencies
pip install -r requirements.txt

# Set your OpenAI API key
set OPENAI_API_KEY=your-key-here

# Run on a project
python run.py --project-id TAKEOFF-28 --input-dir "path/to/project/files" --use-llm

# Run evaluation (for sample projects with expected output)
python -c "from src.evaluation.evaluator import Evaluator; e = Evaluator(); r = e.evaluate('outputs/TAKEOFF-28/TAKEOFF-28_prediction.json', 'path/to/expected.xlsx'); print(r.overall_notes)"
```

**Requirements:**
- Python 3.11+
- OpenAI API key (for LLM extraction)
- Windows/Linux/Mac

---

## 3. Projects Processed

| Set | Takeoff ID | Project Name | Files Used | Output Created? | Scored? |
|-----|-----------|--------------|------------|-----------------|---------|
| Sample | TAKEOFF-28 | Maryland Vision Institute | 4 PDFs (SOW, Addendum, Drawings, Break Out) | ✅ Yes | ✅ Yes |
| Sample | TAKEOFF-50 | Portland VA Surgical Center | 17 PDFs | ✅ Yes | ⏳ Pending |
| Sample | TAKEOFF-56 | Jack & Jones Staten Island | 13 PDFs | ✅ Yes | ⏳ Pending |
| Challenge | TAKEOFF-31 | Walmart 1783 | 2 PDFs | ✅ Yes | No hidden gold |
| Challenge | TAKEOFF-36 | Gucci Perm — Cherry Creek | 2 PDFs | ✅ Yes | No hidden gold |

**Total: 5 projects, 1,242 line items extracted**

---

## 4. System Pipeline

```
1. FILE INGESTION
   - Read all PDFs from Project Files/ folder
   - Classify by type: drawing, spec, sow, addendum, rules
   - Extract text using PyMuPDF (fast)
   - Filter out pages with < 200 characters

2. EXTRACTION
   - Chunk pages into 30K character blocks
   - Send to GPT-4o (small files) or GPT-4o-mini (large files > 50 pages)
   - Extract structured line items with: description, trade, quantity, unit, confidence
   - Rate limit protection: 0.3s delay + retry on 429 errors

3. OUTPUT GENERATION
   - Generate JSON following 03_Output_Template.json schema
   - Include metadata: tools used, assumptions, warnings

4. EVALUATION (Sample projects only)
   - Load expected output from Excel files
   - Fuzzy match predicted vs expected descriptions (rapidfuzz)
   - Classify: Matched / Missing / Extra
   - Calculate quantity differences

5. CORRECTION LOOP
   - Structured JSON format for reviewer corrections
   - Captures: items to add, remove, or correct
   - Stored for future prompt improvement
```

---

## 5. Output Summary

### Sample Line Items (TAKEOFF-28)

```json
{
  "description": "Furnish and install studs, insulation, drywall and finishing",
  "trade": "Drywall",
  "quantity": null,
  "unit": "SF",
  "confidence": 0.85,
  "source_reference": "Scope of Work.pdf"
}
```

```json
{
  "description": "6\" Dia Duct",
  "trade": "HVAC",
  "quantity": 28.21,
  "unit": "FT",
  "confidence": 0.9,
  "source_reference": "Drawings.pdf"
}
```

---

## 6. Evaluation / Scoring Results

### TAKEOFF-28 (Maryland Vision Institute)

| Metric | Value |
|--------|-------|
| Expected Items | 121 |
| Predicted Items | 187 |
| Matched | 21 (17.4%) |
| Missing | 100 |
| Extra | 166 |

**Analysis:**
- Low match rate due to **description format differences**
- Human estimate uses codes: `PNT-01`, `CL-03`, specific Sherwin Williams colors
- AI extracts general descriptions: "Furnish and install painting and wall finishes"
- **Quantities:** Many predicted items have null quantity (drawings not analyzed for dimensions)

**Example Miss:**
- Expected: `PNT-01 (9'-6" High): Mfg: Sherwin Williams, Color: Wordly Gray #SW7043`
- Predicted: `Furnish and install all painting and wall finishes`

---

## 7. Automation vs Manual Work

| Task | Status | Notes |
|------|--------|-------|
| PDF ingestion | ✅ Automated | PyMuPDF extracts text |
| File classification | ✅ Automated | By filename keywords |
| Text extraction | ✅ Automated | LLM (GPT-4o) |
| Quantity calculation | ⚠️ Partial | Null for most items (need drawing dimension analysis) |
| Evaluation | ✅ Automated | Fuzzy matching + scoring |
| Correction capture | ✅ Automated | JSON template generated |

---

## 8. AI / Tools Used

| Tool | Purpose |
|------|---------|
| **OpenAI GPT-4o** | Primary extraction engine |
| **OpenAI GPT-4o-mini** | Large files (> 50 pages) to save cost |
| **PyMuPDF** | Fast PDF text extraction |
| **pdfplumber** | Table extraction (fallback) |
| **rapidfuzz** | Fuzzy string matching for evaluation |
| **pandas** | Excel reading for expected outputs |
| **pydantic** | Data validation |

---

## 9. Limitations and Risks

### Current Limitations
1. **Scanned Drawings:** OCR not implemented — scanned PDFs return 0 items
2. **Quantity Extraction:** Cannot calculate areas/lengths from drawing dimensions
3. **Description Mismatch:** AI descriptions don't match human estimate codes (PNT-01, etc.)
4. **Large Specifications:** Files > 500 pages take too long (rate limits)
5. **No Visual Analysis:** Cannot read dimensions from drawing images

### Risks
- API rate limits slow processing
- API costs for large projects
- Inconsistent output quality across project types

### Assumptions
- Text-based PDFs contain sufficient information
- LLM can interpret construction terminology
- Fuzzy matching threshold of 50% is appropriate

---

## 10. 30-Day Plan If Hired

### Week 1-2: Foundation
- Implement OCR for scanned drawings (Tesseract/Azure Document Intelligence)
- Build dimension extraction from drawing images (OpenCV + scale detection)
- Improve prompt engineering with few-shot examples

### Week 3-4: Accuracy
- Fine-tune LLM on corrected outputs (if dataset available)
- Build rule-based post-processors for common errors
- Implement confidence calibration

### Week 5-8: Scale
- Batch processing pipeline with queue system
- Database storage (PostgreSQL) for projects and outputs
- Web UI for human review and correction
- Integration with pricing databases (RSMeans)

---

## 11. Reviewer Notes

- **Honest assessment:** This is a functional prototype, not production-ready AI
- **Key strength:** Complete end-to-end pipeline that works
- **Key weakness:** Low match rate vs human estimates due to description format gap
- **Scalability:** System can process any number of projects with API key
- **Data discipline:** Expected outputs never used during extraction (only for evaluation)

---

**Time spent:** ~8 hours  
**Projects processed:** 5 (3 sample + 2 challenge)  
**Total line items:** 1,242  
**System status:** Functional and repeatable
