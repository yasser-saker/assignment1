import fitz, re
pdf_path = 'test_data/TAKEOFF-28/Maryland Vision Institute_Drawings.pdf'
doc = fitz.open(pdf_path)
for i in range(24, min(41, len(doc))):
    page = doc.load_page(i)
    text = page.get_text()
    if not text.strip():
        continue
    print('Page %d:' % (i+1))
    duct = re.findall(r'\d+"\s*[xX]\s*\d+"', text)
    if duct:
        print('  Duct: %s' % list(set(duct))[:5])
    elec = re.findall(r'(?i)(occupancy sensor|vacancy sensor|daylight sensor|single pole|three way|dimmer)', text)
    if elec:
        print('  Elec: %s' % list(set(elec))[:5])
    if not duct and not elec:
        print('  (no duct/electrical text)')
doc.close()
