"""Scoring and evaluation report generation."""
from typing import List, Optional

from src.models import EvaluationReport, QuantityDifference, LineItem
from src.evaluation.comparator import Comparator


class ScoringEngine:
    """Generates evaluation reports."""

    def __init__(self):
        self.comparator = Comparator()

    def evaluate(
        self,
        predicted_items: List[LineItem],
        expected_items: List[dict]
    ) -> EvaluationReport:
        """Compare predictions to expected output."""
        matched = 0
        missing = []
        extra = []
        qty_diffs = []
        
        # Track which expected items were matched
        expected_matched = [False] * len(expected_items)
        
        for pred in predicted_items:
            match = self.comparator.find_match(pred, expected_items)
            if match:
                matched += 1
                # Mark expected item as matched
                for i, exp in enumerate(expected_items):
                    if exp is match:
                        expected_matched[i] = True
                        break
                
                # Calculate quantity difference
                expected_qty = match.get("quantity", 0) or 0
                if pred.quantity is not None and expected_qty > 0:
                    diff = self.comparator.calculate_qty_diff(pred.quantity, expected_qty)
                    diff.description = pred.description
                    qty_diffs.append(diff)
            else:
                extra.append(pred.description)
        
        # Find missing items
        for i, exp in enumerate(expected_items):
            if not expected_matched[i]:
                missing.append(exp.get("description", "Unknown"))
        
        return EvaluationReport(
            matched_items=matched,
            missing_items=missing,
            extra_items=extra,
            quantity_differences=qty_diffs,
            overall_notes=f"Matched {matched}/{len(expected_items)} items. {len(missing)} missing, {len(extra)} extra."
        )
