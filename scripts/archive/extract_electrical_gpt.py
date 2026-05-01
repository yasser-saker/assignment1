import sys
sys.path.insert(0, '.')

from src.extraction.llm_client import LLMClient
import fitz

pdf = fitz.open('test_data/TAKEOFF-28/Maryland Vision Institute_Drawings.pdf')

# Get electrical plan (page 38) and panel schedule (page 41)
page38 = pdf[37]
page41 = pdf[40]

text38 = page38.get_text()
text41 = page41.get_text()

llm = LLMClient(model='gpt-4o')

# Extract electrical items from page 38
prompt38 = f"""From this electrical plan text, extract all electrical device items.

The text contains room names and device codes like:
- GFI = GFCI Receptacle
- GFI/C = Ceiling Mounted GFCI Receptacle  
- C = Ceiling Mounted Receptacle
- USB = USB Outlet
- TV = TV Outlet
- Monitor = Monitor/Display Outlet
- CR = Card Reader (Door Access)
- RC = Ceiling Mounted Receptacle
- D1, D2 = Door devices

For each room, count the devices and create line items.

TEXT:
{text38[:4000]}

Return JSON array with: description, trade="Electrical", quantity, unit="EA", confidence."""

items38 = llm.extract_line_items(prompt38)
print(f"Page 38: {len(items38)} items")
for item in items38[:10]:
    print('-', item.get('description', '')[:80])

# Extract VAV and Fire Alarm from page 41
prompt41 = f"""From this electrical panel schedule text, extract:
1. VAV units mentioned (VAV-9, VAV-10, VAV-12, VAV-13, etc.) — format: "VAV-XX: Mfg/Model: JCI/TSS"
2. Fire Alarm items — format: "Wall Mounted Fire Alarm" or "Fire Alarm Control Panel"
3. Any other equipment items

TEXT:
{text41[:4000]}

Return JSON array with: description, trade, quantity, unit="EA", confidence."""

items41 = llm.extract_line_items(prompt41)
print(f"\nPage 41: {len(items41)} items")
for item in items41:
    print('-', item.get('description', '')[:80])
