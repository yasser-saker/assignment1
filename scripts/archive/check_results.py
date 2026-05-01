import json
with open('outputs/TAKEOFF-28/TAKEOFF-28_prediction.json') as f:
    data = json.load(f)

# Check what we have now
categories = {
    'VAV': ['vav-'],
    'Duct': ['"x', 'dia duct', 'duct:'],
    'Sensor': ['occupancy sensor', 'vacancy sensor', 'daylight sensor'],
    'Switch': ['single pole', 'three way', 'dimmer'],
    'Remove': ['remove'],
    'Refrigerant': ['refrigerant'],
}

for cat, kws in categories.items():
    items = [i for i in data['line_items'] if any(kw in i.get('description', '').lower() for kw in kws)]
    print(cat + ': ' + str(len(items)))
    for item in items[:5]:
        print('  ' + item['description'][:70])
    print()
