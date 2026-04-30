"""Extract structured context (schedules, legends) from drawings text."""
import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import OrderedDict


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


class ContextExtractor:
    """Extract schedules and legends from drawings text."""

    def extract_all(self, pages: List[dict]) -> dict:
        """Extract all context from a list of pages."""
        context = {
            'finish_legend': [],
            'room_schedule': [],
            'equipment_schedule': [],
        }
        
        for page in pages:
            text = page.get('text', '')
            page_num = page.get('page_number', 0)
            
            # Detect page type
            if 'INTERIOR FINISH LEGEND' in text or 'FINISH LEGEND' in text:
                finishes = self._extract_finish_legend(text)
                context['finish_legend'].extend(finishes)
                print(f"  [Context] Page {page_num}: Extracted {len(finishes)} finish codes")
            
            if 'ROOM FINISH SCHEDULE' in text or 'FINISH SCHEDULE' in text:
                rooms = self._extract_room_schedule(text)
                context['room_schedule'].extend(rooms)
                print(f"  [Context] Page {page_num}: Extracted {len(rooms)} room finishes")
            
            if any(kw in text for kw in ['RTU-', 'EQUIPMENT SCHEDULE', 'ROOFTOP']):
                equipment = self._extract_equipment_schedule(text)
                context['equipment_schedule'].extend(equipment)
                print(f"  [Context] Page {page_num}: Extracted {len(equipment)} equipment items")
        
        return context

    def _extract_finish_legend(self, text: str) -> List[FinishCode]:
        """Extract finish legend entries from INTERIOR FINISH LEGEND section.
        
        Note: PDF text extraction returns each cell on a separate line,
        so we need to read multiple lines per finish entry.
        """
        finishes = []
        
        # Find the INTERIOR FINISH LEGEND section
        legend_start = text.find('INTERIOR FINISH LEGEND')
        if legend_start == -1:
            return finishes
        
        legend_text = text[legend_start:text.find('ROOM FINISH SCHEDULE')] if 'ROOM FINISH SCHEDULE' in text else text[legend_start:]
        lines = [l.strip() for l in legend_text.split('\n') if l.strip()]
        
        # Each finish entry has the following fields in order:
        # COLOR/FINISH, TYPE/SIZE, PATTERN, PRODUCT_LINE, MANUFACTURER, MATERIAL, TAG, REMARKS, INSTALL_PATTERN
        # But the number of fields varies by material type.
        
        # We detect entries by finding TAG codes (PNT-##, CL-##, LVT-##, FT-##, CPT-##, WB-##, etc.)
        # and work backwards to extract other fields.
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check if this line is a TAG code
            tag_match = re.match(r'^(PNT-\d+|CL-\d+|LVT-\d+|FT-\d+|CPT-\d+|WB-\d+|VCT-\d+|GR-\d+|WT-\d+|TR-\d+|CG-\d+|WC-\d+|SS-\d+|QT-\d+|PL-\d+|DR-\d+|FR-\d+|AL-\d+|TS-\d+|CR-\d+)$', line)
            if not tag_match:
                i += 1
                continue
            
            tag = line
            
            # Work backwards to find related fields
            # TAG is at position i, MATERIAL is at i-1, MANUFACTURER at i-2, etc.
            fields = {'tag': tag}
            
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
            
            # Determine material type and build FinishCode
            material_type = fields.get('material', '').upper()
            
            if 'PAINT' in material_type:
                finishes.append(FinishCode(
                    code=tag,
                    material='Paint',
                    manufacturer=fields.get('manufacturer', ''),
                    product='Interior Paint',
                    color=fields.get('color', ''),
                    type_size=fields.get('type_size', ''),
                    remarks=''
                ))
            elif 'CEILING' in material_type or 'GYPSUM' in material_type:
                finishes.append(FinishCode(
                    code=tag,
                    material=fields.get('material', ''),
                    manufacturer=fields.get('manufacturer', ''),
                    product=fields.get('product_line', ''),
                    color=fields.get('color', 'White'),
                    type_size=fields.get('type_size', ''),
                    remarks=''
                ))
            elif 'FLOOR' in material_type or 'VINYL' in material_type or 'TILE' in material_type:
                finishes.append(FinishCode(
                    code=tag,
                    material=fields.get('material', ''),
                    manufacturer=fields.get('manufacturer', ''),
                    product=fields.get('product_line', ''),
                    color=fields.get('color', ''),
                    type_size=fields.get('type_size', ''),
                    remarks=''
                ))
            elif 'WALL' in material_type or 'BASE' in material_type or 'COVE' in material_type:
                finishes.append(FinishCode(
                    code=tag,
                    material=fields.get('material', ''),
                    manufacturer=fields.get('manufacturer', ''),
                    product=fields.get('product_line', ''),
                    color=fields.get('color', ''),
                    type_size=fields.get('type_size', ''),
                    remarks=''
                ))
            elif 'CARPET' in material_type:
                finishes.append(FinishCode(
                    code=tag,
                    material=fields.get('material', ''),
                    manufacturer=fields.get('manufacturer', ''),
                    product=fields.get('product_line', ''),
                    color=fields.get('color', ''),
                    type_size=fields.get('type_size', ''),
                    remarks=''
                ))
            else:
                finishes.append(FinishCode(
                    code=tag,
                    material=fields.get('material', ''),
                    manufacturer=fields.get('manufacturer', ''),
                    product=fields.get('product_line', ''),
                    color=fields.get('color', ''),
                    type_size=fields.get('type_size', ''),
                    remarks=''
                ))
            
            i += 1
        
        # Remove duplicates based on code
        seen = set()
        unique = []
        for f in finishes:
            if f.code not in seen:
                seen.add(f.code)
                unique.append(f)
        
        return unique

    def _extract_room_schedule(self, text: str) -> List[RoomFinish]:
        """Extract room finish schedule from ROOM FINISH SCHEDULE section.
        
        Note: PDF text extraction returns each cell on a separate line,
        so we need to read 14-15 lines per room row.
        """
        rooms = []
        
        # Find the ROOM FINISH SCHEDULE section
        schedule_start = text.find('ROOM FINISH SCHEDULE')
        if schedule_start == -1:
            return rooms
        
        schedule_text = text[schedule_start:]
        lines = [l.strip() for l in schedule_text.split('\n') if l.strip()]
        
        # Skip header lines until we find the first room number (3 digits)
        i = 0
        while i < len(lines):
            if re.match(r'^\d{3}$', lines[i]):
                break
            i += 1
        
        # Parse room rows - each room has 14-15 fields in order:
        # NUMBER, NAME, FLOOR, GROUT, BASE, CHAIR_RAIL, PRIMARY, ACCENT, CEILING_MAT, CEILING_FIN, CEILING_HT, WALL_CABS, BASE_CABS, COUNTERTOP, [NOTES]
        while i < len(lines):
            if not re.match(r'^\d{3}$', lines[i]):
                i += 1
                continue
            
            number = lines[i]      # NUMBER
            i += 1
            if i >= len(lines):
                break
            
            name = lines[i]        # NAME
            i += 1
            if i >= len(lines):
                break
            
            floor = lines[i]       # FLOOR
            i += 1
            if i >= len(lines):
                break
            
            grout = lines[i]       # GROUT
            i += 1
            if i >= len(lines):
                break
            
            base = lines[i]        # BASE
            i += 1
            if i >= len(lines):
                break
            
            chair_rail = lines[i]  # CHAIR_RAIL
            i += 1
            if i >= len(lines):
                break
            
            primary = lines[i]     # PRIMARY
            i += 1
            if i >= len(lines):
                break
            
            accent = lines[i]      # ACCENT
            i += 1
            if i >= len(lines):
                break
            
            ceiling_mat = lines[i] # CEILING_MAT
            i += 1
            if i >= len(lines):
                break
            
            ceiling_fin = lines[i] # CEILING_FIN
            i += 1
            if i >= len(lines):
                break
            
            ceiling_ht = lines[i]  # CEILING_HT
            i += 1
            if i >= len(lines):
                break
            
            wall_cabs = lines[i]   # WALL_CABS
            i += 1
            if i >= len(lines):
                break
            
            base_cabs = lines[i]   # BASE_CABS
            i += 1
            if i >= len(lines):
                break
            
            countertop = lines[i]  # COUNTERTOP
            i += 1
            
            # Notes are optional - check if next line is a 3-digit number (new room) or notes
            notes = ''
            if i < len(lines) and not re.match(r'^\d{3}$', lines[i]) and not re.match(r'^\d+\.\s', lines[i]):
                notes = lines[i]
                i += 1
            
            rooms.append(RoomFinish(
                room_number=number,
                room_name=name,
                floor=floor,
                floor_grout=grout,
                base=base,
                chair_rail=chair_rail,
                walls_primary=primary,
                walls_accent=accent,
                ceiling_material=ceiling_mat,
                ceiling_finish=ceiling_fin,
                ceiling_height=ceiling_ht,
                millwork_wall_cabinets=wall_cabs,
                millwork_base_cabinets=base_cabs,
                millwork_countertop=countertop,
                notes=notes
            ))
        
        return rooms

    def _extract_equipment_schedule(self, text: str) -> List[EquipmentItem]:
        """Extract equipment schedule."""
        equipment = []
        
        # Pattern for RTU/AC units: RTU-1 MODEL ### ...
        equip_pattern = r'(RTU-\d+|AC-\d+|EF-\d+|UV-1)'
        
        for match in re.finditer(equip_pattern, text):
            tag = match.group(1)
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 300)
            context = text[start:end]
            
            # Extract model
            model_match = re.search(r'(?:MODEL|Model)\s+([A-Z0-9]+)', context)
            model = model_match.group(1) if model_match else ''
            
            # Extract manufacturer
            mfg = self._extract_manufacturer(context)
            
            # Determine type
            equip_type = 'Rooftop Unit' if 'RTU' in tag else 'Split System' if 'AC' in tag else 'Exhaust Fan' if 'EF' in tag else 'UV Air Purifier'
            
            equipment.append(EquipmentItem(
                tag=tag,
                equipment_type=equip_type,
                manufacturer=mfg or 'Local Source',
                model=model,
                size='',
                remarks=''
            ))
        
        return equipment

    def _extract_manufacturer(self, text: str) -> Optional[str]:
        """Extract manufacturer name from text."""
        manufacturers = [
            'SHERWIN-WILLIAMS', 'ARMSTRONG', 'ARMSTRONG FLOORING', 'DAL TILE',
            'SCHLUTER', 'ROPPE', 'WILSONART', 'KAWNEER', 'TARKETT',
            'CONSTRUCTION SPECIALTIES', 'EKENA MILLWORK', 'CUSTOM BUILDING PRODUCTS',
            'KOROSEAL', 'JOLLY', 'SHAW CONTRACT'
        ]
        for mfg in manufacturers:
            if mfg in text.upper():
                return mfg.title()
        return None

    def build_enhanced_prompt(self, context: dict, chunk: str) -> str:
        """Build extraction prompt with context."""
        prompt_parts = []
        
        if context.get('finish_legend'):
            prompt_parts.append("INTERIOR FINISH LEGEND (use these exact codes and products):")
            for f in context['finish_legend'][:40]:
                prompt_parts.append(f"  {f.code}: {f.manufacturer} {f.product}, Color: {f.color}, Type: {f.type_size}")
        
        if context.get('room_schedule'):
            prompt_parts.append("\nROOM FINISH SCHEDULE:")
            for r in context['room_schedule'][:25]:
                prompt_parts.append(f"  {r.room_number} {r.room_name}: Floor={r.floor}, Base={r.base}, Walls={r.walls_primary}/{r.walls_accent}, Ceiling={r.ceiling_material}/{r.ceiling_finish}, Height={r.ceiling_height}")
        
        if context.get('equipment_schedule'):
            prompt_parts.append("\nEQUIPMENT SCHEDULE:")
            for e in context['equipment_schedule'][:10]:
                prompt_parts.append(f"  {e.tag}: {e.manufacturer} {e.model} ({e.equipment_type})")
        
        prompt_parts.append(f"\n--- EXTRACTION CONTENT ---\n{chunk}")
        
        return "\n".join(prompt_parts)
