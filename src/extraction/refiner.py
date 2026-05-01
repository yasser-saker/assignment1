"""LLM-based extraction refiner to reduce false positives."""
import json
import re
import time
from typing import List, Dict, Set, Optional

from src.models import LineItem
from src.extraction.llm_client import LLMClient


def _extract_json(text: str) -> Optional[dict]:
    """Extract JSON from text, handling markdown blocks."""
    text = text.strip()
    if not text:
        return None
    
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try markdown code blocks with objects
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try markdown code blocks with arrays
    match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', text, re.DOTALL)
    if match:
        try:
            arr = json.loads(match.group(1))
            return {"kept_indices": arr} if isinstance(arr, list) else arr
        except json.JSONDecodeError:
            pass
    
    # Try finding any JSON object
    for pattern in [r'\{.*"kept_indices".*\}', r'\{.*"kept".*\}']:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                continue
    
    return None


class ExtractionRefiner:
    """Uses LLM to analyze predictions and identify/filter false positives."""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.filter_rules: List[dict] = []
    
    def _call_llm_raw(self, prompt: str, max_tokens: int = 2000) -> str:
        """Call LLM and return raw text response."""
        client = self.llm_client._get_client()
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Always return valid JSON."},
            {"role": "user", "content": prompt}
        ]
        
        kwargs = self.llm_client._build_api_kwargs(messages, max_tokens)
        # Override response format for openai
        if self.llm_client.provider == "openai":
            kwargs.pop('response_format', None)
        
        try:
            response = client.chat.completions.create(**kwargs)
            time.sleep(0.3)
        except Exception as e:
            print(f"  LLM error: {e}")
            return ""
        
        return response.choices[0].message.content
    
    def refine_batch(self, items: List[LineItem], batch_size: int = 80) -> List[LineItem]:
        """Directly ask LLM to filter items batch by batch."""
        all_filtered = []
        total_batches = (len(items) + batch_size - 1) // batch_size
        
        for batch_idx in range(total_batches):
            start = batch_idx * batch_size
            end = min(start + batch_size, len(items))
            batch = items[start:end]
            
            prompt = f"""You are reviewing construction takeoff line items. Keep only REAL, SPECIFIC construction materials, equipment, and finishes. Remove generic notes, instructions, section headers, insurance clauses, and duplicate variants.

Items to review (batch {batch_idx+1}/{total_batches}):

"""
            for i, item in enumerate(batch):
                prompt += f"[{i}] {item.description[:180]}\n"
            
            prompt += """
Return ONLY this exact JSON format:
{"kept_indices": [0, 2, 5, ...]}
"""
            
            content = self._call_llm_raw(prompt, max_tokens=2000)
            result = _extract_json(content)
            
            kept_indices = set()
            if result and isinstance(result, dict):
                indices = result.get('kept_indices', result.get('kept', []))
                if isinstance(indices, list):
                    kept_indices = set(indices)
            
            kept_count = 0
            for i, item in enumerate(batch):
                if i in kept_indices:
                    all_filtered.append(item)
                    kept_count += 1
            
            print(f"  Batch {batch_idx+1}/{total_batches}: kept {kept_count}/{len(batch)}")
        
        return all_filtered
    
    def analyze_and_filter(self, predicted_items: List[LineItem], 
                           extra_descriptions: List[str],
                           matched_descriptions: List[str]) -> List[LineItem]:
        """Two-stage refinement: analyze patterns, then apply programmatic filtering."""
        
        # Stage 1: Get filter rules from LLM
        sample_extras = extra_descriptions[:80]
        sample_matched = matched_descriptions[:80]
        
        prompt = f"""You are an expert construction estimator. Analyze these two groups and identify patterns that distinguish false positives from real items.

FALSE POSITIVES (should be removed):
{chr(10).join(f"- {desc[:150]}" for desc in sample_extras[:40])}

REAL ITEMS (should be kept):
{chr(10).join(f"- {desc[:150]}" for desc in sample_matched[:40])}

Return JSON with filter rules:
{{"rules": [
  {{"pattern": "keyword or regex", "action": "remove", "reason": "brief explanation"}}
]}}
"""
        
        content = self._call_llm_raw(prompt, max_tokens=2000)
        result = _extract_json(content)
        
        if result and isinstance(result, dict) and 'rules' in result:
            self.filter_rules = result['rules']
            print(f"  Learned {len(self.filter_rules)} filter rules from LLM")
        else:
            print(f"  Could not parse filter rules, using defaults")
            self.filter_rules = self._default_rules()
        
        # Stage 2: Apply rules
        return self.apply_rules(predicted_items)
    
    def _default_rules(self) -> List[dict]:
        """Default filter rules based on common false positive patterns."""
        return [
            {"pattern": "^SECTION\s+\d+", "action": "remove", "reason": "Section headers"},
            {"pattern": "^\d+\.\s+(SEE|COORDINATE|PROVIDE|INSTALL|CONTRACTOR|MAINTAIN)", "action": "remove", "reason": "Numbered spec notes"},
            {"pattern": "^i\.\s+\\$", "action": "remove", "reason": "Insurance clauses"},
            {"pattern": "^(Floor Finish|Wall Base|Wall Finish|Ceiling Finish|Millwork):\s+EXIST", "action": "remove", "reason": "Existing finish placeholders"},
            {"pattern": "PRODUCT INFORMATION, INSTALLATION METHODS", "action": "remove", "reason": "Generic product info"},
            {"pattern": "PROVIDE.*COORDINATE.*WITH", "action": "remove", "reason": "Coordination notes"},
            {"pattern": "Color:\s*STAIRS|Type:\s*EXIST", "action": "remove", "reason": "Invalid finish legend entries"},
        ]
    
    def apply_rules(self, items: List[LineItem]) -> List[LineItem]:
        """Apply learned filter rules to remove false positives."""
        if not self.filter_rules:
            self.filter_rules = self._default_rules()
        
        filtered = []
        for item in items:
            desc = item.description
            keep = True
            
            for rule in self.filter_rules:
                pattern = rule.get('pattern', '')
                action = rule.get('action', 'keep')
                
                if not pattern or action != 'remove':
                    continue
                
                try:
                    if re.search(pattern, desc, re.IGNORECASE):
                        keep = False
                        break
                except re.error:
                    if pattern.lower() in desc.lower():
                        keep = False
                        break
            
            if keep:
                filtered.append(item)
        
        return filtered
