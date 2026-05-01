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

# Check which predicted items match S-2 expected (index 52)
s2_exp = expected_items[52]['description']
print('=== Which predicted items match S-2 expected? ===')
for j, pred in enumerate(predicted_items):
    score = compute_match_score(s2_exp, pred.get('description', ''))
    if score >= 60:
        print(f"  Predicted {j}: Score={score:.0f}, {pred.get('description', '')[:80]}")

# Check which predicted items match R-1 expected (index 55)
r1_exp = expected_items[55]['description']
print('\n=== Which predicted items match R-1 expected? ===')
for j, pred in enumerate(predicted_items):
    score = compute_match_score(r1_exp, pred.get('description', ''))
    if score >= 60:
        print(f"  Predicted {j}: Score={score:.0f}, {pred.get('description', '')[:80]}")

# Check which predicted items match RTU-1 expected (index 56)
rtu1_exp = expected_items[56]['description']
print('\n=== Which predicted items match RTU-1 expected? ===')
for j, pred in enumerate(predicted_items):
    score = compute_match_score(rtu1_exp, pred.get('description', ''))
    if score >= 60:
        print(f"  Predicted {j}: Score={score:.0f}, {pred.get('description', '')[:80]}")
