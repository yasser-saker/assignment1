"""OCR engine using Tesseract with full image preprocessing support."""
import io
import logging
from typing import List, Tuple, Optional, Dict, Any

import numpy as np
import pytesseract
from PIL import Image, ImageFilter, ImageEnhance, ImageOps

logger = logging.getLogger(__name__)


class OCREngine:
    """Performs OCR on images with preprocessing options.
    
    Supports multiple Tesseract page segmentation modes (PSM) and
    OCR engine modes (OEM), image preprocessing, and structured
    data extraction with bounding boxes.
    """

    # Tesseract Page Segmentation Modes
    PSM_AUTO = 3              # Fully automatic page segmentation
    PSM_SINGLE_COLUMN = 4     # Assume a single column of text
    PSM_SINGLE_BLOCK = 6      # Assume a single uniform block of text
    PSM_SINGLE_LINE = 7       # Treat image as a single text line
    PSM_SINGLE_WORD = 8       # Treat image as a single word
    PSM_SPARSE_TEXT = 11      # Find as much text as possible
    PSM_SPARSE_TEXT_OSD = 12  # Sparse text with orientation/script detection
    PSM_RAW_LINE = 13         # Raw line (best for preserving layout)

    # Tesseract OCR Engine Modes
    OEM_LSTM_ONLY = 1         # Neural nets LSTM engine only
    OEM_TESSERACT_LSTM = 3    # Default, based on what is available

    def __init__(
        self,
        lang: str = "eng",
        psm: int = PSM_AUTO,
        oem: int = OEM_TESSERACT_LSTM,
        dpi: int = 300,
        preprocess: bool = True,
        sharpen: bool = True,
        contrast_enhance: float = 1.5,
        deskew: bool = False,
    ):
        """Initialize OCR engine.
        
        Args:
            lang: Tesseract language code(s), e.g. "eng", "eng+ara"
            psm: Page segmentation mode (see PSM_* constants)
            oem: OCR engine mode (see OEM_* constants)
            dpi: Target DPI for image rendering/rescaling
            preprocess: Whether to apply image preprocessing pipeline
            sharpen: Whether to apply sharpening filter
            contrast_enhance: Contrast enhancement factor (1.0 = no change)
            deskew: Whether to attempt deskewing (requires numpy/skimage)
        """
        self.lang = lang
        self.psm = psm
        self.oem = oem
        self.dpi = dpi
        self.preprocess = preprocess
        self.sharpen = sharpen
        self.contrast_enhance = contrast_enhance
        self.deskew = deskew
        self.config = f"--psm {psm} --oem {oem}"

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Apply preprocessing pipeline to improve OCR accuracy.
        
        Steps:
            1. Convert to grayscale
            2. Resize to target DPI if needed
            3. Enhance contrast
            4. Apply sharpening
            5. Denoise with median filter
            6. Adaptive thresholding (Otsu-like)
        """
        img = image.convert("L")  # Grayscale
        
        # Resize to target DPI if image is very small or very large
        orig_dpi = img.info.get("dpi", (72, 72))
        if isinstance(orig_dpi, tuple):
            orig_dpi = orig_dpi[0]
        
        if orig_dpi < self.dpi * 0.8 or orig_dpi > self.dpi * 1.5:
            scale = self.dpi / max(orig_dpi, 1)
            new_size = (int(img.width * scale), int(img.height * scale))
            # Limit max dimension to avoid memory issues
            max_dim = 4000
            if max(new_size) > max_dim:
                ratio = max_dim / max(new_size)
                new_size = (int(new_size[0] * ratio), int(new_size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Enhance contrast
        if self.contrast_enhance != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(self.contrast_enhance)
        
        # Sharpen
        if self.sharpen:
            img = img.filter(ImageFilter.SHARPEN)
        
        # Median filter for noise reduction (light)
        img = img.filter(ImageFilter.MedianFilter(size=3))
        
        # Adaptive thresholding using point operation
        # This is a simple Otsu-like approach using PIL
        img_array = np.array(img)
        
        # Apply local thresholding if image is large enough
        if img_array.size > 10000:
            # Simple adaptive threshold: if pixel > mean, set to white, else black
            mean_val = np.mean(img_array)
            # Use a slightly lower threshold to preserve faint text
            threshold = mean_val * 0.85
            img_array = np.where(img_array > threshold, 255, 0).astype(np.uint8)
            img = Image.fromarray(img_array, mode="L")
        
        # Deskew if enabled
        if self.deskew:
            img = self._deskew_image(img)
        
        return img

    def _deskew_image(self, image: Image.Image) -> Image.Image:
        """Attempt to deskew an image using projection profile.
        
        Returns the original image if deskewing fails.
        """
        try:
            img_array = np.array(image)
            # Coarse search for best angle
            angles = np.arange(-5, 5.5, 0.5)
            best_angle = 0.0
            best_score = -1
            
            for angle in angles:
                rotated = self._rotate_image(img_array, angle)
                # Score based on variance of row sums (text lines create peaks)
                row_sums = np.sum(rotated < 128, axis=1)  # Count dark pixels per row
                score = np.var(row_sums)
                if score > best_score:
                    best_score = score
                    best_angle = angle
            
            if abs(best_angle) > 0.25:
                rotated_array = self._rotate_image(img_array, best_angle)
                return Image.fromarray(rotated_array, mode="L")
        except Exception as e:
            logger.warning(f"Deskewing failed: {e}")
        
        return image

    @staticmethod
    def _rotate_image(image_array: np.ndarray, angle: float) -> np.ndarray:
        """Rotate a grayscale image array by given angle in degrees."""
        from scipy import ndimage
        return ndimage.rotate(image_array, angle, reshape=False, order=1, mode='constant', cval=255)

    def extract_text(self, image: Image.Image, lang: Optional[str] = None) -> Tuple[str, float]:
        """Extract text from image and return (text, avg_confidence).
        
        Args:
            image: PIL Image
            lang: Override language for this call
            
        Returns:
            Tuple of (extracted_text, average_confidence)
        """
        if image is None:
            return "", 0.0
        
        target_lang = lang or self.lang
        
        try:
            if self.preprocess:
                processed = self._preprocess_image(image)
            else:
                processed = image.convert("L")
            
            # Get data with confidence scores
            data = pytesseract.image_to_data(
                processed,
                lang=target_lang,
                config=self.config,
                output_type=pytesseract.Output.DICT,
            )
            
            texts = []
            confidences = []
            
            for i, text in enumerate(data["text"]):
                if text and text.strip() and int(data["conf"][i]) > 0:
                    texts.append(text)
                    confidences.append(int(data["conf"][i]))
            
            full_text = "\n".join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return full_text, avg_confidence
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return "", 0.0

    def extract_structured(
        self, image: Image.Image, lang: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Extract structured OCR data with bounding boxes.
        
        Returns a list of word/line entries with:
            - text: extracted text
            - conf: confidence (0-100)
            - bbox: {left, top, width, height}
            - line_num: line number in block
            - block_num: block number
            - par_num: paragraph number
            
        Args:
            image: PIL Image
            lang: Override language for this call
            
        Returns:
            List of word dictionaries
        """
        if image is None:
            return []
        
        target_lang = lang or self.lang
        
        try:
            if self.preprocess:
                processed = self._preprocess_image(image)
            else:
                processed = image.convert("L")
            
            data = pytesseract.image_to_data(
                processed,
                lang=target_lang,
                config=self.config,
                output_type=pytesseract.Output.DICT,
            )
            
            words = []
            n_boxes = len(data["text"])
            
            for i in range(n_boxes):
                conf = int(data["conf"][i])
                text = data["text"][i]
                if text and text.strip() and conf > 0:
                    words.append({
                        "text": text,
                        "conf": conf,
                        "bbox": {
                            "left": data["left"][i],
                            "top": data["top"][i],
                            "width": data["width"][i],
                            "height": data["height"][i],
                        },
                        "line_num": data["line_num"][i],
                        "block_num": data["block_num"][i],
                        "par_num": data["par_num"][i],
                        "page_num": data["page_num"][i],
                    })
            
            return words
            
        except Exception as e:
            logger.error(f"Structured OCR extraction failed: {e}")
            return []

    def extract_text_with_layout(
        self, image: Image.Image, lang: Optional[str] = None
    ) -> Tuple[str, float, List[Dict[str, Any]]]:
        """Extract text, confidence, and structured layout data in one pass.
        
        Returns:
            Tuple of (text, avg_confidence, structured_words)
        """
        structured = self.extract_structured(image, lang)
        
        if not structured:
            return "", 0.0, []
        
        # Reconstruct text with line breaks based on line_num
        lines = {}
        confidences = []
        
        for word in structured:
            line_key = (word["block_num"], word["par_num"], word["line_num"])
            if line_key not in lines:
                lines[line_key] = []
            lines[line_key].append(word["text"])
            confidences.append(word["conf"])
        
        # Sort by block, paragraph, line and join
        sorted_lines = [
            " ".join(lines[key]) 
            for key in sorted(lines.keys())
        ]
        full_text = "\n".join(sorted_lines)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return full_text, avg_confidence, structured

    def ocr_pdf_page(
        self, page_image: Image.Image, 
        page_number: int = 0,
        file_name: str = ""
    ) -> Dict[str, Any]:
        """Run complete OCR on a single PDF page image.
        
        Returns a result dictionary compatible with the ingestion pipeline.
        """
        text, confidence, structured = self.extract_text_with_layout(page_image)
        
        result = {
            "page_number": page_number,
            "text": text,
            "ocr_confidence": round(confidence, 2),
            "ocr_words": len(structured),
            "ocr_used": True,
            "is_scanned": True,
        }
        
        if not text.strip():
            logger.warning(
                f"OCR produced no text for page {page_number} of {file_name}"
            )
        else:
            logger.info(
                f"OCR page {page_number} of {file_name}: "
                f"{len(structured)} words, confidence={confidence:.1f}%"
            )
        
        return result

    def get_tesseract_info(self) -> Dict[str, Any]:
        """Return information about the Tesseract installation."""
        try:
            version = pytesseract.get_tesseract_version()
            languages = pytesseract.get_languages()
            return {
                "version": str(version),
                "languages": languages,
                "config": self.config,
                "lang": self.lang,
                "dpi": self.dpi,
            }
        except Exception as e:
            return {"error": str(e)}
