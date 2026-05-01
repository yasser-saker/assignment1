import sys
sys.path.insert(0, '.')
from src.extraction.context_extractor_v2 import ContextExtractorV2

# Test with sample text
text = '''
VAV-1 MODEL TSS CFM 1005
VAV-2 MODEL TSS CFM 870
6"x6" Duct Supply
12"x10" Duct Return Insulated
Occupancy Sensor
Single Pole Switch
Remove Existing Fire Damper
'''

extractor = ContextExtractorV2()
pages = [{'text': text, 'page_number': 1}]
ctx = extractor.extract_all(pages)

print('Equipment:', len(ctx['equipment_schedule']))
for e in ctx['equipment_schedule']:
    print(' ', e.tag, e.model, e.size)

print('Ducts:', len(ctx['ducts']))
for d in ctx['ducts']:
    print(' ', d.size, d.duct_type, d.application)

print('Electrical:', len(ctx['electrical_devices']))
for ed in ctx['electrical_devices']:
    print(' ', ed.device_type)

print('Remove:', len(ctx['remove_items']))
for r in ctx['remove_items']:
    print(' ', r.description)
