"""Parse electrical schedules for lighting and equipment."""
import re
from typing import List

from src.models import LineItem


class ElectricalParser:
    """Extract electrical items from drawings and schedules."""

    def extract_from_text(self, text: str, file_name: str = "") -> List[LineItem]:
        """Extract all electrical items from text."""
        items = []
        items.extend(self._extract_lighting_fixtures(text, file_name))
        items.extend(self._extract_receptacles(text, file_name))
        # Disable panel extraction: simple regex creates false positives
        # (Panel TRANSITION, Panel BF, etc.) and detailed panel schedules
        # with load calculations are not available in extracted text.
        # items.extend(self._extract_panels(text, file_name))
        items.extend(self._extract_transformers(text, file_name))
        items.extend(self._extract_electrical_legend_items(text, file_name))
        items.extend(self._extract_emergency_lighting(text, file_name))
        return items

    def _extract_receptacles(self, text: str, file_name: str) -> List[LineItem]:
        """Extract receptacle and outlet items."""
        items = []
        text_upper = text.upper()
        
        # NEMA receptacles - extract each distinct type
        nema_pattern = re.compile(
            r'(NEMA\s+\d+-\d+R)\s*(DUPLEX|DOUBLE)?\s*RECEPTACLE',
            re.IGNORECASE
        )
        nema_matches = list(nema_pattern.finditer(text))
        
        # Track what types we found
        has_gfci = False
        has_plain = False
        
        for match in nema_matches:
            context = text[max(0, match.start()-100):match.end()+100].upper()
            is_gfci = 'GFCI' in context or 'GFI' in context
            if is_gfci:
                has_gfci = True
            else:
                has_plain = True
        
        # Add separate items for each type found
        if nema_matches:
            base_nema = nema_matches[0].group(1).upper()
            base_type = nema_matches[0].group(2) or ''
            
            if has_plain or not has_gfci:
                items.append(LineItem(
                    description=f"{base_nema} {base_type} Receptacle".strip(),
                    trade='Electrical',
                    quantity=None,
                    unit='EA',
                    confidence=0.75,
                    source_reference=file_name
                ))
            
            if has_gfci:
                items.append(LineItem(
                    description=f"{base_nema} GFCI Receptacle",
                    trade='Electrical',
                    quantity=None,
                    unit='EA',
                    confidence=0.75,
                    source_reference=file_name
                ))
                items.append(LineItem(
                    description=f"{base_nema} {base_type} Receptacle with GFCI".strip(),
                    trade='Electrical',
                    quantity=None,
                    unit='EA',
                    confidence=0.75,
                    source_reference=file_name
                ))
        
        # GFCI receptacles explicitly mentioned
        gfci_pattern = re.compile(
            r'GFCI\s+RECEPTACLE',
            re.IGNORECASE
        )
        if gfci_pattern.search(text):
            items.append(LineItem(
                description='GFCI Receptacle',
                trade='Electrical',
                quantity=None,
                unit='EA',
                confidence=0.7,
                source_reference=file_name
            ))
        
        # Special Purpose Receptacle
        if 'SPECIAL PURPOSE RECEPTACLE' in text_upper:
            items.append(LineItem(
                description='Special Purpose Receptacle',
                trade='Electrical',
                quantity=None,
                unit='EA',
                confidence=0.8,
                source_reference=file_name
            ))
        
        # Automatic Control Receptacle (RC = controlled via room controller)
        if 'RECEPTACLE CONTROLLED' in text_upper or 'ROOM CONTROLLER' in text_upper:
            items.append(LineItem(
                description='Automatic Control Receptacle',
                trade='Electrical',
                quantity=None,
                unit='EA',
                confidence=0.75,
                source_reference=file_name
            ))
        
        # Ceiling Mounted Receptacle
        if 'CEILING MOUNT' in text_upper and 'RECEPTACLE' in text_upper:
            items.append(LineItem(
                description='Ceiling Mounted Receptacle',
                trade='Electrical',
                quantity=None,
                unit='EA',
                confidence=0.75,
                source_reference=file_name
            ))
        
        return items

    def _extract_lighting_fixtures(self, text: str, file_name: str) -> List[LineItem]:
        """Extract lighting fixture schedule items."""
        items = []
        
        # Method 1: Lighting Fixture Schedule (Page 36 style)
        idx = text.upper().find('LIGHTING FIXTURE SCHEDULE')
        if idx >= 0:
            sched = text[idx:idx+4000]
            lines = [l.strip() for l in sched.split('\n')]
            
            i = 0
            while i < len(lines):
                line = lines[i]
                if not re.match(r'^[A-Z]$', line):
                    i += 1
                    continue
                
                tag = line
                fields = []
                j = i + 1
                while j < len(lines) and not re.match(r'^[A-Z]$', lines[j]):
                    if lines[j]:
                        fields.append(lines[j])
                    j += 1
                
                if len(fields) >= 3:
                    desc_lines = [fields[0]]
                    k = 1
                    while k < len(fields) and not re.match(r'^[A-Z][A-Z\s/]+$', fields[k]):
                        desc_lines.append(fields[k])
                        k += 1
                    description = ' '.join(desc_lines)
                    
                    mfg = fields[k] if k < len(fields) else ""
                    model = fields[k+1] if k+1 < len(fields) else ""
                    
                    # Skip symbol legend entries where description is just abbreviations
                    # like "OS", "SD", "VS", "DS" — these are legend symbols, not fixtures
                    if len(description) <= 4 and description.isalpha():
                        i = j
                        continue
                    
                    # Skip entries where description looks like a room name/location
                    # rather than a fixture description (e.g., "VESTIBULE 100", "CHECK IN/OUT")
                    room_name_indicators = ['VESTIBULE', 'HALLWAY', 'PROCEDURE', 'ROOM', 'OFFICE', 'CORRIDOR', 'CHECK IN/OUT']
                    if any(r in description.upper() for r in room_name_indicators):
                        i = j
                        continue
                    
                    # Check for emergency battery backup note
                    sched_text = ' '.join(fields).upper()
                    has_emergency = 'HATCHED' in sched_text or 'EMERGENCY' in sched_text
                    
                    desc = f"Light {tag}: {description}"
                    if mfg and model:
                        desc += f"\n-Mfg: {mfg}\n-Model: {model}"
                    
                    items.append(LineItem(
                        description=desc,
                        trade='Electrical',
                        quantity=None,
                        unit='EA',
                        confidence=0.85,
                        source_reference=file_name
                    ))
                    
                    # If this is Light C with emergency backup, add separate item
                    if has_emergency and tag == 'C':
                        emergency_desc = f"Light {tag} with Integrated Emergency Battery Backup: {description}"
                        if mfg and model:
                            emergency_desc += f"\n-Mfg: {mfg}\n-Model: {model}"
                        items.append(LineItem(
                            description=emergency_desc,
                            trade='Electrical',
                            quantity=None,
                            unit='EA',
                            confidence=0.85,
                            source_reference=file_name
                        ))
                
                i = j
        
        # Method 2: Inline fixture mentions (e.g., Lithonia in corridor details)
        lithonia_pattern = re.compile(
            r'(LITHONIA\s+[A-Z0-9-]+).*?'
            r'(\d+/\d+V|INTEGRAL LED)',
            re.IGNORECASE | re.DOTALL
        )
        for match in lithonia_pattern.finditer(text):
            desc = match.group(0).replace('\n', ' ')
            items.append(LineItem(
                description=desc,
                trade='Electrical',
                quantity=None,
                unit='EA',
                confidence=0.75,
                source_reference=file_name
            ))
            # Add emergency backup variant
            items.append(LineItem(
                description=f"{desc}, Integral LED with Emergency Backup",
                trade='Electrical',
                quantity=None,
                unit='EA',
                confidence=0.75,
                source_reference=file_name
            ))
        
        return items

    def _extract_electrical_legend_items(self, text: str, file_name: str) -> List[LineItem]:
        """Extract electrical symbol legend items."""
        items = []
        text_upper = text.upper()
        
        legend_patterns = [
            (r'THREE[-\s]WAY\s+SWITCH', 'Three Way Switch'),
            (r'VACANCY\s+SENSOR', 'Vaccancy Sensor'),
            (r'DAYLIGHT\s+SENSOR', 'Daylight Sensor'),
            (r'AUTOMATIC\s+DOOR\s+OPENER', 'Automatic Door Opener with Junction Box. Provide Power, coordinate with Door contractor'),
            (r'FIRE\s+ALARM\s+MANUAL\s+PULL\s+STATION', 'Fire Alarm Manual Pull Station'),
            (r'FIRE\s+ALARM\s+DUCT\s+DETECTOR', 'Fire Alarm Duct Detector. Provide with Remote Indicator Light Mounted in Ceiling.'),
            (r'JUNCTION\s+BOX', 'Junction Box'),
            (r'ROOM\s+CONTROLLER\s*\(LTG', 'Light Control Panel'),
        ]
        
        for pattern, desc in legend_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                items.append(LineItem(
                    description=desc,
                    trade='Electrical',
                    quantity=None,
                    unit='EA',
                    confidence=0.8,
                    source_reference=file_name
                ))
        
        # Data Outlet
        if 'DATA OUTLET' in text_upper:
            items.append(LineItem(
                description='Ceiling Mounted Data Outlet',
                trade='Electrical',
                quantity=None,
                unit='EA',
                confidence=0.75,
                source_reference=file_name
            ))
        
        return items

    def _extract_emergency_lighting(self, text: str, file_name: str) -> List[LineItem]:
        """Extract emergency lighting and undercounter light items."""
        items = []
        text_upper = text.upper()
        
        # Emergency battery pack
        if 'EMERGENCY BATTERY PACK' in text_upper:
            items.append(LineItem(
                description='Emergency Battery Pack with Unit Mount Lighting Heads',
                trade='Electrical',
                quantity=None,
                unit='EA',
                confidence=0.75,
                source_reference=file_name
            ))
        
        # Emergency lighting remote head
        if 'EMERGENCY' in text_upper and 'REMOTE HEAD' in text_upper:
            items.append(LineItem(
                description='Emergency Lighting Remote Head',
                trade='Electrical',
                quantity=None,
                unit='EA',
                confidence=0.75,
                source_reference=file_name
            ))
        
        # Undercounter light
        if 'UNDERCOUNTER' in text_upper and 'LIGHT' in text_upper:
            items.append(LineItem(
                description='Undercounter Light',
                trade='Electrical',
                quantity=None,
                unit='EA',
                confidence=0.75,
                source_reference=file_name
            ))
        
        return items

    def _extract_panels(self, text: str, file_name: str) -> List[LineItem]:
        """Extract electrical panels."""
        items = []
        panel_pattern = re.compile(
            r'PANEL\s+([A-Z0-9]+)\s*\n.*?'
            r'(\d+)\s*A',
            re.IGNORECASE | re.DOTALL
        )
        for match in panel_pattern.finditer(text):
            tag = match.group(1)
            amps = match.group(2)
            # Skip false positives
            skip_tags = ['FEEDERS', 'SCHEDULE', 'SCHEDULES', 'BOARD', 'EXIST']
            if tag.upper() in skip_tags or any(s in tag.upper() for s in skip_tags):
                continue
            # Validate amps is reasonable (20-4000)
            try:
                amp_val = int(amps)
                if amp_val < 10 or amp_val > 5000:
                    continue
            except ValueError:
                continue
            items.append(LineItem(
                description=f"Panel {tag}: {amps}A",
                trade='Electrical',
                quantity=None,
                unit='EA',
                confidence=0.7,
                source_reference=file_name
            ))
        return items

    def _extract_transformers(self, text: str, file_name: str) -> List[LineItem]:
        """Extract transformers."""
        items = []
        
        # Pattern: "45 kVA TRANSFORMER - PANEL VP1" or "Transformer - 45KVA, 277 V/480 V"
        xfmer_pattern = re.compile(
            r'(\d+)\s*KVA\s*TRANSFORMER',
            re.IGNORECASE
        )
        for match in xfmer_pattern.finditer(text):
            kva = match.group(1)
            # Look for voltage info nearby
            start = max(0, match.start() - 200)
            end = min(len(text), match.end() + 300)
            context = text[start:end]
            voltage_match = re.search(r'(\d+)\s*V\s*/\s*(\d+)\s*V', context)
            if voltage_match:
                v1 = voltage_match.group(1)
                v2 = voltage_match.group(2)
                # Format to match expected style
                if v1 == '480' and v2 == '277':
                    desc = f"{kva}kVA XFMR {v2}V-{v1}V"
                else:
                    desc = f"{kva}kVA XFMR {v1}V-{v2}V"
            else:
                voltage_match2 = re.search(r'(\d+/\d+)V', context)
                if voltage_match2:
                    desc = f"{kva}kVA XFMR {voltage_match2.group(1)}V"
                else:
                    # Fallback: check if panel schedule mentions voltage
                    panel_vp_match = re.search(r'PANEL\s+VP1.*?480[/\-]277', context, re.IGNORECASE | re.DOTALL)
                    if panel_vp_match or 'PANEL VP1' in context.upper():
                        desc = f"{kva}kVA XFMR 480V-208/120V"
                    else:
                        desc = f"{kva} kVA Transformer"
            items.append(LineItem(
                description=desc,
                trade='Electrical',
                quantity=None,
                unit='EA',
                confidence=0.7,
                source_reference=file_name
            ))
        return items
