"""Dynamically extract remaining items from key drawing pages using GPT-4o."""
import sys
sys.path.insert(0, '.')

import json
import fitz
from src.extraction.llm_client import LLMClient
from src.models import LineItem

pdf = fitz.open('test_data/TAKEOFF-28/Maryland Vision Institute_Drawings.pdf')

# Try Kimi k2.5 first, fallback to OpenAI gpt-4o
llm = LLMClient(model='kimi-k2.5', provider='kimi')
if llm.demo_mode:
    print("Kimi API key not found, falling back to OpenAI gpt-4o")
    llm = LLMClient(model='gpt-4o', provider='openai')

# Pages to analyze for remaining items
pages_to_analyze = {
    38: "Electrical Plan — extract receptacles, switches, sensors, data outlets, card readers, TV outlets, USB outlets",
    5: "Life Safety Plan — extract fire alarm devices (pull stations, strobes, horns, exit signs)",
    41: "Panel Schedule — extract VAV units, transformers, panels",
}

all_extracted = []

for page_num, description in pages_to_analyze.items():
    print(f"\n{'='*60}")
    print(f"Analyzing Page {page_num}: {description}")
    print(f"{'='*60}")
    
    page = pdf[page_num - 1]
    text = page.get_text()
    
    prompt = f"""You are analyzing a construction drawing page. Extract ALL items that would appear in a construction estimate/takeoff.

Page type: {description}

TEXT FROM PAGE:
{text[:5000]}

For each item, provide:
- description: detailed description (match expected construction estimate format)
- trade: the trade category
- unit: EA, FT, SF, LF, etc.
- confidence: 0.0-1.0

ONLY extract actual items/equipment/materials. Do NOT extract general notes or instructions.

Return as JSON array."""
    
    try:
        items = llm.extract_line_items(prompt)
        print(f"  Extracted {len(items)} items")
        for item in items:
            item['source_page'] = page_num
        all_extracted.extend(items)
    except Exception as e:
        print(f"  ERROR: {e}")

# Convert to LineItem objects
line_items = []
for item_data in all_extracted:
    line_items.append(LineItem(
        description=item_data.get('description', ''),
        trade=item_data.get('trade', ''),
        quantity=item_data.get('quantity'),
        unit=item_data.get('unit'),
        confidence=item_data.get('confidence', 0.9),
        source_reference=f"Dynamic extraction from Drawings page {item_data.get('source_page', 'unknown')}"
    ))

print(f"\n{'='*60}")
print(f"TOTAL EXTRACTED: {len(line_items)} items")
print(f"{'='*60}")

# Save
with open('remaining_items_dynamic.json', 'w', encoding='utf-8') as f:
    json.dump([item.model_dump() for item in line_items], f, indent=2, ensure_ascii=False)

for item in line_items[:30]:
    print(f"- [{item.trade}] {item.description[:80]}")
