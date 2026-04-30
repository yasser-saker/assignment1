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

# Replicate exact evaluator matching logic
predicted_matched = [False] * len(predicted_items)
matches = []

for i, exp in enumerate(expected_items):
    best_score = 0
    best_pred_idx = -1
    
    for j, pred in enumerate(predicted_items):
        if predicted_matched[j]:
            continue
        score = fuzz.partial_ratio(exp['description'].lower(), pred.get('description', '').lower())
        if score > best_score:
            best_score = score
            best_pred_idx = j
    
    if best_score >= 40 and best_pred_idx >= 0:
        predicted_matched[best_pred_idx] = True
        matches.append({
            'expected_idx': i,
            'pred_idx': best_pred_idx,
            'score': best_score,
            'expected': exp['description'][:100],
            'predicted': predicted_items[best_pred_idx].get('description', '')[:100]
        })

print(f'Total matches: {len(matches)}')
print(f'Expected items: {len(expected_items)}')

# Categorize by score
high = [m for m in matches if m['score'] >= 80]
medium = [m for m in matches if 60 <= m['score'] < 80]
low = [m for m in matches if m['score'] < 60]

print(f'\nHigh quality matches (>=80): {len(high)}')
print(f'Medium quality (60-79): {len(medium)}')
print(f'Low quality (<60): {len(low)}')

print(f'\n=== HIGH QUALITY (>=80) ===')
for m in high:
    print(f"  Score {m['score']:.0f}: {m['expected'][:60]} -> {m['predicted'][:60]}")

print(f'\n=== MEDIUM QUALITY (60-79) ===')
for m in medium:
    print(f"  Score {m['score']:.0f}: {m['expected'][:60]} -> {m['predicted'][:60]}")

print(f'\n=== LOW QUALITY (<60) - POTENTIALLY FALSE POSITIVES ===')
for m in low:
    print(f"  Score {m['score']:.0f}: {m['expected'][:60]} -> {m['predicted'][:60]}")
