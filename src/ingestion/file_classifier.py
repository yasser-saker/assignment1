"""Classifies PDF files by type based on filename keywords."""
from pathlib import Path
from typing import List

from src.config import (
    DRAWING_KEYWORDS, SPEC_KEYWORDS, SOW_KEYWORDS,
    ADDENDUM_KEYWORDS, RULES_KEYWORDS, BREAKOUT_KEYWORDS
)


class FileClassifier:
    """Classifies construction project files."""

    KEYWORD_MAP = {
        "drawing": DRAWING_KEYWORDS,
        "spec": SPEC_KEYWORDS,
        "sow": SOW_KEYWORDS,
        "addendum": ADDENDUM_KEYWORDS,
        "rules": RULES_KEYWORDS,
        "breakout": BREAKOUT_KEYWORDS,
    }

    def classify(self, file_name: str) -> str:
        """Classify file by name. Returns: drawing, spec, sow, addendum, rules, breakout, other."""
        name_lower = file_name.lower()
        
        for file_type, keywords in self.KEYWORD_MAP.items():
            for keyword in keywords:
                if keyword in name_lower:
                    return file_type
        
        return "other"

    def classify_batch(self, file_names: List[str]) -> dict:
        """Classify multiple files."""
        return {name: self.classify(name) for name in file_names}
