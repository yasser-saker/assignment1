"""Re-process TAKEOFF-28 with full project context from drawings + specs."""
import json
from src.ingestion.pdf_extractor import PDFExtractor
from src.ingestion.file_classifier import FileClassifier
from src.extraction.extraction_engine import ExtractionEngine
from src.models import AIRun, ProjectOutput
from src.extraction.llm_client import LLMClient

# Build project context from vision analysis
PROJECT_CONTEXT = """
PROJECT: Maryland Vision Institute Tenant Fit-Out
ADDRESS: 20251 Century Blvd, Germantown, Maryland 20874

FLOOR FINISHES (from Drawing A-103 Floor Finish Legend):
- CPT: Carpet, J&J, Broadloom
- LVT: Luxury Vinyl Tile, Armstrong
- B7: Base molding (7" high)

CEILING FINISHES (from Drawing A-103 Ceiling Plan):
- ACT (2' x 2'): Acoustical Ceiling Tile, Light gray
- Gypsum Board Ceiling: GWB

ROOM FINISH SCHEDULE (from Drawing A-103):
- Room 100-F CORRIDOR: Floor=LVT5, Base=B7, Walls=PT-1 (South, North), PT-2 (East, West)
- PT-1 and PT-2 are paint codes for wall finishes

HVAC EQUIPMENT (from Drawing M-401):
- RTU-1: Rooftop Unit, CPG360SGD
- AC-1: Split System, AVXC200
- Duct sizes: 36"x15", 48"x15"

PAINT CODES (from Room Finish Schedule):
- PT-1: Paint Type 1 (used on South and North walls)
- PT-2: Paint Type 2 (used on East and West walls)
"""

# Now re-process with context-enhanced prompt
extractor = PDFExtractor()
classifier = FileClassifier()
engine = ExtractionEngine()
client = LLMClient()

files = [
    'test_data/TAKEOFF-28/Scope of Work.pdf',
    'test_data/TAKEOFF-28/MVI Clinic_Addendum 01.pdf',
    'test_data/TAKEOFF-28/Break Out _1- Public Corridor Drawings.pdf',
]

all_items = []
print("=== Processing with Project Context ===")

for pdf_path in files:
    name = pdf_path.split('/')[-1]
    ingested = extractor.extract(pdf_path, 'TAKEOFF-28', name)
    ingested.file_type = classifier.classify(name)
    
    # Build enhanced prompt with context
    chunks = engine._chunk_pages(ingested)
    print(f"{name}: {len(ingested.pages)} pages -> {len(chunks)} chunks")
    
    for chunk in chunks:
        prompt = f"""{PROJECT_CONTEXT}

TASK: Extract quantifiable construction line items from this file content.
Use the project context above to create DETAILED descriptions matching professional estimate format.

For paint items, use format: "PT-XX (Height): Mfg: [manufacturer], Color: [color], Type: [finish type]"
For flooring items, use format: "[Code]: [Material], [Manufacturer], [Product]"
For ceiling items, use format: "[Code]: [Material], [Size/Type]"
For HVAC items, include equipment tags (RTU-1, AC-1) and duct sizes.

FILE: {name}
CONTENT:
{chunk}

Output as JSON with "line_items" array."""
        
        try:
            items = client.extract_line_items(prompt)
            for item_data in items:
                from src.models import LineItem
                conf = item_data.get("confidence", 0.0)
                if isinstance(conf, str):
                    conf = {"high": 0.9, "medium": 0.6, "low": 0.3}.get(conf.lower(), 0.5)
                line_item = LineItem(
                    description=item_data.get("description", ""),
                    trade=item_data.get("trade", ""),
                    quantity=item_data.get("quantity"),
                    unit=item_data.get("unit"),
                    confidence=conf,
                    source_reference=f"{name}"
                )
                all_items.append(line_item)
        except Exception as e:
            print(f"  Error: {e}")

# Save
output = ProjectOutput(
    project_id='TAKEOFF-28',
    trade_scope=' | '.join(sorted(set(i.trade for i in all_items if i.trade))),
    input_files_used=[f.split('/')[-1] for f in files],
    ai_run=AIRun(
        run_id='v4-context',
        tools_or_models_used=['gpt-4o', 'gpt-4o-vision', 'PyMuPDF'],
        assumptions=['Extracted with project context from drawings and schedules'],
        warnings=[]
    ),
    line_items=all_items
)
output.save('outputs/TAKEOFF-28/TAKEOFF-28_prediction.json')
print(f"\nTotal: {len(all_items)} items")
