import pdfplumber
import re

def extract_project_context(pdf_path):
    """Extract finish schedules, color codes, and product codes from Specifications."""
    context = {
        "paint_colors": [],
        "product_codes": {},
        "finish_schedules": [],
        "room_schedules": []
    }
    
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages[:150]):  # First 150 pages
            text = page.extract_text() or ""
            
            # Look for paint/color references
            lines = text.split('\n')
            for line in lines:
                # Extract color codes like SW7043, PNT-01, etc.
                color_match = re.search(r'(SW\d{4}|PNT-\d{2}|CL-\d{2}|GWB-\d{2})', line)
                if color_match:
                    context["product_codes"][color_match.group(1)] = line.strip()
                
                # Extract finish schedule entries
                if "Finish Schedule" in line or "Room Schedule" in line:
                    context["finish_schedules"].append(f"Page {i+1}: {line.strip()}")
                
                # Extract color names
                if "Color:" in line or "Finish:" in line:
                    context["paint_colors"].append(line.strip())
            
            # Extract tables
            tables = page.extract_tables()
            for table in tables:
                if table and len(table) > 1:
                    header = table[0]
                    if any(keyword in str(header) for keyword in ['Room', 'Finish', 'Color', 'Paint', 'Wall', 'Ceiling', 'Floor']):
                        context["room_schedules"].append({
                            "page": i+1,
                            "header": header,
                            "rows": table[1:]
                        })
    
    return context

# Extract from TAKEOFF-28 Specifications
context = extract_project_context("test_data/TAKEOFF-28/Maryland Vision Institute_Specifications.pdf")

print("=== PRODUCT CODES ===")
for code, line in list(context["product_codes"].items())[:20]:
    print(f"{code}: {line[:100]}")

print(f"\n=== PAINT COLORS ({len(context['paint_colors'])} found) ===")
for color in context["paint_colors"][:20]:
    print(color[:100])

print(f"\n=== ROOM/FINISH SCHEDULES ({len(context['room_schedules'])} tables) ===")
for sched in context["room_schedules"][:5]:
    print(f"\nPage {sched['page']}:")
    print(f"Header: {sched['header']}")
    for row in sched['rows'][:5]:
        print(f"  {row}")
