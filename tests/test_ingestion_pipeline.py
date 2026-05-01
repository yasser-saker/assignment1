"""Tests for the unified ingestion pipeline."""
import io
import tempfile
from pathlib import Path

import pytest
import fitz
from PIL import Image, ImageDraw, ImageFont

from src.ingestion.ingestion_pipeline import IngestionPipeline
from src.ingestion.ocr_engine import OCREngine
from src.models import IngestedFile


class TestIngestionPipeline:
    """Test suite for IngestionPipeline."""

    @pytest.fixture
    def pipeline(self):
        """Default pipeline fixture."""
        return IngestionPipeline()

    @pytest.fixture
    def sample_project_dir(self, tmp_path):
        """Create a temporary project directory with mixed PDFs."""
        project_dir = tmp_path / "TAKEOFF-TEST"
        project_dir.mkdir()
        
        # Create a text-based PDF (spec-like)
        spec_pdf = project_dir / "Project Specifications.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Project Specifications Document")
        page.insert_text((72, 100), "This document contains technical specifications for the construction project.")
        page.insert_text((72, 130), "Materials: Concrete grade C30, Steel reinforcement grade 500B.")
        doc.save(str(spec_pdf))
        doc.close()
        
        # Create a drawing-like PDF (image-only)
        drawing_pdf = project_dir / "Floor Plan Drawing.pdf"
        img = Image.new("RGB", (800, 600), color="white")
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        except Exception:
            font = ImageFont.load_default()
        draw.text((50, 50), "FLOOR PLAN - LEVEL 1", fill="black", font=font)
        draw.text((50, 100), 'Scale: 1/8" = 1\'-0"', fill="black", font=font)
        
        doc = fitz.open()
        page = doc.new_page(width=800, height=600)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        page.insert_image(page.rect, stream=img_bytes.read())
        doc.save(str(drawing_pdf))
        doc.close()
        
        return str(project_dir)

    def test_process_file_text(self, pipeline, tmp_path):
        """Test processing a single text-based PDF."""
        pdf_path = tmp_path / "test.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "This is a specification document with sufficient text content.")
        doc.save(str(pdf_path))
        doc.close()
        
        result = pipeline.process_file(
            file_path=str(pdf_path),
            project_id="TEST-01",
        )
        
        assert isinstance(result, IngestedFile)
        assert result.project_id == "TEST-01"
        assert result.file_type in ["spec", "other", "drawing"]  # classified based on name
        assert len(result.pages) == 1
        assert result.pages[0].is_scanned is False

    def test_process_project(self, pipeline, sample_project_dir):
        """Test processing all files in a project directory."""
        results = pipeline.process_project(
            project_dir=sample_project_dir,
            project_id="TAKEOFF-TEST",
        )
        
        assert isinstance(results, list)
        assert len(results) == 2
        
        # Check classification
        types = {r.file_type for r in results}
        assert "spec" in types or "drawing" in types
        
        # Check OCR stats
        stats = pipeline.get_ocr_stats(results)
        assert stats["total_files"] == 2
        assert stats["total_pages"] == 2
        # The drawing should be OCR'd
        assert stats["scanned_pages"] >= 1

    def test_ocr_stats_empty(self, pipeline):
        """Test stats with no results."""
        stats = pipeline.get_ocr_stats([])
        assert stats["total_files"] == 0
        assert stats["total_pages"] == 0
        assert stats["avg_ocr_confidence"] is None

    def test_file_not_found(self, pipeline):
        """Test handling of missing file."""
        with pytest.raises(FileNotFoundError):
            pipeline.process_file(
                file_path="/nonexistent/missing.pdf",
                project_id="TEST",
            )

    def test_non_pdf_file(self, pipeline, tmp_path):
        """Test handling of non-PDF file."""
        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("Not a PDF")
        
        with pytest.raises(ValueError):
            pipeline.process_file(
                file_path=str(txt_file),
                project_id="TEST",
            )

    def test_custom_ocr_engine(self, sample_project_dir):
        """Test pipeline with custom OCR configuration."""
        custom_ocr = OCREngine(
            lang="eng",
            psm=6,
            dpi=300,
            preprocess=True,
        )
        pipeline = IngestionPipeline(ocr_engine=custom_ocr)
        
        results = pipeline.process_project(
            project_dir=sample_project_dir,
            project_id="TAKEOFF-CUSTOM",
        )
        
        assert len(results) == 2
        # Verify OCR was applied
        stats = pipeline.get_ocr_stats(results)
        assert stats["ocr_pages"] >= 1

    def test_stats_calculation(self, pipeline):
        """Test OCR statistics calculation."""
        from src.models import Page
        ingested1 = IngestedFile(
            file_id="f1",
            project_id="P1",
            file_name="a.pdf",
            file_type="drawing",
            pages=[
                Page(page_number=1, is_scanned=True, ocr_used=True, ocr_confidence=85.5, text="hello"),
                Page(page_number=2, is_scanned=False, ocr_used=False, text="world"),
            ]
        )
        ingested2 = IngestedFile(
            file_id="f2",
            project_id="P1",
            file_name="b.pdf",
            file_type="spec",
            pages=[
                Page(page_number=1, is_scanned=False, ocr_used=False, text="spec text"),
            ]
        )
        
        stats = pipeline.get_ocr_stats([ingested1, ingested2])
        
        assert stats["total_files"] == 2
        assert stats["files_with_ocr"] == 1
        assert stats["total_pages"] == 3
        assert stats["scanned_pages"] == 1
        assert stats["ocr_pages"] == 1
        assert stats["scanned_ratio"] == round(1/3, 4)
        assert stats["ocr_ratio"] == round(1/3, 4)
        assert stats["avg_ocr_confidence"] == 85.5
        assert stats["min_ocr_confidence"] == 85.5
        assert stats["max_ocr_confidence"] == 85.5
