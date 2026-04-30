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

# Replicate evaluator logic with print
predicted_matched = [False] * len(predicted_items)
expected_matched = [False] * len(expected_items)

# Focus on expected items 50-60 (S-1 through AC-3)
for i in range(50, 61):
    if i >= len(expected_items):
        break
    exp = expected_items[i]
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
        expected_matched[i] = True
        print(f"MATCH: Expected {i} -> Predicted {best_pred_idx} (score={best_score:.0f})")
        print(f"  Exp:  {exp['description'][:60]}")
        print(f"  Pred: {predicted_items[best_pred_idx].get('description', '')[:60]}")
    else:
        print(f"MISS:  Expected {i} (best_score={best_score:.0f})")
        print(f"  Exp:  {exp['description'][:60]}")
    print()
