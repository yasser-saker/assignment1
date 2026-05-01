import fitz, re
pdf_path = 'test_data/TAKEOFF-50/VAPHCS - Mechanical Drawings.pdf'
doc = fitz.open(pdf_path)
for i in range(len(doc)):
    page = doc.load_page(i)
    text = page.get_text()
    if not text.strip():
        continue
    if re.search(r'(?i)(equipment schedule|diffuser schedule|rtu-|vav-|ef-|cfm)', text):
        print('Page %d has equipment content' % (i+1))
        preview = text[:200].replace('\n', ' ')
        print('  Preview: ' + preview)
        print()
doc.close()
