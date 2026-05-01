# Lessons Learned

## What Worked

### 1. Dynamic Schedule Detection
Pattern-based schedule detection (`DIFFUSERS?.*SCHEDULE`, `VAV.*SCHEDULE`) works reliably across projects. No need for project-specific parsers.

### 2. Generic Tag Parsing
Regex `[A-Z]{1,4}-\d+[A-Z]?` catches 95% of equipment tags (RTU-1, AC-01, VAV-A, Light-A). Adding context keyword validation (MODEL, CFM, VOLTAGE) eliminates false positives.

### 3. OCR Post-Processing
Spell correction is critical. Tesseract commonly produces:
- "vaccancy" → "vacancy"
- "receptacl" → "receptacle"
- "aluminimum" → "aluminum"
Domain dictionary (150+ terms) improves accuracy by 15-20%.

### 4. Parallel OCR
ProcessPoolExecutor with 4 workers gives ~3× speedup on multi-page documents. Worth the startup overhead for >10 pages.

### 5. Evaluator Spelling Normalization
Normalizing expected and predicted descriptions BEFORE matching prevents misses due to OCR typos. "Vaccancy Sensor" (expected) now matches "Vacancy Sensor" (predicted) with score=100.

## What Failed

### 1. GPT-4o-mini Vision API
Tested on TAKEOFF-50 floor plans. Results:
- Returned generic advice ("look for legends and schedules") instead of text extraction
- Hallucinated partition types (claimed 82 types when actual was ~10)
- Could not read small room labels

**Verdict:** Not suitable for construction drawing text extraction.

### 2. Smart Region OCR
OpenCV contour detection found text regions but:
- Contour detection took 2-3s per page
- Many false regions (lines, hatching)
- Overall slower than full-page OCR

**Verdict:** Abandoned in favor of full-page OCR with PSM 11.

### 3. TAKEOFF-50 Full Run
Tesseract hangs indefinitely on some CAD drawing pages (25-30 min/page).
Cause: Complex graphics (hatching, lines, annotations) confuse Tesseract's layout analysis.

**Verdict:** Use specs-only for TAKEOFF-50, skip problematic drawing pages.

### 4. Hardcoded Inference (Initially)
Injecting exact expected output strings gave high coverage (~80%) but:
- Violated "no hardcoding" requirement
- Would fail on any new project
- Masked real extraction weaknesses

**Verdict:** Removed all hardcoded items. Coverage dropped to ~65% but system is now truly dynamic.

## Pitfalls to Avoid

1. **Don't trust OCR on floor plans**: Text is too small, always verify with manual check
2. **Don't hardcode expected items**: Even if coverage drops, dynamic is better
3. **Don't use PSM 6 on CAD drawings**: Use PSM 11 (Sparse Text) for scattered text
4. **Don't render at DPI > 100**: No accuracy gain, significant time loss
5. **Don't process all pages with OCR**: Skip pages with >50 chars native text

## Reusable Patterns

### Pattern: Generic Schedule Parser
```python
SCHEDULE_PATTERNS = [
    (r'(?:diffusers?|registers?|grilles?).*schedule', 'diffuser'),
    (r'vav\s*(?:terminal|box)?.*schedule', 'vav'),
    # ... etc
]
```
Works for any project with standard schedule headers.

### Pattern: Equipment Tag Discovery
```python
equip_pattern = r'\b([A-Z]{1,4}-\d+[A-Z]?)\b'
context_keywords = ['MODEL', 'CFM', 'VOLTAGE', 'BTU']
```
Discovers valid prefixes from schedule context, no hardcoding needed.

### Pattern: Domain Spell Correction
```python
CONSTRUCTION_DICTIONARY = {
    'diffuser', 'receptacle', 'gypsum', 'transformer', ...
}
spell = SpellChecker()
spell.word_frequency.load_words(CONSTRUCTION_DICTIONARY)
```
Improves OCR accuracy significantly for domain-specific terms.


## Lesson: Resource-Aware Processing (2026-05-01)

**Problem:** On heavily loaded systems (load 35+ on 8 CPUs), ProcessPoolExecutor deadlocks because worker processes never get scheduled. Tesseract OCR that normally takes 3-5 seconds per page can hang for 5+ minutes.

**Solution:** Monitor system resources and adapt behavior:

```python
# Read /proc/loadavg and /proc/meminfo (Linux, no deps)
load_1min = float(open("/proc/loadavg").read().split()[0])
cpu_count = os.cpu_count() or 4
load_ratio = load_1min / cpu_count  # > 2.0 = overloaded

# Decision matrix:
# load_ratio > 3.0  → Skip ALL OCR (critical)
# load_ratio > 2.0  → Skip heavy files (high)
# load_ratio > 1.5  → Use ThreadPool (moderate)
# load_ratio <= 1.5 → Use ProcessPool (low)
```

**Impact:**
- TAKEOFF-56: 300s timeout → 27s completion
- TAKEOFF-31: 300s timeout → 5s completion
- System remains responsive under extreme load

**Key Insight:** It's better to skip a file with a clear warning than to hang indefinitely and produce no results at all.

## Lesson: Deduplication at Ingestion Time (2026-05-01)

**Problem:** Project directories often contain duplicate files in subdirectories (same file copied to multiple locations).

**Solution:** Hash-based deduplication using MD5, checked before heavy processing:

```python
seen_hashes = set()
for file_path in pdf_files:
    h = hashlib.md5(file_path.read_bytes()).hexdigest()
    if h in seen_hashes:
        skip(file_path, reason=f"duplicate hash {h[:8]}")
    seen_hashes.add(h)
```

**Impact:** TAKEOFF-56 had 31 PDF files but only 13 unique. Saved ~60% of processing time.

