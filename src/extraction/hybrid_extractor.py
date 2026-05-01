"""Hybrid extractor: Local text extraction + LLM reasoning."""
import json
import os
import re
from typing import List, Dict, Optional
from collections import defaultdict

from src.models import LineItem
from src.extraction.vision_extractor import VisionExtractor


class StructureClassifier:
    """Classify text chunks by document structure type."""
    
    SCHEDULE_HEADERS = [
        ("diffuser", ["diffuser", "register", "grille", "supply air", "return air"]),
        ("vav", ["vav terminal", "variable air volume"]),
        ("rtu", ["rooftop unit", "rtu schedule", "air conditioning unit"]),
        ("lighting", ["lighting fixture", "fixture schedule", "luminaire"]),
        ("panel", ["panel schedule", "panelboard", "one-line diagram"]),
        ("equipment", ["equipment schedule", "mechanical equipment"]),
        ("door", ["door schedule", "door types"]),
        ("finish", ["finish schedule", "room finish", "finish legend"]),
    ]
    
    SPEC_SECTIONS = [
        ("paint", ["painting", "paint coating", "primer"]),
        ("flooring", ["flooring", " resilient flooring", "carpet"]),
        ("ceiling", ["ceiling", "acoustical tile", "gypsum board"]),
        ("hvac", ["mechanical", "hvac", "ductwork", "refrigerant"]),
        ("electrical", ["electrical", "lighting", "power", "conduit"]),
        ("plumbing", ["plumbing", "sanitary", "water supply"]),
    ]
    
    def classify(self, text: str) -> Dict[str, any]:
        """Classify a text chunk."""
        text_upper = text.upper()
        scores = defaultdict(float)
        
        # Check for schedule headers
        for sched_type, keywords in self.SCHEDULE_HEADERS:
            for kw in keywords:
                if kw.upper() in text_upper:
                    scores[f"schedule:{sched_type}"] += 1.0
        
        # Check for spec sections
        for spec_type, keywords in self.SPEC_SECTIONS:
            for kw in keywords:
                if kw.upper() in text_upper:
                    scores[f"spec:{spec_type}"] += 0.5
        
        # Check for drawing plans
        if any(kw in text_upper for kw in ["PLAN", "FLOOR PLAN", "REFLECTED CEILING"]):
            scores["drawing:plan"] += 1.0
        
        # Check for general notes
        if "GENERAL NOTES" in text_upper or "NOTES:" in text_upper:
            scores["notes:general"] += 1.0
        
        if not scores:
            return {"type": "unknown", "confidence": 0.0}
        
        best = max(scores.items(), key=lambda x: x[1])
        return {"type": best[0], "confidence": min(best[1], 1.0), "all_scores": dict(scores)}


class LLMExtractor:
    """Use LLM to extract line items from text chunks."""
    
    def __init__(self, model: str = "gpt-4o"):
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
    
    def extract_from_chunk(self, text: str, chunk_type: str, file_name: str = "") -> List[LineItem]:
        """Extract line items from a text chunk using LLM."""
        if not self.client:
            return []
        
        prompt = self._build_prompt(text, chunk_type)
        
        # Use gpt-4o-mini for large files (faster, cheaper, higher rate limit)
        model = self.model
        if len(text) > 5000:
            model = "gpt-4o-mini"
            print(f"    [LLM] Using gpt-4o-mini for large chunk ({len(text)} chars)")
        
        try:
            import time
            max_retries = 5
            base_delay = 2
            
            for attempt in range(max_retries):
                try:
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "You are a construction takeoff estimator. Extract line items from construction documents."},
                            {"role": "user", "content": prompt}
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.1,
                        max_tokens=4000,
                    )
                    break
                except Exception as e:
                    error_str = str(e).lower()
                    if 'rate limit' in error_str or '429' in error_str:
                        delay = base_delay * (2 ** attempt)
                        print(f"    [LLM] Rate limit hit, waiting {delay}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        if attempt == max_retries - 1:
                            raise
                    else:
                        raise
            
            content = response.choices[0].message.content
            
            # Robust JSON parsing with fallback for truncated JSON
            result = None
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # Try to find JSON object in response
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        pass
                
                # Last resort: extract items array manually
                if result is None:
                    items_match = re.findall(r'"description"\s*:\s*"([^"]*)".*?"trade"\s*:\s*"([^"]*)"', content, re.DOTALL)
                    if items_match:
                        line_items = []
                        for desc, trade in items_match:
                            line_items.append(LineItem(
                                description=desc,
                                trade=trade.title() if trade else "Other",
                                quantity=None,
                                unit="EA",
                                confidence=0.7,
                                source_reference=file_name
                            ))
                        return line_items
            
            if result is None:
                print(f"  [LLM] Could not parse JSON response")
                return []
            
            items = result.get("items", result.get("line_items", []))
            
            line_items = []
            for item in items:
                if isinstance(item, dict):
                    line_items.append(LineItem(
                        description=item.get("description", ""),
                        trade=item.get("trade", "Other"),
                        quantity=item.get("quantity"),
                        unit=item.get("unit", "EA"),
                        confidence=item.get("confidence", 0.75),
                        source_reference=file_name
                    ))
            
            return line_items
        except Exception as e:
            print(f"  [LLM] Error extracting from chunk: {e}")
            return []
    
    def _build_prompt(self, text: str, chunk_type: str) -> str:
        """Build LLM prompt based on chunk type with detailed few-shot examples."""
        
        base_rules = """
CRITICAL RULES:
1. Extract ONLY actual material/equipment line items (things a contractor would buy/install)
2. Do NOT extract: general notes, coordination instructions, insurance clauses, temp facilities, safety requirements
3. For each item include: description, quantity, unit, trade, confidence
4. Quantities: use explicit numbers from text when available. If not available, set quantity to null
5. Units: EA (each), LF (linear feet), SF (square feet), CF (cubic feet), RM (room), GAL (gallon), SET
6. Trade must be one of: HVAC, Electrical, Plumbing, Painting, Flooring, Ceilings, Drywall, Millwork, Doors, Fire Protection, Glazing, Framing, Demolition, Other
7. Description MUST be specific and detailed - include manufacturer, model, size, tag, color, material, voltage, capacity
8. Output JSON with key "items" containing array of objects

DESCRIPTION FORMAT (be specific):
- BAD: "Diffuser" 
- GOOD: "S-2: B.O.D: 4-WAY, Nominal Module Size: 24\"x24\", CFM: 95-210, Material: Aluminum"
- BAD: "Paint"
- GOOD: "PNT-01 (9'-6\" High): Mfg: Sherwin Williams, Color: Wordly Gray #SW7043, Type: Eggshell"
- BAD: "Light"
- GOOD: "Light C (Emergency): 2x4 LED Troffer, 4000K, 4400 lumens, Lithonia GTB"
- BAD: "Panel"
- GOOD: "Panel A: 225A, 208Y/120V, 42-space, NEMA 1, Mfg: Siemens"
"""
        
        if chunk_type.startswith("schedule:"):
            sched_type = chunk_type.split(":")[1]
            return f"""You are a construction estimator extracting {sched_type} schedule items.

{base_rules}

SCHEDULE EXTRACTION GUIDELINES:
- Extract EVERY row from the schedule table
- Include equipment tag (RTU-1, VAV-1, S-1, Light A, Panel A)
- Include manufacturer AND model (e.g., "Mfg: JCI, Model: TSS")
- Include ALL specifications: CFM, BTU, voltage, phase, amps, watts, size, material
- If schedule has columns for different specs, include them ALL in description
- Quantity is usually 1 per tag unless explicitly stated otherwise

EXAMPLE SCHEDULE OUTPUT:
{{
  "items": [
    {{
      "description": "S-2: B.O.D: 4-WAY, Nominal Module Size: 24\"x24\", CFM: 95-210, Material: Aluminum, Mfg: Titus",
      "trade": "HVAC",
      "quantity": 1,
      "unit": "EA",
      "confidence": 0.95
    }},
    {{
      "description": "VAV-1: Mfg: JCI, Model: TSS, CFM: 500, Min CFM: 150, Reheat: Hot Water",
      "trade": "HVAC",
      "quantity": 1,
      "unit": "EA",
      "confidence": 0.92
    }},
    {{
      "description": "Light C (Emergency): 2x4 LED Troffer, 4000K, 4400 lumens, Mfg: Lithonia, Model: GTB",
      "trade": "Electrical",
      "quantity": 1,
      "unit": "EA",
      "confidence": 0.90
    }}
  ]
}}

SCHEDULE TEXT:
{text}

OUTPUT JSON:"""
        
        elif chunk_type.startswith("spec:"):
            spec_type = chunk_type.split(":")[1]
            return f"""You are a construction estimator extracting {spec_type} materials and equipment from specifications.

{base_rules}

SPECIFICATION EXTRACTION GUIDELINES:
- Extract each DISTINCT product/material as a separate item
- Include manufacturer name and product name when specified
- Include color, finish type, pattern number when available
- Include size/dimensions (thickness, width, height)
- Include installation method if it affects quantity
- If spec says "Provide [product] by [manufacturer]", extract it
- Look for "SECTION" headers to identify trade context

EXAMPLE SPEC OUTPUT:
{{
  "items": [
    {{
      "description": "PNT-01: Mfg: Sherwin Williams, Color: Wordly Gray #SW7043, Type: Eggshell, Location: Exam Rooms",
      "trade": "Painting",
      "quantity": null,
      "unit": "SF",
      "confidence": 0.88
    }},
    {{
      "description": "VCT-01: 12\"x12\" Vinyl Composition Tile, Mfg: Armstrong, Color: Sterling Gray",
      "trade": "Flooring",
      "quantity": null,
      "unit": "SF",
      "confidence": 0.85
    }}
  ]
}}

SPECIFICATION TEXT:
{text}

OUTPUT JSON:"""
        
        elif chunk_type == "drawing:plan":
            return f"""You are a construction estimator reading a construction drawing/plan.

{base_rules}

DRAWING EXTRACTION GUIDELINES:
- Extract equipment tags with their descriptions (e.g., RTU-1, VAV-1, S-1)
- Extract fixture types with quantities if shown
- Extract material callouts (e.g., "5/8\" GWB", "ACT", "VCT")
- Extract demolition/removal items (shown with dashed lines or "DEMO" notes)
- Extract room names with finish codes if present
- Look for legend items and their descriptions

EXAMPLE DRAWING OUTPUT:
{{
  "items": [
    {{
      "description": "RTU-1: Rooftop Unit, 5-ton, 208V, 3-phase",
      "trade": "HVAC",
      "quantity": 1,
      "unit": "EA",
      "confidence": 0.90
    }},
    {{
      "description": "S-1: Supply Diffuser, 24\"x24\", CFM: 500",
      "trade": "HVAC",
      "quantity": 4,
      "unit": "EA",
      "confidence": 0.85
    }}
  ]
}}

PLAN TEXT:
{text}

OUTPUT JSON:"""
        
        else:
            return f"""You are a construction estimator extracting line items from construction documents.

{base_rules}

TEXT:
{text}

OUTPUT JSON:"""


class HybridExtractor:
    """Main hybrid extraction engine."""
    
    def __init__(self):
        self.classifier = StructureClassifier()
        self.llm = LLMExtractor()
        self.vision = VisionExtractor()
    
    def extract_from_project(self, ingested_files: List) -> List[LineItem]:
        """Extract line items from all ingested files."""
        all_items = []
        
        if not self.llm.is_available():
            print("  [Hybrid] LLM not available (no OPENAI_API_KEY). Falling back to rule-based.")
            from src.extraction.rule_based_extractor_v2 import RuleBasedExtractorV2
            fallback = RuleBasedExtractorV2()
            return fallback.extract_from_project(ingested_files)
        
        print("  [Hybrid] Using LLM extraction with local pre-processing + Vision for scanned pages")
        
        # Skip files that don't contain construction items
        skip_patterns = [
            'wage', 'markup', 'pcra', 'icra', 'risk assessment',
            'preconstruction', 'photo', 'wage rates',
        ]
        
        for ingested in ingested_files:
            # Skip non-construction files
            file_name_lower = ingested.file_name.lower()
            if any(p in file_name_lower for p in skip_patterns):
                print(f"  Skipping {ingested.file_name} - non-construction file")
                continue
            
            file_items = self._extract_from_file(ingested)
            
            # Vision fallback for scanned drawings with little text
            total_text = sum(len(p.text) for p in ingested.pages)
            scanned_pages = sum(1 for p in ingested.pages if p.is_scanned)
            
            # Only use vision for important drawing files, max 2 pages (cost control)
            important_drawings = ['Mechanical', 'Electrical', 'Plumbing', 'Fire Alarm', 'Architectural']
            is_important = any(kw in ingested.file_name for kw in important_drawings)
            
            if scanned_pages > 0 and total_text < 5000 and self.vision.is_available() and is_important:
                print(f"  [Vision] Processing up to 2 scanned pages from {ingested.file_name}")
                vision_items = self.vision.extract_from_pdf(
                    ingested.file_path if hasattr(ingested, 'file_path') else "",
                    ingested.file_name,
                    max_pages=2
                )
                file_items.extend(vision_items)
            
            all_items.extend(file_items)
            print(f"  {ingested.file_name}: {len(file_items)} items")
        
        # Smart deduplication
        unique = self._smart_deduplicate(all_items)
        
        return unique
    
    def _smart_deduplicate(self, items: List[LineItem]) -> List[LineItem]:
        """Deduplicate items with fuzzy matching and intelligent merging."""
        # Normalize trade names
        trade_map = {
            'ceiling': 'Ceilings', 'ceilings': 'Ceilings',
            'floor': 'Flooring', 'flooring': 'Flooring',
            'paint': 'Painting', 'painting': 'Painting',
            'door': 'Doors', 'doors': 'Doors',
            'wall': 'Drywall', 'drywall': 'Drywall',
            'gypsum': 'Drywall',
            'electrical': 'Electrical',
            'hvac': 'HVAC',
            'plumbing': 'Plumbing',
            'fire protection': 'Fire Protection', 'fire_protection': 'Fire Protection',
            'millwork': 'Millwork',
            'glazing': 'Glazing',
            'framing': 'Framing',
            'demolition': 'Demolition',
        }
        
        unique = []
        
        for item in items:
            # Normalize trade
            trade_lower = item.trade.lower().strip()
            item.trade = trade_map.get(trade_lower, item.trade.title() if item.trade else 'Other')
            
            desc = item.description.lower().strip()
            
            # Normalize description for comparison
            desc_norm = re.sub(r'\s+', ' ', desc)
            desc_norm = desc_norm.replace("vfd ", "vfd").replace("vfd1-6", "vfd 1-6")
            desc_norm = desc_norm.replace(" - ", "-").replace(" / ", "/")
            
            # Check for duplicates
            is_dup = False
            for existing in unique:
                existing_desc = existing.description.lower().strip()
                existing_norm = re.sub(r'\s+', ' ', existing_desc)
                existing_norm = existing_norm.replace("vfd ", "vfd").replace("vfd1-6", "vfd 1-6")
                existing_norm = existing_norm.replace(" - ", "-").replace(" / ", "/")
                
                # Exact match after normalization
                if desc_norm == existing_norm:
                    is_dup = True
                    break
                
                # Same trade only
                if item.trade != existing.trade:
                    continue
                
                # Check for equipment tag pattern duplication
                tag_patterns = [
                    r'(vfd\s*\d+[\s\-]*\d*)',  # VFD1-6, VFD 1-6
                    r'(vfd\s*\d+)',  # VFD 1, VFD 2
                    r'(rtu[\s\-]*\d+)',  # RTU-1
                    r'(vav[\s\-]*\d+)',  # VAV-1
                    r'(s[\s\-]*\d+)',  # S-1
                    r'(light\s*[a-z])',  # Light A
                    r'(panel\s*[a-z])',  # Panel A
                ]
                
                item_tags = set()
                existing_tags = set()
                for pattern in tag_patterns:
                    item_tags.update(re.findall(pattern, desc_norm))
                    existing_tags.update(re.findall(pattern, existing_norm))
                
                # If they share tags, they might be duplicates
                if item_tags and existing_tags:
                    shared = item_tags & existing_tags
                    if shared:
                        # Keep the more detailed one
                        if len(desc_norm) > len(existing_norm):
                            existing.description = item.description
                            existing.confidence = max(existing.confidence, item.confidence)
                        is_dup = True
                        break
                
                # Check for subset (e.g., "VFD 1" vs "VFD 1-6")
                if desc_norm in existing_norm or existing_norm in desc_norm:
                    if len(desc_norm) > len(existing_norm):
                        existing.description = item.description
                        existing.confidence = max(existing.confidence, item.confidence)
                    is_dup = True
                    break
                
                # Check for near-match (same first 25 chars for long descriptions)
                if len(desc_norm) > 25 and len(existing_norm) > 25:
                    if desc_norm[:25] == existing_norm[:25]:
                        if len(desc_norm) > len(existing_norm):
                            existing.description = item.description
                            existing.confidence = max(existing.confidence, item.confidence)
                        is_dup = True
                        break
            
            if not is_dup:
                unique.append(item)
        
        return unique
    
    def _extract_from_file(self, ingested) -> List[LineItem]:
        """Extract from a single file."""
        items = []
        
        # Strategy 1: Extract from schedules (grouped by page ranges)
        schedules = self._extract_schedules(ingested)
        for sched_text, sched_type in schedules:
            sched_items = self.llm.extract_from_chunk(sched_text, f"schedule:{sched_type}", ingested.file_name)
            items.extend(sched_items)
        
        # Strategy 2: Extract from specs (large text chunks)
        if len(schedules) == 0 and hasattr(ingested, 'pages'):
            # No schedules found - try extracting from full text
            full_text = "\n\n".join(p.text for p in ingested.pages if p.text)
            
            # Split into chunks of ~25000 chars (fewer API calls)
            chunks = self._split_text(full_text, max_chars=25000)
            for chunk in chunks:
                classification = self.classifier.classify(chunk)
                if classification["confidence"] > 0.3:
                    chunk_items = self.llm.extract_from_chunk(chunk, classification["type"], ingested.file_name)
                    items.extend(chunk_items)
        
        return items
    
    def _extract_schedules(self, ingested) -> List[tuple]:
        """Extract schedule sections from a file."""
        schedules = []
        
        if not hasattr(ingested, 'pages'):
            return schedules
        
        full_text = "\n\n".join(p.text for p in ingested.pages if p.text)
        
        # Look for schedule boundaries
        schedule_markers = [
            (r'DIFFUSERS?\s*,?\s*REGISTERS?\s*(AND|&)\s*GRILLES?\s*SCHEDULE', 'diffuser'),
            (r'VAV\s*TERMINAL\s*UNIT\s*SCHEDULE', 'vav'),
            (r'ROOFTOP\s*AIR\s*CONDITIONING\s*UNIT\s*SCHEDULE', 'rtu'),
            (r'LIGHTING\s*FIXTURE\s*SCHEDULE', 'lighting'),
            (r'PANEL\s*SCHEDULE', 'panel'),
            (r'EQUIPMENT\s*SCHEDULE', 'equipment'),
            (r'DOOR\s*SCHEDULE', 'door'),
            (r'FINISH\s*(SCHEDULE|LEGEND)', 'finish'),
        ]
        
        for pattern, sched_type in schedule_markers:
            matches = list(re.finditer(pattern, full_text, re.IGNORECASE))
            for match in matches:
                start = match.start()
                # Find end of schedule (next major section or 3000 chars)
                end = start + 3000
                next_section = re.search(r'\n\s*(SCHEDULE|PLAN|SECTION|NOTES)\s*\n', full_text[start+50:start+5000], re.IGNORECASE)
                if next_section:
                    end = start + 50 + next_section.start()
                
                schedule_text = full_text[start:end]
                if len(schedule_text) > 100:
                    schedules.append((schedule_text, sched_type))
        
        return schedules
    
    def _split_text(self, text: str, max_chars: int = 4000) -> List[str]:
        """Split text into chunks of max_chars, preserving page boundaries."""
        chunks = []
        current = ""
        
        for page_text in text.split("\n\n"):
            if len(current) + len(page_text) > max_chars:
                if current:
                    chunks.append(current)
                current = page_text
            else:
                current += "\n\n" + page_text
        
        if current:
            chunks.append(current)
        
        return chunks
