import fitz

pdf = fitz.open('test_data/TAKEOFF-28/Maryland Vision Institute_Specifications.pdf')

# Search for key sections in first 100 pages
keywords = ['TABLE OF CONTENTS', 'DIVISION 15', 'DIVISION 16', 'ELECTRICAL', 'MECHANICAL', 'HVAC', 'PLUMBING', 'FIRE PROTECTION', 'DOORS', 'LIGHTING', 'RECEPTACLE']

for i in range(min(100, len(pdf))):
    text = pdf[i].get_text()
    for kw in keywords:
        if kw in text.upper():
            print(f'Page {i+1}: Found "{kw}"')
            break
