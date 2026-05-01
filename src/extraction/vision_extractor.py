"""Vision-based extraction for scanned drawing PDFs."""
import os
import tempfile
from typing import List, Optional
from pathlib import Path

from src.models import LineItem


class VisionExtractor:
    """Extract line items from scanned drawings using GPT-4o vision."""
    
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
    
    def extract_from_pdf(self, pdf_path: str, file_name: str = "", max_pages: int = 20) -> List[LineItem]:
        """Extract from a scanned PDF by converting pages to images."""
        if not self.client:
            return []
        
        items = []
        
        try:
            import fitz
            doc = fitz.open(pdf_path)
            
            # Only process first max_pages pages (cost control)
            pages_to_process = min(len(doc), max_pages)
            
            for page_num in range(pages_to_process):
                page = doc[page_num]
                
                # Render page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale for better OCR
                
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    pix.save(tmp.name)
                    tmp_path = tmp.name
                
                try:
                    page_items = self._extract_from_image(tmp_path, file_name, page_num + 1)
                    items.extend(page_items)
                    print(f"    Vision page {page_num + 1}: {len(page_items)} items")
                finally:
                    os.unlink(tmp_path)
            
            doc.close()
            
        except Exception as e:
            print(f"  Vision extraction error: {e}")
        
        return items
    
    def _extract_from_image(self, image_path: str, file_name: str, page_num: int) -> List[LineItem]:
        """Send image to GPT-4o vision for extraction."""
        import base64
        
        with open(image_path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode('utf-8')
        
        prompt = """You are a construction estimator analyzing a construction drawing page.

TASK: Extract ALL equipment tags, material callouts, fixture schedules, and construction items visible on this drawing.

LOOK FOR:
1. Equipment tags (e.g., RTU-1, VAV-1, S-1, Light A, Panel A)
2. Duct sizes (e.g., 12"x8", 6" diameter)
3. Pipe sizes (e.g., 2" copper, 4" PVC)
4. Fixture counts and types
5. Material callouts (e.g., 5/8" GWB, ACT, VCT)
6. Room names with finish codes
7. Legend items with descriptions

RULES:
1. Extract ONLY items with specific tags/sizes/codes
2. Do NOT extract generic notes or instructions
3. If you see a schedule table, extract every row as a separate item
4. For each item include: description, trade, quantity (if visible), unit
5. Description MUST include tag, size, manufacturer if visible

OUTPUT FORMAT (strict JSON, no markdown):
{"items": [{"description": "RTU-1: Rooftop Unit 5-ton 208V", "trade": "HVAC", "quantity": 1, "unit": "EA", "confidence": 0.85}]}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}",
                                    "detail": "low"  # Cost optimization
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1500,
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            
            # Parse JSON
            import json
            import re
            
            # Find JSON in response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                items_data = result.get("items", [])
                
                line_items = []
                for item in items_data:
                    line_items.append(LineItem(
                        description=item.get("description", ""),
                        trade=item.get("trade", "Other"),
                        quantity=item.get("quantity"),
                        unit=item.get("unit", "EA"),
                        confidence=item.get("confidence", 0.75),
                        source_reference=f"{file_name} (page {page_num})"
                    ))
                
                return line_items
            
        except Exception as e:
            print(f"    Vision page {page_num} error: {e}")
        
        return []
