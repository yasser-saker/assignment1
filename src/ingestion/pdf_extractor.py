"""PDF text and image extraction using pdfplumber, PyMuPDF, and Tesseract OCR."""
import io
import logging
from pathlib import Path
from typing import List, Tuple, Optional

import pdfplumber
import fitz  # PyMuPDF
from PIL import Image

# Construction drawings can be very large; raise PIL's decompression limit
Image.MAX_IMAGE_PIXELS = None

from src.models import Page, IngestedFile
from src.ingestion.ocr_engine import OCREngine
from src.ingestion.fast_ocr import FastOCRWithGPTFallback
from src.ingestion.ocr_post_processor import OCRPostProcessor
from src.ingestion.parallel_ocr import ParallelOCR
from src.ingestion.chunked_ocr import ChunkedOCR

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extracts text, images, and metadata from PDF files with OCR fallback.
    
    Automatically detects scanned pages (low text content) and runs OCR
    to extract text from rendered page images.
    """

    def __init__(
        self,
        min_text_chars: int = 50,
        ocr_engine: Optional[OCREngine] = None,
        auto_ocr: bool = True,
        ocr_dpi: int = 300,
        ocr_on_drawings_only: bool = False,
    ):
        """Initialize PDF extractor.
        
        Args:
            min_text_chars: Minimum characters to consider a page as non-scanned
            ocr_engine: OCREngine instance (created with defaults if None)
            auto_ocr: Whether to automatically OCR scanned pages
            ocr_dpi: DPI for rendering pages to images when OCR is needed
            ocr_on_drawings_only: If True, only OCR pages from drawing files
        """
        self.min_text_chars = min_text_chars
        self.ocr_engine = ocr_engine or OCREngine()
        self.auto_ocr = auto_ocr
        self.ocr_dpi = ocr_dpi
        self.ocr_on_drawings_only = ocr_on_drawings_only
        self.post_processor = OCRPostProcessor()
        self.parallel_ocr = ParallelOCR(max_workers=4)
        self.chunked_ocr = ChunkedOCR(chunk_size=10, max_workers=4)

    def extract(
        self,
        pdf_path: str,
        project_id: str,
        file_id: str,
        file_type: str = "unknown",
    ) -> IngestedFile:
        """Extract text from all pages of a PDF with automatic OCR fallback.
        
        Uses PyMuPDF for fast text extraction, then renders pages to images
        and runs OCR for pages with insufficient text (scanned pages).
        
        Args:
            pdf_path: Path to PDF file
            project_id: Project identifier
            file_id: File identifier
            file_type: File type classification (drawing, spec, etc.)
            
        Returns:
            IngestedFile with extracted pages
        """
        path = Path(pdf_path)
        file_name = path.name
        pages: List[Page] = []
        
        # Determine if this file should get OCR treatment
        should_ocr = self.auto_ocr
        if self.ocr_on_drawings_only and file_type != "drawing":
            should_ocr = False
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            # First pass: identify scanned pages and collect their images
            scanned_pages = []  # (page_num, text_stripped, image)
            page_data = []      # (page_num, text_stripped, is_scanned)
            
            for i in range(total_pages):
                page_num = i + 1
                page = doc.load_page(i)
                
                # Fast text extraction
                text = page.get_text()
                text_stripped = text.strip()
                is_scanned = len(text_stripped) < self.min_text_chars
                page_data.append((page_num, text_stripped, is_scanned))
                
                if is_scanned and should_ocr:
                    # Render page to image
                    dpi = self.ocr_dpi
                    rect = page.rect
                    w_in = rect.width / 72
                    h_in = rect.height / 72
                    approx_pixels = (w_in * dpi) * (h_in * dpi)
                    max_pixels = 8_000_000
                    if approx_pixels > max_pixels:
                        dpi = int((max_pixels / (w_in * h_in)) ** 0.5)
                        dpi = max(dpi, 72)
                    
                    pix = page.get_pixmap(dpi=dpi)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    img = img.convert("L")
                    if img.width > 3000:
                        ratio = 3000 / img.width
                        new_size = (3000, int(img.height * ratio))
                        img = img.resize(new_size, Image.LANCZOS)
                    
                    scanned_pages.append((page_num, text_stripped, img))
            
            # Second pass: chunked parallel OCR on all scanned pages
            ocr_results = {}
            if scanned_pages and should_ocr:
                logger.info(
                    f"Running chunked parallel OCR on {len(scanned_pages)}/{total_pages} pages of {file_name}"
                )
                import tempfile
                checkpoint_path = tempfile.mktemp(suffix='_ocr_checkpoint.json')
                chunk_results = self.chunked_ocr.process_pages_with_checkpoint(
                    [(p[0], p[2]) for p in scanned_pages],
                    checkpoint_path=checkpoint_path,
                )
                for result in chunk_results:
                    ocr_results[result['page_number']] = result
            
            # Third pass: build Page objects
            for page_num, text_stripped, is_scanned in page_data:
                ocr_text = ""
                ocr_confidence = None
                ocr_used = False
                
                if is_scanned and page_num in ocr_results:
                    result = ocr_results[page_num]
                    ocr_text = result['text']
                    ocr_confidence = result['confidence']
                    ocr_used = True
                    
                    if text_stripped:
                        combined_text = f"{text_stripped}\n{ocr_text}".strip()
                    else:
                        combined_text = ocr_text
                    
                    # Post-process OCR text
                    if combined_text:
                        combined_text = self.post_processor.process_text(combined_text)
                else:
                    combined_text = text_stripped
                
                pages.append(Page(
                    page_number=page_num,
                    text=combined_text,
                    is_scanned=is_scanned,
                    ocr_confidence=ocr_confidence,
                    ocr_used=ocr_used,
                    ocr_text=ocr_text if ocr_used else None,
                ))
                
            doc.close()
            
            logger.info(
                f"Extracted {len(pages)} pages from {file_name} "
                f"({sum(1 for p in pages if p.is_scanned)} scanned, "
                f"{sum(1 for p in pages if p.ocr_used)} OCR'd)"
            )
            
        except Exception as e:
            logger.error(f"Could not process {file_name}: {e}")
            pages.append(Page(
                page_number=1,
                text="",
                is_scanned=False,
                ocr_used=False,
            ))

        return IngestedFile(
            file_id=file_id,
            project_id=project_id,
            file_name=file_name,
            file_path=pdf_path,
            file_type=file_type,
            pages=pages,
        )

    def extract_with_pdfplumber(
        self,
        pdf_path: str,
        project_id: str,
        file_id: str,
        file_type: str = "unknown",
    ) -> IngestedFile:
        """Extract text using pdfplumber (better for tables) with OCR fallback.
        
        Args:
            pdf_path: Path to PDF file
            project_id: Project identifier
            file_id: File identifier
            file_type: File type classification
            
        Returns:
            IngestedFile with extracted pages
        """
        path = Path(pdf_path)
        file_name = path.name
        pages: List[Page] = []
        
        should_ocr = self.auto_ocr
        if self.ocr_on_drawings_only and file_type != "drawing":
            should_ocr = False
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                
                # Open PyMuPDF for image rendering if OCR needed
                doc = fitz.open(pdf_path) if should_ocr else None
                
                for i, pdf_page in enumerate(pdf.pages, start=1):
                    text = pdf_page.extract_text() or ""
                    text_stripped = text.strip()
                    is_scanned = len(text_stripped) < self.min_text_chars
                    
                    ocr_text = ""
                    ocr_confidence = None
                    ocr_used = False
                    
                    if is_scanned and should_ocr and doc:
                        try:
                            logger.info(
                                f"OCR triggered for page {i}/{total_pages} of {file_name}"
                            )
                            page = doc.load_page(i - 1)
                            dpi = self.ocr_dpi
                            rect = page.rect
                            w_in = rect.width / 72
                            h_in = rect.height / 72
                            approx_pixels = (w_in * dpi) * (h_in * dpi)
                            max_pixels = 40_000_000
                            if approx_pixels > max_pixels:
                                dpi = int((max_pixels / (w_in * h_in)) ** 0.5)
                                dpi = max(dpi, 72)
                                logger.info(
                                    f"Page {i} too large ({approx_pixels:,.0f} px), "
                                    f"reducing OCR DPI to {dpi}"
                                )
                            pix = page.get_pixmap(dpi=dpi)
                            img = Image.open(io.BytesIO(pix.tobytes("png")))
                            
                            ocr_result = self.ocr_engine.ocr_pdf_page(
                                img,
                                page_number=i,
                                file_name=file_name,
                            )
                            
                            ocr_text = ocr_result["text"]
                            ocr_confidence = ocr_result["ocr_confidence"]
                            ocr_used = True
                            
                            if text_stripped:
                                combined_text = f"{text_stripped}\n{ocr_text}".strip()
                            else:
                                combined_text = ocr_text
                            
                            # Post-process OCR text to fix spelling errors
                            if ocr_used and combined_text:
                                combined_text = self.post_processor.process_text(combined_text)
                                
                        except Exception as ocr_err:
                            logger.error(
                                f"OCR failed for page {i} of {file_name}: {ocr_err}"
                            )
                            combined_text = text_stripped
                    else:
                        combined_text = text_stripped
                    
                    pages.append(Page(
                        page_number=i,
                        text=combined_text,
                        is_scanned=is_scanned,
                        ocr_confidence=ocr_confidence,
                        ocr_used=ocr_used,
                        ocr_text=ocr_text if ocr_used else None,
                    ))
                
                if doc:
                    doc.close()
                    
        except Exception as e:
            logger.error(f"pdfplumber extraction failed for {file_name}: {e}")
            pages.append(Page(
                page_number=1,
                text="",
                is_scanned=False,
                ocr_used=False,
            ))

        return IngestedFile(
            file_id=file_id,
            project_id=project_id,
            file_name=file_name,
            file_path=pdf_path,
            file_type=file_type,
            pages=pages,
        )

    def extract_images(
        self,
        pdf_path: str,
        dpi: int = 200,
        page_numbers: Optional[List[int]] = None,
    ) -> List[Tuple[int, Image.Image]]:
        """Render PDF pages as images using PyMuPDF.
        
        Args:
            pdf_path: Path to PDF file
            dpi: Resolution for rendering
            page_numbers: Specific pages to render (1-indexed), or None for all
            
        Returns:
            List of (page_number, PIL Image) tuples
        """
        doc = fitz.open(pdf_path)
        images = []
        
        for page_num in range(len(doc)):
            actual_page = page_num + 1
            if page_numbers and actual_page not in page_numbers:
                continue
                
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=dpi)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            images.append((actual_page, img))
            
        doc.close()
        return images

    def extract_images_with_ocr(
        self,
        pdf_path: str,
        dpi: int = 300,
        page_numbers: Optional[List[int]] = None,
        lang: Optional[str] = None,
    ) -> List[Tuple[int, Image.Image, str, float]]:
        """Render PDF pages as images and run OCR on each.
        
        Args:
            pdf_path: Path to PDF file
            dpi: Resolution for rendering
            page_numbers: Specific pages to render (1-indexed), or None for all
            lang: Override OCR language
            
        Returns:
            List of (page_number, image, ocr_text, confidence) tuples
        """
        images = self.extract_images(pdf_path, dpi=dpi, page_numbers=page_numbers)
        results = []
        
        for page_num, img in images:
            text, confidence = self.ocr_engine.extract_text(img, lang=lang)
            results.append((page_num, img, text, confidence))
            
        return results
