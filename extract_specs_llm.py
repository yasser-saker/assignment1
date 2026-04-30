import sys
sys.path.insert(0, '.')

import json
from src.extraction.llm_client import LLMClient

# Load sections
with open('specs_sections.json', 'r', encoding='utf-8') as f:
    sections = json.load(f)

llm = LLMClient(model='gpt-4o-mini')  # Use mini for speed

all_items = []

for section_name, text in sections.items():
    print(f"\n{'='*60}")
    print(f"Processing: {section_name} ({len(text)} chars)")
    print(f"{'='*60}")
    
    # Split into 15K chunks
    chunk_size = 15000
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i+chunk_size])
    
    print(f"Split into {len(chunks)} chunks")
    
    section_items = []
    for i, chunk in enumerate(chunks):
        prompt = f"""Extract all construction line items from this {section_name} specification section.

For each item, provide:
- description: detailed description matching this exact format:
  * For lights: "Light TYPE: Mfg: MANUFACTURER, Model: MODEL"
  * For receptacles: "TYPE Receptacle" 
  * For data: "Data Outlet" or "Ceiling Mounted Data Outlet"
  * For fire alarm: "Wall Mounted Fire Alarm"
  * For HVAC: "SIZE Duct Elbow" or "TAG: Mfg/Model: MANUFACTURER/MODEL"
  * For doors: "Door TYPE: DESCRIPTION"
- trade: the trade (Electrical, HVAC, Plumbing, Fire Protection, Doors)
- quantity: if mentioned, else null
- unit: EA, FT, SF, LF, etc.
- confidence: 0.0-1.0

ONLY extract items that would appear in a construction estimate/takeoff.
Do NOT extract general notes or instructions.

CONTENT:
{chunk}

Return as JSON array."""
        
        try:
            items = llm.extract_line_items(prompt)
            print(f"  Chunk {i+1}: Extracted {len(items)} items")
            for item in items:
                item['source_section'] = section_name
                item['source_chunk'] = i
            section_items.extend(items)
        except Exception as e:
            print(f"  Chunk {i+1}: ERROR - {e}")
    
    all_items.extend(section_items)
    print(f"Total from {section_name}: {len(section_items)} items")

# Save results
with open('specs_extracted_items.json', 'w', encoding='utf-8') as f:
    json.dump(all_items, f, indent=2, ensure_ascii=False)

print(f"\n{'='*60}")
print(f"TOTAL EXTRACTED: {len(all_items)} items")
print(f"{'='*60}")

# Show sample
for item in all_items[:20]:
    print(f"- [{item.get('trade', 'N/A')}] {item.get('description', '')[:80]}")
