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

# Check which expected items match Predicted 118 (S-2 Diffuser)
pred118 = predicted_items[118]['description']
print('=== Which expected items match Predicted 118 (S-2 Diffuser)? ===')
for i, exp in enumerate(expected_items):
    score = compute_match_score(exp['description'], pred118)
    if score >= 60:
        print(f"  Expected {i}: Score={score:.0f}, {exp['description'][:60]}")

# Check which expected items match Predicted 121 (R-1 Grille)
pred121 = predicted_items[121]['description']
print('\n=== Which expected items match Predicted 121 (R-1 Grille)? ===')
for i, exp in enumerate(expected_items):
    score = compute_match_score(exp['description'], pred121)
    if score >= 60:
        print(f"  Expected {i}: Score={score:.0f}, {exp['description'][:60]}")

# Check which expected items match Predicted 125 (RTU-1)
pred125 = predicted_items[125]['description']
print('\n=== Which expected items match Predicted 125 (RTU-1)? ===')
for i, exp in enumerate(expected_items):
    score = compute_match_score(exp['description'], pred125)
    if score >= 60:
        print(f"  Expected {i}: Score={score:.0f}, {exp['description'][:60]}")
