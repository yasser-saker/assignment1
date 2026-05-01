import fitz, re
pdf_path = 'test_data/TAKEOFF-50/VAPHCS Specs 100Pct BID Set REV 3.pdf'
doc = fitz.open(pdf_path)
for i in range(len(doc)):
    page = doc.load_page(i)
    text = page.get_text()
    if not text.strip():
        continue
    # Look for equipment-related content
    if re.search(r'(?i)(rtu-|vav-|ef-|hp-|cfm|equipment schedule|diffuser)', text):
        print('Page %d has equipment content' % (i+1))
        preview = text[:300].replace('\n', ' ')
        print('  Preview: ' + preview)
        print()
doc.close()
