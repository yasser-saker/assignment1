import json
from rapidfuzz import fuzz

# Load prediction
with open('outputs/TAKEOFF-28/TAKEOFF-28_prediction.json', 'r') as f:
    pred = json.load(f)

# Load expected
import sys
sys.path.insert(0, '.')
from src.evaluation.evaluator import Evaluator
evaluator = Evaluator()
expected = evaluator.load_expected_excel('test_data/TAKEOFF-28/TAKEOFF-28_EXPECTED_OUTPUT.xlsx')

pred_descs = [item['description'] for item in pred['line_items']]

algorithms = {
    'ratio': fuzz.ratio,
    'partial_ratio': fuzz.partial_ratio,
    'token_sort_ratio': fuzz.token_sort_ratio,
    'token_set_ratio': fuzz.token_set_ratio,
    'WRatio': fuzz.WRatio,
}

for name, algo in algorithms.items():
    matched = 0
    used_pred = set()
    
    for exp in expected:
        best_score = 0
        best_idx = -1
        
        for j, pred_desc in enumerate(pred_descs):
            if j in used_pred:
                continue
            
            score = algo(exp['description'].lower(), pred_desc.lower())
            if score > best_score:
                best_score = score
                best_idx = j
        
        if best_score >= 40:  # Test with 40 threshold
            matched += 1
            used_pred.add(best_idx)
    
    print(f"{name:20s}: {matched}/121 ({matched/121*100:.1f}%)")
