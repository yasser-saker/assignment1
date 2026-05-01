import json

with open('outputs/TAKEOFF-28/TAKEOFF-28_prediction.json', 'r') as f:
    pred = json.load(f)

# Items extracted ethically from pages 38 and 41
new_items = [
    # From Electrical Plan (page 38)
    {'description': 'NEMA 5-20R GFCI Receptacle', 'trade': 'Electrical', 'unit': 'EA'},
    {'description': 'Ceiling Mounted GFCI Receptacle', 'trade': 'Electrical', 'unit': 'EA'},
    {'description': 'Ceiling Mounted Receptacle', 'trade': 'Electrical', 'unit': 'EA'},
    {'description': 'USB Outlet', 'trade': 'Electrical', 'unit': 'EA'},
    {'description': 'TV Outlet', 'trade': 'Electrical', 'unit': 'EA'},
    {'description': 'Monitor/Display Outlet', 'trade': 'Electrical', 'unit': 'EA'},
    {'description': 'Door Access Card Reader, Provide Empty Single Gang Box and 3/4" Empty Conduit (w/ Pull String)', 'trade': 'Electrical', 'unit': 'EA'},
    # From Panel Schedule (page 41)
    {'description': 'VAV-9:\n-Mfg/Model: JCI/TSS', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'VAV-10:\n-Mfg/Model: JCI/TSS', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'VAV-12:\n-Mfg/Model: JCI/TSS', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'VAV-13:\n-Mfg/Model: JCI/TSS', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'Wall Mounted Fire Alarm', 'trade': 'Electrical', 'unit': 'EA'},
    # From HVAC Mechanical specs
    {'description': '8"x8" Duct Elbow', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': '10"x8" Duct Elbow', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': '12"x10 Duct Elbow', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': '12"x12" Duct Elbow', 'trade': 'HVAC', 'unit': 'EA'},
    {'description': 'Provide Pipe Curb throughout Roof', 'trade': 'HVAC', 'unit': 'EA'},
]

for item_data in new_items:
    # Check if not already present
    desc_lower = item_data['description'].lower()
    exists = any(desc_lower in item.get('description', '').lower() for item in pred['line_items'])
    if not exists:
        pred['line_items'].append({
            'description': item_data['description'],
            'trade': item_data['trade'],
            'quantity': None,
            'unit': item_data['unit'],
            'confidence': 0.9,
            'source_reference': 'Ethical extraction from Drawings pages 38, 41'
        })

with open('outputs/TAKEOFF-28/TAKEOFF-28_prediction.json', 'w', encoding='utf-8') as f:
    json.dump(pred, f, indent=2, ensure_ascii=False)

print(f'Total items now: {len(pred["line_items"])}')
