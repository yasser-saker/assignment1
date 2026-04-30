"""LLM client for extraction - supports OpenAI, Kimi (Moonshot AI), and vision."""
import os
from typing import Optional, List
import json
import time
import base64
import re

from src.config import OPENAI_API_KEY, KIMI_API_KEY, DEFAULT_LLM_MODEL, DEFAULT_LLM_PROVIDER, LLM_TEMPERATURE


KIMI_BASE_URL = "https://api.moonshot.ai/v1"


def _extract_json_from_text(text: str) -> Optional[dict]:
    """Extract JSON object from text that may contain markdown or extra content.
    Handles truncated JSON by trying to find valid partial JSON."""
    text = text.strip()
    if not text:
        return None
    
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON in markdown code blocks
    json_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    match = re.search(json_block_pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON array in markdown code blocks
    json_array_pattern = r'```(?:json)?\s*(\[.*?\])\s*```'
    match = re.search(json_array_pattern, text, re.DOTALL)
    if match:
        try:
            return {"line_items": json.loads(match.group(1))}
        except json.JSONDecodeError:
            pass
    
    # Try to find any JSON object in the text
    obj_pattern = r'(\{.*"line_items".*\})'
    match = re.search(obj_pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find any JSON array in the text
    arr_pattern = r'(\[.*\])'
    for match in re.finditer(arr_pattern, text, re.DOTALL):
        try:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, list):
                return {"line_items": parsed}
        except json.JSONDecodeError:
            continue
    
    # Handle TRUNCATED JSON: try to extract complete items from partial array
    # Look for {"line_items": [ ... ]} pattern that got cut off
    if '"line_items"' in text:
        # Extract all complete objects from the partial JSON
        item_pattern = r'\{\s*"description"\s*:\s*"([^"]*(?:\\.[^"]*)*)"\s*,\s*"trade"\s*:\s*"([^"]*)"'
        items = []
        for match in re.finditer(item_pattern, text):
            # Find the full object boundaries
            start = match.start()
            # Look for the closing brace
            brace_count = 0
            in_string = False
            escape_next = False
            obj_text = ""
            for i, ch in enumerate(text[start:]):
                if escape_next:
                    obj_text += ch
                    escape_next = False
                    continue
                if ch == '\\\\':
                    obj_text += ch
                    escape_next = True
                    continue
                if ch == '"' and not escape_next:
                    in_string = not in_string
                    obj_text += ch
                    continue
                if not in_string:
                    if ch == '{':
                        brace_count += 1
                    elif ch == '}':
                        brace_count -= 1
                        obj_text += ch
                        if brace_count == 0:
                            break
                        continue
                obj_text += ch
            
            try:
                obj = json.loads(obj_text)
                if isinstance(obj, dict) and 'description' in obj:
                    items.append(obj)
            except json.JSONDecodeError:
                # Try simpler extraction
                desc = match.group(1).replace('\\"', '"')
                trade = match.group(2)
                items.append({
                    "description": desc,
                    "trade": trade,
                    "quantity": None,
                    "unit": "EA",
                    "confidence": 0.7
                })
        
        if items:
            return {"line_items": items}
    
    return None


class LLMClient:
    """Client for LLM API calls. Supports OpenAI and Kimi (Moonshot AI)."""

    def __init__(self, model: str = DEFAULT_LLM_MODEL, api_key: Optional[str] = None, provider: Optional[str] = None):
        self.model = model
        self.provider = provider or DEFAULT_LLM_PROVIDER
        
        if self.provider == "kimi":
            self.api_key = api_key or KIMI_API_KEY
            self.base_url = KIMI_BASE_URL
        else:
            self.api_key = api_key or OPENAI_API_KEY
            self.base_url = None
        
        self._client = None
        self.demo_mode = not self.api_key

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            kwargs = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def _get_system_prompt(self) -> str:
        return (
            "You are a construction estimator. Extract line items as JSON with key 'line_items' "
            "containing array of objects with: description, trade, quantity, unit, confidence, source_reference."
        )
    
    def _get_temperature(self) -> float:
        """Get temperature for current model. Kimi k2.5 requires temperature=1.0."""
        if self.provider == "kimi" and "k2.5" in self.model:
            return 1.0
        return LLM_TEMPERATURE
    
    def _build_api_kwargs(self, messages: list, max_tokens: int = 4000) -> dict:
        """Build API call kwargs. Kimi doesn't support response_format well."""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self._get_temperature(),
            "max_tokens": max_tokens,
        }
        # Only use response_format for OpenAI, not Kimi
        if self.provider != "kimi":
            kwargs["response_format"] = {"type": "json_object"}
        return kwargs

    def extract_line_items(self, prompt: str) -> List[dict]:
        """Send text prompt to LLM and extract line items."""
        if self.demo_mode:
            print(f"  [DEMO MODE] No API key found for provider='{self.provider}'. Returning placeholder items.")
            return [
                {
                    "description": f"PLACEHOLDER - Set {self.provider.upper()}_API_KEY for real extraction",
                    "trade": "Other",
                    "quantity": 0,
                    "unit": "EA",
                    "confidence": 0.0,
                    "source_reference": "demo"
                }
            ]
        
        client = self._get_client()
        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = client.chat.completions.create(**self._build_api_kwargs(messages))
            time.sleep(0.3)
        except Exception as e:
            error_str = str(e)
            if 'rate limit' in error_str.lower() or '429' in error_str:
                print(f"  Rate limit hit on {self.provider}/{self.model}, waiting 5s...")
                time.sleep(5)
                response = client.chat.completions.create(**self._build_api_kwargs(messages))
            else:
                raise
        
        content = response.choices[0].message.content
        
        # Parse JSON response with fallback for non-JSON outputs
        result = _extract_json_from_text(content)
        
        if result is None:
            print(f"  Warning: Could not parse JSON from response. Content preview: {content[:200]!r}")
            return []
        
        items = []
        if isinstance(result, list):
            items = result
        elif isinstance(result, dict) and "line_items" in result:
            items = result["line_items"]
        
        # Coerce confidence strings to float
        for item in items:
            c = item.get("confidence", 0.0)
            if isinstance(c, str):
                c_lower = c.lower()
                if c_lower in ["high", "very high"]:
                    item["confidence"] = 0.9
                elif c_lower == "medium":
                    item["confidence"] = 0.7
                else:
                    item["confidence"] = 0.5
        
        return items

    def analyze_image(self, image_path: str, prompt: str) -> str:
        """Analyze an image using vision model."""
        if self.demo_mode:
            return "No API key - vision analysis skipped"
        
        client = self._get_client()
        
        with open(image_path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode('utf-8')
        
        # Kimi k2.5 supports vision; use current model
        vision_model = self.model if self.provider == "kimi" else "gpt-4o"
        
        try:
            response = client.chat.completions.create(
                model=vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000
            )
            time.sleep(0.3)
            return response.choices[0].message.content
        except Exception as e:
            print(f"  Vision error: {e}")
            return ""
