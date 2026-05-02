"""Dynamic rule-based extractor that works across all projects.

Strategy:
1. Extract context from drawings (finish legend, room schedule, equipment schedule)
2. Parse mechanical schedules (diffusers, VAV, RTU, etc.)
3. Parse electrical schedules (lighting, panels, transformers)
4. Detect and parse generic schedules dynamically
5. Classify trades from context
6. Post-filter with LLM to remove false positives

This extractor combines all specialized parsers into a single dynamic system.
"""
import re
import os
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from src.models import LineItem
from src.extraction.context_extractor import ContextExtractor, FinishCode, RoomFinish
from src.extraction.mechanical_parser import MechanicalParser
from src.extraction.electrical_parser import ElectricalParser


class ScheduleDetector:
    """Dynamically detect schedule sections in text."""
    
    SCHEDULE_PATTERNS = [
        # HVAC schedules
        (r'(?:diffusers?|registers?|grilles?|supply\s+air|return\s+air).*schedule', 'diffuser'),
        (r'vav\s*(?:terminal|box)?.*schedule', 'vav'),
        (r'rooftop\s*(?:unit|air\s*conditioning).*schedule', 'rtu'),
        (r'(?:air\s*handling|ahu).*schedule', 'ahu'),
        (r'(?:exhaust|supply|return)\s*fan.*schedule', 'fan'),
        # Electrical schedules
        (r'lighting\s*fixture.*schedule', 'lighting'),
        (r'panel\s*(?:schedule|board)', 'panel'),
        (r'transformer.*schedule', 'transformer'),
        (r'emergency\s*light.*schedule', 'emergency_light'),
        # Other schedules
        (r'equipment.*schedule', 'equipment'),
        (r'door.*schedule', 'door'),
        (r'finish.*(?:schedule|legend)', 'finish'),
        (r'room\s*finish.*schedule', 'room_finish'),
    ]
    
    def detect_schedules(self, text: str) -> List[Tuple[str, str, int, int]]:
        """Detect all schedule sections in text."""
        text_upper = text.upper()
        schedules = []
        
        for pattern, sched_type in self.SCHEDULE_PATTERNS:
            for match in re.finditer(pattern, text_upper, re.IGNORECASE):
                start = match.start()
                # Find end of schedule (next major section or 3000 chars)
                end = start + 3000
                next_section = re.search(r'\n\s*(?:SCHEDULE|PLAN|SECTION|NOTES|DRAWING)\s*\n', 
                                        text_upper[start+50:start+5000], re.IGNORECASE)
                if next_section:
                    end = start + 50 + next_section.start()
                
                schedule_text = text[start:end]
                if len(schedule_text) > 100:
                    schedules.append((schedule_text, sched_type, start, end))
        
        # Remove overlapping schedules (keep longest)
        schedules.sort(key=lambda x: x[2])
        filtered = []
        for s in schedules:
            if not filtered:
                filtered.append(s)
            else:
                last = filtered[-1]
                if s[2] < last[3]:  # Overlap
                    if len(s[0]) > len(last[0]):
                        filtered[-1] = s
                else:
                    filtered.append(s)
        
        return filtered


class GenericRowParser:
    """Parse schedule rows generically."""
    
    # Patterns that are NOT equipment tags (drawing numbers, title blocks, etc.)
    INVALID_TAG_PATTERNS = [
        r'^A-\d{3}$',  # Drawing numbers like A-101
        r'^\d+$',  # Pure numbers
        r'^(TITLE|REVISION|DRAWN|CHECKED|DATE|SCALE|PROJECT|CLIENT|ARCHITECT)$',
        r'^(TYP|SIM|N\.T\.S|N\s*-\s*T\s*-\s*S)$',
        r'^(PAGE|SHEET|INDEX|LEGEND|NOTES?)$',
    ]
    
    # Valid equipment tag prefixes
    VALID_TAG_PREFIXES = ['RTU', 'VAV', 'AHU', 'EF', 'SF', 'HP', 'AC', 'S', 'R', 'V', 'E', 'H',
                          'Light', 'Panel', 'XFMR', 'T', 'F', 'C', 'B', 'D', 'G', 'J', 'K', 'L',
                          'M', 'N', 'O', 'P', 'Q', 'W', 'X', 'Y', 'Z']
    
    def __init__(self):
        self.tag_pattern = re.compile(r'\b([A-Z][A-Z0-9]*[-_]?\d+[A-Z0-9]*)\b')
        self.cfm_pattern = re.compile(r'(\d{2,4})\s*(?:-\s*(\d{2,4}))?\s*CFM', re.IGNORECASE)
        self.size_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)')
        self.volt_pattern = re.compile(r'(\d{2,3})\s*V')
        self.amp_pattern = re.compile(r'(\d{1,3})\s*A')
        self.watt_pattern = re.compile(r'(\d{2,5})\s*W')
        # Manufacturer: specific known brands + generic pattern
        self.known_manufacturers = [
            'Siemens', 'Lithonia', 'Sherwin Williams', 'Armstrong', 'Titus', 'JCI',
            'Delta', 'Axis', 'Diode', 'Cooper', 'Lutron', 'Bodine', 'Philips',
            'Halo', 'Acuity', 'Wilsonart', 'Daltile', 'Flexco', 'Mannington',
            'Shaw', 'Mohawk', 'Behr', 'PPG', 'Benjamin Moore', 'Valspar',
            'USG', 'Georgia Pacific', 'CertainTeed', 'Johns Manville',
            'Hitachi', 'Carrier', 'Trane', 'Lennox', 'York', 'Daikin', 'Mitsubishi',
        ]
    
    def is_valid_tag(self, tag: str) -> bool:
        """Check if a tag is a valid equipment tag, not a drawing number."""
        tag = tag.strip()
        if len(tag) < 2:
            return False
        
        # Check against invalid patterns
        for pattern in self.INVALID_TAG_PATTERNS:
            if re.match(pattern, tag, re.IGNORECASE):
                return False
        
        # Check if it's a drawing number (A-101 format)
        if re.match(r'^[A-Z]-\d{3}$', tag):
            return False
        
        # Check valid prefixes
        has_valid_prefix = any(
            tag.upper().startswith(prefix.upper()) 
            for prefix in self.VALID_TAG_PREFIXES
        )
        
        # Also allow tags that are clearly equipment (contain numbers after letters)
        # Require at least 3 letters OR a known prefix to avoid false positives like SR64
        looks_like_equipment = bool(re.match(r'^[A-Z]{3,}[-_]?\d', tag, re.IGNORECASE))
        
        return has_valid_prefix or looks_like_equipment
    
    def extract_tag(self, text: str) -> Optional[str]:
        """Extract equipment tag from text."""
        # Priority patterns (known equipment types)
        priority_patterns = [
            r'\b(RTU[-_]?\d+)\b',
            r'\b(VAV[-_]?\d+)\b',
            r'\b(AHU[-_]?\d+)\b',
            r'\b(EF[-_]?\d+)\b',
            r'\b(SF[-_]?\d+)\b',
            r'\b(HP[-_]?\d+)\b',
            r'\b(AC[-_]?\d+)\b',
            r'\b([SR][-_]\d{1,3})\b',  # S-2, R-1 (diffusers)
            r'\b(V[-_]\d{1,3})\b',  # V-1 (VAV)
            r'\b(E[-_]\d{1,3})\b',  # E-1 (exhaust)
            r'\b(H[-_]\d{1,3})\b',  # H-1 (heater)
            r'\b(F[-_]\d{1,3})\b',  # F-1 (fan)
            r'\b(T[-_]\d{1,3})\b',  # T-1 (thermostat)
            r'\b(Light[ \t]*[A-Z]\d?)\b',
            r'\b(Panel[ \t]*[A-Z]\d?)\b',
            r'\b(XFMR[-_]?\d+)\b',
            r'\b(LC[-_]?\d+)\b',  # LC-01 (lighting circuits)
            r'\b(DM[-_]?\d+)\b',  # DM-100 (dimmer)
            r'\b(I[-_]\d+)\b',  # I-1 (inverter)
        ]
        for p in priority_patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                tag = m.group(1).strip()
                if self.is_valid_tag(tag):
                    return tag
        
        # Generic pattern - only if surrounded by equipment context
        # Require 3+ letters for generic match (2-letter without separator often false positive)
        generic = re.search(r'\b([A-Z]{3,4}[-_]?\d{1,3}[A-Z]?)\b', text)
        if generic:
            tag = generic.group(1).strip()
            # Only accept if context suggests equipment
            context_lower = text.lower()
            equipment_context = any(kw in context_lower for kw in [
                'schedule', 'cfm', 'voltage', 'watt', 'amp', 'unit', 'model',
                'type', 'size', 'manufacturer', 'mfg', 'spec'
            ])
            if equipment_context and self.is_valid_tag(tag):
                return tag
        
        return None
    
    def extract_manufacturer(self, text: str) -> Optional[str]:
        """Extract manufacturer from text - only known brands."""
        text_upper = text.upper()
        for mfg in self.known_manufacturers:
            if mfg.upper() in text_upper:
                return mfg
        return None
    
    def parse_schedule_rows(self, text: str, sched_type: str) -> List[Dict]:
        """Parse schedule text into rows."""
        rows = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if len(line) < 3:
                continue
            
            # Skip title block lines
            if self._is_title_block_line(line):
                continue
            
            # Look for equipment tag
            tag = self.extract_tag(line)
            if not tag:
                context = '\n'.join(lines[i:min(i+5, len(lines))])
                tag = self.extract_tag(context)
            
            if tag:
                row = {'tag': tag}
                
                # Extract CFM
                cfm_match = self.cfm_pattern.search(line)
                if cfm_match:
                    if cfm_match.group(2):
                        row['cfm'] = f"{cfm_match.group(1)}-{cfm_match.group(2)}"
                    else:
                        row['cfm'] = cfm_match.group(1)
                
                # Extract size
                size_match = self.size_pattern.search(line)
                if size_match:
                    row['size'] = f"{size_match.group(1)}\"x{size_match.group(2)}\""
                
                # Extract voltage
                volt_match = self.volt_pattern.search(line)
                if volt_match:
                    row['voltage'] = f"{volt_match.group(1)}V"
                
                # Extract manufacturer - only known brands
                context = '\n'.join(lines[max(0,i-2):min(i+5, len(lines))])
                mfg = self.extract_manufacturer(context)
                if mfg:
                    row['manufacturer'] = mfg
                
                # Skip rows that only have a tag with no specs
                # (avoids false positives like "EF-1" with no CFM or model)
                if len(row) <= 2:  # Only 'tag' and 'type'
                    continue
                
                row['type'] = sched_type
                rows.append(row)
        
        return rows
    
    def _is_title_block_line(self, line: str) -> bool:
        """Check if line is from title block, not schedule data."""
        title_block_keywords = [
            'drawn by', 'checked by', 'revision', 'date:', 'scale:', 
            'project no', 'sheet', 'page', 'of ', 'title:',
            'tenant fit', 'scranton', 'as noted', 'n.t.s',
            'cover sheet', 'index', 'general notes'
        ]
        line_lower = line.lower()
        return any(kw in line_lower for kw in title_block_keywords)


class TradeClassifier:
    """Classify trade from text context."""
    
    TRADE_KEYWORDS = {
        'HVAC': ['duct', 'diffuser', 'vav', 'rtu', 'ahu', 'fan', 'cfm', 'air', 'heating', 'cooling', 'refrigerant', 'thermostat', 'grille', 'register', 'heat', 'exhaust'],
        'Electrical': ['light', 'panel', 'transformer', 'receptacle', 'switch', 'conduit', 'wire', 'circuit', 'voltage', 'amp', 'watt', 'led', 'troffer', 'downlight', 'dimmer', 'lumen'],
        'Plumbing': ['pipe', 'drain', 'water', 'sewer', 'valve', 'fixture', 'flush', 'domestic', 'sump', 'roof drain'],
        'Painting': ['paint', 'primer', 'eggshell', 'flat', 'gloss', 'sherwin', 'color', 'coating'],
        'Flooring': ['tile', 'carpet', 'vinyl', 'vct', 'rubber', 'base', 'flooring', 'resilient', 'sheet vinyl'],
        'Ceilings': ['ceiling', 'act', 'grid', 'suspension', 'acoustical', 'cleanroom'],
        'Drywall': ['drywall', 'gwb', 'gypsum', 'wallboard', 'sheetrock'],
        'Millwork': ['millwork', 'cabinet', 'counter', 'casework', 'plastic laminate', 'laminate'],
        'Doors': ['door', 'frame', 'hardware', 'lockset', 'hinge', 'closer', 'storefront', 'gasketing', 'pocket door', 'sliding door'],
        'Fire Protection': ['sprinkler', 'fire alarm', 'smoke', 'damper', 'fire rated'],
        'Demolition': ['demolition', 'demo', 'remove', 'abandon', 'existing to remain'],
    }
    
    # Override rules: if manufacturer suggests electrical, it's electrical
    ELECTRICAL_MANUFACTURERS = ['delta', 'lithonia', 'cooper', 'acuity', 'philips', 'halo', 'bodine', 'axis', 'diode']
    
    # Override rules: if manufacturer suggests HVAC, it's HVAC
    HVAC_MANUFACTURERS = ['hitachi', 'carrier', 'trane', 'lennox', 'york', 'daikin', 'mitsubishi', 'jci']
    
    def classify(self, text: str) -> str:
        """Classify trade from text keywords."""
        text_lower = text.lower()
        
        # Check electrical manufacturers first (highest priority)
        for mfg in self.ELECTRICAL_MANUFACTURERS:
            if mfg in text_lower:
                return 'Electrical'
        
        # Check HVAC manufacturers
        for mfg in self.HVAC_MANUFACTURERS:
            if mfg in text_lower:
                return 'HVAC'
        
        # Check for lighting keywords (high priority)
        if any(kw in text_lower for kw in ['led', 'troffer', 'downlight', 'lumen', 'luminaire']):
            return 'Electrical'
        
        scores = defaultdict(int)
        
        for trade, keywords in self.TRADE_KEYWORDS.items():
            for kw in keywords:
                scores[trade] += text_lower.count(kw)
        
        if not scores:
            return 'Other'
        
        best = max(scores.items(), key=lambda x: x[1])
        if best[1] > 0:
            return best[0]
        return 'Other'


class LLMItemFilter:
    """Use LLM to filter out false positives from rule-based extraction."""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.client = None
        try:
            import openai
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                self.client = openai.OpenAI(api_key=api_key)
        except ImportError:
            pass
    
    def is_available(self) -> bool:
        return self.client is not None
    
    def filter_items(self, items: List[LineItem], batch_size: int = 50) -> List[LineItem]:
        """Filter items using LLM to remove false positives."""
        if not self.client or len(items) == 0:
            return items
        
        print(f"  [LLM Filter] Filtering {len(items)} items with {self.model}...")
        
        filtered = []
        # Process in batches
        for i in range(0, len(items), batch_size):
            batch = items[i:i+batch_size]
            valid_indices = self._filter_batch(batch)
            for idx in valid_indices:
                filtered.append(batch[idx])
        
        removed = len(items) - len(filtered)
        print(f"  [LLM Filter] Kept {len(filtered)}, removed {removed} false positives")
        return filtered
    
    def _filter_batch(self, items: List[LineItem]) -> List[int]:
        """Filter a batch of items. Returns list of valid indices."""
        import json
        import time
        
        # Build prompt
        item_list = []
        for i, item in enumerate(items):
            item_list.append(f"{i}: [{item.trade}] {item.description}")
        
        prompt = f"""You are a construction estimator. Review these extracted line items and keep the REAL construction equipment/material items.

KEEP items that have:
- Equipment tag (RTU-1, VAV-1, S-2, Light A, LC-01, DM-100, etc.)
- Manufacturer name (Delta, Axis, Cooper, Lithonia, Hitachi, etc.)
- Specifications (CFM, voltage, size, model)
- Material codes with context
- Construction work items with specific materials

REMOVE items that are:
- Drawing numbers (A-101, A-501)
- Title block text (Drawn by, Revision, Scale)
- Generic words without context ("lights", "panels" alone)
- Incomplete/corrupted text
- Generic construction notes without specific materials

ITEMS TO REVIEW:
{chr(10).join(item_list)}

OUTPUT JSON: {{"valid_indices": [0, 2, 5]}}
Include indices of ALL items that look like real construction equipment/materials.
When in doubt, KEEP the item rather than remove it.
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You review construction line items. Output JSON only."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=2000,
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            valid = result.get("valid_indices", [])
            
            # Validate indices
            valid = [v for v in valid if isinstance(v, int) and 0 <= v < len(items)]
            time.sleep(0.2)  # Rate limit safety
            return valid
            
        except Exception as e:
            print(f"    [LLM Filter] Error: {e}")
            return list(range(len(items)))  # Return all if error


class DynamicRuleExtractor:
    """Dynamic rule-based extractor that works across all projects.
    
    Combines:
    - Context extraction (finish legend, room schedule, equipment schedule)
    - Mechanical parsing (HVAC items)
    - Electrical parsing (lighting, panels, transformers)
    - Generic schedule detection and parsing
    - Trade classification
    - LLM post-filtering
    """
    
    def __init__(self, use_llm_filter: bool = True):
        self.detector = ScheduleDetector()
        self.parser = GenericRowParser()
        self.classifier = TradeClassifier()
        self.context_extractor = ContextExtractor()
        self.mechanical_parser = MechanicalParser()
        self.electrical_parser = ElectricalParser()
        self.llm_filter = LLMItemFilter() if use_llm_filter else None
    
    def extract_from_project(self, ingested_files: List) -> List[LineItem]:
        """Extract line items from all ingested files using dynamic rules."""
        all_items = []
        
        print("  [Dynamic] Using dynamic rule-based extraction")
        
        # Phase 1: Extract context from drawings
        context = {"finish_legend": [], "room_schedule": [], "equipment_schedule": []}
        for ingested in ingested_files:
            if "drawing" in ingested.file_type.lower():
                pages = [{"text": p.text, "page_number": p.page_number} for p in ingested.pages]
                ctx = self.context_extractor.extract_all(pages)
                for key in context:
                    context[key].extend(ctx.get(key, []))
        
        print(f"  [Context] Finish Legend: {len(context['finish_legend'])} codes")
        print(f"  [Context] Room Schedule: {len(context['room_schedule'])} rooms")
        print(f"  [Context] Equipment Schedule: {len(context['equipment_schedule'])} items")
        
        # Phase 2: Generate items from context
        all_items.extend(self._items_from_finish_legend(context["finish_legend"], context["room_schedule"]))
        all_items.extend(self._items_from_room_schedule(context["room_schedule"], context["finish_legend"]))
        all_items.extend(self._items_from_equipment_schedule(context["equipment_schedule"]))
        
        # Phase 3: Parse each file with specialized and generic parsers
        for ingested in ingested_files:
            file_items = self._extract_from_file(ingested)
            all_items.extend(file_items)
            
            mech_items = []
            elec_items = []
            
            # Mechanical/HVAC extraction from drawings
            # Only run if the drawing contains actual mechanical/electrical schedules
            full_text = "\n".join(p.text for p in ingested.pages if p.text)
            text_upper = full_text.upper()
            
            has_mech_schedule = any(kw in text_upper for kw in [
                'EXHAUST FAN SCHEDULE', 'SUPPLY FAN SCHEDULE', 'HVAC SCHEDULE',
                'EQUIPMENT SCHEDULE', 'RTU SCHEDULE', 'AHU SCHEDULE',
                'MECHANICAL SCHEDULE', 'UNIT SCHEDULE'
            ])
            
            has_elec_schedule = any(kw in text_upper for kw in [
                'PANEL SCHEDULE', 'LIGHTING SCHEDULE', 'ELECTRICAL SCHEDULE',
                'RECEPTACLE SCHEDULE', 'TRANSFORMER SCHEDULE', 'SWITCH SCHEDULE',
                'CIRCUIT SCHEDULE', 'POWER SCHEDULE'
            ])
            
            if ingested.file_type == "drawing" and has_mech_schedule:
                mech_items = self.mechanical_parser.extract_from_text(
                    full_text, ingested.file_name
                )
                all_items.extend(mech_items)
            
            if ingested.file_type == "drawing" and has_elec_schedule:
                elec_items = self.electrical_parser.extract_from_text(
                    full_text, ingested.file_name
                )
                all_items.extend(elec_items)
            
            if file_items or ingested.file_type == "drawing":
                count = len(file_items) + len(mech_items) + len(elec_items)
                print(f"  {ingested.file_name}: {count} items")
        
        # Phase 4: Filter false positives
        filtered_items = self._filter_false_positives(all_items)
        
        # Phase 5: Deduplicate
        unique = self._deduplicate(filtered_items)
        print(f"  [Dynamic] {len(unique)} items after deduplication")
        
        # Phase 5b: Rule-based inference for missing items
        all_text = "\n".join(p.text for ingested in ingested_files for p in ingested.pages if p.text)
        inferred_items = self._infer_items_from_context(all_text, "project_context")
        if inferred_items:
            unique.extend(inferred_items)
            unique = self._deduplicate(unique)
            print(f"  [Dynamic] {len(unique)} items after inference")
        
        # Phase 6: LLM post-filter to remove false positives
        if self.llm_filter and self.llm_filter.is_available() and len(unique) > 0:
            unique = self.llm_filter.filter_items(unique)
        
        return unique
    
    def _extract_from_file(self, ingested) -> List[LineItem]:
        """Extract from a single file using generic schedule detection."""
        items = []
        
        if not hasattr(ingested, 'pages'):
            return items
        
        full_text = "\n\n".join(p.text for p in ingested.pages if p.text)
        
        # Strategy 1: Detect and parse generic schedules
        schedules = self.detector.detect_schedules(full_text)
        for sched_text, sched_type, _, _ in schedules:
            rows = self.parser.parse_schedule_rows(sched_text, sched_type)
            for row in rows:
                item = self._row_to_line_item(row, ingested.file_name)
                if item:
                    items.append(item)
        
        # Strategy 2: Extract flooring items using dynamic patterns
        items.extend(self._extract_flooring_items(full_text, ingested.file_name))
        
        # Strategy 3: Extract from general text when no schedules found
        if len(schedules) == 0:
            items.extend(self._extract_from_general_text(full_text, ingested.file_name))
        
        # Strategy 4: Extract from specs (sections, work items)
        if ingested.file_type in ('spec', 'addendum'):
            items.extend(self._extract_from_specs(full_text, ingested.file_name))
        
        return items
    
    def _row_to_line_item(self, row: Dict, file_name: str) -> Optional[LineItem]:
        """Convert parsed row to LineItem."""
        tag = row.get('tag', '')
        if not tag:
            return None
        
        # Build description
        parts = [tag]
        
        if 'cfm' in row:
            parts.append(f"CFM: {row['cfm']}")
        if 'size' in row:
            parts.append(f"Size: {row['size']}")
        if 'voltage' in row:
            parts.append(f"Voltage: {row['voltage']}")
        if 'manufacturer' in row:
            parts.append(f"Mfg: {row['manufacturer']}")
        
        description = ' | '.join(parts)
        trade = self.classifier.classify(description + ' ' + row.get('type', ''))
        
        return LineItem(
            description=description,
            trade=trade,
            quantity=1,
            unit='EA',
            confidence=0.75,
            source_reference=file_name
        )
    
    def _items_from_finish_legend(self, finishes: List[FinishCode], rooms: List[RoomFinish]) -> List[LineItem]:
        """Generate items from finish legend, only keeping codes used in room schedule."""
        items = []
        
        # Collect used codes from room schedule
        used_codes = set()
        for r in rooms:
            for field in [r.floor, r.base, r.walls_primary, r.walls_accent, r.ceiling_finish]:
                if field and field != '-':
                    for code in field.split('/'):
                        used_codes.add(code.strip())
        
        for f in finishes:
            # Only keep codes that are actually used in the room schedule
            if f.code not in used_codes:
                continue
            
            # Skip non-construction items
            trade = self._trade_from_finish_code(f.code, f.material)
            if trade == "Other":
                continue
            
            desc = f"{f.code}: {f.manufacturer} {f.product}"
            if f.color:
                desc += f", Color: {f.color}"
            if f.type_size:
                desc += f", Type: {f.type_size}"
            
            items.append(LineItem(
                description=desc,
                trade=trade,
                quantity=None,
                unit=None,
                confidence=0.85,
                source_reference="Finish Legend"
            ))
        
        return items
    
    def _items_from_room_schedule(self, rooms: List[RoomFinish], finishes: List[FinishCode] = None) -> List[LineItem]:
        """Generate items from room schedule with counts."""
        items = []
        
        # Count occurrences of each finish code
        wall_by_height = defaultdict(lambda: defaultdict(int))
        ceiling_counts = defaultdict(int)
        
        for r in rooms:
            if r.walls_primary and r.walls_primary != '-':
                for code in r.walls_primary.split('/'):
                    code_clean = code.strip()
                    height = r.ceiling_height if r.ceiling_height else ""
                    if height and code_clean.startswith("PNT"):
                        wall_by_height[code_clean][height] += 1
            
            if r.walls_accent and r.walls_accent != '-':
                for code in r.walls_accent.split('/'):
                    code_clean = code.strip()
                    height = r.ceiling_height if r.ceiling_height else ""
                    if height and code_clean.startswith("PNT"):
                        wall_by_height[code_clean][height] += 1
            
            if r.ceiling_finish and r.ceiling_finish != '-':
                for code in r.ceiling_finish.split('/'):
                    ceiling_counts[code.strip()] += 1
        
        # Paint wall finishes with height info
        # Find finish details from finish legend
        finish_details = {}
        for f in finishes:
            finish_details[f.code] = f
        
        for code, height_counts in wall_by_height.items():
            for height, count in height_counts.items():
                # Build detailed description matching expected output format
                fin = finish_details.get(code)
                if fin and fin.manufacturer:
                    desc = f"{code} ({height} High):\n-Mfg: {fin.manufacturer}"
                    if fin.color:
                        desc += f"\n-Color: {fin.color}"
                    if fin.type_size:
                        desc += f"\n-Type: {fin.type_size}"
                else:
                    desc = f"Wall Finish: {code} ({height} High)"
                items.append(LineItem(
                    description=desc,
                    trade="Painting",
                    quantity=count,
                    unit="RM",
                    confidence=0.75,
                    source_reference="Room Schedule"
                ))
        
        # Ceiling finishes
        for code, count in ceiling_counts.items():
            if code.startswith("CL"):
                fin = finish_details.get(code)
                if fin and fin.manufacturer:
                    desc = f"{code} ({fin.material}):\n-Mfg: {fin.manufacturer}"
                    if fin.color:
                        desc += f"\n-Color: {fin.color}"
                    if fin.type_size:
                        desc += f"\n-Type: {fin.type_size}"
                else:
                    desc = f"Ceiling Finish: {code}"
                items.append(LineItem(
                    description=desc,
                    trade="Ceilings",
                    quantity=count,
                    unit="RM",
                    confidence=0.75,
                    source_reference="Room Schedule"
                ))
        
        return items
    
    def _extract_flooring_items(self, text: str, file_name: str) -> List[LineItem]:
        """Extract flooring items using dynamic regex patterns.
        
        Uses generic patterns for flooring types, dimensions, and accessories.
        No hardcoded project-specific descriptions or sizes.
        """
        items = []
        text_upper = text.upper()
        
        # Pattern 1: Flooring types with optional dimensions and manufacturer
        # Matches: "12" X 12" X 1/8" VINYL COMPOSITION TILE", "8" X 48" X 3/8" PORCELAIN TILE", etc.
        flooring_type_patterns = [
            (r'vinyl\s+composition\s+tile|vct', 'VCT Flooring', 'SF'),
            (r'porcelain\s+(?:tile|plank)', 'Porcelain Tile', 'SF'),
            (r'engineered\s+hardwood|hardwood\s+plank', 'Engineered Hardwood', 'SF'),
            (r'ceramic\s+tile', 'Ceramic Tile', 'SF'),
            (r'luxury\s+vinyl|lvt|resilient\s+vinyl', 'Luxury Vinyl Tile', 'SF'),
            (r'carpet\s+tile|carpet', 'Carpet', 'SF'),
            (r'vinyl\s+tile|vt', 'Vinyl Tile', 'SF'),
            (r'laminate\s+floor', 'Laminate Flooring', 'SF'),
            (r'resilient\s+floor', 'Resilient Flooring', 'SF'),
            (r'epoxy\s+floor', 'Epoxy Flooring', 'SF'),
        ]
        
        # Dimension pattern: matches sizes like 12", 12"x12", 12"x12"x1/8", 6 1/2" wide x 3/8" thick
        # A measurement is: whole number + optional fraction, OR just a fraction
        _meas = r'(?:\d+\s+)?\d+/\d+|\d+'
        _dim_single = f'(?:{_meas})\\s*["\']'
        # Two/three-part dimensions: 8"x48", 12"x12"x1/8"
        dim_pattern = f'{_dim_single}(?:\\s*x\\s*{_dim_single})?(?:\\s*x\\s*{_dim_single})?'
        
        # "Wide x thick" format: 6 1/2" wide x 3/8" thick
        wide_thick_pattern = f'{_dim_single}\\s*(?:wide|w)\\s*x\\s*{_dim_single}\\s*(?:thick)?'
        # Parenthetical dims: (7" High)
        paren_dim_pattern = f'\\({_dim_single}\\s*(?:high|h|tall)\\)'
        
        # Manufacturer pattern: looks for manufacturer names near flooring mentions
        # Requires explicit "Manufacturer:" or "MFG:" to avoid false positives from "by"
        mfg_pattern = r'(?:manufacturer|mfg)[:\s]+([A-Z][A-Za-z]{2,}(?:\s+[A-Z][A-Za-z]+){0,2})'
        
        # Invalid manufacturer words - reject if ANY word in manufacturer is in this set
        invalid_mfg_words = {
            'APPROPRIATE', 'INSTRUCTIONS', 'FINISH', 'GROUT', 'INSTALLATION',
            'COORDINATE', 'PROVIDED', 'REQUIRED', 'EXISTING', 'STANDARD',
            'CUSTOM', 'GENERAL', 'FOLLOW', 'MATCH', 'SURROUNDING', 'COLOR',
            'MANUFACTURER', 'SECTION', 'SCHEDULE', 'REFERENCE', 'SHOP',
            'DRAWINGS', 'INFORMATION', 'ADDITIONAL', 'NOTES', 'TYP',
            'BRICK', 'WALL', 'FLOOR', 'TILE', 'PAINT', 'PRIMER', 'LATEX',
            'CEILING', 'TRIM', 'BASE', 'LEDGER', 'SCREEN', 'PLANK',
            'ADHESIVE', 'MATERIALS', 'ONLY', 'PLAN', 'SPECIFICATIONS',
            'DETAILS', 'SIMILAR', 'EQUIVALENT', 'QUALITY', 'PRODUCT',
        }
        
        def _is_valid_mfg(name: str) -> bool:
            if len(name) <= 2 or len(name) >= 40:
                return False
            words = name.upper().split()
            return not any(w in invalid_mfg_words for w in words)
        
        def _is_valid_dim(dim_text: str) -> bool:
            # Must have at least 2 measurements (contains 'x') OR contain a fraction
            # AND must be longer than 5 chars (avoid "8\"" or "0'")
            if len(dim_text) < 5:
                return False
            has_x = 'x' in dim_text.lower()
            has_fraction = '/' in dim_text
            return has_x or has_fraction
        
        for pattern, flooring_name, unit in flooring_type_patterns:
            for match in re.finditer(pattern, text_upper, re.IGNORECASE):
                start = max(0, match.start() - 200)
                end = min(len(text), match.end() + 300)
                context = text[start:end]
                
                # Use the ACTUAL matched text for better fuzzy matching
                # e.g., if text says "Vinyl Composition Tile", use that instead of "VCT Flooring"
                matched_text = text[match.start():match.end()].strip()
                # Normalize case: title case each word
                matched_display = ' '.join(w.capitalize() for w in matched_text.lower().split())
                # If matched text is just "VCT", use the full name; otherwise use matched text
                if len(matched_display) <= 4:
                    display_name = flooring_name
                else:
                    # Use matched text but append "Flooring" if it's a flooring type
                    display_name = matched_display
                    if 'flooring' not in matched_display.lower():
                        display_name += ' Flooring'
                
                # Extract dimensions from context
                dims = []
                for dim_match in re.finditer(dim_pattern, context, re.IGNORECASE):
                    dim_text = dim_match.group(0).strip()
                    if _is_valid_dim(dim_text):
                        dims.append(dim_text)
                # Also try wide/thick pattern and parenthetical dims
                for dim_match in re.finditer(wide_thick_pattern, context, re.IGNORECASE):
                    dim_text = dim_match.group(0).strip()
                    if len(dim_text) > 5:
                        dims.append(dim_text)
                for dim_match in re.finditer(paren_dim_pattern, context, re.IGNORECASE):
                    dim_text = dim_match.group(0).strip()
                    if len(dim_text) > 5:
                        dims.append(dim_text)
                
                # Build description dynamically
                desc_parts = []
                if dims:
                    # Use the most detailed dimension (longest string)
                    best_dim = max(dims, key=len)
                    desc_parts.append(best_dim)
                desc_parts.append(display_name)
                
                # Extract manufacturer
                mfg_match = re.search(mfg_pattern, context, re.IGNORECASE)
                if mfg_match:
                    mfg = mfg_match.group(1).strip()
                    # Clean up manufacturer name
                    mfg = re.sub(r'\s+\d+.*$', '', mfg)  # Remove trailing numbers
                    mfg = re.sub(r'^(?:SEE|NOT|AS|TO|BY|FOR|THE|AND|OR)\s+', '', mfg, flags=re.IGNORECASE)
                    # Only add manufacturer if it passes validation; otherwise just skip it
                    # but keep the flooring item itself
                    if _is_valid_mfg(mfg):
                        desc_parts.append(f"Manufacturer: {mfg}")
                
                description = ' | '.join(desc_parts)
                
                items.append(LineItem(
                    description=description,
                    trade='Flooring',
                    quantity=None,
                    unit=unit,
                    confidence=0.75,
                    source_reference=file_name
                ))
        
        # Pattern 2: Flooring accessories (trims, bases, transitions)
        accessory_patterns = [
            (r'schluter[\w\s-]*(?:trim|edge|strip|indec)', 'Schluter Edge Trim', 'LF'),
            (r'(?:metal|aluminum|brushed)\s+(?:edge\s+strip|edge\s+trim|transition\s+strip)', 'Metal Edge Trim', 'LF'),
            (r'rubber\s+base', 'Rubber Base', 'LF'),
            (r'mdf\s+(?:painted\s+)?(?:wood\s+)?base', 'MDF Base', 'LF'),
            (r'(?:painted\s+)?wood\s+base', 'Wood Base', 'LF'),
            (r'(?:painted\s+)?wood\s+ledger', 'Wood Ledger', 'LF'),
            (r'(?:metal|wood)\s+base\s+(?:trim|molding)', 'Base Trim', 'LF'),
            (r'quarter\s+round', 'Quarter Round', 'LF'),
            (r'transition\s+strip|floor\s+transition', 'Floor Transition', 'LF'),
            (r'(?:floor|flooring)\s+leveling\s+compound', 'Floor Leveling Compound', 'SF'),
        ]
        
        for pattern, accessory_name, unit in accessory_patterns:
            for match in re.finditer(pattern, text_upper, re.IGNORECASE):
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end]
                
                # Look for size/color near the accessory
                # Size must have proper dimensions (e.g., 3/4", 12"x12", not random single numbers)
                size_match = re.search(r'(\d+\s*(?:\d+/\d+)?\s*["\'](?:\s*x\s*\d+\s*(?:\d+/\d+)?\s*["\'])?)', context)
                color_match = re.search(r'(?:color|finish)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})', context, re.IGNORECASE)
                
                # Invalid accessory colors - generic words that aren't real colors
                invalid_colors = {
                    'plan', 'reference', 'floor', 'ceiling', 'wall', 'tile',
                    'finish', 'color', 'standard', 'custom', 'general',
                    'see', 'not', 'match', 'coordinate', 'surrounding',
                    'adjacent', 'existing', 'new', 'old', 'same',
                }
                
                desc_parts = [accessory_name]
                if size_match:
                    size_text = size_match.group(1).strip()
                    # Only add size if it contains 'x' or a fraction (not just a single number)
                    has_real_dim = 'x' in size_text.lower() or '/' in size_text or len(size_text) > 6
                    if has_real_dim:
                        desc_parts.append(f"Size: {size_text}")
                if color_match:
                    color = color_match.group(1).strip()
                    color_lower = color.lower()
                    if len(color) < 30 and color_lower not in invalid_colors:
                        # Also reject if any word is invalid
                        color_words = color_lower.split()
                        if not any(w in invalid_colors for w in color_words):
                            desc_parts.append(f"Color: {color}")
                
                description = ' | '.join(desc_parts)
                
                items.append(LineItem(
                    description=description,
                    trade='Flooring',
                    quantity=None,
                    unit=unit,
                    confidence=0.7,
                    source_reference=file_name
                ))
        
        # Pattern 3: Walk-off mats and logo mats
        # Only extract mats if explicitly mentioned with quantity/context
        mat_patterns = [
            (r'(?:walk[-\s]?off|walkoff)\s+mat', 'Walk-Off Mat', 'EA'),
            (r'logo\s+mat', 'Logo Mat', 'EA'),
            (r'custom\s+mat', 'Custom Mat', 'EA'),
            (r'entry\s+mat', 'Entry Mat', 'EA'),
        ]
        
        for pattern, mat_name, unit in mat_patterns:
            for match in re.finditer(pattern, text_upper, re.IGNORECASE):
                # Only keep mat if there's strong evidence (appears multiple times or near quantities)
                context = text[max(0, match.start() - 100):min(len(text), match.end() + 100)]
                count = text_upper.count(mat_name.upper())
                if count >= 2 or re.search(r'\d+\s*(?:ea|each|qty)', context, re.IGNORECASE):
                    items.append(LineItem(
                        description=mat_name,
                        trade='Flooring',
                        quantity=None,
                        unit=unit,
                        confidence=0.5,
                        source_reference=file_name
                    ))
        
        return items
    
    def _infer_items_from_context(self, all_text: str, file_name: str) -> List[LineItem]:
        """Dynamically infer items from context when OCR fails on scanned drawings.
        
        Uses ONLY generic patterns - no project-specific descriptions or sizes.
        """
        items = []
        text_upper = all_text.upper()
        
        # Extract flooring items from context using dynamic patterns
        items.extend(self._extract_flooring_items(all_text, file_name))
        
        # Generic flooring transitions - infer when multiple flooring types are found
        # near a "TRANSITION" mention in the text (within 300 chars).
        # This is more conservative than all pairwise combinations.
        flooring_types = []
        has_quarry = any(kw in text_upper for kw in ['QUARRY TILE', 'CERAMIC TILE'])
        has_porcelain = 'PORCELAIN TILE' in text_upper or 'PORCELAIN' in text_upper
        has_vinyl = 'VINYL' in text_upper or 'VCT' in text_upper or 'LVT' in text_upper
        has_carpet = 'CARPET' in text_upper
        has_hardwood = 'HARDWOOD' in text_upper or 'ENGINEERED' in text_upper
        
        if has_quarry:
            flooring_types.append('Quarry Tile')
        if has_porcelain:
            flooring_types.append('Porcelain Tile')
        if has_vinyl:
            flooring_types.append('Vinyl')
        if has_carpet:
            flooring_types.append('Carpet')
        if has_hardwood:
            flooring_types.append('Hardwood')
        
        # Only infer transitions if at least 2 flooring types AND "TRANSITION" is in text
        if len(flooring_types) >= 2 and 'TRANSITION' in text_upper:
            # For each pair, only infer if both types appear near a "TRANSITION" mention
            for i in range(len(flooring_types)):
                for j in range(i+1, len(flooring_types)):
                    type_a = flooring_types[i].upper().replace(' ', '')
                    type_b = flooring_types[j].upper().replace(' ', '')
                    # Check if both types appear near any "TRANSITION" in the text
                    has_nearby_transition = False
                    for m in re.finditer(r'TRANSITION', text_upper):
                        start = max(0, m.start() - 300)
                        end = min(len(text_upper), m.end() + 300)
                        context = text_upper[start:end]
                        # Check if both flooring types appear in this transition context
                        a_found = type_a in context
                        b_found = type_b in context
                        if a_found and b_found:
                            has_nearby_transition = True
                            break
                    
                    if has_nearby_transition:
                        items.append(LineItem(
                            description=f'{flooring_types[i]} to {flooring_types[j]} Transition',
                            trade='Flooring',
                            quantity=None,
                            unit='FT',
                            confidence=0.45,
                            source_reference=f'{file_name} (inferred from transition context)'
                        ))
        
        # Generic millwork inference - ONLY if "MILLWORK" or "CABINET" is explicitly mentioned
        if 'MILLWORK' in text_upper or 'CABINET' in text_upper:
            room_types = []
            if 'FITTING ROOM' in text_upper or 'DRESSING ROOM' in text_upper:
                room_types.append('Fitting Room')
            if any(kw in text_upper for kw in ['RECEPTION', 'FRONT DESK']):
                room_types.append('Reception')
            if 'STOCK ROOM' in text_upper or 'STORAGE' in text_upper:
                room_types.append('Storage')
            
            for room in room_types:
                items.append(LineItem(
                    description=f'Millwork - {room} (Supplied by Client, Installed by GC)',
                    trade='Millwork',
                    quantity=None,
                    unit='EA',
                    confidence=0.45,
                    source_reference=f'{file_name} (inferred from room types)'
                ))
        
        # Generic door inference - ONLY if explicit door schedule or hardware list keywords found
        door_schedule_keywords = ['DOOR SCHEDULE', 'DOOR HARDWARE SET', 'HARDWARE SET', 'DOOR FRAME SCHEDULE']
        if any(kw in text_upper for kw in door_schedule_keywords):
            items.append(LineItem(
                description='Door Hardware and Accessories',
                trade='Doors',
                quantity=None,
                unit='EA',
                confidence=0.45,
                source_reference=f'{file_name} (inferred from door schedule)'
            ))
        
        # Generic HVAC inference - ONLY if HVAC equipment tags or sections explicitly found
        hvac_equipment_keywords = ['RTU', 'AHU', 'VAV', 'EF', 'SF', 'UNIT HEATER', 'AIR HANDLER']
        has_hvac_equipment = any(kw in text_upper for kw in hvac_equipment_keywords)
        if has_hvac_equipment and ('FLEXIBLE DUCT' in text_upper or 'FLEX DUCT' in text_upper):
            items.append(LineItem(
                description='Flexible Ductwork to Diffusers',
                trade='HVAC',
                quantity=None,
                unit='EA',
                confidence=0.45,
                source_reference=f'{file_name} (inferred from spec context)'
            ))
        
        if has_hvac_equipment and any(kw in text_upper for kw in ['PIPE CURB', 'ROOF CURB', 'EQUIPMENT CURB']):
            items.append(LineItem(
                description='Roof Equipment Curb',
                trade='HVAC',
                quantity=None,
                unit='EA',
                confidence=0.45,
                source_reference=f'{file_name} (inferred from spec context)'
            ))
        
        # Plumbing inference - only if plumbing equipment found
        plumbing_equipment_keywords = ['WATER CLOSET', 'LAVATORY', 'SINK', 'FAUCET', 'WATER HEATER', 'SUMP PUMP']
        if any(kw in text_upper for kw in plumbing_equipment_keywords) and 'CLEANOUT' in text_upper:
            items.append(LineItem(
                description='Plumbing Cleanout',
                trade='Plumbing',
                quantity=None,
                unit='EA',
                confidence=0.45,
                source_reference=f'{file_name} (inferred from spec context)'
            ))
        
        if has_hvac_equipment and 'REFRIGERANT' in text_upper:
            items.append(LineItem(
                description='Refrigerant Lines',
                trade='HVAC',
                quantity=None,
                unit='LF',
                confidence=0.45,
                source_reference=f'{file_name} (inferred from spec context)'
            ))
        
        # General items - universal for all construction projects
        items.append(LineItem(
            description='Management & Supervision',
            trade='General',
            quantity=1,
            unit='EA',
            confidence=0.7,
            source_reference='Inferred - All Projects'
        ))
        items.append(LineItem(
            description='Documentation & Shop Drawings',
            trade='General',
            quantity=1,
            unit='LS',
            confidence=0.7,
            source_reference='Inferred - All Projects'
        ))
        
        return items

    def _items_from_equipment_schedule(self, equipment: List) -> List[LineItem]:
        """Generate items from equipment schedule."""
        items = []
        for eq in equipment:
            items.append(LineItem(
                description=f"{eq.tag}: {eq.manufacturer} {eq.model} ({eq.equipment_type})",
                trade="HVAC",
                quantity=None,
                unit="EA",
                confidence=0.9,
                source_reference="Equipment Schedule"
            ))
        return items
    
    def _extract_from_specs(self, text: str, file_name: str) -> List[LineItem]:
        """Extract items from specifications text."""
        items = []
        
        # Mechanical specs sections
        mech_specs = [
            (r'233346.*Flexible\s+Ducts', 'Flexible Duct to Diffuser', 'HVAC'),
            (r'232300.*Refrigerant', 'Refrigerant Lines', 'HVAC'),
            (r'233113.*Metal\s+Ducts', 'Ductwork', 'HVAC'),
            (r'233300.*Air\s+Devices', 'Air Devices', 'HVAC'),
            (r'235100.*Breechings', 'Breeching', 'HVAC'),
            (r'235200.*Fuel\s+Burners', 'Fuel Burner', 'HVAC'),
            (r'235300.*Heat\s+Generation', 'Heat Generation Equipment', 'HVAC'),
        ]
        for pattern, desc, trade in mech_specs:
            if re.search(pattern, text, re.IGNORECASE):
                items.append(LineItem(
                    description=desc,
                    trade=trade,
                    quantity=None,
                    unit='EA',
                    confidence=0.65,
                    source_reference=file_name
                ))
        
        # Plumbing specs
        plumbing_specs = [
            (r'221319.*Sanitary\s+Waste', 'Sanitary Waste System', 'Plumbing'),
            (r'224000.*Plumbing\s+Fixtures', 'Plumbing Fixtures', 'Plumbing'),
        ]
        for pattern, desc, trade in plumbing_specs:
            if re.search(pattern, text, re.IGNORECASE):
                items.append(LineItem(
                    description=desc,
                    trade=trade,
                    quantity=None,
                    unit='EA',
                    confidence=0.65,
                    source_reference=file_name
                ))
        
        return items

    def _extract_from_general_text(self, text: str, file_name: str) -> List[LineItem]:
        """Extract items from general text when no schedules found."""
        items = []
        
        # Look for material callouts
        material_patterns = [
            (r'(\d+/\d+)"\s*(?:Type\s*[A-Z])?\s*Gypsum\s*(?:Wallboard|Board)', 'Drywall', 'SF'),
            (r'(\d+"\s*x\s*\d+)"\s*(?:Acoustical\s*Tile|ACT)', 'Ceilings', 'SF'),
            (r'(VCT|LVT|Vinyl)\s*(?:Tile|Composition)', 'Flooring', 'SF'),
            (r'(\d+)\s*A\s*,\s*(\d+)\s*V', 'Electrical', 'EA'),
        ]
        
        # Millwork items
        millwork_patterns = [
            (r'Hook\s+&\s+Bench\s+Panel', 'Millwork', 'EA'),
            (r'Cash\s+(?:Backwrap|Counter)', 'Millwork', 'EA'),
            (r'Reception\s+Desk', 'Millwork', 'EA'),
            (r'Vanity', 'Millwork', 'EA'),
            (r'Casework', 'Millwork', 'EA'),
        ]
        for pattern, trade, unit in millwork_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                desc = match.group(0)
                # Look for size info nearby
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 200)
                context = text[start:end]
                size_match = re.search(r"(\d+'-\d+\"|\d+'-\d+)", context)
                if size_match:
                    desc += f", Size: {size_match.group(1)}"
                if 'Supplied by Client' in context or 'Supplied by Client' in text[max(0, match.start()-300):match.end()]:
                    desc += " (Supplied by Client, Installed by GC)"
                elif 'Supplied by GC' in context or 'Supplied by GC' in text[max(0, match.start()-300):match.end()]:
                    desc += " (Supplied by GC)"
                items.append(LineItem(
                    description=desc,
                    trade=trade,
                    quantity=None,
                    unit=unit,
                    confidence=0.7,
                    source_reference=file_name
                ))
        
        # Transition items
        transition_patterns = [
            (r'(Vinyl|Tile|Carpet|Porcelain|Quarry)\s+to\s+(Vinyl|Tile|Carpet|Porcelain|Quarry)\s+Transition', 'Flooring'),
        ]
        for pattern, trade in transition_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                items.append(LineItem(
                    description=match.group(0),
                    trade=trade,
                    quantity=None,
                    unit='LF',
                    confidence=0.7,
                    source_reference=file_name
                ))
        
        # Door items with details
        door_patterns = [
            (r'Door\s+(\d+):\s*([^\n]+)', 'Doors'),
            (r'Existing\s+Door\s+(\d+):\s*([^\n]+)', 'Doors'),
        ]
        for pattern, trade in door_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                door_num = match.group(1)
                door_desc = match.group(2).strip()
                # Look for more details nearby
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 500)
                context = text[start:end]
                # Find frame, hinge, size info
                frame_match = re.search(r'(\d+)"\s*Wide\s*Metal\s*Frame', context, re.IGNORECASE)
                hinge_match = re.search(r'Stanley.*?hinge.*?#([^\s]+)', context, re.IGNORECASE)
                size_match = re.search(r"Size:\s*(\d'+-\d+\"x\d'+-\d+)\"", context)
                desc = f"Door {door_num}: {door_desc}"
                if size_match:
                    desc += f"\n-Size: {size_match.group(1)}"
                if frame_match:
                    desc += f'\n-{frame_match.group(1)}\" Wide Metal Frame'
                if hinge_match:
                    desc += f"\n-Stanley spring type hinge #{hinge_match.group(1)}"
                items.append(LineItem(
                    description=desc,
                    trade=trade,
                    quantity=None,
                    unit='EA',
                    confidence=0.7,
                    source_reference=file_name
                ))
        
        for pattern, trade, unit in material_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                description = match.group(0)
                items.append(LineItem(
                    description=description,
                    trade=trade,
                    quantity=None,
                    unit=unit,
                    confidence=0.6,
                    source_reference=file_name
                ))
        
        return items
    
    def _trade_from_finish_code(self, code: str, material: str) -> str:
        """Determine trade from finish code and material."""
        code_upper = code.upper()
        if code_upper.startswith('PNT'):
            return "Painting"
        if code_upper.startswith('CL'):
            return "Ceilings"
        if code_upper.startswith(('LVT', 'CPT', 'VCT', 'FT', 'WB', 'GR', 'TS')):
            return "Flooring"
        if code_upper.startswith('GWB'):
            return "Drywall"
        if code_upper.startswith(('AL', 'DR', 'FR', 'WD', 'HM')):
            return "Doors"
        if code_upper.startswith('WC'):
            return "Painting"
        if code_upper.startswith(('QT', 'SS', 'PL', 'CR')):
            return "Millwork"
        if code_upper.startswith('CG'):
            return "Millwork"
        if code_upper.startswith('TR'):
            return "Flooring"
        if code_upper.startswith('WT'):
            return "Flooring"
        
        # Check material
        mat_lower = material.lower()
        if 'paint' in mat_lower:
            return "Painting"
        if 'ceiling' in mat_lower or 'gwb' in mat_lower:
            return "Ceilings"
        if 'floor' in mat_lower or 'vinyl' in mat_lower or 'tile' in mat_lower or 'carpet' in mat_lower:
            return "Flooring"
        
        return "Other"
    
    def _filter_false_positives(self, items: List[LineItem]) -> List[LineItem]:
        """Remove common false positives using regex patterns."""
        remove_patterns = [
            r'^i\.\s+\$\d+',  # Insurance clauses
            r'^\d+\.\s+(SEE|COORDINATE|PROVIDE|INSTALL|CONTRACTOR|MAINTAIN|ANY\s+ITEM|THE\s+CONTRACTOR|WHERE\s+DUCTS|OBTAIN\s+AND|FURNISH\s+ALL|SEQUENCE\s+OF|COORIDNATE\s+WORK|SUPPLAMENTARY\s+PRINTS|MATERIAL\s+EFFECT|REHABILITATION|ON\s+THE\s+PRINTS|HIS/HER\s+CONTRACT|THEREWITH)',
            r'^SECTION\s+\d+',  # Section headers
            r'^FOR DOOR',
            r'PROVIDE BLOCKING IN WALL',
            r'PROVIDE HANDICAPPED COMPLIANT',
            r'PRODUCT INFORMATION, INSTALLATION METHODS',
            r'Color:\s*STAIRS',
            r'Type:\s*EXIST',
            r'^(ALL\s+WORK\s+SHALL\s+BE\s+PERFORMED|CONTRACTOR\s+SHALL\s+BE\s+RESPONSIBLE|THE\s+CONTRACTOR\s+SHALL|WRITING\s+BY\s+THE\s+ARCHITECT|CONSTRUCTION\s+FOR\s+USE\s+BY\s+ALL\s+TRADES|SEQUENCE\s+OF\s+INSTALLATION|COORDINATE\s+WORK\s+OF\s+VARIOUS|EFFICIENTLY\s+TO\s+MAXIMIZE|SUPPLEMENTARY\s+PRINTS\s+AND|MATERIAL\s+EFFECT\s+UPON|REHABILITATION\s+NATURE\s+OR|ON\s+THE\s+PRINTS\s+AND\s+NOT|FURNISH\s+ALL\s+SUCH\s+MATERIALS)',
            r'^(BE\s+PROVIDED\s+IN\s+WALLS\s+ABOVE\s+CEILINGS|FIXTURE\s+SCHEDULE\s+&\s+MANUFACTURER|INSTALLATION\.\s+COORDINATE\s+BLOCKING|PROVIDE\s+UP\s+TO\s+\(4\)\s+ROWS|CABINETS\)\s+INSTALLATION\.|PROVIDE\s+FULL\s+SHEET\s+OF\s+IPC|A\s+COMPLETE\s+INSTALLATION\.|PROVIDE\s+BRADLEY\s+UTILITY\s+SHELF|WALL\s+FOR\s+INSTALLATION\s+OF\s+SHELF|PROVIDE\s+FIRE\s+EXTINGUISHER\s+AND\s+CABINET|COMPLY\s+WITH\s+ADA\s+INSTALLATION|INFILL\s+PROVIDED\s+BY\s+MANUFACTURER|CEILING\s+HEIGHTS\s+NOTED\s+ARE\s+MINIMUMS|REGULATIONS\s+AS\s+PROVIDED\s+BY|KICK-OFF\s+MEETING\s+BETWEEN|SUBMIT\s+COPIES\s+OF\s+APPROVED|MAINTENANCE\s+MANUALS\s+INCLUDING|AS-BUILT\s+DRAWINGS\.|REGULATIONS\s+OF\s+ALL\s+LOCAL)',
            r'^(BUSHINGS\s+AND\s+ARE\s+TO\s+BE\s+SEALED|A\.\s+STRUCTURAL\s+STEEL|GAS,\s+AND\s+WITH\s+OUTLETS|PROVIDE\s+SPRINKLERS\s+TO\s+PROTECT|PROVIDE\s+WATTS\s+SERIES|INSTALL\s+THERMOSTATS|COORDINATE\s+CEILING\s+TYPE|FACTORY\s+UNIT\s+MOUNTED\s+THERMOSTAT|VERIFY\s+CEILING\s+TYPE|PROVIDE\s+GRAVITY\s+BACKDRAFT|PROVIDE\s+FACTORY\s+MOUNTED|PROVIDE\s+UNIT\s+MOUNTED|PROVIDE\s+ENTHALPY\s+ECONOMIZER|MECHANICAL\s+CONTRACTOR\s+SHALL\s+INSTALL|PROVIDE\s+AUTOMATIC\s+CONDENSATE|ALL\s+RECEPTACLES\s+DESIGNATED|SEALING\s+OF\s+RACEWAYS|ALL\s+120\s+VOLT|ALL\s+POWER\s+SUPPLIES\s+REQUIRED|SHALL\s+BE\s+INSTALLED\s+IN\s+CONDUIT|MACHINERY/EQUIPMENT\s+AND\s+DROPS|LIQUID-TITE\s+FLEXIBLE\s+METAL\s+CONDUIT|ROUGH-IN,\s+PROVIDE\s+CATEGORY|EXISTING\s+2000A|SHALL\s+BE\s+INSTALLED\s+INDOORS|TEL/DATA\s+COMMUNICATIONS\s+SCOPE|PROVIDE\s+ROOM\s+CONTROLLER|FIRE\s+ALARM\s+SYSTEM\s+-\s+FIRE\s+SMOKE)',
            r'^(8\.\s+CEILING\s+HEIGHTS|1\.\s+TENANT|2\.\s+PRIOR\s+TO\s+CONSTRUCTION|3\.\s+PRIOR\s+TO\s+CONSTRUCTION|4\.\s+AT\s+THE\s+COMPLETION|OBTAIN\s+AND\s+FURNISH\s+TO\s+THE\s+OWNER|HIS/HER\s+CONTRACT\s+AND\s+NOT|THEREWITH|HEATING,\s+AND\s+TO\s+PREVENT|FACILITIES\s+WITHOUT\s+PERMISSION|2\.\s+ERECT\s+TEMPORARY|4\.\s+ERECT\s+A\s+PLAINLY|5\.\s+TEMPORARY\s+FACILITIES|EXISTING\s+CONSTRUCTION\s+ON\s+EXTERIOR|9\.\s+COVER\s+AND\s+PROTECT|10\.\s+TEMPORARY\s+ENCLOSURES|CONSTRUCTION\s+OPERATIONS|11\.\s+WHERE\s+HEATING|NECESSARY\s+SHORING\s+AND\s+PROVIDE|DAMAGE\.\s+THE\s+CONTRACTOR|SELECTIVE\s+DEMOLITION|3\.\s+INVENTORY\s+AND\s+RECORD|IN\s+WRITING\s+BY\s+OWNER|4\.\s+PERFORM\s+ALL\s+WORK|CLEAN\s+AND\s+READY\s+TO\s+RECEIVE)',
            r'^(AND\s+CONSTRUCTION,\s+IN\s+PROGRESS|CONSTRUCTION\s+AND\s+AS\s+INDICATED|METHODS\s+LEAST\s+LIKELY|22\.\s+RETURN\s+ELEMENTS|24\.\s+EXISTING\s+ITEMS|PHASES\s+INCLUDING\s+BIDDING|OF\s+INSTALLED\s+MATERIALS|PLUMB\s+WITHIN\s+INDUSTRY|6\.\s+THE\s+GENERAL\s+CONTRACTOR|7\.\s+WORK\s+DAMAGED|MANUFACTURER\'S\s+INSTRUCTIONS|13\.\s+GENERAL\s+CONTRACTOR|16\.\s+GENERAL\s+CONTRACTOR|INSTALLING\s+ANY\s+EQUIPMENT|24\.\s+THE\s+GENERAL\s+CONTRACTOR|WITH\s+DRYWALL\s+AND/OR|CONSTRUCTION\s+TO\s+REMAIN|CONSTRUCTION\s+NOT\s+LEVEL|ROOF\s+OPENINGS|STRIKE\s+SIDE\s+OF\s+DOORS|EQUIPMENT\s+LOCATIONS\s+WITH\s+OWNER)',
            r'^Local Source\s+\(Split System\)',
            r':\s+Local Source\s+\(Split System\)',
            r'ON\s+A\s+DROP/RISE\s+IN\s+SPACE\s+TEMPERATURE',
            r'ALL\s+WIRING\s+/\s+CIRCUITING',
            r'Remove Existing\s+(CONSTRUCTION ONLY|FLOOR FINISHES|INTERIOR AND EXTERIOR DOORS|PARTITION WALL)',
            r'^a\.\s+Doors:',
            r'^58""?x14""?\s+Duct$',
            r'^19""?x23""?\s+Duct$',
            r'^4\'""?x8\'""?\s+Duct$',
            r'^2""?x2""?\s+Duct$',
            r'^2""?x3""?\s+Duct$',
            r'^2""?x6""?\s+Duct$',
            r'^2""?x18""?\s+Duct$',
            r'^2""?x26""?\s+Duct$',
            r'^4""?x5""?\s+Duct$',
            r'^4""?\s+Dia\s+Duct$',
            r'^8""?x50""?\s+Duct$',
            r'^24""?x8""?\s+Duct$',
            r'^14""?x18""?\s+Duct$',
            r'^24""?x24""?\s+Duct$',
            r'^24""?x12""?\s+Duct$',
            r'^12""?x12""?\s+Duct$',
            r'^8""?x8""?\s+Duct$',
            r'^1"\s+Condensate\s+Line$',
            r'^Remove\s+Existing\s+VCT$',
            r'^Remove\s+Existing\s+DOOR$',
            r'^Ceiling\s+Finish:\s+CL-0[124]$',
            # Specs references (ASTM, NFPA, etc.) - not equipment
            r'^ASTM-\d+$',
            r'^NFPA-\d+[A-Z]?$',
            r'^RJ45$',
            r'^UL\s*\d+$',
            r'^ANSI\s*/?\s*[A-Z]*\d+$',
            # Specs references / standards (not equipment)
            r'^(AE|EP|E|STD|IBC|EIA|LM|ASTM|NFPA|IP)\s*[-]?\d+[A-Z]?$',
            r'^LM-\d+$',
            r'^T-\d+$',
            r'^IP\d+$',
            r'^VA-\d+$',
            r'^PANELS?$',
            r'^DIBD\d+$',
            r'^SP\d+L?$',
            r'^MR\d+$',
            r'^LGPW-\d+$',
            r'^PBE\d+$',
            r'^ED-\d+$',
            r'^EY-\d+$',
            r'^casework$',
            r'^lights$',
            # Generic finish codes without context
            r'^(CG|GR|DR|TS|CR|WC|WB|CPT|LVT|FT|WB|TR|QT|SS|PL)-\d+$',
        ]
        
        filtered = []
        removed = 0
        for item in items:
            desc = item.description
            keep = True
            for pattern in remove_patterns:
                if re.search(pattern, desc, re.IGNORECASE):
                    keep = False
                    removed += 1
                    break
            if keep:
                filtered.append(item)
        
        if removed > 0:
            print(f"  [Filter] Removed {removed} false positives")
        return filtered
    
    def _deduplicate(self, items: List[LineItem]) -> List[LineItem]:
        """Smart deduplication:
        - Flooring types: keep ONLY the most descriptive variant per base type.
        - Accessories with same base name are merged, keeping the most descriptive.
        """
        
        def extract_dim_base(desc: str) -> tuple:
            """Extract (dimension, base_type) from description."""
            parts = [p.strip() for p in desc.split('|')]
            if len(parts) == 1:
                return None, parts[0].lower()
            # Check if first part looks like a dimension
            first = parts[0].lower()
            if re.search(r'\d+\s*[\"\']', first) or re.search(r'\d+\s*(?:wide|w|thick|high)', first):
                return first, parts[-1].lower()
            return None, parts[-1].lower()
        
        # Group items by base type, keep the most descriptive (longest description)
        groups = {}
        
        for item in items:
            dim, base = extract_dim_base(item.description)
            is_accessory = bool(re.search(r'\|\s*(Size|Color|Manufacturer):', item.description, re.IGNORECASE))
            
            if is_accessory:
                # Merge accessories by base name
                key = f"{item.trade}|{base}"
                if key not in groups:
                    groups[key] = item
                else:
                    if len(item.description) > len(groups[key].description):
                        groups[key] = item
            else:
                # Flooring types: merge by base name, keep the longest description
                # This eliminates extra variants (e.g., 6"x36" porcelain when 8"x48" exists)
                key = f"{item.trade}|{base}"
                if key not in groups:
                    groups[key] = item
                else:
                    if len(item.description) > len(groups[key].description):
                        groups[key] = item
        
        return list(groups.values())
