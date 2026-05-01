"""Unified ingestion pipeline for construction project PDFs.

Orchestrates file classification, text extraction, OCR fallback,
and metadata collection into structured IngestedFile objects.
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.ingestion.file_classifier import FileClassifier
from src.ingestion.pdf_extractor import PDFExtractor
from src.ingestion.ocr_engine import OCREngine
from src.ingestion.resource_monitor import ResourceMonitor
from src.ingestion.file_skipper import FileSkipper
from src.models import IngestedFile
from src.config import (
    MIN_TEXT_CHARS_FOR_NON_SCANNED,
    OCR_DPI,
    OCR_AUTO_ENABLED,
    OCR_ON_DRAWINGS_ONLY,
    OCR_DEFAULT_LANG,
    OCR_DEFAULT_PSM,
    OCR_DEFAULT_OEM,
    OCR_PREPROCESS_ENABLED,
    OCR_SHARPEN_ENABLED,
    OCR_CONTRAST_ENHANCE,
    OCR_DESKEW_ENABLED,
)

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """End-to-end ingestion pipeline for construction project files.
    
    Usage:
        pipeline = IngestionPipeline()
        results = pipeline.process_project(project_dir, project_id="TAKEOFF-28")
    """

    def __init__(
        self,
        classifier: Optional[FileClassifier] = None,
        extractor: Optional[PDFExtractor] = None,
        ocr_engine: Optional[OCREngine] = None,
        file_skipper: Optional[FileSkipper] = None,
    ):
        """Initialize pipeline with optional custom components.
        
        Args:
            classifier: FileClassifier instance (default if None)
            extractor: PDFExtractor instance (default if None)
            ocr_engine: OCREngine instance (default if None)
            file_skipper: FileSkipper instance (default if None)
        """
        self.classifier = classifier or FileClassifier()
        self.ocr_engine = ocr_engine or self._build_default_ocr_engine()
        self.file_skipper = file_skipper or FileSkipper()
        self.extractor = extractor or self._build_default_extractor(self.file_skipper)

    @staticmethod
    def _build_default_ocr_engine() -> OCREngine:
        """Build OCR engine from config settings."""
        return OCREngine(
            lang=OCR_DEFAULT_LANG,
            psm=OCR_DEFAULT_PSM,
            oem=OCR_DEFAULT_OEM,
            dpi=OCR_DPI,
            preprocess=OCR_PREPROCESS_ENABLED,
            sharpen=OCR_SHARPEN_ENABLED,
            contrast_enhance=OCR_CONTRAST_ENHANCE,
            deskew=OCR_DESKEW_ENABLED,
        )

    @staticmethod
    def _build_default_extractor(file_skipper: Optional[FileSkipper] = None) -> PDFExtractor:
        """Build PDF extractor from config settings."""
        # We need to build OCR engine first since extractor depends on it
        ocr = IngestionPipeline._build_default_ocr_engine()
        return PDFExtractor(
            min_text_chars=MIN_TEXT_CHARS_FOR_NON_SCANNED,
            ocr_engine=ocr,
            auto_ocr=OCR_AUTO_ENABLED,
            ocr_dpi=OCR_DPI,
            ocr_on_drawings_only=OCR_ON_DRAWINGS_ONLY,
            file_skipper=file_skipper,
        )

    def process_file(
        self,
        file_path: str,
        project_id: str,
        file_id: Optional[str] = None,
    ) -> IngestedFile:
        """Process a single PDF file through the pipeline.
        
        Args:
            file_path: Path to PDF file
            project_id: Project identifier
            file_id: Optional file identifier (defaults to filename stem)
            
        Returns:
            IngestedFile with extracted content
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Only PDF files supported, got: {path.suffix}")
        
        file_name = path.name
        file_id = file_id or path.stem
        
        # Step 1: Classify file
        file_type = self.classifier.classify(file_name)
        logger.info(f"Classified {file_name} as: {file_type}")
        
        # Step 2: Extract with OCR fallback
        ingested = self.extractor.extract(
            pdf_path=file_path,
            project_id=project_id,
            file_id=file_id,
            file_type=file_type,
        )
        
        return ingested

    def process_project(
        self,
        project_dir: str,
        project_id: str,
        file_pattern: str = "*.pdf",
    ) -> List[IngestedFile]:
        """Process all PDF files in a project directory.
        
        Uses adaptive skipping based on system resources and file traits.
        Heavy/scanned files are skipped when system is under pressure.
        
        Args:
            project_dir: Directory containing project PDF files
            project_id: Project identifier
            file_pattern: Glob pattern for matching files
            
        Returns:
            List of IngestedFile objects
        """
        project_path = Path(project_dir)
        if not project_path.exists():
            raise FileNotFoundError(f"Project directory not found: {project_dir}")
        
        # Log system status at start
        monitor = self.file_skipper.monitor
        logger.info(f"=== Ingestion Start === {monitor}")
        
        # Search recursively for PDFs
        pdf_files = sorted(project_path.rglob(file_pattern))
        logger.info(f"Found {len(pdf_files)} PDF files in {project_dir}")
        
        results: List[IngestedFile] = []
        for pdf_file in pdf_files:
            try:
                ingested = self.process_file(
                    file_path=str(pdf_file),
                    project_id=project_id,
                )
                results.append(ingested)
            except Exception as e:
                logger.error(f"Failed to process {pdf_file}: {e}")
        
        # Log summary at end
        self.file_skipper.log_summary()
        logger.info(f"=== Ingestion Complete === {len(results)} files processed")
        
        return results

    def get_ocr_stats(self, results: List[IngestedFile]) -> Dict[str, Any]:
        """Calculate OCR usage statistics from ingestion results.
        
        Args:
            results: List of IngestedFile objects
            
        Returns:
            Dictionary with OCR statistics
        """
        total_pages = 0
        scanned_pages = 0
        ocr_pages = 0
        avg_confidences = []
        files_with_ocr = 0
        
        for ingested in results:
            file_had_ocr = False
            for page in ingested.pages:
                total_pages += 1
                if page.is_scanned:
                    scanned_pages += 1
                if page.ocr_used:
                    ocr_pages += 1
                    file_had_ocr = True
                    if page.ocr_confidence is not None:
                        avg_confidences.append(page.ocr_confidence)
            if file_had_ocr:
                files_with_ocr += 1
        
        return {
            "total_files": len(results),
            "files_with_ocr": files_with_ocr,
            "total_pages": total_pages,
            "scanned_pages": scanned_pages,
            "ocr_pages": ocr_pages,
            "scanned_ratio": round(scanned_pages / total_pages, 4) if total_pages else 0,
            "ocr_ratio": round(ocr_pages / total_pages, 4) if total_pages else 0,
            "avg_ocr_confidence": round(sum(avg_confidences) / len(avg_confidences), 2)
            if avg_confidences else None,
            "min_ocr_confidence": round(min(avg_confidences), 2)
            if avg_confidences else None,
            "max_ocr_confidence": round(max(avg_confidences), 2)
            if avg_confidences else None,
        }
