import json
from rapidfuzz import fuzz

with open('outputs/TAKEOFF-28/TAKEOFF-28_prediction.json', 'r') as f:
    pred = json.load(f)

pred_descs = [item['description'] for item in pred['line_items']]

expected = "PNT-01 (9'-0\" High):\n-Mfg: Sherwin Williams\n-Color: Wordly Gray #SW7043\n-Type: Eggshell"

for i, desc in enumerate(pred_descs):
    score = fuzz.ratio(expected.lower(), desc.lower())
    if score > 50:
        print(f'Item {i}: Score={score}')
        print('Desc:', repr(desc))
        print()
