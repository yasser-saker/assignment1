import fitz

pdf = fitz.open('test_data/TAKEOFF-28/Maryland Vision Institute_Drawings.pdf')

keywords = ['LIGHTING SCHEDULE', 'LIGHT B', 'LIGHT D', 'LIGHT E', 'LIGHT F', 'PRESCOLITE', 'LUMINI', 'LFR-4', 'CSDHM']

for i in range(len(pdf)):
    text = pdf[i].get_text()
    for kw in keywords:
        if kw in text.upper():
            print(f'Page {i+1}: Found "{kw}"')
            # Print context
            idx = text.upper().find(kw)
            start = max(0, idx - 100)
            end = min(len(text), idx + 200)
            print(text[start:end])
            print('---')
            break
