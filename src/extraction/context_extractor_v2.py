"""Enhanced Context Extractor — searches for multiple schedule patterns dynamically."""
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class FinishCode:
    code: str
    material: str
    manufacturer: str
    product: str
    color: str
    type_size: str
    remarks: str


@dataclass
class RoomFinish:
    room_number: str
    room_name: str
    floor: str
    floor_grout: str
    base: str
    chair_rail: str
    walls_primary: str
    walls_accent: str
    ceiling_material: str
    ceiling_finish: str
    ceiling_height: str
    millwork_wall_cabinets: str
    millwork_base_cabinets: str
    millwork_countertop: str
    notes: str


@dataclass
class EquipmentItem:
    tag: str
    equipment_type: str
    manufacturer: str
    model: str
    size: str
    remarks: str


@dataclass
class DuctItem:
    size: str
    duct_type: str  # rectangular, round, flexible
    application: str  # supply, return, exhaust
    insulation: str


@dataclass
class ElectricalDeviceItem:
    device_type: str  # Occupancy Sensor, Vacancy Sensor, etc.
    specification: str
    location: str


@dataclass
class RemoveItem:
    description: str
    trade: str


@dataclass
class ManagementItem:
    description: str
    unit: str


class ContextExtractorV2:
    """Extract schedules and legends from drawings text using flexible pattern matching."""

    # Flexible patterns for detecting schedule pages
    SCHEDULE_PATTERNS = {
        'finish_legend': [
            'INTERIOR FINISH LEGEND',
            'FINISH LEGEND',
            'FINISH SCHEDULE',
            'ROOM FINISH SCHEDULE',
            'SCHEDULE OF FINISHES',
            'FINISH PLAN',
        ],
        'room_schedule': [
            'ROOM FINISH SCHEDULE',
            'ROOM SCHEDULE',
            'FINISH SCHEDULE',
            'SCHEDULE OF FINISHES',
        ],
        'equipment_schedule': [
            'EQUIPMENT SCHEDULE',
            'MECHANICAL SCHEDULE',
            'HVAC SCHEDULE',
            'DIFFUSER SCHEDULE',
            'FAN SCHEDULE',
            'RTU SCHEDULE',
            'VAV SCHEDULE',
            'ROOFTOP UNIT SCHEDULE',
        ],
        'door_schedule': [
            'DOOR SCHEDULE',
            'DOOR AND FRAME SCHEDULE',
            'DOOR HARDWARE SCHEDULE',
        ],
        'lighting_schedule': [
            'LIGHTING SCHEDULE',
            'LIGHT FIXTURE SCHEDULE',
            'LUMINAIRE SCHEDULE',
        ],
        'electrical_schedule': [
            'PANEL SCHEDULE',
            'ELECTRICAL SCHEDULE',
            'RECEPTACLE SCHEDULE',
        ],
        'plumbing_schedule': [
            'PLUMBING FIXTURE SCHEDULE',
            'PLUMBING SCHEDULE',
            'FIXTURE SCHEDULE',
        ],
        'fire_protection_schedule': [
            'FIRE PROTECTION SCHEDULE',
            'SPRINKLER SCHEDULE',
            'FIRE ALARM SCHEDULE',
        ],
    }

    def extract_all(self, pages: List[dict]) -> dict:
        """Extract all context from a list of pages."""
        context = {
            'finish_legend': [],
            'room_schedule': [],
            'equipment_schedule': [],
            'door_schedule': [],
            'lighting_schedule': [],
            'electrical_schedule': [],
            'plumbing_schedule': [],
            'fire_protection_schedule': [],
            'ducts': [],
            'electrical_devices': [],
            'remove_items': [],
            'management_items': [],
        }

        for page in pages:
            text = page.get('text', '')
            page_num = page.get('page_number', 0)
            
            # Detect page type using flexible patterns
            detected_types = self._detect_page_type(text)
            
            for page_type in detected_types:
                if page_type == 'finish_legend':
                    finishes = self._extract_finish_legend(text)
                    context['finish_legend'].extend(finishes)
                    if finishes:
                        print(f"  [Context] Page {page_num}: Extracted {len(finishes)} finish codes")
                
                elif page_type == 'room_schedule':
                    rooms = self._extract_room_schedule(text)
                    context['room_schedule'].extend(rooms)
                    if rooms:
                        print(f"  [Context] Page {page_num}: Extracted {len(rooms)} room finishes")
                
                elif page_type == 'equipment_schedule':
                    equipment = self._extract_equipment_schedule(text)
                    context['equipment_schedule'].extend(equipment)
                    if equipment:
                        print(f"  [Context] Page {page_num}: Extracted {len(equipment)} equipment items")
                
                elif page_type == 'door_schedule':
                    doors = self._extract_door_schedule(text)
                    context['door_schedule'].extend(doors)
                    if doors:
                        print(f"  [Context] Page {page_num}: Extracted {len(doors)} door items")
                
                elif page_type == 'lighting_schedule':
                    lights = self._extract_lighting_schedule(text)
                    context['lighting_schedule'].extend(lights)
                    if lights:
                        print(f"  [Context] Page {page_num}: Extracted {len(lights)} lighting items")
                
                elif page_type == 'electrical_schedule':
                    electrical = self._extract_electrical_schedule(text)
                    context['electrical_schedule'].extend(electrical)
                    if electrical:
                        print(f"  [Context] Page {page_num}: Extracted {len(electrical)} electrical items")
                
                elif page_type == 'plumbing_schedule':
                    plumbing = self._extract_plumbing_schedule(text)
                    context['plumbing_schedule'].extend(plumbing)
                    if plumbing:
                        print(f"  [Context] Page {page_num}: Extracted {len(plumbing)} plumbing items")
                
                elif page_type == 'fire_protection_schedule':
                    fire = self._extract_fire_protection_schedule(text)
                    context['fire_protection_schedule'].extend(fire)
                    if fire:
                        print(f"  [Context] Page {page_num}: Extracted {len(fire)} fire protection items")

            # Always scan for drawing callouts (ducts, electrical devices, remove items)
            # These may appear on any page, not just schedule pages
            ducts = self._extract_ducts(text)
            context['ducts'].extend(ducts)
            
            elec_devices = self._extract_electrical_devices(text)
            context['electrical_devices'].extend(elec_devices)
            
            removes = self._extract_remove_items(text)
            context['remove_items'].extend(removes)
            
            # Scan for management items
            mgmt = self._extract_management_items(text)
            context['management_items'].extend(mgmt)

        # Deduplicate
        context['equipment_schedule'] = self._deduplicate_equipment(context['equipment_schedule'])
        context['ducts'] = self._deduplicate_ducts(context['ducts'])
        context['electrical_devices'] = self._deduplicate_electrical_devices(context['electrical_devices'])
        context['remove_items'] = self._deduplicate_remove_items(context['remove_items'])
        context['management_items'] = self._deduplicate_management(context['management_items'])

        return context

    def _detect_page_type(self, text: str) -> List[str]:
        """Detect what type of schedule/legend this page contains."""
        detected = []
        text_upper = text.upper()
        
        for page_type, patterns in self.SCHEDULE_PATTERNS.items():
            for pattern in patterns:
                if pattern in text_upper:
                    detected.append(page_type)
                    break
        
        return detected

    def _extract_finish_legend(self, text: str) -> List[FinishCode]:
        """Extract finish legend entries dynamically."""
        finishes = []
        legend_start = -1
        
        for pattern in self.SCHEDULE_PATTERNS['finish_legend']:
            idx = text.find(pattern)
            if idx != -1:
                legend_start = idx
                break
        
        if legend_start == -1:
            return finishes
        
        # Look for the legend section
        legend_text = text[legend_start:]
        if 'ROOM FINISH SCHEDULE' in legend_text:
            legend_text = legend_text[:legend_text.find('ROOM FINISH SCHEDULE')]
        
        lines = [l.strip() for l in legend_text.split('\n') if l.strip()]
        
        # Find all finish codes (PNT-01, CL-01, LVT-01, etc.)
        for i, line in enumerate(lines):
            code_match = re.match(r'^(PNT-\d+|CL-\d+|LVT-\d+|FT-\d+|CPT-\d+|WB-\d+|VCT-\d+|GR-\d+|WT-\d+|TR-\d+|CG-\d+|WC-\d+|SS-\d+|QT-\d+|PL-\d+|DR-\d+|FR-\d+|AL-\d+|TS-\d+|CR-\d+)$', line)
            if code_match:
                tag = line
                # Work backwards to extract fields
                fields = {}
                if i >= 1:
                    fields['material'] = lines[i - 1]
                if i >= 2:
                    fields['manufacturer'] = lines[i - 2]
                if i >= 3:
                    fields['product_line'] = lines[i - 3]
                if i >= 4:
                    fields['pattern'] = lines[i - 4]
                if i >= 5:
                    fields['type_size'] = lines[i - 5]
                if i >= 6:
                    fields['color'] = lines[i - 6]
                
                material_type = fields.get('material', '').upper()
                
                if 'PAINT' in material_type:
                    finishes.append(FinishCode(code=tag, material='Paint', manufacturer=fields.get('manufacturer', ''), product='Interior Paint', color=fields.get('color', ''), type_size=fields.get('type_size', ''), remarks=''))
                elif 'CEILING' in material_type or 'GYPSUM' in material_type:
                    finishes.append(FinishCode(code=tag, material=fields.get('material', ''), manufacturer=fields.get('manufacturer', ''), product=fields.get('product_line', ''), color=fields.get('color', 'White'), type_size=fields.get('type_size', ''), remarks=''))
                elif 'FLOOR' in material_type or 'VINYL' in material_type or 'TILE' in material_type or 'CARPET' in material_type:
                    finishes.append(FinishCode(code=tag, material=fields.get('material', ''), manufacturer=fields.get('manufacturer', ''), product=fields.get('product_line', ''), color=fields.get('color', ''), type_size=fields.get('type_size', ''), remarks=''))
                elif 'WALL' in material_type or 'BASE' in material_type or 'COVE' in material_type:
                    finishes.append(FinishCode(code=tag, material=fields.get('material', ''), manufacturer=fields.get('manufacturer', ''), product=fields.get('product_line', ''), color=fields.get('color', ''), type_size=fields.get('type_size', ''), remarks=''))
                else:
                    finishes.append(FinishCode(code=tag, material=fields.get('material', ''), manufacturer=fields.get('manufacturer', ''), product=fields.get('product_line', ''), color=fields.get('color', ''), type_size=fields.get('type_size', ''), remarks=''))
        
        # Remove duplicates
        seen = set()
        unique = []
        for f in finishes:
            if f.code not in seen:
                seen.add(f.code)
                unique.append(f)
        
        return unique

    def _extract_room_schedule(self, text: str) -> List[RoomFinish]:
        """Extract room finish schedule."""
        rooms = []
        schedule_start = -1
        
        for pattern in self.SCHEDULE_PATTERNS['room_schedule']:
            idx = text.find(pattern)
            if idx != -1:
                schedule_start = idx
                break
        
        if schedule_start == -1:
            return rooms
        
        schedule_text = text[schedule_start:]
        lines = [l.strip() for l in schedule_text.split('\n') if l.strip()]
        
        # Skip header lines until first room number
        i = 0
        while i < len(lines):
            if re.match(r'^\d{3}$', lines[i]):
                break
            i += 1
        
        while i < len(lines):
            if not re.match(r'^\d{3}$', lines[i]):
                i += 1
                continue
            
            # Parse room row (14-15 fields)
            try:
                number = lines[i]
                name = lines[i + 1]
                floor = lines[i + 2]
                grout = lines[i + 3]
                base = lines[i + 4]
                chair_rail = lines[i + 5]
                primary = lines[i + 6]
                accent = lines[i + 7]
                ceiling_mat = lines[i + 8]
                ceiling_fin = lines[i + 9]
                ceiling_ht = lines[i + 10]
                wall_cabs = lines[i + 11]
                base_cabs = lines[i + 12]
                countertop = lines[i + 13]
                
                notes = ''
                if i + 14 < len(lines) and not re.match(r'^\d{3}$', lines[i + 14]):
                    notes = lines[i + 14]
                    i += 15
                else:
                    i += 14
                
                rooms.append(RoomFinish(
                    room_number=number, room_name=name, floor=floor, floor_grout=grout,
                    base=base, chair_rail=chair_rail, walls_primary=primary, walls_accent=accent,
                    ceiling_material=ceiling_mat, ceiling_finish=ceiling_fin, ceiling_height=ceiling_ht,
                    millwork_wall_cabinets=wall_cabs, millwork_base_cabinets=base_cabs,
                    millwork_countertop=countertop, notes=notes
                ))
            except (IndexError, ValueError):
                i += 1
        
        return rooms

    def _extract_equipment_schedule(self, text: str) -> List[EquipmentItem]:
        """Extract equipment schedule."""
        equipment = []
        
        # Pattern for RTU/AC/VAV/EF/S/R units
        equip_pattern = r'(RTU-\d+|AC-\d+|EF-\d+|VAV-\d+|UV-1|HP-\d+|CUH-\d+|S-\d+|R-\d+)'
        
        for match in re.finditer(equip_pattern, text):
            tag = match.group(1)
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 300)
            context = text[start:end]
            
            # Skip if this looks like a drawing sheet number (no equipment context)
            context_upper = context.upper()
            has_equipment_context = any(kw in context_upper for kw in [
                'CFM', 'MODEL', 'MFG', 'MANUFACTURER', 'SIZE', 'CAPACITY',
                'ANEMOSTAT', 'DIFFUSER', 'GRILLE', 'REGISTER', 'UNIT',
                'ROOFTOP', 'EXHAUST', 'SUPPLY', 'RETURN'
            ])
            
            # For S-# and R-# tags, require stronger evidence of being diffusers
            if tag.startswith(('S-', 'R-')):
                # Must have diffuser-related context or be on a schedule page
                has_diffuser_context = any(kw in context_upper for kw in [
                    'DIFFUSER', 'ANEMOSTAT', 'CFM', 'GRILLE', 'REGISTER',
                    'NOMINAL', 'MODULE', 'B.O.D', 'BOC', 'FACE',
                    'SUPPLY AIR', 'RETURN AIR'
                ])
                if not has_diffuser_context:
                    continue
            
            model_match = re.search(r'(?:MODEL|Model)\s+([A-Z0-9\-/]+)', context)
            model = model_match.group(1) if model_match else ''
            
            # Filter out common non-model values
            if model.upper() in ['REMARKS', 'NOTE', 'NOTES', 'TBD', 'N/A']:
                model = ''
            
            mfg = self._extract_manufacturer(context)
            
            # Try to find CFM/size for VAV units
            size = ''
            if 'VAV' in tag:
                cfm_match = re.search(r'(\d{2,4})\s*CFM', context)
                if cfm_match:
                    size = cfm_match.group(1) + ' CFM'
            
            equip_type = 'Rooftop Unit' if 'RTU' in tag else 'Split System' if 'AC' in tag else 'Exhaust Fan' if 'EF' in tag else 'VAV Unit' if 'VAV' in tag else 'Heat Pump' if 'HP' in tag else 'Unit Heater' if 'CUH' in tag else 'Supply Diffuser' if tag.startswith('S-') else 'Return Diffuser' if tag.startswith('R-') else 'UV Air Purifier'
            
            equipment.append(EquipmentItem(
                tag=tag, equipment_type=equip_type, manufacturer=mfg or 'Local Source',
                model=model, size=size, remarks=''
            ))
        
        return equipment

    def _extract_ducts(self, text: str) -> List[DuctItem]:
        """Extract duct sizes from drawing text/callouts."""
        ducts = []
        text_upper = text.upper()
        
        # Rectangular ducts: e.g., "6"x6"", "12"x10"", "32"x26""
        rect_pattern = r'(\d+)"\s*[xX]\s*(\d+)"'
        for match in re.finditer(rect_pattern, text):
            w, h = match.group(1), match.group(2)
            size = f'{w}"x{h}"'
            context = text[max(0, match.start()-50):min(len(text), match.end()+50)].upper()
            
            # Skip if this is an elbow (handled separately)
            if 'ELBOW' in context:
                continue
            
            app = 'Supply'
            if 'RETURN' in context or 'RET' in context:
                app = 'Return'
            elif 'EXHAUST' in context or 'EF' in context:
                app = 'Exhaust'
            
            ins = ''
            if 'INSUL' in context:
                ins = 'Insulated'
            
            ducts.append(DuctItem(size=size, duct_type='Rectangular', application=app, insulation=ins))
        
        # Round ducts: e.g., "6" Dia Duct", "8" Dia"
        round_pattern = r'(\d+)"\s*(?:Dia\.?|DIA\.?|Diameter)\s*(?:Duct|DUCT)'
        for match in re.finditer(round_pattern, text):
            size = f'{match.group(1)}" Dia'
            context = text[max(0, match.start()-50):min(len(text), match.end()+50)].upper()
            
            # Skip if this is an elbow
            if 'ELBOW' in context:
                continue
            
            app = 'Supply'
            if 'RETURN' in context or 'RET' in context:
                app = 'Return'
            elif 'EXHAUST' in context or 'EF' in context:
                app = 'Exhaust'
            
            ducts.append(DuctItem(size=size, duct_type='Round', application=app, insulation=''))
        
        # Flexible ducts to diffuser
        flex_pattern = r'(\d+)"\s*(?:Flexible|FLEX)'
        for match in re.finditer(flex_pattern, text):
            size = f'{match.group(1)}" Dia'
            ducts.append(DuctItem(size=size, duct_type='Flexible', application='Supply', insulation=''))
        
        # Duct elbows
        elbow_pattern1 = r'(\d+)"\s*(?:Dia\.?|DIA\.?|Diameter)?\s*(?:Duct|DUCT)?\s*(?:Elbow|ELBOW)'
        for match in re.finditer(elbow_pattern1, text):
            size = f'{match.group(1)}" Dia'
            ducts.append(DuctItem(size=size, duct_type='Elbow', application='Supply', insulation=''))
        
        elbow_pattern2 = r'(\d+)"\s*[xX]\s*(\d+)"\s*(?:Duct|DUCT)?\s*(?:Elbow|ELBOW)'
        for match in re.finditer(elbow_pattern2, text):
            w, h = match.group(1), match.group(2)
            size = f'{w}"x{h}"'
            ducts.append(DuctItem(size=size, duct_type='Elbow', application='Supply', insulation=''))
        
        return ducts

    def _extract_electrical_devices(self, text: str) -> List[ElectricalDeviceItem]:
        """Extract electrical sensor/switch devices from drawing text."""
        devices = []
        
        patterns = [
            (r'(?i)occupancy\s+sensor', 'Occupancy Sensor'),
            (r'(?i)vacancy\s+sensor', 'Vacancy Sensor'),
            (r'(?i)daylight\s+sensor', 'Daylight Sensor'),
            (r'(?i)single\s+pole\s+switch', 'Single Pole Switch'),
            (r'(?i)three\s+way\s+switch', 'Three Way Switch'),
            (r'(?i)dimmer\s+switch', 'Dimmer Switch'),
        ]
        
        for pattern, device_type in patterns:
            for match in re.finditer(pattern, text):
                context = text[max(0, match.start()-30):min(len(text), match.end()+30)]
                devices.append(ElectricalDeviceItem(
                    device_type=device_type,
                    specification='',
                    location=''
                ))
        
        return devices

    def _extract_remove_items(self, text: str) -> List[RemoveItem]:
        """Extract demolition/remove items from text."""
        removes = []
        
        patterns = [
            (r'(?i)remove\s+existing\s+([\w\s]+?)(?:\.|,|;|$)', 'Demolition'),
            (r'(?i)existing\s+([\w\s]+?)\s+to\s+be\s+removed', 'Demolition'),
            (r'(?i)remove\s+section\s+of\s+([\w\s]+?)(?:\.|,|;|$)', 'Demolition'),
            (r'(?i)remove\s+([\w\s]+?)\s+for\s+new\s+([\w\s]+?)(?:\.|,|;|$)', 'Demolition'),
        ]
        
        for pattern, trade in patterns:
            for match in re.finditer(pattern, text):
                desc = match.group(0).strip()
                # Clean up
                desc = desc.replace('\n', ' ')
                removes.append(RemoveItem(description=desc, trade=trade))
        
        return removes

    def _extract_management_items(self, text: str) -> List[ManagementItem]:
        """Extract management/supervision items from scope of work."""
        mgmt = []
        
        patterns = [
            (r'(?i)management\s+&?\s+supervision\s*\(?\s*(?:weeks?)?\s*\)?', 'Weeks'),
            (r'(?i)documentation\s+&?\s+shop\s+drawings', 'LS'),
            (r'(?i)project\s+management', 'Weeks'),
            (r'(?i)site\s+supervision', 'Weeks'),
        ]
        
        for pattern, unit in patterns:
            for match in re.finditer(pattern, text):
                desc = match.group(0).strip().title()
                mgmt.append(ManagementItem(description=desc, unit=unit))
        
        return mgmt

    def _deduplicate_management(self, items: List[ManagementItem]) -> List[ManagementItem]:
        """Remove duplicate management items."""
        seen = set()
        unique = []
        for item in items:
            key = item.description.lower()
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique

    def _deduplicate_equipment(self, equipment: List[EquipmentItem]) -> List[EquipmentItem]:
        """Remove duplicate equipment items (same tag)."""
        seen = set()
        unique = []
        for e in equipment:
            if e.tag not in seen:
                seen.add(e.tag)
                unique.append(e)
        return unique

    def _deduplicate_ducts(self, ducts: List[DuctItem]) -> List[DuctItem]:
        """Remove duplicate duct sizes."""
        seen = set()
        unique = []
        for d in ducts:
            key = (d.size, d.duct_type, d.application)
            if key not in seen:
                seen.add(key)
                unique.append(d)
        return unique

    def _deduplicate_electrical_devices(self, devices: List[ElectricalDeviceItem]) -> List[ElectricalDeviceItem]:
        """Remove duplicate electrical devices."""
        seen = set()
        unique = []
        for d in devices:
            key = d.device_type
            if key not in seen:
                seen.add(key)
                unique.append(d)
        return unique

    def _deduplicate_remove_items(self, items: List[RemoveItem]) -> List[RemoveItem]:
        """Remove duplicate remove items."""
        seen = set()
        unique = []
        for item in items:
            key = item.description.lower()
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique

    def _extract_door_schedule(self, text: str) -> List[dict]:
        """Extract door schedule."""
        doors = []
        return doors

    def _extract_lighting_schedule(self, text: str) -> List[dict]:
        """Extract lighting schedule."""
        lights = []
        return lights

    def _extract_electrical_schedule(self, text: str) -> List[dict]:
        """Extract electrical schedule."""
        electrical = []
        return electrical

    def _extract_plumbing_schedule(self, text: str) -> List[dict]:
        """Extract plumbing schedule."""
        plumbing = []
        return plumbing

    def _extract_fire_protection_schedule(self, text: str) -> List[dict]:
        """Extract fire protection schedule."""
        fire = []
        return fire

    def _extract_manufacturer(self, text: str) -> Optional[str]:
        """Extract manufacturer name from text."""
        manufacturers = [
            'SHERWIN-WILLIAMS', 'ARMSTRONG', 'ARMSTRONG FLOORING', 'DAL TILE',
            'SCHLUTER', 'ROPPE', 'WILSONART', 'KAWNEER', 'TARKETT',
            'CONSTRUCTION SPECIALTIES', 'EKENA MILLWORK', 'CUSTOM BUILDING PRODUCTS',
            'KOROSEAL', 'JOLLY', 'SHAW CONTRACT', 'GREENHECK', 'HITACHI',
            'JOHNSON CONTROLS', 'JCI', 'QMARK', 'ANEMOSTAT'
        ]
        for mfg in manufacturers:
            if mfg in text.upper():
                return mfg.title()
        return None
