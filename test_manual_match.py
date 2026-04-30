import json
from rapidfuzz import fuzz

# Load prediction
with open('outputs/TAKEOFF-28/TAKEOFF-28_prediction.json', 'r') as f:
    pred = json.load(f)

# Expected PNT-01 (9'-0" High)
expected_desc = "PNT-01 (9'-0\" High):\n-Mfg: Sherwin Williams\n-Color: Wordly Gray #SW7043\n-Type: Eggshell"

print("Looking for match for:")
print(expected_desc)
print()

for i, item in enumerate(pred['line_items']):
    pred_desc = item['description']
    score = fuzz.ratio(expected_desc.lower(), pred_desc.lower())
    if score > 50:
        print(f"Item {i}: Score={score:.1f}%")
        print(f"  Predicted: {pred_desc}")
        print()
