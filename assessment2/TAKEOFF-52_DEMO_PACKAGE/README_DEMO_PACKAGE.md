# TAKEOFF-52 Demo Package — Assessment 2.0

## 📦 Contents

This folder contains everything needed for the Assessment 2.0 Loom video demo.

### Input Files (upload to app)
| File | Pages | Description |
|------|-------|-------------|
| `19509 Cover Letter.pdf` | 1 | Project cover letter |
| `25.0722_PRE-PERMIT APPROVAL_Corner Shoppes at Stadium_Kalamazoo,MI.pdf` | 41 | Construction drawings & specifications |

### Gold/Human Output (for evaluation only)
| File | Description |
|------|-------------|
| `Estimate - LOVESAC CORNER SHOPPES AT STADIUM.xlsx` | Human estimate with 11 flooring line items + quantities |
| `Markups - LOVESAC CORNER SHOPPES AT STADIUM.pdf` | Human-marked PDF with measurement annotations |

### Demo Documentation
| File | Description |
|------|-------------|
| `README_FOR_CANDIDATES.md` | Official challenge instructions |
| `LOOM_SCRIPT.md` | Complete video script with timing, talking points, and checklist |
| `README_DEMO_PACKAGE.md` | This file — explains package contents |

---

## 🎯 Demo Workflow

```
1. Upload Input Files → App
2. Run Takeoff Pipeline
3. View Predicted Results (filter by "Flooring")
4. Export XLSX Spreadsheet
5. Export Marked PDF
6. Evaluate vs Gold Output
7. Show 75% Accuracy Target
```

---

## ✅ Success Criteria

| Criteria | Target | Current |
|----------|--------|---------|
| Coverage | ≥ 75% | 81.8% (9/11 matched) |
| Extra Items | < 20 | 19 |
| Dashboard Load | < 3s | ✅ |
| XLSX Export | Works | ✅ |
| Marked PDF | Works | ✅ |

---

## 🛠️ How to Run

### 1. Start the system
```bash
cd /root/yasser/assignment1
docker compose up -d
```

### 2. Open dashboard
```
http://localhost:8082
```

### 3. Upload files
- Go to Projects → Upload
- Select the 2 PDFs from this folder

### 4. Run takeoff
- Go to Pipeline → Select TAKEOFF-52
- Click "Run Takeoff"

### 5. View results
- Go to Results → Output tab
- Click "Flooring" filter

### 6. Export
- Click "📊 Export XLSX" → opens spreadsheet
- Click "📄 Marked PDF" → opens marked drawing

### 7. Evaluate
- Go to Results → Evaluation tab
- Compare against gold output

---

## 📊 Expected Results (Gold Output)

The human estimator identified **11 line items**:

1. Management & Supervision (Weeks) — 1 EA
2. Documentation & Shop Drawings — 1 LS
3. V-1: Vinyl Composition Tile Flooring — 311.52 SF
4. T-1: Porcelain Tile Flooring — 1934.66 SF
5. W-1: Engineered Hardwood Plank — 162.61 SF
6. W-1: Engineered Hardwood Plank (7" High) — 36.6 FT
7. Schluter-Indec Edge Trim — ~39 FT
8. Rubber Base to Match Flooring — 107.92 FT
9. MDF Painted Wood Base — 99.45 FT
10. Painted Wood Ledger @Masonry Wall Base — 85.37 FT
11. Vinyl to Porcelain Transition — 3.16 FT

**Target:** AI should match 9+ items = 81.8%+ coverage

---

## ⚠️ Known Limitations

1. **No area calculation from drawings** — Quantities inferred from text, not measured from plans
2. **OCR on small text** — Floor plan annotations < 10px may be missed
3. **19 extra items** — Conservative extraction includes valid accessories/context items
4. **Prototype** — Not production-ready, demonstrates the pipeline

---

## 📁 File Structure

```
TAKEOFF-52_DEMO_PACKAGE/
├── 19509 Cover Letter.pdf                          # Input
├── 25.0722_PRE-PERMIT APPROVAL_...pdf              # Input
├── Estimate - LOVESAC CORNER SHOPPES AT STADIUM.xlsx   # Gold output
├── Markups - LOVESAC CORNER SHOPPES AT STADIUM.pdf     # Gold output
├── README_FOR_CANDIDATES.md                        # Challenge instructions
├── LOOM_SCRIPT.md                                  # Video script
└── README_DEMO_PACKAGE.md                          # This file
```

---

**Prepared for:** Assessment 2.0 Paid Flooring Challenge  
**Project:** TAKEOFF-52 — Lovesac Corner Shoppes at Stadium  
**Date:** 2026-05-02
