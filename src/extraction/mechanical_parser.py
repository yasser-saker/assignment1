"""Parse mechanical schedules and drawings for HVAC items."""
import re
from typing import List, Tuple, Dict
from collections import Counter, defaultdict

from src.models import LineItem


class MechanicalParser:
    """Extract HVAC items from mechanical drawings and schedules."""

    def extract_from_text(self, text: str, file_name: str = "") -> List[LineItem]:
        """Extract all mechanical/HVAC items from text."""
        items = []
        items.extend(self._extract_ductwork(text, file_name))
        items.extend(self._extract_diffusers(text, file_name))
        items.extend(self._extract_equipment(text, file_name))
        items.extend(self._extract_refrigerant_lines(text, file_name))
        items.extend(self._extract_demolition(text, file_name))
        items.extend(self._extract_fittings(text, file_name))
        return items

    def _extract_ductwork(self, text: str, file_name: str) -> List[LineItem]:
        """Extract duct sizes from mechanical plans."""
        items = []
        
        # Round ducts: 6"ø, 8"ø, 10"ø, etc.
        round_ducts = re.findall(r'\b(\d+"?)\s*[\u00f8\u2205]\b', text)
        round_counts = Counter(round_ducts)
        for size, count in round_counts.items():
            # Filter realistic duct sizes (2" to 36")
            try:
                num = int(size.replace('"', ''))
                if 2 <= num <= 36:
                    items.append(LineItem(
                        description=f'{size} Dia Duct',
                        trade='HVAC',
                        quantity=count,
                        unit='EA',
                        confidence=0.75,
                        source_reference=file_name
                    ))
            except ValueError:
                continue
        
        # Rectangular ducts: 6"x6", 10"x8", etc.
        rect_ducts = re.findall(r'\b(\d+[\"\']?)\s*x\s*(\d+[\"\']?)\b', text)
        rect_counts = Counter(rect_ducts)
        for (w, h), count in rect_counts.items():
            try:
                w_num = int(w.replace('"', '').replace("'", ''))
                h_num = int(h.replace('"', '').replace("'", ''))
                # Filter realistic sizes
                if 2 <= w_num <= 60 and 2 <= h_num <= 60:
                    items.append(LineItem(
                        description=f'{w}"x{h}" Duct',
                        trade='HVAC',
                        quantity=count,
                        unit='EA',
                        confidence=0.75,
                        source_reference=file_name
                    ))
            except ValueError:
                continue
        
        return items

    def _extract_diffusers(self, text: str, file_name: str) -> List[LineItem]:
        """Extract diffuser/grille schedule items dynamically.
        
        Works with various schedule formats and materials.
        """
        items = []
        
        # Detect diffuser schedule by multiple possible headers
        sched_headers = ['DIFFUSERS, REGISTERS AND GRILLES SCHEDULE', 
                         'AIR DEVICE SCHEDULE', 'DIFFUSER SCHEDULE', 'GRILLE SCHEDULE']
        sched_start = -1
        for header in sched_headers:
            idx = text.find(header)
            if idx != -1:
                sched_start = idx
                break
        
        if sched_start == -1:
            return items
        
        # Find end of section (next major schedule or end of text)
        next_schedules = [
            'ELECTRIC TERMINAL UNIT HEATER SCHEDULE',
            'EXHAUST FAN SCHEDULE',
            'ROOFTOP AIR CONDITIONING UNIT SCHEDULE',
            'VAV TERMINAL UNIT SCHEDULE',
            'AIR HANDLING UNIT SCHEDULE',
            'UNIT HEATER SCHEDULE',
            'CHILLER SCHEDULE',
            'BOILER SCHEDULE',
        ]
        sched_end = len(text)
        for ns in next_schedules:
            idx = text.find(ns, sched_start + 1)
            if idx != -1 and idx < sched_end:
                sched_end = idx
        
        section = text[sched_start:sched_end]
        
        # Generic diffuser row parsing - look for tag patterns followed by numeric specs
        # Tag can be: S-1, R-1, AD-1, D-1, etc.
        lines = [l.strip() for l in section.split('\n')]
        
        i = 0
        while i < len(lines):
            # Look for diffuser tag (e.g., S-1, R-2, AD-1)
            tag_match = re.match(r'^([A-Z]{1,3}-\d+)$', lines[i])
            if not tag_match:
                i += 1
                continue
            
            tag = tag_match.group(1)
            fields = []
            j = i + 1
            while j < len(lines) and j < i + 15:
                if re.match(r'^([A-Z]{1,3}-\d+)$', lines[j]):
                    break
                if lines[j]:
                    fields.append(lines[j])
                j += 1
            
            # Try to extract meaningful fields
            cfm_range = ''
            module_size = ''
            material = 'Aluminum'
            pattern = ''
            bod = ''
            
            for field in fields:
                # CFM range: "95 - 210" or "100-500"
                if re.match(r'^\d+\s*[-\u2013]\s*\d+$', field):
                    cfm_range = field.replace(' ', '')
                # Module size: "24 x 24" or "12x12"
                elif re.match(r'^\d+\s*x\s*\d+$', field):
                    module_size = field.replace(' ', '')
                # Pattern: 4-WAY, 2-WAY, etc.
                elif re.match(r'^(\d-WAY|GRID CORE|PERFORATED|LOUVERED)$', field.upper()):
                    pattern = field
                # Material: ALUMINUM, STEEL, etc.
                elif field.upper() in ['ALUMINUM', 'STEEL', 'GALVANIZED', 'STAINLESS']:
                    material = field.title()
                # B.O.D: numbers with inches
                elif re.match(r'^\d+"?$', field):
                    bod = field
            
            if module_size or cfm_range:
                desc = f"{tag}:"
                if bod:
                    desc += f"\n-B.O.D: {bod}"
                if module_size:
                    dims = module_size.split('x')
                    if len(dims) == 2:
                        desc += f"\n-Nominal Module Size: {dims[0]}\"x{dims[1]}\""
                if cfm_range:
                    desc += f"\n-CFM: {cfm_range}"
                desc += f"\n-Material: {material}"
                
                items.append(LineItem(
                    description=desc,
                    trade='HVAC',
                    quantity=None,
                    unit='EA',
                    confidence=0.85,
                    source_reference=file_name
                ))
            
            i = j
        
        return items

    def _extract_vav_schedule(self, text: str, file_name: str) -> List[LineItem]:
        """Extract VAV terminal units from schedule dynamically."""
        items = []
        
        idx = text.upper().find('VAV TERMINAL UNIT SCHEDULE')
        if idx == -1:
            return items
        
        sched = text[idx:idx+3000]
        # Find all VAV tags in the schedule section
        vav_tags = re.findall(r'\bVAV-(\d+[A-Z]?)\b', sched)
        
        # Look for any manufacturer/model pattern (MFG / MODEL)
        mfg = None
        model = None
        
        # Try common patterns
        mfg_patterns = [
            r'([A-Z]{2,5})\s*/\s*([A-Z0-9\-]{2,10})',
            r'MANUFACTURER[:\s]+([A-Z]{2,10}).*MODEL[:\s]+([A-Z0-9\-]{2,10})',
        ]
        for pattern in mfg_patterns:
            mfg_match = re.search(pattern, sched)
            if mfg_match:
                candidate_mfg = mfg_match.group(1).strip()
                candidate_model = mfg_match.group(2).strip()
                # Exclude common false positives
                if candidate_mfg not in ('IN', 'NO', 'MAX', 'MIN', 'CFM', 'UNIT'):
                    mfg = candidate_mfg
                    model = candidate_model
                    break
        
        if not mfg:
            mfg = 'Unknown'
            model = ''
        
        for tag_num in sorted(set(vav_tags)):
            tag = f"VAV-{tag_num}"
            desc = f"{tag}:\n-Mfg/Model: {mfg}/{model}"
            items.append(LineItem(
                description=desc,
                trade='HVAC',
                quantity=None,
                unit='EA',
                confidence=0.85,
                source_reference=file_name
            ))
        
        return items

    def _extract_equipment(self, text: str, file_name: str) -> List[LineItem]:
        """Extract HVAC equipment from schedules."""
        items = []
        
        # VAV schedule (prioritized)
        vav_items = self._extract_vav_schedule(text, file_name)
        items.extend(vav_items)
        
        # RTU schedule
        rtu_pattern = re.compile(
            r'RTU-(\d+)\s*\n([A-Z][A-Z\s/]+?)\s*\n.*?'
            r'(\d[,\d]*)\s*\n.*?'
            r'([A-Z][A-Z\s/-]+\s*/\s*[A-Z0-9-]+)',
            re.DOTALL
        )
        for match in rtu_pattern.finditer(text):
            tag = f"RTU-{match.group(1)}"
            area = match.group(2).strip()
            cfm = match.group(3).replace(',', '')
            mfg_model = match.group(4).strip()
            items.append(LineItem(
                description=f"{tag}: {mfg_model}, {cfm} CFM, Area: {area}",
                trade='HVAC',
                quantity=None,
                unit='EA',
                confidence=0.9,
                source_reference=file_name
            ))
        
        # AC/HP units from AC/HP schedule (Page 32 style)
        # Pattern: AC-X ... HITACHI / RAC-... followed by HP-X ... HITACHI / RAK-...
        ac_hp_pattern = re.compile(
            r'AC-(\d+).*?HITACHI\s*/\s*(RAC-[A-Z0-9]+)',
            re.DOTALL | re.IGNORECASE
        )
        for match in ac_hp_pattern.finditer(text):
            ac_tag = f"AC-{match.group(1)}"
            ac_model = match.group(2)
            items.append(LineItem(
                description=f"{ac_tag}: B.O.D Outdoor Unit: HITACHI / {ac_model}",
                trade='HVAC',
                quantity=None,
                unit='EA',
                confidence=0.85,
                source_reference=file_name
            ))
        
        hp_pattern = re.compile(
            r'HP-(\d+).*?HITACHI\s*/\s*(RAK-[A-Z0-9]+)',
            re.DOTALL | re.IGNORECASE
        )
        for match in hp_pattern.finditer(text):
            hp_tag = f"HP-{match.group(1)}"
            hp_model = match.group(2)
            items.append(LineItem(
                description=f"{hp_tag}: B.O.D Indoor Unit: HITACHI / {hp_model}",
                trade='HVAC',
                quantity=None,
                unit='EA',
                confidence=0.85,
                source_reference=file_name
            ))
        
        # Fallback: AC/HP units from general plan text
        ac_pattern = re.compile(r'AC-(\d+)\s*[/,\s]*HP-(\d+)', re.IGNORECASE)
        ac_matches = list(ac_pattern.finditer(text))
        for match in ac_matches:
            ac_tag = f"AC-{match.group(1)}"
            hp_tag = f"HP-{match.group(2)}"
            # Find manufacturer nearby
            start = max(0, match.start() - 300)
            end = min(len(text), match.end() + 300)
            context = text[start:end]
            mfg_match = re.search(r'([A-Z][A-Z\s/-]+)\s*/\s*([A-Z0-9-]+)', context)
            if mfg_match:
                mfg = mfg_match.group(1).strip()
                model = mfg_match.group(2).strip()
                items.append(LineItem(
                    description=f"{ac_tag}: B.O.D Outdoor Unit: {mfg} / {model}",
                    trade='HVAC',
                    quantity=None,
                    unit='EA',
                    confidence=0.85,
                    source_reference=file_name
                ))
                items.append(LineItem(
                    description=f"{hp_tag}: B.O.D Indoor Unit: {mfg} / {model}",
                    trade='HVAC',
                    quantity=None,
                    unit='EA',
                    confidence=0.85,
                    source_reference=file_name
                ))
        
        # Exhaust Fans
        ef_pattern = re.compile(
            r'EF-(\d+)\s*\n.*?'
            r'(\d+)\s*\n.*?'
            r'([A-Z][A-Z\s/-]+)\s*/\s*([A-Z0-9-]+)',
            re.DOTALL
        )
        for match in ef_pattern.finditer(text):
            tag = f"EF-{match.group(1)}"
            cfm = match.group(2)
            mfg = match.group(3).strip()
            model = match.group(4).strip()
            items.append(LineItem(
                description=f"{tag}: {mfg} / {model}, {cfm} CFM",
                trade='HVAC',
                quantity=None,
                unit='EA',
                confidence=0.85,
                source_reference=file_name
            ))
        
        # CUH (Ceiling Unit Heater)
        cuh_pattern = re.compile(
            r'CUH-(\d+)\s*\n.*?'
            r'(\d[,\d]+)\s*\n.*?'
            r'(\d+[,\d]*)\s*\n.*?'
            r'(\d+)\s*\n.*?'
            r'(\d+/\d+)\s*\n.*?'
            r'([A-Z][A-Z\s/-]+)\s*/\s*([A-Z0-9-]+)',
            re.DOTALL
        )
        for match in cuh_pattern.finditer(text):
            tag = f"CUH-{match.group(1)}"
            btuh = match.group(2).replace(',', '')
            amps = match.group(3).replace(',', '')
            kw = match.group(4)
            voltage = match.group(5)
            mfg = match.group(6).strip()
            model = match.group(7).strip()
            items.append(LineItem(
                description=f"{tag}: {mfg} / {model}, {btuh} BTUH, {kw}KW, {voltage}V",
                trade='HVAC',
                quantity=None,
                unit='EA',
                confidence=0.85,
                source_reference=file_name
            ))
        
        # VAV Terminal Unit Schedule
        # Pattern: VAV-X followed by CFM values and inlet size and manufacturer
        vav_schedule_pattern = re.compile(
            r'VAV-(\d+)\s*\n'
            r'(\d+)\s*\n'
            r'(\d+)\s*\n'
            r'(\d+)\s*\n'
            r'(\d+)\s*\n'
            r'(\d+)\s*\n'
            r'(\d+)\s*\n'
            r'(\d+)\s*\n'
            r'(\d+)\s*\n'
            r'(\d+\.?\d*)\s*\n'
            r'(\d+\.?\d*)\s*\n'
            r'(\d+\.?\d*)\s*\n'
            r'(\d+)\s*\n'
            r'([A-Z][A-Z\s/-]+)\s*/\s*([A-Z0-9-]+)',
            re.DOTALL
        )
        for match in vav_schedule_pattern.finditer(text):
            tag = f"VAV-{match.group(1)}"
            max_cfm = match.group(2)
            min_cfm = match.group(3)
            htg_cfm = match.group(4)
            pri_cfm = match.group(5)
            vent_cfm = match.group(6)
            apd = match.group(7)
            inlet = match.group(8)
            volts = match.group(9)
            phase = match.group(10)
            kw = match.group(11)
            mbh = match.group(12)
            mfg = match.group(13).strip()
            model = match.group(14).strip()
            items.append(LineItem(
                description=f"{tag}: Mfg/Model: {mfg} / {model}, Inlet: {inlet}\", Max CFM: {max_cfm}",
                trade='HVAC',
                quantity=None,
                unit='EA',
                confidence=0.85,
                source_reference=file_name
            ))
        
        # Fallback: VAV boxes from plan text only (if no schedule found)
        if not any('VAV-' in item.description and 'Mfg/Model' in item.description for item in items):
            vav_pattern = re.compile(r'VAV\s*(\d+)', re.IGNORECASE)
            vav_counts = Counter(vav_pattern.findall(text))
            for vav_num, count in vav_counts.items():
                items.append(LineItem(
                    description=f"VAV-{vav_num}: Variable Air Volume Terminal Unit",
                    trade='HVAC',
                    quantity=count,
                    unit='EA',
                    confidence=0.7,
                    source_reference=file_name
                ))
        
        return items

    def _extract_refrigerant_lines(self, text: str, file_name: str) -> List[LineItem]:
        """Extract refrigerant and condensate lines."""
        items = []
        
        # Refrigerant lines up to roof
        ref_pattern = re.compile(r'(\d/\d+\"|1\"|3/4\")\s*(?:ø|∅)?\s*REFRIGERANT', re.IGNORECASE)
        ref_matches = ref_pattern.findall(text)
        ref_counts = Counter(ref_matches)
        for size, count in ref_counts.items():
            items.append(LineItem(
                description=f'{size} Dia Refrigerant Lines',
                trade='HVAC',
                quantity=count,
                unit='FT',
                confidence=0.7,
                source_reference=file_name
            ))
        
        # Fallback: refrigerant mentions without size
        if not ref_matches and 'REFRIGERANT' in text.upper():
            for match in re.finditer(r'REFRIGERANT\s+(?:SUCTION|LIQUID|GAS)', text, re.IGNORECASE):
                start = max(0, match.start() - 200)
                end = min(len(text), match.end() + 200)
                context = text[start:end]
                size_match = re.search(r'(\d/\d+"|1"|3/4")', context)
                size = size_match.group(1) if size_match else '1"'
                items.append(LineItem(
                    description=f'{size} Dia Refrigerant Lines',
                    trade='HVAC',
                    quantity=None,
                    unit='FT',
                    confidence=0.7,
                    source_reference=file_name
                ))
        
        # Pipe up to roof
        # Pipe up to roof
        pipe_pattern = re.compile(r'(\d/\d+\"|1\"|3/4\")\s*(?:ø|∅)?\s*PIPE\s+(?:UP\s+)?TO\s+ROOF', re.IGNORECASE)
        pipe_matches = pipe_pattern.findall(text)
        pipe_counts = Counter(pipe_matches)
        for size, count in pipe_counts.items():
            items.append(LineItem(
                description=f'{size} Pipe upto Roof',
                trade='HVAC',
                quantity=count,
                unit='FT',
                confidence=0.7,
                source_reference=file_name
            ))
        
        # Condensate lines
        cond_pattern = re.compile(r'(\d/\d+\"|1\"|3/4\")\s*CONDENSATE', re.IGNORECASE)
        cond_matches = cond_pattern.findall(text)
        cond_counts = Counter(cond_matches)
        for size, count in cond_counts.items():
            items.append(LineItem(
                description=f'{size} Condensate Line',
                trade='HVAC',
                quantity=count,
                unit='FT',
                confidence=0.7,
                source_reference=file_name
            ))
        
        return items

    def _extract_demolition(self, text: str, file_name: str) -> List[LineItem]:
        """Extract demolition items from mechanical demo plans."""
        items = []
        
        demo_patterns = [
            (r'REMOVE\s+EXISTING\s+([A-Z][A-Z\s]+)', "Remove Existing {}"),
            (r'EXISTING\s+([A-Z][A-Z\s]+)\s+TO\s+BE\s+REMOVED', "Existing {} to be Removed"),
            (r'REMOVE\s+SECTION\s+OF\s+([A-Z][A-Z\s]+)', "Remove Section of {}"),
        ]
        
        for pattern, template in demo_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                desc = template.format(match.group(1).strip())
                items.append(LineItem(
                    description=desc,
                    trade='Demolition',
                    quantity=None,
                    unit='EA',
                    confidence=0.7,
                    source_reference=file_name
                ))
        
        return items

    def _extract_fittings(self, text: str, file_name: str) -> List[LineItem]:
        """Extract duct fittings from mechanical plans."""
        items = []
        
        # Flexible ductwork
        flex_patterns = [
            r'(\d+)"\s+Flexible\s+Duct\s+to\s+Diffuser',
            r'(\d+)"\s+FLEXIBLE\s+DUCTWORK',
        ]
        for pattern in flex_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                size = match.group(1)
                items.append(LineItem(
                    description=f'{size}" Flexible Duct to Diffuser',
                    trade='HVAC',
                    quantity=None,
                    unit='EA',
                    confidence=0.8,
                    source_reference=file_name
                ))
        
        # Flexible duct to diffuser
        flex_pattern = re.compile(
            r'(\d+)"\s+Flexible\s+Duct\s+to\s+Diffuser',
            re.IGNORECASE
        )
        for match in flex_pattern.finditer(text):
            size = match.group(1)
            items.append(LineItem(
                description=f'{size}" Flexible Duct to Diffuser',
                trade='HVAC',
                quantity=None,
                unit='EA',
                confidence=0.8,
                source_reference=file_name
            ))
        
        # Duct elbows - mentioned explicitly
        elbow_pattern = re.compile(
            r'\b(\d+\"?)\s*(?:ø|∅)?\s*ELBOW|\b(\d+[\"\']?)\s*x\s*(\d+[\"\']?)\s*ELBOW',
            re.IGNORECASE
        )
        for match in elbow_pattern.finditer(text):
            if match.group(1):
                size = match.group(1)
                items.append(LineItem(
                    description=f'{size} Dia Duct Elbow',
                    trade='HVAC',
                    quantity=None,
                    unit='EA',
                    confidence=0.7,
                    source_reference=file_name
                ))
            else:
                w, h = match.group(2), match.group(3)
                items.append(LineItem(
                    description=f'{w}"x{h}" Duct Elbow',
                    trade='HVAC',
                    quantity=None,
                    unit='EA',
                    confidence=0.7,
                    source_reference=file_name
                ))
        
        # Clinch collar
        if 'CLINCH' in text.upper() or 'CLINCH COLLAR' in text.upper():
            items.append(LineItem(
                description='Clinch Collar w/ Clinch Lock',
                trade='HVAC',
                quantity=None,
                unit='EA',
                confidence=0.7,
                source_reference=file_name
            ))
        
        # Duct to duct connections
        if 'DUCT TO DUCT' in text.upper() or 'DUCT CONNECTION' in text.upper():
            items.append(LineItem(
                description='Duct to Duct Connections',
                trade='HVAC',
                quantity=None,
                unit='EA',
                confidence=0.7,
                source_reference=file_name
            ))
        
        # Exterior ductwork support
        if 'EXTERIOR DUCTWORK SUPPORT' in text.upper():
            items.append(LineItem(
                description='Exterior Ductwork Support (5/M402)',
                trade='HVAC',
                quantity=None,
                unit='EA',
                confidence=0.7,
                source_reference=file_name
            ))
        
        # Pipe curb / portal
        if 'PIPE CURB' in text.upper() or 'PIPE PORTAL' in text.upper():
            items.append(LineItem(
                description='Provide Pipe Curb throughout Roof',
                trade='HVAC',
                quantity=None,
                unit='EA',
                confidence=0.7,
                source_reference=file_name
            ))
        
        # Cleanout
        if 'CLEANOUT' in text.upper():
            items.append(LineItem(
                description='Cleanout',
                trade='Plumbing',
                quantity=None,
                unit='EA',
                confidence=0.7,
                source_reference=file_name
            ))
        
        return items
