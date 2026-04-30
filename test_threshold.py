import sys
sys.path.insert(0, '.')

from src.evaluation.evaluator import Evaluator

for threshold in [60, 55, 50, 45, 40]:
    evaluator = Evaluator(fuzzy_threshold=threshold)
    report = evaluator.evaluate(
        'outputs/TAKEOFF-28/TAKEOFF-28_prediction.json',
        'test_data/TAKEOFF-28/TAKEOFF-28_EXPECTED_OUTPUT.xlsx'
    )
    print(f"Threshold {threshold}%: Matched {report.matched_items}/121 ({report.matched_items/121*100:.1f}%)")
