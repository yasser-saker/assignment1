import sys
sys.path.insert(0, '.')
from src.evaluation.evaluator import Evaluator, compute_match_score
import json

project_id = 'TAKEOFF-28'
pred_path = f'outputs/{project_id}/{project_id}_prediction.json'
expected_path = r'\\?\D:\my_files\programming\Projects\assignment1\new project\new project\client_files\01_Sample_Projects_With_Expected_Output\01_Sample_Projects_With_Expected_Output\TAKEOFF-28 - Maryland Vision Institute\Expected Manual Output\Estimate - MARYLAND VISION INSTITUTE.xlsx'

eval = Evaluator(fuzzy_threshold=60)
expected_items = eval.load_expected_excel(expected_path)

with open(pred_path, 'r') as f:
    pred_data = json.load(f)
predicted_items = pred_data.get('line_items', [])

# Full evaluator logic
predicted_matched = [False] * len(predicted_items)
matches = []
misses = []

for i, exp in enumerate(expected_items):
    best_score = 0
    best_pred_idx = -1
    
    for j, pred in enumerate(predicted_items):
        if predicted_matched[j]:
            continue
        score = compute_match_score(exp['description'], pred.get('description', ''))
        if score > best_score:
            best_score = score
            best_pred_idx = j
    
    if best_score >= 60:
        predicted_matched[best_pred_idx] = True
        matches.append((i, best_pred_idx, best_score, exp['description'], predicted_items[best_pred_idx].get('description', '')))
    else:
        misses.append((i, best_score, exp['description']))

print(f'Matches: {len(matches)}')
print(f'Misses: {len(misses)}')
print(f'Total: {len(matches) + len(misses)}')

# Show first 20 misses
print('\n=== FIRST 20 MISSES ===')
for i, score, desc in misses[:20]:
    print(f'  Expected {i}: Score={score:.0f}, {desc[:80]}')

# Show all matches
print('\n=== ALL MATCHES ===')
for exp_idx, pred_idx, score, exp_desc, pred_desc in matches:
    print(f'  Expected {exp_idx} -> Predicted {pred_idx} (score={score:.0f})')
    print(f'    Exp:  {exp_desc[:70]}')
    print(f'    Pred: {pred_desc[:70]}')
