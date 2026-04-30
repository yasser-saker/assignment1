"""Fuzzy matching comparator for evaluation."""
from typing import List, Tuple, Optional
from rapidfuzz import fuzz

from src.models import LineItem, QuantityDifference
from src.config import FUZZY_MATCH_THRESHOLD


class Comparator:
    """Compares predicted line items to expected items."""

    def find_match(self, predicted: LineItem, expected_items: List[dict]) -> Optional[dict]:
        """Find best matching expected item using fuzzy string matching."""
        best_match = None
        best_score = 0
        
        for expected in expected_items:
            expected_desc = expected.get("description", "")
            score = fuzz.ratio(predicted.description.lower(), expected_desc.lower())
            
            if score > best_score:
                best_score = score
                best_match = expected
        
        if best_score >= FUZZY_MATCH_THRESHOLD:
            return best_match
        return None

    def calculate_qty_diff(self, predicted_qty: Optional[float], expected_qty: float) -> QuantityDifference:
        """Calculate quantity difference."""
        if predicted_qty is None or expected_qty == 0:
            return QuantityDifference(
                description="",
                predicted=predicted_qty or 0,
                expected=expected_qty,
                pct_diff=0.0
            )
        
        pct_diff = ((predicted_qty - expected_qty) / expected_qty) * 100
        return QuantityDifference(
            description="",
            predicted=predicted_qty,
            expected=expected_qty,
            pct_diff=round(pct_diff, 2)
        )
