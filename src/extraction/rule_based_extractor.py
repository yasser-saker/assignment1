"""Rule-based extractor as fallback when LLM is not available."""
import re
from typing import List

from src.models import LineItem, IngestedFile


class RuleBasedExtractor:
    """Extracts line items using regex patterns and rules."""

    # Common trade keywords
    TRADE_PATTERNS = {
        "Demolition": ["demo", "demolition", "remove", "removal"],
        "Drywall": ["drywall", "gypsum", "gwb"],
        "Flooring": ["floor", "flooring", "carpet", "tile", "vinyl", "epoxy"],
        "Painting": ["paint", "painting", "primer", "coat"],
        "Ceilings": ["ceiling", "acoustic", "act"],
        "Millwork": ["millwork", "cabinet", "countertop", "casework"],
        "Electrical": ["electrical", "outlet", "light", "switch", "panel"],
        "Plumbing": ["plumbing", "fixture", "sink", "toilet"],
        "HVAC": ["hvac", "duct", "diffuser", "grille"],
        "Doors": ["door", "frame", "hardware"],
        "Glazing": ["glass", "glazing", "window"],
        "Signage": ["sign", "signage"],
    }

    # Unit patterns
    UNIT_PATTERNS = [
        (r'\b(\d[\d,\.\s]*)\s*SF\b', 'SF'),
        (r'\b(\d[\d,\.\s]*)\s*L\.?F\.?\b', 'LF'),
        (r'\b(\d[\d,\.\s]*)\s*EA\b', 'EA'),
        (r'\b(\d[\d,\.\s]*)\s*CY\b', 'CY'),
        (r'\b(\d[\d,\.\s]*)\s*SY\b', 'SY'),
    ]

    def detect_trade(self, text: str) -> str:
        """Detect trade from text."""
        text_lower = text.lower()
        for trade, keywords in self.TRADE_PATTERNS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return trade
        return "Other"

    def extract_quantities(self, text: str) -> List[tuple]:
        """Extract quantity-unit pairs from text."""
        results = []
        for pattern, unit in self.UNIT_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                qty_str = match.group(1).replace(',', '').replace(' ', '')
                try:
                    qty = float(qty_str)
                    if qty > 0:
                        results.append((qty, unit))
                except ValueError:
                    continue
        return results

    def extract_from_text(self, text: str, file_name: str) -> List[LineItem]:
        """Extract line items from text."""
        items = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if len(line) < 10:
                continue
            
            # Try to find quantity-unit pairs
            qty_pairs = self.extract_quantities(line)
            if qty_pairs:
                trade = self.detect_trade(line)
                for qty, unit in qty_pairs[:1]:  # Take first match
                    item = LineItem(
                        description=line[:200],
                        trade=trade,
                        quantity=qty,
                        unit=unit,
                        confidence=0.5,
                        source_reference=file_name
                    )
                    items.append(item)
        
        return items

    def extract_from_file(self, ingested: IngestedFile) -> List[LineItem]:
        """Extract from all pages of a file."""
        all_items = []
        for page in ingested.pages:
            if page.text:
                items = self.extract_from_text(page.text, ingested.file_name)
                all_items.extend(items)
        return all_items
