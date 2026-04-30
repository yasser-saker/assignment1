import fitz
import json

pdf = fitz.open('test_data/TAKEOFF-28/Maryland Vision Institute_Specifications.pdf')

# Define key sections with page ranges (1-indexed)
sections = {
    'ELECTRICAL': [21, 23, 25, 26, 27, 32, 41, 44, 54, 83, 92, 100],
    'HVAC_MECHANICAL': [5, 31, 37, 51, 79, 81, 82, 89, 90, 91],
    'PLUMBING': [47, 53, 55, 95],
    'FIRE_PROTECTION': [50, 59],
    'DOORS': [43, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 76, 77, 78],
}

all_text = {}
for section, pages in sections.items():
    section_text = f"\n{'='*60}\nSECTION: {section}\n{'='*60}\n"
    for p in pages:
        if p <= len(pdf):
            text = pdf[p-1].get_text()
            section_text += f"\n--- Page {p} ---\n{text[:3000]}\n"  # Limit to 3000 chars per page
    all_text[section] = section_text

# Save for processing
with open('specs_sections.json', 'w', encoding='utf-8') as f:
    json.dump(all_text, f, ensure_ascii=False)

print("Sections extracted:")
for section, text in all_text.items():
    print(f"  {section}: {len(text)} chars")
