"""PDF text and image extraction using pdfplumber and PyMuPDF."""
import pdfplumber
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Tuple
import io
from PIL import Image

from src.models import Page, IngestedFile


class PDFExtractor:
    """Extracts text and metadata from PDF files."""

    def __init__(self, min_text_chars: int = 50):
        self.min_text_chars = min_text_chars

    def extract(self, pdf_path: str, project_id: str, file_id: str) -> IngestedFile:
        """Extract text from all pages of a PDF using PyMuPDF (fast)."""
        path = Path(pdf_path)
        file_name = path.name

        pages: List[Page] = []
        
        try:
            # Use PyMuPDF for fast text extraction
            doc = fitz.open(pdf_path)
            for i in range(len(doc)):
                page = doc.load_page(i)
                text = page.get_text()
                is_scanned = len(text.strip()) < self.min_text_chars
                pages.append(Page(
                    page_number=i + 1,
                    text=text.strip(),
                    is_scanned=is_scanned
                ))
            doc.close()
        except Exception as e:
            # If PyMuPDF fails, return a single page with error info
            pages.append(Page(
                page_number=1,
                text=f"",
                is_scanned=False
            ))
            print(f"  Warning: Could not open {file_name} ({e})")

        return IngestedFile(
            file_id=file_id,
            project_id=project_id,
            file_name=file_name,
            file_type="unknown",
            pages=pages
        )

    def extract_with_pdfplumber(self, pdf_path: str, project_id: str, file_id: str) -> IngestedFile:
        """Extract text using pdfplumber (better for tables)."""
        path = Path(pdf_path)
        file_name = path.name

        pages: List[Page] = []

        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                is_scanned = len(text.strip()) < self.min_text_chars
                pages.append(Page(
                    page_number=i,
                    text=text.strip(),
                    is_scanned=is_scanned
                ))

        return IngestedFile(
            file_id=file_id,
            project_id=project_id,
            file_name=file_name,
            file_type="unknown",
            pages=pages
        )

    def extract_images(self, pdf_path: str, dpi: int = 200) -> List[Tuple[int, Image.Image]]:
        """Render PDF pages as images using PyMuPDF."""
        doc = fitz.open(pdf_path)
        images = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=dpi)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            images.append((page_num + 1, img))
        doc.close()
        return images
