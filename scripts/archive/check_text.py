import pdfplumber
import re

pdf_path = 'test_data/TAKEOFF-28/Maryland Vision Institute_Drawings.pdf'
with pdfplumber.open(pdf_path) as pdf:
    # Check pages 25-41 (mechanical/electrical typically at end)
    for i in range(24, min(41, len(pdf.pages))):
        page = pdf.pages[i]
        text = page.extract_text() or ''
        if not text.strip():
            continue
        print(f'\n=== Page {i+1} ===')
        # Duct patterns
        duct_matches = re.findall(r'\d+"\s*[xX]\s*\d+"', text)
        if duct_matches:
            print(f'  Duct sizes: {list(set(duct_matches))[:10]}')
        # Electrical
        elec_matches = re.findall(r'(?i)(occupancy sensor|vacancy sensor|daylight sensor|single pole|three way switch|dimmer)', text)
        if elec_matches:
            print(f'  Electrical: {elec_matches[:5]}')
        # VAV
        vav_matches = re.findall(r'VAV-\d+.*?\n', text)
        if vav_matches:
            print(f'  VAV: {len(vav_matches)} mentions')
        # Show first 200 chars
        print(f'  Text preview: {text[:200].replace(chr(10), " ")}')
