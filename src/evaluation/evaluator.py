"""Evaluation module for comparing predictions to expected outputs."""
import json
import re
from pathlib import Path
from typing import List, Dict, Tuple
import pandas as pd
from rapidfuzz import fuzz

from src.models import ProjectOutput, LineItem, EvaluationReport, QuantityDifference


# Equipment tag patterns for exact matching
EQUIPMENT_TAG_PATTERNS = [
    r'\b(S-\d+)\b', r'\b(R-\d+)\b', r'\b(RTU-\d+)\b', r'\b(AC-\d+)\b',
    r'\b(HP-\d+)\b', r'\b(EF-\d+)\b', r'\b(VAV-\d+)\b', r'\b(CUH-\d+)\b',
    r'\b(PNT-\d+)\b', r'\b(CL-\d+)\b', r'\b(LVT-\d+)\b', r'\b(FT-\d+)\b',
    r'\b(CPT-\d+)\b', r'\b(VCT-\d+)\b', r'\b(WB-\d+)\b', r'\b(WT-\d+)\b',
    r'\b(DR-\d+)\b', r'\b(FR-\d+)\b', r'\b(AL-\d+)\b', r'\b(TS-\d+)\b',
    r'\b(CR-\d+)\b', r'\b(CG-\d+)\b', r'\b(PT-\d+)\b', r'\b(QT-\d+)\b',
    r'\b(GWB-\d+)\b',
]

# Critical keywords that must appear in predicted for certain expected items
CRITICAL_KEYWORDS = {
    'occupancy sensor': ['occupancy', 'sensor', 'vacancy'],
    'vacancy sensor': ['vacancy', 'sensor', 'occupancy'],
    'daylight sensor': ['daylight', 'sensor', 'photo'],
    'dimmer switch': ['dimmer', 'switch'],
    'single pole switch': ['single pole', 'switch'],
    'three way switch': ['three way', 'switch'],
    'junction box': ['junction box', 'j-box'],
    'data outlet': ['data', 'outlet', 'network'],
    'fire alarm': ['fire alarm', 'smoke detector', 'duct detector'],
    'receptacle': ['receptacle', 'outlet'],
    'cleanout': ['cleanout', 'clean out'],
    'duct elbow': ['elbow', 'duct elbow'],
    'flexible duct': ['flexible duct', 'flex duct'],
}

# Item type categories for tag validation
ITEM_TYPE_CATEGORIES = {
    'diffuser': ['diffuser', 'supply', 'grille', 'register', 'anemostat'],
    'sink': ['sink', 'bowl', 'basin'],
    'fan': ['fan', 'exhaust', 'blower'],
    'unit': ['unit', 'rtu', 'ac', 'hp', 'vav', 'cuh'],
    'light': ['light', 'troffer', 'downlight', 'pendant', 'cove', 'exit sign', 'led'],
    'switch': ['switch', 'dimmer'],
    'sensor': ['sensor', 'occupancy', 'vacancy', 'daylight'],
    'panel': ['panel', 'breaker', 'switchboard'],
    'receptacle': ['receptacle', 'outlet'],
}


def extract_equipment_tags(text: str) -> List[str]:
    """Extract equipment tags like S-1, VAV-1, EF-1 from text."""
    tags = []
    text_upper = text.upper()
    for pattern in EQUIPMENT_TAG_PATTERNS:
        matches = re.findall(pattern, text_upper, re.IGNORECASE)
        tags.extend([m.upper() for m in matches])
    return tags


def get_item_type(text: str) -> str:
    """Determine item type category from text."""
    text_lower = text.lower()
    for category, keywords in ITEM_TYPE_CATEGORIES.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return 'other'


def has_critical_keyword(expected_desc: str, predicted_desc: str) -> bool:
    """Check if predicted contains critical keywords from expected."""
    exp_lower = expected_desc.lower()
    pred_lower = predicted_desc.lower()
    
    for key, keywords in CRITICAL_KEYWORDS.items():
        if key in exp_lower:
            # Expected has this critical keyword - predicted MUST have at least one
            if not any(kw in pred_lower for kw in keywords):
                return False
    return True


def _extract_significant_words(text: str) -> set:
    """Extract significant words (length > 3) excluding common stop words."""
    stop_words = {'the', 'and', 'for', 'with', 'from', 'this', 'that', 'are', 'was', 'were',
                  'been', 'have', 'has', 'had', 'will', 'would', 'should', 'could', 'shall',
                  'may', 'might', 'must', 'can', 'need', 'used', 'each', 'all', 'any', 'both',
                  'into', 'onto', 'upon', 'over', 'under', 'above', 'below', 'between',
                  'through', 'during', 'before', 'after', 'since', 'until', 'while',
                  'supply', 'client', 'installed', 'provide', 'provided', 'provides',
                  'inch', 'inches', 'diameter', 'size', 'high', 'height', 'wide', 'width',
                  'deep', 'depth', 'long', 'length', 'type', 'color', 'name', 'product',
                  'collection', 'mfg', 'manufacturer', 'equivalent', 'similar'}
    words = re.findall(r'\b[a-z]{4,}\b', text.lower())
    return set(w for w in words if w not in stop_words)


def _normalize_spelling(text: str) -> str:
    """Normalize common spelling variations in construction terms."""
    replacements = {
        'vaccancy': 'vacancy',
        'receptacl': 'receptacle',
        'recepticles': 'receptacles',
        'aluminium': 'aluminum',
        'anestostat': 'anemostat',
        'difuser': 'diffuser',
        'difusers': 'diffusers',
        'gypsom': 'gypsum',
        'electrical': 'electrical',
        'mechanical': 'mechanical',
        'plumming': 'plumbing',
        'ceiling': 'ceiling',
        'flourescent': 'fluorescent',
        'florescent': 'fluorescent',
    }
    text_lower = text.lower()
    for wrong, correct in replacements.items():
        text_lower = text_lower.replace(wrong, correct)
    return text_lower


def compute_match_score(expected_desc: str, predicted_desc: str) -> int:
    """Compute fuzzy match score with multi-layer validation."""
    exp_lower = _normalize_spelling(expected_desc)
    pred_lower = _normalize_spelling(predicted_desc)
    exp_len = len(expected_desc)
    
    # Layer 0: Keyword overlap validation (prevents cross-matching on common suffixes)
    exp_words = _extract_significant_words(exp_lower)
    pred_words = _extract_significant_words(pred_lower)
    if exp_words and pred_words:
        common_words = exp_words & pred_words
        # If less than 2 significant words overlap, penalize heavily
        if len(common_words) < 2:
            base_score = fuzz.partial_ratio(exp_lower, pred_lower)
            return int(base_score * 0.3)
    
    # Layer 1: Equipment tag exact matching with type validation
    exp_tags = extract_equipment_tags(expected_desc)
    pred_tags = extract_equipment_tags(predicted_desc)
    
    if exp_tags and pred_tags:
        common_tags = set(exp_tags) & set(pred_tags)
        if common_tags:
            # Tags match - validate item type AND keywords
            exp_type = get_item_type(expected_desc)
            pred_type = get_item_type(predicted_desc)
            
            # Check for type mismatch (Diffuser vs Sink, etc.)
            type_mismatch = (exp_type != 'other' and pred_type != 'other' and 
                           exp_type != pred_type)
            
            if type_mismatch:
                # Different types (e.g., Diffuser vs Sink) - penalize heavily
                return min(fuzz.partial_ratio(exp_lower, pred_lower), 35)
            
            # For expected items with known types, predicted should have matching keywords
            if exp_type == 'diffuser' and not any(kw in pred_lower for kw in ['diffuser', 'grille', 'supply', 'anemostat']):
                return min(fuzz.partial_ratio(exp_lower, pred_lower), 40)
            if exp_type == 'sink' and not any(kw in pred_lower for kw in ['sink', 'bowl', 'basin']):
                return min(fuzz.partial_ratio(exp_lower, pred_lower), 40)
            if exp_type == 'fan' and not any(kw in pred_lower for kw in ['fan', 'exhaust', 'blower']):
                return min(fuzz.partial_ratio(exp_lower, pred_lower), 40)
            if exp_type == 'unit' and not any(kw in pred_lower for kw in ['unit', 'rtu', 'ac', 'hp', 'vav', 'cuh', 'system']):
                return min(fuzz.partial_ratio(exp_lower, pred_lower), 40)
            if exp_type == 'light' and not any(kw in pred_lower for kw in ['light', 'troffer', 'downlight', 'pendant', 'cove', 'exit', 'led']):
                return min(fuzz.partial_ratio(exp_lower, pred_lower), 40)
            
            # Tags match and type is compatible - high score
            score = fuzz.partial_ratio(exp_lower, pred_lower)
            return max(score, 85)
        else:
            # Tags don't match
            return min(fuzz.partial_ratio(exp_lower, pred_lower), 30)
    
    # Layer 2: Critical keyword validation
    if not has_critical_keyword(expected_desc, predicted_desc):
        # Missing critical keyword - severe penalty
        base_score = fuzz.partial_ratio(exp_lower, pred_lower)
        return int(base_score * 0.4)
    
    # Layer 3: Length-appropriate fuzzy matching
    if exp_len < 20:
        # Very short - token_set_ratio is safer
        return fuzz.token_set_ratio(exp_lower, pred_lower)
    elif exp_len < 40:
        # Short descriptions - blend token_set and partial
        ts_score = fuzz.token_set_ratio(exp_lower, pred_lower)
        pr_score = fuzz.partial_ratio(exp_lower, pred_lower)
        if pr_score > ts_score + 20:
            return int((ts_score + pr_score) / 2)
        return ts_score
    else:
        # Medium/long descriptions - partial_ratio with length penalty
        score = fuzz.partial_ratio(exp_lower, pred_lower)
        # Penalize if predicted is much longer (likely false positive)
        if len(predicted_desc) > exp_len * 3:
            score = int(score * 0.7)
        return score


class Evaluator:
    """Evaluates predictions against expected human outputs."""

    def __init__(self, fuzzy_threshold: int = 60):
        self.fuzzy_threshold = fuzzy_threshold

    def load_expected_excel(self, xlsx_path: str) -> List[Dict]:
        """Load expected items from Excel estimate file."""
        import os
        path = os.path.abspath(xlsx_path)
        # Windows long path support
        if os.name == 'nt' and len(path) > 240 and not path.startswith('\\\\?\\'):
            path = '\\\\?\\' + path
        df = pd.read_excel(path, header=None)
        df_data = df.iloc[7:].copy()
        # Handle different column counts
        if len(df_data.columns) == 16:
            df_data.columns = ['ITEM_NUM', 'DRAWING', 'SECTION', 'DESCRIPTION', 
                              'QUANTITY', 'WASTAGE', 'QTY_WITH_WASTAGE', 'UNIT',
                              'UNIT_MATERIAL', 'UNIT_LABOUR', 'UNIT_EQUIPMENT',
                              'TOTAL_MATERIAL', 'TOTAL_LABOR', 'TOTAL_EQUIPMENT', 
                              'TOTAL_COST', 'TRADE']
        elif len(df_data.columns) == 15:
            df_data.columns = ['ITEM_NUM', 'DRAWING', 'DESCRIPTION', 
                              'QUANTITY', 'WASTAGE', 'QTY_WITH_WASTAGE', 'UNIT',
                              'UNIT_MATERIAL', 'UNIT_LABOUR', 'UNIT_EQUIPMENT',
                              'TOTAL_MATERIAL', 'TOTAL_LABOR', 'TOTAL_EQUIPMENT', 
                              'TOTAL_COST', 'TRADE']
        else:
            # Generic fallback
            cols = ['COL_' + str(i) for i in range(len(df_data.columns))]
            df_data.columns = cols
        
        # Filter valid rows
        df_items = df_data[
            df_data['DESCRIPTION'].notna() & 
            df_data['QUANTITY'].notna() & 
            df_data['ITEM_NUM'].notna() & 
            (df_data['ITEM_NUM'] != 'DESCRIPTION') &
            (df_data['DESCRIPTION'] != 'DIVISION 1- GENERAL')
        ]
        
        items = []
        for _, row in df_items.iterrows():
            try:
                qty = float(row['QUANTITY']) if pd.notna(row['QUANTITY']) else 0
                if qty > 0:
                    items.append({
                        'description': str(row['DESCRIPTION']).strip(),
                        'quantity': qty,
                        'unit': str(row['UNIT']).strip() if pd.notna(row['UNIT']) else ''
                    })
            except (ValueError, TypeError):
                continue
        
        return items

    def evaluate(self, prediction_path: str, expected_path: str) -> EvaluationReport:
        """Compare prediction to expected output."""
        # Load prediction
        with open(prediction_path, 'r', encoding='utf-8') as f:
            pred_data = json.load(f)
        
        predicted_items = pred_data.get('line_items', [])
        
        # Load expected
        expected_items = self.load_expected_excel(expected_path)
        
        matched = 0
        missing = []
        extra = []
        qty_diffs = []
        
        # Track which expected items were matched
        expected_matched = [False] * len(expected_items)
        predicted_matched = [False] * len(predicted_items)
        
        # Find matches
        for i, exp in enumerate(expected_items):
            best_score = 0
            best_pred_idx = -1
            
            for j, pred in enumerate(predicted_items):
                if predicted_matched[j]:
                    continue
                
                score = compute_match_score(
                    exp['description'], 
                    pred.get('description', '')
                )
                if score > best_score:
                    best_score = score
                    best_pred_idx = j
            
            if best_score >= self.fuzzy_threshold:
                matched += 1
                expected_matched[i] = True
                predicted_matched[best_pred_idx] = True
                
                # Calculate quantity difference
                pred_qty = predicted_items[best_pred_idx].get('quantity')
                if pred_qty is not None and exp['quantity'] > 0:
                    pct_diff = ((pred_qty - exp['quantity']) / exp['quantity']) * 100
                    qty_diffs.append(QuantityDifference(
                        description=exp['description'][:100],
                        predicted=pred_qty,
                        expected=exp['quantity'],
                        pct_diff=round(pct_diff, 2)
                    ))
        
        # Find missing items
        for i, exp in enumerate(expected_items):
            if not expected_matched[i]:
                missing.append(exp['description'][:100])
        
        # Find extra items
        for j, pred in enumerate(predicted_items):
            if not predicted_matched[j]:
                extra.append(pred.get('description', '')[:100])
        
        return EvaluationReport(
            matched_items=matched,
            missing_items=missing,
            extra_items=extra,
            quantity_differences=qty_diffs,
            overall_notes=f"Matched {matched}/{len(expected_items)} items. "
                         f"Missing: {len(missing)}, Extra: {len(extra)}. "
                         f"Prediction coverage: {matched/max(1,len(expected_items))*100:.1f}%"
        )
