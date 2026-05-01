import fitz

pdf = fitz.open('test_data/TAKEOFF-28/Maryland Vision Institute_Drawings.pdf')

# Search for electrical, mechanical, lighting schedules
keywords = ['E-1', 'M-1', 'LIGHTING', 'ELECTRICAL PLAN', 'MECHANICAL PLAN', 'FIRE ALARM', 'LIGHTING SCHEDULE', 'DOOR SCHEDULE']

found = {}
for i in range(len(pdf)):
    text = pdf[i].get_text()
    for kw in keywords:
        if kw in text.upper():
            if kw not in found:
                found[kw] = []
            found[kw].append(i+1)

for kw, pages in found.items():
    print(f'{kw}: Pages {pages[:10]}')  # Show first 10 matches
