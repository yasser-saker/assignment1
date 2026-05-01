import sys
sys.path.insert(0, '.')

from src.evaluation.evaluator import Evaluator

evaluator = Evaluator()
expected = evaluator.load_expected_excel('test_data/TAKEOFF-28/TAKEOFF-28_EXPECTED_OUTPUT.xlsx')

print('Total expected items:', len(expected))
print()
print('=== FIRST 20 EXPECTED ITEMS ===')
for item in expected[:20]:
    print('Qty=' + str(item['quantity']) + ', Unit=' + item['unit'] + ', Desc=' + item['description'][:60])
