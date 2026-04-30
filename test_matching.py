import sys
sys.path.insert(0, '.')
from src.evaluation.evaluator import compute_match_score

tests = [
    ('S-2 Diffuser expected', 
     'S-2 \n-B.O.D: ANEMOSTAT / E\n-Nominal Module Size: 24"x24"\n-CFM: 95-210\n-Material: Aluminum', 
     'S-2 Diffuser: 24" x 24" Aluminum, 4-Way, Anemostat, Supply, Neck Size: 8", Finish to be selected by Architect'),
    ('R-1 Grille expected',
     'R-1 \n-B.O.D: ANEMOSTAT / GC\n-Nominal Module Size: 24"x12"\n-CFM: 0-950\n-Material: Aluminum',
     'R-1 Grille: 24" x 12" Aluminum, Grid Core, Anemostat, Return, Finish to be selected by Architect'),
    ('RTU-1 expected',
     'RTU-1:\nMfg/Model: JOHNSON CONTROLS / KD28T\n-Approx. Weight: 2560 LBS',
     'RTU-1 Rooftop Air Conditioning Unit: Variable Air Volume, 8,300 CFM, Natural Gas Heating Furnace, Johnson Controls / KD28T'),
    ('VAV-1 expected',
     'VAV-1:\n-Mfg/Model: JCI/TSS',
     'VAV-1 Terminal Unit: JCI / TSS, Maximum Cooling CFM: 1,005, Includes Sound Attenuator and Non-Fused Disconnect'),
    ('S-1 expected (should NOT match Sink)',
     'S-1:\n-B.O.D: ANEMOSTAT / E\n-Nominal Module Size: 12"x12"',
     'S-1: Lustertone 23-1/2"x18-1/4"x5-3/8" Deep Drop-In Single Bowl Sink, 18 Gauge, Type 304 Stainless Steel'),
]

for name, exp, pred in tests:
    score = compute_match_score(exp, pred)
    status = 'MATCH' if score >= 60 else 'MISS'
    print(f'{status} (score={score:.0f}): {name}')
    print(f'  Exp:  {exp[:70]}')
    print(f'  Pred: {pred[:70]}')
    print()
