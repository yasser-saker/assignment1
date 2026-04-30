# 30-Day Execution Plan

## Week 1: Foundation & OCR

### Days 1-3: Scanned Drawing Support
- Integrate Tesseract OCR for scanned PDFs
- Test on sample projects with scanned drawings
- Implement image preprocessing (deskew, denoise)

### Days 4-5: Dimension Extraction
- Build drawing scale detection (from title block or known dimensions)
- Extract room areas from floor plans (polygon detection)
- Calculate wall lengths and surface areas

### Days 6-7: Prompt Engineering
- Create few-shot examples from corrected outputs
- A/B test prompts for better description matching
- Add trade-specific extraction rules

## Week 2: Accuracy Improvement

### Days 8-10: Quantity Calculation
- Implement area calculation from drawing coordinates
- Build length extraction for linear elements (ducts, pipes)
- Add count detection for symbols (doors, lights, outlets)

### Days 11-12: Evaluation Pipeline
- Automated evaluation dashboard
- Per-trade accuracy metrics
- Regression testing on sample projects

### Days 13-14: Error Analysis
- Categorize common errors (missing items, wrong quantities)
- Build correction rule engine
- Implement confidence calibration

## Week 3: Scale & Infrastructure

### Days 15-17: Database & API
- PostgreSQL schema for projects, files, outputs
- REST API for project upload and status checking
- Background job queue (Celery/RQ) for processing

### Days 18-19: Web UI
- Project upload interface
- Review and correction UI
- Output comparison view (prediction vs expected)

### Days 20-21: Batch Processing
- Parallel processing of multiple projects
- Progress tracking and notifications
- Error handling and retry logic

## Week 4: Integration & Polish

### Days 22-24: Pricing Integration
- Connect to RSMeans or similar pricing database
- Add unit cost calculations
- Generate full estimates (not just quantities)

### Days 25-26: Testing
- End-to-end tests for all project types
- Performance benchmarks
- Security audit

### Days 27-28: Documentation
- API documentation (OpenAPI/Swagger)
- User guide for reviewers
- Deployment documentation

### Days 29-30: Deployment
- Docker containers for all services
- CI/CD pipeline
- Production monitoring setup

## Success Metrics

| Metric | Current | Target (30 days) |
|--------|---------|------------------|
| Projects processed | 5 | 50+ |
| Match rate (samples) | 17-57% | 60%+ |
| Scanned drawing support | 0% | 80% |
| Quantity accuracy | Low | ±10% |
| Processing time/project | 10-30 min | <5 min |

## Resource Requirements

- 1 Backend Engineer (full-time)
- 1 ML Engineer (part-time, for prompt tuning)
- OpenAI API credits ($500-1000/month)
- Cloud infrastructure ($200-500/month)
