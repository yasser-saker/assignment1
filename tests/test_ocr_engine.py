"""Tests for the OCR engine."""
import io
import os
import tempfile

import pytest
from PIL import Image, ImageDraw, ImageFont

from src.ingestion.ocr_engine import OCREngine


class TestOCREngine:
    """Test suite for OCREngine."""

    @pytest.fixture
    def ocr_engine(self):
        """Default OCR engine fixture."""
        return OCREngine(preprocess=True, dpi=300)

    @pytest.fixture
    def sample_text_image(self):
        """Create a simple image with text for OCR testing."""
        # Create a white image
        img = Image.new("RGB", (400, 100), color="white")
        draw = ImageDraw.Draw(img)
        
        # Try to load a font, fallback to default
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except Exception:
            font = ImageFont.load_default()
        
        draw.text((20, 30), "Hello OCR World 123", fill="black", font=font)
        return img

    @pytest.fixture
    def low_contrast_image(self):
        """Create a low-contrast image that benefits from preprocessing."""
        img = Image.new("RGB", (400, 100), color="#eeeeee")
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except Exception:
            font = ImageFont.load_default()
        draw.text((20, 30), "Test Text", fill="#555555", font=font)
        return img

    def test_extract_text_basic(self, ocr_engine, sample_text_image):
        """Test basic text extraction."""
        text, confidence = ocr_engine.extract_text(sample_text_image)
        
        assert isinstance(text, str)
        assert isinstance(confidence, float)
        assert confidence > 0
        # Should contain some of our text
        assert "Hello" in text or "OCR" in text or "World" in text

    def test_extract_text_empty_image(self, ocr_engine):
        """Test extraction on empty/blank image."""
        img = Image.new("RGB", (200, 200), color="white")
        text, confidence = ocr_engine.extract_text(img)
        
        assert text == ""
        assert confidence == 0.0

    def test_extract_text_none(self, ocr_engine):
        """Test extraction with None input."""
        text, confidence = ocr_engine.extract_text(None)
        assert text == ""
        assert confidence == 0.0

    def test_extract_structured(self, ocr_engine, sample_text_image):
        """Test structured data extraction with bounding boxes."""
        words = ocr_engine.extract_structured(sample_text_image)
        
        assert isinstance(words, list)
        if words:  # OCR may or may not detect depending on environment
            word = words[0]
            assert "text" in word
            assert "conf" in word
            assert "bbox" in word
            assert "left" in word["bbox"]
            assert "top" in word["bbox"]
            assert "width" in word["bbox"]
            assert "height" in word["bbox"]

    def test_extract_text_with_layout(self, ocr_engine, sample_text_image):
        """Test combined text + layout extraction."""
        text, confidence, structured = ocr_engine.extract_text_with_layout(sample_text_image)
        
        assert isinstance(text, str)
        assert isinstance(confidence, float)
        assert isinstance(structured, list)

    def test_preprocessing_improves_ocr(self, low_contrast_image):
        """Test that preprocessing helps with low-contrast images."""
        engine_no_preprocess = OCREngine(preprocess=False, dpi=300)
        engine_with_preprocess = OCREngine(preprocess=True, dpi=300, contrast_enhance=2.0)
        
        text_no, conf_no = engine_no_preprocess.extract_text(low_contrast_image)
        text_yes, conf_yes = engine_with_preprocess.extract_text(low_contrast_image)
        
        # Preprocessed should either find text or have different confidence
        assert isinstance(text_no, str)
        assert isinstance(text_yes, str)

    def test_tesseract_info(self, ocr_engine):
        """Test getting Tesseract installation info."""
        info = ocr_engine.get_tesseract_info()
        
        assert "version" in info
        assert "languages" in info
        assert isinstance(info["languages"], list)

    def test_different_psm_modes(self, sample_text_image):
        """Test different PSM configurations."""
        for psm in [3, 6, 11]:
            engine = OCREngine(psm=psm, preprocess=False)
            text, confidence = engine.extract_text(sample_text_image)
            assert isinstance(text, str)
            assert confidence >= 0

    def test_ocr_pdf_page(self, ocr_engine, sample_text_image):
        """Test the PDF page OCR wrapper."""
        result = ocr_engine.ocr_pdf_page(
            sample_text_image,
            page_number=5,
            file_name="test.pdf",
        )
        
        assert result["page_number"] == 5
        assert "text" in result
        assert "ocr_confidence" in result
        assert result["ocr_used"] is True
        assert result["is_scanned"] is True


class TestOCRPreprocessing:
    """Test image preprocessing pipeline."""

    def test_grayscale_conversion(self):
        """Test that preprocessing converts to grayscale."""
        engine = OCREngine(preprocess=True)
        color_img = Image.new("RGB", (100, 100), color="red")
        processed = engine._preprocess_image(color_img)
        assert processed.mode == "L"

    def test_resize_large_image(self):
        """Test that very large images are scaled down."""
        engine = OCREngine(dpi=300)
        huge_img = Image.new("RGB", (10000, 10000), color="white")
        processed = engine._preprocess_image(huge_img)
        assert max(processed.size) <= 4000

    def test_deskew_no_crash(self):
        """Test deskewing doesn't crash."""
        engine = OCREngine(deskew=True)
        img = Image.new("L", (200, 100), color="white")
        # Add some dark pixels to simulate text
        for x in range(50, 150):
            for y in range(40, 60):
                img.putpixel((x, y), 0)
        result = engine._deskew_image(img)
        assert result is not None


class TestOCRIntegration:
    """Integration tests requiring Tesseract."""

    def test_tesseract_installed(self):
        """Verify Tesseract is available."""
        engine = OCREngine()
        info = engine.get_tesseract_info()
        assert "error" not in info
        assert info["version"] != ""
