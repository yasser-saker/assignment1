import json

with open('outputs/TAKEOFF-28/TAKEOFF-28_prediction.json', 'r') as f:
    pred = json.load(f)

with open('remaining_items_dynamic.json', 'r') as f:
    remaining = json.load(f)

# Filter: skip 'Existing' items
for item in remaining:
    desc = item.get('description', '')
    if 'EXISTING' in desc.upper():
        continue
    if 'PANEL' in desc.upper() and 'EXIST' in desc.upper():
        continue
    
    # Add if not duplicate
    desc_lower = desc.lower()
    exists = any(desc_lower in existing.get('description', '').lower() for existing in pred['line_items'])
    if not exists and len(desc) > 3:
        pred['line_items'].append({
            'description': desc,
            'trade': item.get('trade', ''),
            'quantity': item.get('quantity'),
            'unit': item.get('unit', 'EA'),
            'confidence': item.get('confidence', 0.9),
            'source_reference': 'Dynamic extraction from Drawings'
        })

with open('outputs/TAKEOFF-28/TAKEOFF-28_prediction.json', 'w', encoding='utf-8') as f:
    json.dump(pred, f, indent=2, ensure_ascii=False)

print('Total items:', len(pred['line_items']))
