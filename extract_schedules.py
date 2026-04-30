import fitz  # PyMuPDF
from pathlib import Path

def find_schedule_pages(pdf_path):
    """Find pages containing 'Schedule' in drawings."""
    doc = fitz.open(pdf_path)
    schedule_pages = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()
        
        if any(keyword in text for keyword in ["Schedule", "SCHEDULE", "FINISH", "DOOR SCHEDULE", "ROOM SCHEDULE", "FINISH SCHEDULE"]):
            schedule_pages.append(page_num)
            print(f"Page {page_num + 1}: Found schedule content")
            # Print first few lines
            lines = [l.strip() for l in text.split('\n') if l.strip()][:5]
            for line in lines:
                print(f"  {line[:80]}")
    
    doc.close()
    return schedule_pages

# Check TAKEOFF-28 Drawings
print("=== TAKEOFF-28 Drawings ===")
pages_28 = find_schedule_pages("test_data/TAKEOFF-28/Maryland Vision Institute_Drawings.pdf")
print(f"Found {len(pages_28)} schedule pages")

# Check TAKEOFF-50 Drawings
print("\n=== TAKEOFF-50 Drawings ===")
for pdf_file in Path("test_data/TAKEOFF-50").glob("*.pdf"):
    if "Drawing" in pdf_file.name or "Architectural" in pdf_file.name:
        pages_50 = find_schedule_pages(str(pdf_file))
        print(f"{pdf_file.name}: {len(pages_50)} schedule pages")
