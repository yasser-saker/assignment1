"""Smart Region OCR: Detects text regions in drawings and runs focused OCR.

Strategy:
1. Detect text blobs using OpenCV contours
2. Filter by size/aspect ratio
3. Classify regions (schedule, legend, notes, callouts)
4. Run Tesseract OCR on each crop with higher DPI
5. Fallback to GPT-4o-mini for low-confidence regions
6. Return merged text with source annotations
"""
import io
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image
import cv2
import fitz


@dataclass
class TextRegion:
    x1: int
    y1: int
    x2: int
    y2: int
    region_type: str  # schedule, legend, notes, title_block, callout, general
    confidence: float = 0.0
    text: str = ""
    ocr_confidence: float = 0.0


class SmartRegionOCR:
    """Extract text from scanned drawings using smart region detection."""
    
    # Region classification keywords
    SCHEDULE_KEYWORDS = [
        'schedule', 'legend', 'fixture', 'equipment', 'door', 'finish',
        'panel', 'diffuser', 'lighting', 'symbol'
    ]
    NOTES_KEYWORDS = [
        'notes', 'general notes', 'drawing notes', 'specifications',
        'provide', 'install', 'furnish', 'contractor shall'
    ]
    CALLOUT_KEYWORDS = [
        'detail', 'section', 'typical', 'refer to', 'see plan',
        'nt.s', 'n.t.s', 'scale'
    ]
    
    def __init__(
        self,
        min_crop_width: int = 80,
        min_crop_height: int = 20,
        max_crop_width: int = 2000,
        max_crop_height: int = 800,
        ocr_dpi: int = 200,
        confidence_threshold: float = 60.0,
        gpt_fallback: bool = True,
    ):
        self.min_crop_width = min_crop_width
        self.min_crop_height = min_crop_height
        self.max_crop_width = max_crop_width
        self.max_crop_height = max_crop_height
        self.ocr_dpi = ocr_dpi
        self.confidence_threshold = confidence_threshold
        self.gpt_fallback = gpt_fallback
        self.gpt_client = None
        if gpt_fallback:
            self._init_gpt()
    
    def _init_gpt(self):
        """Initialize GPT-4o-mini client for fallback."""
        try:
            import openai
            import os
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                self.gpt_client = openai.OpenAI(api_key=api_key)
        except ImportError:
            pass
    
    def extract_from_page(self, page: fitz.Page, page_num: int = 0) -> Dict:
        """Extract text from a single PDF page using smart regions.
        
        Returns dict with:
        - text: combined extracted text
        - regions: list of TextRegion objects
        - ocr_stats: {total_regions, high_confidence, low_confidence, gpt_used}
        """
        # Render page to image at working DPI
        pix = page.get_pixmap(dpi=self.ocr_dpi)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        img_gray = img.convert("L")
        img_np = np.array(img_gray)
        
        # Detect text regions
        regions = self._detect_regions(img_np)
        
        # Classify regions
        regions = self._classify_regions(regions, img_np)
        
        # Run OCR on each region
        regions = self._ocr_regions(regions, img)
        
        # GPT fallback for low-confidence regions
        if self.gpt_fallback and self.gpt_client:
            regions = self._gpt_fallback(regions, img)
        
        # Build combined text
        lines = []
        for r in regions:
            if r.text.strip():
                lines.append(f"[{r.region_type.upper()}]: {r.text.strip()}")
        
        combined_text = "\n".join(lines)
        
        stats = {
            "total_regions": len(regions),
            "high_confidence": sum(1 for r in regions if r.ocr_confidence >= self.confidence_threshold),
            "low_confidence": sum(1 for r in regions if 0 < r.ocr_confidence < self.confidence_threshold),
            "gpt_used": sum(1 for r in regions if r.confidence >= 90 and r.ocr_confidence < self.confidence_threshold),
        }
        
        return {
            "text": combined_text,
            "regions": regions,
            "ocr_stats": stats,
        }
    
    def _detect_regions(self, img_np: np.ndarray) -> List[TextRegion]:
        """Detect text regions using OpenCV contours."""
        # Adaptive threshold to handle varying backgrounds
        binary = cv2.adaptiveThreshold(
            img_np, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 15, 10
        )
        
        # Dilate to connect nearby text
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
        dilated = cv2.dilate(binary, kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        regions = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            
            # Filter by size
            if w < self.min_crop_width or h < self.min_crop_height:
                continue
            if w > self.max_crop_width or h > self.max_crop_height:
                continue
            
            # Filter by aspect ratio (text is usually wider than tall)
            aspect = w / h if h > 0 else 0
            if aspect < 0.3 or aspect > 15:
                continue
            
            # Filter by fill ratio (text has moderate fill)
            area = cv2.contourArea(cnt)
            bbox_area = w * h
            fill_ratio = area / bbox_area if bbox_area > 0 else 0
            if fill_ratio < 0.05 or fill_ratio > 0.9:
                continue
            
            regions.append(TextRegion(x1=x, y1=y, x2=x+w, y2=y+h, region_type="general"))
        
        # Merge overlapping regions
        regions = self._merge_overlapping_regions(regions)
        
        return regions
    
    def _merge_overlapping_regions(self, regions: List[TextRegion], overlap_threshold: float = 0.3) -> List[TextRegion]:
        """Merge regions that overlap significantly."""
        if not regions:
            return regions
        
        # Sort by y then x
        regions.sort(key=lambda r: (r.y1, r.x1))
        
        merged = []
        current = regions[0]
        
        for r in regions[1:]:
            # Calculate overlap
            x_overlap = max(0, min(current.x2, r.x2) - max(current.x1, r.x1))
            y_overlap = max(0, min(current.y2, r.y2) - max(current.y1, r.y1))
            overlap_area = x_overlap * y_overlap
            
            current_area = (current.x2 - current.x1) * (current.y2 - current.y1)
            r_area = (r.x2 - r.x1) * (r.y2 - r.y1)
            min_area = min(current_area, r_area)
            
            if min_area > 0 and overlap_area / min_area > overlap_threshold:
                # Merge
                current = TextRegion(
                    x1=min(current.x1, r.x1),
                    y1=min(current.y1, r.y1),
                    x2=max(current.x2, r.x2),
                    y2=max(current.y2, r.y2),
                    region_type=current.region_type,
                )
            else:
                merged.append(current)
                current = r
        
        merged.append(current)
        return merged
    
    def _classify_regions(self, regions: List[TextRegion], img_np: np.ndarray) -> List[TextRegion]:
        """Classify each region by type based on position and content."""
        h, w = img_np.shape
        
        for r in regions:
            # Position-based heuristics
            center_x = (r.x1 + r.x2) / 2
            center_y = (r.y1 + r.y2) / 2
            
            # Title block: bottom right corner
            if center_y > h * 0.85 and center_x > w * 0.6:
                r.region_type = "title_block"
                continue
            
            # Schedules/Legends: usually right side or top
            if (center_x > w * 0.6 and r.y2 - r.y1 > h * 0.1) or r.y2 - r.y1 > h * 0.3:
                r.region_type = "schedule"
                continue
            
            # Notes: usually top left or bottom left
            if center_y < h * 0.3 and center_x < w * 0.5:
                r.region_type = "notes"
                continue
            
            # General callouts: scattered
            r.region_type = "callout"
        
        return regions
    
    def _ocr_regions(self, regions: List[TextRegion], img: Image.Image) -> List[TextRegion]:
        """Run Tesseract OCR on each region."""
        import pytesseract
        
        for r in regions:
            # Crop region
            crop = img.crop((r.x1, r.y1, r.x2, r.y2))
            
            # Convert to numpy for Tesseract
            crop_np = np.array(crop.convert("L"))
            
            # Run OCR with data for confidence
            try:
                data = pytesseract.image_to_data(
                    crop_np,
                    config='--psm 6',
                    output_type=pytesseract.Output.DICT
                )
                
                # Calculate average confidence
                confidences = [int(c) for c in data['conf'] if int(c) > 0]
                avg_conf = sum(confidences) / len(confidences) if confidences else 0
                
                # Extract text
                words = [w for w, c in zip(data['text'], data['conf']) if int(c) > 0 and w.strip()]
                text = " ".join(words)
                
                r.text = text
                r.ocr_confidence = avg_conf
                
            except Exception as e:
                r.text = ""
                r.ocr_confidence = 0
        
        return regions
    
    def _gpt_fallback(self, regions: List[TextRegion], img: Image.Image) -> List[TextRegion]:
        """Use GPT-4o-mini for low-confidence regions."""
        if not self.gpt_client:
            return regions
        
        low_conf_regions = [r for r in regions if 0 < r.ocr_confidence < self.confidence_threshold and len(r.text) < 20]
        
        # Limit to max 10 regions per page to control cost
        low_conf_regions = low_conf_regions[:10]
        
        for r in low_conf_regions:
            crop = img.crop((r.x1, r.y1, r.x2, r.y2))
            
            # Convert to base64
            import base64
            buffer = io.BytesIO()
            crop.save(buffer, format="JPEG", quality=70)
            img_b64 = base64.b64encode(buffer.getvalue()).decode()
            
            try:
                response = self.gpt_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Read the text in this image. Output ONLY the text, nothing else. If no readable text, output 'NONE'."},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                            ]
                        }
                    ],
                    max_tokens=100,
                    temperature=0.0,
                )
                
                result = response.choices[0].message.content.strip()
                if result and result != "NONE":
                    r.text = result
                    r.confidence = 95  # High confidence from GPT
                    
            except Exception as e:
                # GPT failed, keep Tesseract result
                pass
        
        return regions


def extract_text_from_scanned_page(page: fitz.Page, page_num: int = 0, use_smart_ocr: bool = True) -> Dict:
    """Helper function to extract text from a scanned page.
    
    Args:
        page: PyMuPDF page object
        page_num: Page number for logging
        use_smart_ocr: Whether to use SmartRegionOCR or fallback to basic OCR
        
    Returns:
        Dict with text, regions, and stats
    """
    if not use_smart_ocr:
        # Fallback to basic OCR
        pix = page.get_pixmap(dpi=150)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        import pytesseract
        text = pytesseract.image_to_string(img, config='--psm 6')
        return {"text": text, "regions": [], "ocr_stats": {}}
    
    extractor = SmartRegionOCR()
    return extractor.extract_from_page(page, page_num)
