# Assignment 2 — TAKEOFF-52 Demo Output

This folder contains all deliverables produced by the AI Takeoff Builder for Assessment 2.0 (TAKEOFF-52 Lovesac project).

## 📁 Contents

### Generated Outputs (from the system)
| File | Description |
|------|-------------|
| `prediction.json` | AI-predicted line items (27 items) |
| `evaluation_report.json` | Scoring vs human gold output (81.8% coverage) |
| `TAKEOFF-52_takeoff.xlsx` | Spreadsheet export with line items, quantities, units |
| `TAKEOFF-52_marked.pdf` | Marked PDF with highlighted flooring keywords |

### Documentation
| File | Description |
|------|-------------|
| `LOOM_SCRIPT.md` | Complete Loom video script with timing & talking points |
| `ASSESSMENT2_DEMO_PLAN.md` | Timeline, deliverables, and demo flow |

### Key Source Code
| File | Description |
|------|-------------|
| `export.py` | FastAPI export endpoints (XLSX + Marked PDF) |
| `dynamic_rule_extractor.py` | Unified rule-based extraction engine |

---

## 📊 Results Summary

| Metric | Value |
|--------|-------|
| **Coverage** | 81.8% (9/11 matched) |
| **Extra Items** | 19 |
| **Target** | ≥ 75% ✅ |

---

## 🛠️ Tech Stack

- **Backend:** Python + FastAPI + Docker
- **Frontend:** React + Vite
- **OCR:** Tesseract (PSM 11)
- **PDF:** PyMuPDF (fitz)
- **Exports:** openpyxl (XLSX), pymupdf (marked PDF)

---

**Date:** 2026-05-02  
**Project:** TAKEOFF-52 — Lovesac Corner Shoppes at Stadium
