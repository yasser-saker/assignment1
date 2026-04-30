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

# Check which expected items match S-2 predicted
s2_pred = 'S-2 Diffuser: 24" x 24" Aluminum, 4-Way, Anemostat, Supply, Neck Size: 8", Finish to be selected by Architect'
print('=== Which expected items match S-2 predicted? ===')
for i, exp in enumerate(expected_items):
    score = compute_match_score(exp['description'], s2_pred)
    if score >= 60:
        print(f"  Expected {i}: Score={score:.0f}, {exp['description'][:60]}")

# Check which expected items match R-1 predicted
r1_pred = 'R-1 Grille: 24" x 12" Aluminum, Grid Core, Anemostat, Return, Finish to be selected by Architect'
print('\n=== Which expected items match R-1 predicted? ===')
for i, exp in enumerate(expected_items):
    score = compute_match_score(exp['description'], r1_pred)
    if score >= 60:
        print(f"  Expected {i}: Score={score:.0f}, {exp['description'][:60]}")

# Check which expected items match RTU-1 predicted
rtu1_pred = 'RTU-1 Rooftop Air Conditioning Unit: Variable Air Volume, 8,300 CFM, Natural Gas Heating Furnace, Johnson Controls / KD28T'
print('\n=== Which expected items match RTU-1 predicted? ===')
for i, exp in enumerate(expected_items):
    score = compute_match_score(exp['description'], rtu1_pred)
    if score >= 60:
        print(f"  Expected {i}: Score={score:.0f}, {exp['description'][:60]}")
