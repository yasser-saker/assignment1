import fitz

pdf = fitz.open('test_data/TAKEOFF-28/Maryland Vision Institute_Drawings.pdf')

# Read key pages
for page_num in [36, 37, 38, 41]:
    print(f"\n{'='*60}")
    print(f"PAGE {page_num}")
    print(f"{'='*60}")
    page = pdf[page_num - 1]
    text = page.get_text()
    print(text[:3000])
