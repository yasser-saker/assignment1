"""OCR engine using Tesseract."""
from typing import Optional
import pytesseract
from PIL import Image


class OCREngine:
    """Performs OCR on images."""

    def extract_text(self, image: Image.Image, lang: str = "eng") -> Tuple[str, float]:
        """Extract text from image and return (text, confidence)."""
        # Get data with confidence scores
        data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
        
        texts = []
        confidences = []
        
        for i, text in enumerate(data["text"]):
            if text.strip():
                texts.append(text)
                confidences.append(int(data["conf"][i]))
        
        full_text = " ".join(texts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return full_text, avg_confidence
