import fitz

# Extract text from Specifications.pdf to find color codes and product codes
doc = fitz.open(r"test_data/TAKEOFF-28/Maryland Vision Institute_Specifications.pdf")

# Search for paint-related sections
paint_sections = []
for page_num in range(min(100, len(doc))):  # Check first 100 pages
    page = doc.load_page(page_num)
    text = page.get_text()
    
    # Look for paint/color references
    if any(keyword in text for keyword in ["PNT-", "Sherwin Williams", "Eggshell", "Glossy", "Flat", "Color:", "PAINTING"]):
        # Extract relevant lines
        lines = text.split('\n')
        for line in lines:
            if any(keyword in line for keyword in ["PNT-", "Sherwin Williams", "Color:", "Type:", "Eggshell", "Flat", "Glossy"]):
                paint_sections.append(f"Page {page_num + 1}: {line.strip()}")

doc.close()

print("=== PAINT/ COLOR REFERENCES FOUND ===")
for item in paint_sections[:30]:
    print(item)
