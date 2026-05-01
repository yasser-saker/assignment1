import sys
sys.path.insert(0, '.')

from src.extraction.llm_client import LLMClient
import fitz

pdf = fitz.open('test_data/TAKEOFF-28/Maryland Vision Institute_Drawings.pdf')
page32 = pdf[31]
text32 = page32.get_text()

text = text32[:4000]

llm = LLMClient(model='gpt-4o')

prompt = f"""Extract all equipment items from this mechanical schedule as JSON array.
Each item should have: tag, description, trade, unit.

Focus on: Diffusers (S-1, S-2, S-3, S-4, R-1), Exhaust Fans (EF-1, EF-2), AC Units (AC-1,2,3), Heat Pumps (HP-1,2,3), VAV units (VAV-5,6,7,8,9).

For diffusers, format description as:
"TAG \n-B.O.D: MANUFACTURER\n-Nominal Module Size: SIZE\n-CFM: RANGE\n-Material: MATERIAL"

For AC/HP, format as:
"TAG: B.O.D Outdoor Unit : MANUFACTURER/MODEL" or "TAG: B.O.D Indoor Unit : MANUFACTURER/MODEL"

For VAV, format as:
"TAG:\n-Mfg/Model: JCI/TSS"

SCHEDULE TEXT:
{text}

Return JSON array only."""

items = llm.extract_line_items(prompt)
print(f'Extracted {len(items)} items:')
for item in items:
    print('-', item.get('tag', ''), ':', item.get('description', '')[:80])
