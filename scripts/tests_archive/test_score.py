import sys
sys.path.insert(0, '.')
from src.evaluation.evaluator import compute_match_score, get_item_type

exp = 'S-1:\n-B.O.D: ANEMOSTAT / E\n-Nominal Module Size: 12"x12"\n-CFM: 0-95'
pred = 'S-1: Lustertone 23-1/2"x18-1/4"x5-3/8" Deep Drop-In Single Bowl Sink, 18 Gauge, Type 304 Stainless Steel'

print(f'Exp type: {get_item_type(exp)}')
print(f'Pred type: {get_item_type(pred)}')
print(f'Score: {compute_match_score(exp, pred)}')
