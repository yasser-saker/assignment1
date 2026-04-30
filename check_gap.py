import json

with open("outputs/TAKEOFF-28/TAKEOFF-28_prediction.json", "r") as f:
    pred = json.load(f)

print("=== PREDICTED (first 10) ===")
for item in pred["line_items"][:10]:
    print("- " + item["trade"] + ": " + item["description"][:70])

print()
print("=== MISSING (first 10) ===")
for miss in pred["evaluation_when_gold_available"]["missing_items"][:10]:
    print("- " + miss[:70])

print()
print("=== EXTRA (first 10) ===")
for extra in pred["evaluation_when_gold_available"]["extra_items"][:10]:
    print("- " + extra[:70])
