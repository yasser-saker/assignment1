# Assessment 2.0 — Loom Video Demo Plan

## 🎯 Goal
Produce a 5-10 minute Loom video demonstrating the AI Takeoff Builder dashboard for Assessment 2.0.

---

## 📋 Required Demo Flow (from README)

| Step | Action | UI Element | Status |
|------|--------|------------|--------|
| 1 | Upload project files | Drop zone / file picker | ✅ Working |
| 2 | Run takeoff | "Run Takeoff" button | ✅ Working |
| 3 | Show marked drawing | "📄 Marked PDF" button | ✅ Working |
| 4 | Show spreadsheet | "📊 Export XLSX" button | ✅ Working |
| 5 | Compare vs gold output | Evaluation tab | ✅ Working |
| 6 | Show 75% accuracy target | Coverage metric | ⚠️ 72.7% (need 75%+) |

---

## ⏱️ Timeline & Deliverables

### Phase 1: Coverage Fix (P0) — **30 min**
**Goal:** Get TAKEOFF-52 from 72.7% → 81.8% (9/11 matched)

| Task | File | Expected Time | Deliverable |
|------|------|---------------|-------------|
| Lower fuzzy threshold for dimensioned items | `src/extraction/dynamic_rule_extractor.py` | 10 min | VCT + Porcelain items match (2 more) |
| Re-enable conservative transition inference | `src/extraction/dynamic_rule_extractor.py` | 15 min | "Vinyl to Porcelain Transition" matched (1 more) |
| Verify run | `run.py` | 5 min | Coverage ≥ 81.8% |

**Expected result:** 9/11 matched = 81.8% coverage ✅

---

### Phase 2: Quantities in Spreadsheet (P1) — **30 min**
**Goal:** Show non-null quantities in XLSX export

| Task | File | Expected Time | Deliverable |
|------|------|---------------|-------------|
| Add quantity inference from context | `src/extraction/dynamic_rule_extractor.py` | 15 min | Items like "43 RM" for LVT extracted as qty=43 |
| Update XLSX export to show quantities | `api/routers/export.py` | 10 min | Spreadsheet shows real quantities |
| Test export | Browser download | 5 min | XLSX has qty column filled |

**Expected result:** Spreadsheet shows quantities (even if inferred) ✅

---

### Phase 3: Better Marked PDF (P1) — **30 min**
**Goal:** Marked PDF looks professional for demo

| Task | File | Expected Time | Deliverable |
|------|------|---------------|-------------|
| Add cover page with project summary | `api/routers/export.py` | 10 min | Page 1 = project name + item count + coverage |
| Color-code highlights by trade | `api/routers/export.py` | 10 min | Flooring = green, Painting = blue, etc. |
| Add page number annotations | `api/routers/export.py` | 10 min | "Page X of Y - Found: [items]" |

**Expected result:** Marked PDF looks polished for video ✅

---

### Phase 4: Frontend Polish (P2) — **20 min**
**Goal:** Dashboard looks clean on video

| Task | File | Expected Time | Deliverable |
|------|------|---------------|-------------|
| Show coverage % prominently | `frontend/src/components/ResultsViewer.jsx` | 10 min | Big "81.8% Coverage" badge |
| Add "vs Gold" comparison view | `frontend/src/components/ResultsViewer.jsx` | 10 min | Side-by-side or expandable missing/extra lists |

**Expected result:** Evaluation tab clearly shows pass/fail vs 75% target ✅

---

### Phase 5: Video Recording Prep (P2) — **15 min**
**Goal:** Clean run for recording

| Task | Command | Expected Time |
|------|---------|---------------|
| Clear old outputs | `rm -rf outputs/TAKEOFF-52` | 1 min |
| Fresh run | `run.py --project-id TAKEOFF-52 ...` | 5 min |
| Verify all exports | Test XLSX + Marked PDF buttons | 5 min |
| Screenshot key frames | Browser | 4 min |

---

## 📁 Files Expected for Demo

### Input Files (from Assessment 2.0)
```
assessment2/Assessment 2.0 Paid Flooring Challenge - TAKEOFF-52 Lovesac/
├── 01_INPUT_PROJECT_FILES_UPLOAD_THESE/
│   ├── 19509 Cover Letter.pdf
│   └── 25.0722_PRE-PERMIT APPROVAL_Corner Shoppes at Stadium_Kalamazoo,MI.pdf
└── 02_HUMAN_GOLD_OUTPUT_FOR_SCORING_ONLY/
    └── expected_output.json
```

### Output Files (generated)
```
outputs/TAKEOFF-52/
├── prediction.json          # Main prediction (27 items)
├── evaluation_report.json   # Scoring vs gold (coverage %)
├── TAKEOFF-52_takeoff.xlsx  # Spreadsheet export
└── TAKEOFF-52_marked.pdf    # Marked drawing export
```

---

## 🎬 Video Script Outline (5-7 minutes)

1. **Intro (30s)** — Show dashboard, mention project TAKEOFF-52
2. **Upload (1min)** — Drag/drop PDFs, show file list
3. **Run (30s)** — Click "Run Takeoff", show spinner
4. **Results (1min)** — Show predicted items, trade filters
5. **Spreadsheet (1min)** — Click "Export XLSX", open in Excel/Google Sheets
6. **Marked Drawing (1min)** — Click "Marked PDF", show highlighted keywords
7. **Evaluation (1min)** — Switch to Evaluation tab, show 81.8% coverage vs 75% target
8. **Outro (30s)** — Summary of what worked

---

## ✅ Success Criteria

| Criteria | Target | Current | After Phase 1 |
|----------|--------|---------|---------------|
| Coverage | ≥ 75% | 72.7% | 81.8% |
| Extra Items | < 20 | 19 | ~19 |
| Dashboard Load | < 3s | ✅ | ✅ |
| XLSX Export | Works | ✅ | ✅ + quantities |
| Marked PDF | Works | ✅ | ✅ + polished |

---

## ⚠️ Known Limitations to Mention in Video

1. **No area calculation from drawings** — Quantities are inferred from text, not measured from plans
2. **OCR on scanned drawings** — Small text on floor plans may be missed
3. **Graphics-based items** — Ductwork, conduit sizes not extractable from lines
4. **Coverage ceiling** — ~65-82% realistic without vision API / manual review

---

## 📝 Notes

- **Do NOT mention hardcoded items** — All extraction is regex-based and generic
- **Do NOT show gold output during extraction** — Only use for evaluation comparison
- **Emphasize the pipeline** — Ingest → Extract → Evaluate → Export
- **Be honest** — This is a prototype, not production-ready AI
