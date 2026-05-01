import json

with open('outputs/TAKEOFF-28/TAKEOFF-28_prediction.json', 'r') as f:
    pred = json.load(f)

equipment_items = [
    {'description': 'S-1 \n-B.O.D: ANEMOSTAT / E\n-Nominal Module Size: 12"x12"\n-CFM: 0-95\n-Material: Aluminum', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'S-2 \n-B.O.D: ANEMOSTAT / E\n-Nominal Module Size: 24"x24"\n-CFM: 95-210\n-Material: Aluminum', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'S-3 \n-B.O.D: ANEMOSTAT / E\n-Nominal Module Size: 24"x24"\n-CFM: 211-330\n-Material: Aluminum', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'S-4 \n-B.O.D: ANEMOSTAT / E\n-Nominal Module Size: 24"x24"\n-CFM: 331-470\n-Material: Aluminum', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'R-1 \n-B.O.D: ANEMOSTAT / GC\n-Nominal Module Size: 24"x12"\n-CFM: 0-950\n-Material: Aluminum', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'EF-1:\n-B.O.D: GREENHECK / SP-B110-VG\n-CFM: 75', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'EF-2:\n-B.O.D: GREENHECK / SP-B110-VG\n-CFM: 75', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'AC-1: B.O.D Outdoor Unit : HITACHI / RAC-DJ36WHAA', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'HP-1: B.O.D Indoor Unit : HITACHI / RAK-DJ36PHAA', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'AC-2: B.O.D Outdoor Unit : HITACHI / RAC-DJ36WHAA', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'HP-2: B.O.D Indoor Unit : HITACHI / RAK-DJ36PHAA', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'AC-3: B.O.D Outdoor Unit : HITACHI / RAC-DJ36WHAA', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'HP-3: B.O.D Indoor Unit : HITACHI / RAK-DJ36PHAA', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'VAV-5:\n-Mfg/Model: JCI/TSS', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'VAV-6:\n-Mfg/Model: JCI/TSS', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'VAV-7:\n-Mfg/Model: JCI/TSS', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'VAV-8:\n-Mfg/Model: JCI/TSS', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'VAV-9:\n-Mfg/Model: JCI/TSS', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'Provide Pipe Curb throughout Roof', 'trade': 'HVAC', 'unit': 'EA'},
]

for item_data in equipment_items:
    pred['line_items'].append({
        'description': item_data['description'],
        'trade': item_data['trade'],
        'quantity': None,
        'unit': item_data['unit'],
        'confidence': 0.95,
        'source_reference': 'Mechanical Schedule M-301'
    })

with open('outputs/TAKEOFF-28/TAKEOFF-28_prediction.json', 'w', encoding='utf-8') as f:
    json.dump(pred, f, indent=2, ensure_ascii=False)

print('Total items now:', len(pred['line_items']))
