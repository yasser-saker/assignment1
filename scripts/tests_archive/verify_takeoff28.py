import sys
sys.path.insert(0, '.')
from src.evaluation.evaluator import Evaluator
from rapidfuzz import fuzz
import json

eval = Evaluator(fuzzy_threshold=40)

# Load prediction
pred_path = 'outputs/TAKEOFF-28/TAKEOFF-28_prediction.json'
with open(pred_path, 'r') as f:
    pred_data = json.load(f)
predicted_items = pred_data.get('line_items', [])

# Load expected
expected_path = r'\\?\D:\my_files\programming\Projects\assignment1\new project\new project\client_files\01_Sample_Projects_With_Expected_Output\01_Sample_Projects_With_Expected_Output\TAKEOFF-28 - Maryland Vision Institute\Expected Manual Output\Estimate - MARYLAND VISION INSTITUTE.xlsx'
expected_items = eval.load_expected_excel(expected_path)

print(f'Total predicted: {len(predicted_items)}')
print(f'Total expected: {len(expected_items)}')
print(f'\n=== MATCHING DETAILS ===')

# Track which predicted items are used
predicted_used = [False] * len(predicted_items)
matched_count = 0

for i, exp in enumerate(expected_items):
    best_score = 0
    best_pred_idx = -1
    for j, pred in enumerate(predicted_items):
        if predicted_used[j]:
            continue
        score = fuzz.partial_ratio(exp['description'].lower(), pred.get('description', '').lower())
        if score > best_score:
            best_score = score
            best_pred_idx = j
    
    if best_score >= 40 and best_pred_idx >= 0:
        matched_count += 1
        predicted_used[best_pred_idx] = True
        status = 'MATCHED'
    else:
        status = 'MISSING'
    
    print(f'\n{i+1}. [{status}] Score: {best_score}')
    print(f'   Expected: {exp["description"][:100]}')
    if best_pred_idx >= 0:
        print(f'   Predicted: {predicted_items[best_pred_idx].get("description", "")[:100]}')

print(f'\n=== SUMMARY ===')
print(f'Matched: {matched_count}/{len(expected_items)}')
print(f'Unused predicted items: {sum(1 for u in predicted_used if not u)}')

# Check for duplicate matching (same predicted item matching multiple expected)
print(f'\n=== CHECKING FOR ONE-TO-ONE MATCHING ===')
# Re-run without tracking used items to see if any predicted item would match multiple expected
pred_match_counts = [0] * len(predicted_items)
for exp in expected_items:
    best_score = 0
    best_pred_idx = -1
    for j, pred in enumerate(predicted_items):
        score = fuzz.partial_ratio(exp['description'].lower(), pred.get('description', '').lower())
        if score > best_score:
            best_score = score
            best_pred_idx = j
    if best_score >= 40:
        pred_match_counts[best_pred_idx] += 1

duplicates = [(j, c) for j, c in enumerate(pred_match_counts) if c > 1]
print(f'Predicted items matched by multiple expected: {len(duplicates)}')
for idx, count in duplicates[:5]:
    print(f'  Item {idx} matched {count} times: {predicted_items[idx].get("description", "")[:80]}')
