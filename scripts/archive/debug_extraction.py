import time
import sys
sys.path.insert(0, '.')

print("Starting debug extraction...")
start_total = time.time()

print("[1] Importing modules...")
from src.ingestion.ingestion_pipeline import IngestionPipeline
from src.extraction.extraction_engine import ExtractionEngine
from src.extraction.prompt_templates import build_extraction_prompt

print("[2] Creating pipeline...")
pipeline = IngestionPipeline()

print("[3] Running ingestion...")
start = time.time()
results = pipeline.process_project(
    'client_files/01_Sample_Projects_With_Expected_Output/01_Sample_Projects_With_Expected_Output/TAKEOFF-28 - Maryland Vision Institute/Project Files',
    'TAKEOFF-28'
)
print(f"Ingestion took {time.time()-start:.1f}s")

print("[4] Finding drawings file...")
drawings = [r for r in results if 'Drawings' in r.file_name and 'Break' not in r.file_name][0]
print(f"Drawings: {len(drawings.pages)} pages")

print("[5] Creating engine...")
engine = ExtractionEngine()

print("[6] Chunking...")
chunks = engine._chunk_pages(drawings)
print(f"Chunks: {len(chunks)}")

print("[7] Extracting chunk by chunk...")
all_items = []
for i, chunk in enumerate(chunks):
    chunk_start = time.time()
    print(f"  Chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
    prompt = build_extraction_prompt(
        project_name='TAKEOFF-28',
        file_name=drawings.file_name,
        page_number=0,
        file_type=drawings.file_type,
        content=chunk
    )
    try:
        items = engine.llm_client.extract_line_items(prompt)
    except Exception as e:
        print(f"    Error: {e}")
        continue
    print(f"    Got {len(items)} items in {time.time()-chunk_start:.1f}s")
    all_items.extend(items)

print(f"[8] Done. Total items: {len(all_items)}. Total time: {time.time()-start_total:.1f}s")
