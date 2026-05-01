"""Tests for PDF extraction with OCR fallback."""
import io
import tempfile
from pathlib import Path

import pytest
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont

from src.ingestion.pdf_extractor import PDFExtractor
from src.ingestion.ocr_engine import OCREngine
from src.models import IngestedFile


class TestPDFExtractor:
    """Test suite for PDFExtractor."""

    @pytest.fixture
    def text_pdf(self):
        """Create a temporary PDF with real text content."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "This is a test PDF with enough text content to pass the threshold easily.")
            page.insert_text((72, 100), "Line two of the document content.")
            doc.save(f.name)
            doc.close()
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def scanned_pdf(self):
        """Create a temporary PDF that simulates a scanned document (image-only)."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            # Create an image with text
            img = Image.new("RGB", (600, 200), color="white")
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
            except Exception:
                font = ImageFont.load_default()
            draw.text((30, 50), "Scanned document text", fill="black", font=font)
            
            # Save as PDF via PyMuPDF
            doc = fitz.open()
            page = doc.new_page(width=600, height=200)
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG")
            img_bytes.seek(0)
            page.insert_image(page.rect, stream=img_bytes.read())
            doc.save(f.name)
            doc.close()
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def extractor_with_ocr(self):
        """PDF extractor with OCR enabled."""
        ocr = OCREngine(preprocess=True, dpi=300)
        return PDFExtractor(
            min_text_chars=50,
            ocr_engine=ocr,
            auto_ocr=True,
            ocr_dpi=300,
        )

    @pytest.fixture
    def extractor_no_ocr(self):
        """PDF extractor with OCR disabled."""
        return PDFExtractor(
            min_text_chars=50,
            auto_ocr=False,
        )

    def test_extract_text_pdf(self, text_pdf, extractor_no_ocr):
        """Test extraction from a text-based PDF."""
        result = extractor_no_ocr.extract(
            pdf_path=text_pdf,
            project_id="TEST-01",
            file_id="text_doc",
        )
        
        assert isinstance(result, IngestedFile)
        assert result.project_id == "TEST-01"
        assert result.file_id == "text_doc"
        assert len(result.pages) == 1
        
        page = result.pages[0]
        assert page.page_number == 1
        assert "test PDF" in page.text
        assert page.is_scanned is False
        assert page.ocr_used is False

    def test_extract_scanned_pdf_with_ocr(self, scanned_pdf, extractor_with_ocr):
        """Test OCR fallback on image-only PDF."""
        result = extractor_with_ocr.extract(
            pdf_path=scanned_pdf,
            project_id="TEST-02",
            file_id="scanned_doc",
        )
        
        assert isinstance(result, IngestedFile)
        assert len(result.pages) == 1
        
        page = result.pages[0]
        assert page.is_scanned is True
        assert page.ocr_used is True
        assert page.ocr_confidence is not None
        assert page.ocr_text is not None
        # OCR should have found something
        assert len(page.text) > 0

    def test_extract_scanned_pdf_no_ocr(self, scanned_pdf, extractor_no_ocr):
        """Test that scanned PDF without OCR returns empty text."""
        result = extractor_no_ocr.extract(
            pdf_path=scanned_pdf,
            project_id="TEST-03",
            file_id="scanned_no_ocr",
        )
        
        page = result.pages[0]
        assert page.is_scanned is True
        assert page.ocr_used is False
        # Without OCR, text from image-only PDF should be minimal
        assert len(page.text) < 50

    def test_file_type_passed_through(self, text_pdf, extractor_no_ocr):
        """Test that file_type is preserved in output."""
        result = extractor_no_ocr.extract(
            pdf_path=text_pdf,
            project_id="TEST",
            file_id="doc",
            file_type="specification",
        )
        assert result.file_type == "specification"

    def test_extract_images(self, text_pdf, extractor_no_ocr):
        """Test rendering PDF pages as images."""
        images = extractor_no_ocr.extract_images(text_pdf, dpi=150)
        
        assert isinstance(images, list)
        assert len(images) == 1
        
        page_num, img = images[0]
        assert page_num == 1
        assert isinstance(img, Image.Image)
        assert img.size[0] > 0
        assert img.size[1] > 0

    def test_extract_images_with_ocr(self, scanned_pdf, extractor_with_ocr):
        """Test rendering + OCR combined method."""
        results = extractor_with_ocr.extract_images_with_ocr(
            scanned_pdf,
            dpi=300,
        )
        
        assert len(results) == 1
        page_num, img, text, confidence = results[0]
        
        assert page_num == 1
        assert isinstance(img, Image.Image)
        assert isinstance(text, str)
        assert isinstance(confidence, float)
        assert confidence >= 0

    def test_pdfplumber_extraction(self, text_pdf, extractor_no_ocr):
        """Test pdfplumber-based extraction."""
        result = extractor_no_ocr.extract_with_pdfplumber(
            pdf_path=text_pdf,
            project_id="TEST",
            file_id="doc",
        )
        
        assert isinstance(result, IngestedFile)
        assert len(result.pages) == 1
        assert "test PDF" in result.pages[0].text

    def test_invalid_file(self, extractor_no_ocr):
        """Test handling of non-existent file."""
        result = extractor_no_ocr.extract(
            pdf_path="/nonexistent/file.pdf",
            project_id="TEST",
            file_id="bad",
        )
        
        # Should return error page, not crash
        assert len(result.pages) == 1
        assert result.pages[0].text == ""

    def test_non_pdf_file(self, extractor_no_ocr, tmp_path):
        """Test handling of non-PDF file."""
        bad_file = tmp_path / "not_a_pdf.txt"
        bad_file.write_text("This is not a PDF")
        
        result = extractor_no_ocr.extract(
            pdf_path=str(bad_file),
            project_id="TEST",
            file_id="bad",
        )
        
        # PyMuPDF may or may not open it; just ensure no crash
        assert isinstance(result, IngestedFile)
