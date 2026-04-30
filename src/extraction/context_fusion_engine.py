"""Context Fusion Engine — 100% DYNAMIC.

Combines schedules, legends, and drawings to produce specific line items.
NO hardcoded project-specific strings — everything is derived from the PDF text.
"""
from typing import List, Dict
from collections import defaultdict
from src.models import LineItem
from src.extraction.context_extractor_v2 import ContextExtractorV2, FinishCode, RoomFinish


class ContextFusionEngine:
    """Fuses project context (schedules, legends) with drawing data to produce specific line items.
    
    This engine is 100% dynamic — it derives all descriptions from the extracted
    finish codes and room schedules, without any hardcoded project-specific strings.
    """

    def __init__(self):
        self.finish_map: Dict[str, FinishCode] = {}
        self.rooms: List[RoomFinish] = []
        self.equipment: List = []
        self.ducts: List = []
        self.electrical_devices: List = []
        self.remove_items: List = []
        self.management_items: List = []

    def load_context(self, context: dict):
        """Load extracted context."""
        for finish in context.get('finish_legend', []):
            self.finish_map[finish.code] = finish
        self.rooms = context.get('room_schedule', [])
        self.equipment = context.get('equipment_schedule', [])
        self.ducts = context.get('ducts', [])
        self.electrical_devices = context.get('electrical_devices', [])
        self.remove_items = context.get('remove_items', [])
        self.management_items = context.get('management_items', [])
        print(f"[Fusion] Loaded {len(self.finish_map)} finish codes, {len(self.rooms)} rooms, {len(self.equipment)} equipment items, {len(self.ducts)} ducts, {len(self.electrical_devices)} electrical devices, {len(self.remove_items)} remove items, {len(self.management_items)} management items")

    def aggregate_by_finish_code(self) -> List[LineItem]:
        """Aggregate rooms by finish code to generate line items.
        
        Groups wall/ceiling items by height (from room schedule).
        Produces descriptions in a standard format derived from the finish legend.
        """
        items = []

        # Group rooms by finish code AND ceiling height for wall/ceiling items
        floor_groups = defaultdict(lambda: {'count': 0, 'rooms': []})
        wall_groups = defaultdict(lambda: {'count': 0, 'rooms': []})
        ceiling_groups = defaultdict(lambda: {'count': 0, 'rooms': []})
        base_groups = defaultdict(lambda: {'count': 0, 'rooms': []})

        def clean_height(height: str) -> str:
            height = height.strip()
            if '+/-' in height:
                height = height.replace('+/-', '').strip()
            height = height.rstrip('+-').strip()
            if "'" in height and not height.endswith('"'):
                height += '"'
            return height

        for room in self.rooms:
            heights = [clean_height(h) for h in room.ceiling_height.split('/') if clean_height(h)]

            # Floor finishes
            for code in room.floor.split('/'):
                code = code.strip()
                if code and not code.startswith('EXIST'):
                    floor_groups[code]['count'] += 1
                    floor_groups[code]['rooms'].append(room.room_name)

            # Base finishes
            for code in room.base.split('/'):
                code = code.strip()
                if code and not code.startswith('EXIST'):
                    base_groups[code]['count'] += 1
                    base_groups[code]['rooms'].append(room.room_name)

            # Wall finishes (group by code + height)
            for code in room.walls_primary.split('/'):
                code = code.strip()
                if code and not code.startswith('EXIST'):
                    for height in heights:
                        key = f"{code}|{height}"
                        wall_groups[key]['count'] += 1
                        wall_groups[key]['rooms'].append(room.room_name)

            for code in room.walls_accent.split('/'):
                code = code.strip()
                if code and code != '-' and not code.startswith('EXIST'):
                    for height in heights:
                        key = f"{code}|{height}"
                        wall_groups[key]['count'] += 1
                        wall_groups[key]['rooms'].append(room.room_name)

            # Ceiling finishes (group by code + height)
            for code in room.ceiling_finish.split('/'):
                code = code.strip()
                if code and not code.startswith('EXIST'):
                    for height in heights:
                        key = f"{code}|{height}"
                        ceiling_groups[key]['count'] += 1
                        ceiling_groups[key]['rooms'].append(room.room_name)

        # Generate line items for floors
        for code, data in floor_groups.items():
            finish = self.finish_map.get(code)
            if finish:
                items.append(LineItem(
                    description=self._build_floor_description(finish),
                    trade='Flooring',
                    quantity=None,
                    unit='SF',
                    confidence=0.95,
                    source_reference=f"Finish Legend: {code}"
                ))

        # Generate line items for walls (grouped by height)
        for key, data in wall_groups.items():
            code, height = key.split('|')
            finish = self.finish_map.get(code)
            if finish:
                trade = 'Painting' if 'PNT' in code else 'Wall Coverings' if 'WC' in code else 'Tile'
                items.append(LineItem(
                    description=self._build_wall_description(finish, height),
                    trade=trade,
                    quantity=None,
                    unit='SF',
                    confidence=0.95,
                    source_reference=f"Finish Legend: {code}"
                ))

        # Generate line items for ceilings (grouped by height)
        for key, data in ceiling_groups.items():
            code, height = key.split('|')
            finish = self.finish_map.get(code)
            if finish:
                trade = 'Ceilings' if 'CL' in code else 'Drywall'
                items.append(LineItem(
                    description=self._build_ceiling_description(finish, height),
                    trade=trade,
                    quantity=None,
                    unit='SF',
                    confidence=0.95,
                    source_reference=f"Finish Legend: {code}"
                ))

        # Generate line items for base
        for code, data in base_groups.items():
            finish = self.finish_map.get(code)
            if finish:
                items.append(LineItem(
                    description=self._build_base_description(finish),
                    trade='Flooring',
                    quantity=None,
                    unit='LF',
                    confidence=0.95,
                    source_reference=f"Finish Legend: {code}"
                ))
        
        # Generate line items for equipment schedule
        for equip in self.equipment:
            desc = self._build_equipment_description(equip)
            trade = self._get_equipment_trade(equip.equipment_type)
            items.append(LineItem(
                description=desc,
                trade=trade,
                quantity=None,
                unit='EA',
                confidence=0.95,
                source_reference=f"Equipment Schedule: {equip.tag}"
            ))
        
        # Generate line items for duct sizes
        for duct in self.ducts:
            desc = self._build_duct_description(duct)
            items.append(LineItem(
                description=desc,
                trade='Mechanical',
                quantity=None,
                unit='LF',
                confidence=0.90,
                source_reference="Mechanical Drawings"
            ))
        
        # Generate line items for electrical devices
        for device in self.electrical_devices:
            desc = device.device_type
            items.append(LineItem(
                description=desc,
                trade='Electrical',
                quantity=None,
                unit='EA',
                confidence=0.90,
                source_reference="Electrical Drawings"
            ))
        
        # Generate line items for remove/demolition items
        for rem in self.remove_items:
            items.append(LineItem(
                description=rem.description,
                trade=rem.trade,
                quantity=None,
                unit='EA',
                confidence=0.85,
                source_reference="Demolition Notes"
            ))
        
        # Generate line items for management items
        for mgmt in self.management_items:
            items.append(LineItem(
                description=mgmt.description,
                trade='Management',
                quantity=None,
                unit=mgmt.unit,
                confidence=0.80,
                source_reference="Scope of Work"
            ))

        return items

    def _build_floor_description(self, finish: FinishCode) -> str:
        """Build floor finish description dynamically from finish legend data."""
        parts = [finish.code]
        if finish.manufacturer and finish.manufacturer != '-':
            parts.append(finish.manufacturer)
        if finish.product and finish.product != '-':
            parts.append(finish.product)
        if finish.color and finish.color != '-':
            parts.append(f'- {finish.color}')
        return ' '.join(parts)

    def _build_wall_description(self, finish: FinishCode, height: str) -> str:
        """Build wall finish description dynamically.
        
        Standard format:
            CODE (HEIGHT High):
            -Mfg: MANUFACTURER
            -Color: COLOR
            -Type: TYPE
        """
        height_clean = height.strip()
        mfg = finish.manufacturer.replace('-', ' ').strip()
        color = finish.color.strip()
        finish_type = finish.type_size.strip() if finish.type_size else ''

        # Add # before SW color codes if present
        if 'SW' in color and '#SW' not in color:
            color = color.replace('SW', '#SW')

        desc = f"{finish.code} ({height_clean} High):\n"
        desc += f"-Mfg: {mfg}\n"
        desc += f"-Color: {color}\n"
        desc += f"-Type: {finish_type}"
        return desc

    def _build_ceiling_description(self, finish: FinishCode, height: str) -> str:
        """Build ceiling finish description dynamically."""
        # For GWB ceilings, use GWB format (no height)
        if 'GYPSUM' in finish.material.upper() or 'GWB' in finish.material.upper():
            mfg = finish.manufacturer.replace('-', ' ').strip()
            color = finish.color.strip()
            if 'SW' in color and '#SW' not in color:
                color = color.replace('SW', '#SW')
            finish_type = finish.type_size.strip() if finish.type_size else ''
            desc = f"{finish.code} (GWB):\n"
            desc += f"-Mfg: {mfg}\n"
            desc += f"-Color: {color}\n"
            desc += f"-Type: {finish_type}"
            return desc

        # For ACT ceilings, include height
        height_clean = height.strip()
        mfg = finish.manufacturer.replace('-', ' ').strip()
        color = finish.color.strip()
        if 'SW' in color and '#SW' not in color:
            color = color.replace('SW', '#SW')
        finish_type = finish.type_size.strip() if finish.type_size else ''
        desc = f"{finish.code} ({height_clean} High):\n"
        desc += f"-Mfg: {mfg}\n"
        desc += f"-Color: {color}\n"
        desc += f"-Type: {finish_type}"
        return desc

    def _build_equipment_description(self, equip) -> str:
        """Build equipment description dynamically from schedule data."""
        desc = f"{equip.tag}:\n"
        mfg = equip.manufacturer if equip.manufacturer and equip.manufacturer != 'Local Source' else ''
        if mfg and equip.model:
            desc += f"-Mfg/Model: {mfg}/{equip.model}"
        elif mfg:
            desc += f"-Mfg: {mfg}"
        elif equip.model:
            desc += f"-Model: {equip.model}"
        if equip.size:
            desc += f"\n-Size: {equip.size}"
        return desc
    
    def _get_equipment_trade(self, equip_type: str) -> str:
        """Map equipment type to trade."""
        equip_type_lower = equip_type.lower()
        if 'vav' in equip_type_lower or 'rtu' in equip_type_lower or 'fan' in equip_type_lower or 'unit' in equip_type_lower:
            return 'Mechanical'
        elif 'split' in equip_type_lower or 'heat pump' in equip_type_lower:
            return 'Mechanical'
        elif 'light' in equip_type_lower or 'troffer' in equip_type_lower or 'downlight' in equip_type_lower:
            return 'Electrical'
        elif 'panel' in equip_type_lower or 'breaker' in equip_type_lower or 'receptacle' in equip_type_lower:
            return 'Electrical'
        else:
            return 'Mechanical'
    
    def _build_duct_description(self, duct) -> str:
        """Build duct description dynamically."""
        if duct.duct_type == 'Elbow':
            desc = f"{duct.size} Duct Elbow"
        elif duct.duct_type == 'Flexible':
            desc = f"{duct.size} Flexible Duct to Diffuser"
        else:
            desc = f"{duct.size} Duct"
            if duct.application and duct.application != 'Supply':
                desc += f": {duct.application}"
            if duct.insulation:
                desc += f", {duct.insulation}"
        return desc
    
    def _build_base_description(self, finish: FinishCode) -> str:
        """Build base description dynamically."""
        mfg = finish.manufacturer.replace('-', ' ').strip()
        color = finish.color.strip()
        finish_type = finish.type_size.strip() if finish.type_size else ''
        desc = f"{finish.code}:\n"
        desc += f"-Mfg: {mfg}\n"
        desc += f"-Color: {color}\n"
        desc += f"-Type: {finish_type}"
        return desc
