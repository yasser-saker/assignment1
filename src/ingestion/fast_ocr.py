"""Fast OCR with GPT-4o-mini fallback for scanned construction drawings.

Strategy:
1. Quick Tesseract pass on all pages (DPI 72, PSM 11)
2. Identify low-quality pages (< 50 chars or low confidence)
3. Send only those pages to GPT-4o-mini (batch of 5 images per call)
4. Return merged results

Cost: ~$0.005-0.01 per project with many scanned pages.
"""
import io
import base64
import os
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

import fitz
from PIL import Image
import pytesseract
import openai


@dataclass
class PageResult:
    page_num: int
    text: str
    confidence: float
    source: str  # "tesseract" or "gpt"
    char_count: int


class FastOCRWithGPTFallback:
    """Fast OCR using Tesseract + GPT-4o-mini fallback."""
    
    def __init__(
        self,
        tesseract_dpi: int = 72,
        min_chars_threshold: int = 50,
        min_confidence: float = 40.0,
        gpt_model: str = "gpt-4o-mini",
        max_gpt_batch: int = 5,
    ):
        self.tesseract_dpi = tesseract_dpi
        self.min_chars_threshold = min_chars_threshold
        self.min_confidence = min_confidence
        self.gpt_model = gpt_model
        self.max_gpt_batch = max_gpt_batch
        
        # Initialize GPT client
        api_key = os.environ.get("OPENAI_API_KEY")
        self.gpt_client = openai.OpenAI(api_key=api_key) if api_key else None
    
    def process_pdf(self, pdf_path: str, max_pages: Optional[int] = None) -> List[PageResult]:
        """Process all pages in a PDF.
        
        Returns list of PageResult objects.
        """
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        # Phase 1: Tesseract on all pages (parallel)
        print(f"[FastOCR] Processing {total_pages} pages with Tesseract...")
        tesseract_results = self._tesseract_all_pages(doc, total_pages)
        
        # Phase 2: Identify low-quality pages
        low_quality_pages = []
        for result in tesseract_results:
            if result.char_count < self.min_chars_threshold or result.confidence < self.min_confidence:
                low_quality_pages.append(result.page_num)
        
        print(f"[FastOCR] {len(low_quality_pages)} pages need GPT fallback")
        
        # Phase 3: GPT fallback (batched)
        if low_quality_pages and self.gpt_client:
            gpt_results = self._gpt_fallback_batched(doc, low_quality_pages)
            # Merge results
            for page_num, text in gpt_results.items():
                tesseract_results[page_num - 1].text = text
                tesseract_results[page_num - 1].source = "gpt"
                tesseract_results[page_num - 1].char_count = len(text)
                tesseract_results[page_num - 1].confidence = 85.0
        
        doc.close()
        return tesseract_results
    
    def _tesseract_all_pages(self, doc: fitz.Document, total_pages: int) -> List[PageResult]:
        """Run Tesseract OCR on all pages in parallel."""
        results = [None] * total_pages
        
        def process_page(page_num: int) -> Tuple[int, PageResult]:
            page = doc[page_num]
            pix = page.get_pixmap(dpi=self.tesseract_dpi)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            img = img.convert("L")
            
            # Resize if too wide
            if img.width > 2500:
                ratio = 2500 / img.width
                img = img.resize((2500, int(img.height * ratio)), Image.LANCZOS)
            
            # Run Tesseract with data for confidence
            try:
                data = pytesseract.image_to_data(
                    img,
                    config='--psm 11 --oem 1',
                    output_type=pytesseract.Output.DICT
                )
                
                confidences = [int(c) for c in data['conf'] if int(c) > 0]
                avg_conf = sum(confidences) / len(confidences) if confidences else 0
                
                words = [w for w, c in zip(data['text'], data['conf']) if int(c) > 0 and w.strip()]
                text = " ".join(words)
                
                return page_num + 1, PageResult(
                    page_num=page_num + 1,
                    text=text,
                    confidence=avg_conf,
                    source="tesseract",
                    char_count=len(text),
                )
            except Exception as e:
                return page_num + 1, PageResult(
                    page_num=page_num + 1,
                    text="",
                    confidence=0,
                    source="tesseract",
                    char_count=0,
                )
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(process_page, i): i for i in range(total_pages)}
            for future in as_completed(futures):
                page_num, result = future.result()
                results[page_num - 1] = result
                if page_num % 10 == 0:
                    print(f"[FastOCR] Processed {page_num}/{total_pages} pages")
        
        return results
    
    def _gpt_fallback_batched(self, doc: fitz.Document, page_nums: List[int]) -> Dict[int, str]:
        """Send batches of pages to GPT-4o-mini."""
        results = {}
        
        # Process in batches
        for batch_start in range(0, len(page_nums), self.max_gpt_batch):
            batch = page_nums[batch_start:batch_start + self.max_gpt_batch]
            print(f"[FastOCR] GPT batch: pages {batch}")
            
            # Prepare images
            messages = []
            for page_num in batch:
                page = doc[page_num - 1]
                pix = page.get_pixmap(dpi=100)  # Lower DPI for GPT (cheaper)
                img = Image.open(io.BytesIO(pix.tobytes("jpeg")))
                img = img.convert("L")
                if img.width > 1500:
                    ratio = 1500 / img.width
                    img = img.resize((1500, int(img.height * ratio)), Image.LANCZOS)
                
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=60)
                img_b64 = base64.b64encode(buffer.getvalue()).decode()
                
                messages.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                })
            
            # Build prompt
            page_list = ", ".join([f"page {p}" for p in batch])
            prompt = f"""You are reading construction drawing pages ({page_list}).

For EACH page, extract ALL readable text including:
- Labels and callouts
- Notes and specifications
- Schedule entries
- Legend items
- Dimensions

Format your response as:
PAGE X: [extracted text]
PAGE Y: [extracted text]

If a page has no readable text, write: PAGE X: NONE
Be thorough - include every piece of text you can read.
"""
            
            content = [{"type": "text", "text": prompt}] + messages
            
            try:
                response = self.gpt_client.chat.completions.create(
                    model=self.gpt_model,
                    messages=[{"role": "user", "content": content}],
                    max_tokens=4000,
                    temperature=0.0,
                )
                
                result_text = response.choices[0].message.content
                
                # Parse results
                for page_num in batch:
                    marker = f"PAGE {page_num}:"
                    if marker in result_text:
                        start = result_text.find(marker) + len(marker)
                        # Find end (next PAGE marker or end of text)
                        next_marker = None
                        for other_num in batch:
                            if other_num != page_num:
                                other_marker = f"PAGE {other_num}:"
                                pos = result_text.find(other_marker, start)
                                if pos != -1 and (next_marker is None or pos < next_marker):
                                    next_marker = pos
                        
                        if next_marker:
                            page_text = result_text[start:next_marker].strip()
                        else:
                            page_text = result_text[start:].strip()
                        
                        if page_text and page_text != "NONE":
                            results[page_num] = page_text
                        else:
                            results[page_num] = ""
                    else:
                        results[page_num] = ""
                        
            except Exception as e:
                print(f"[FastOCR] GPT error: {e}")
                for page_num in batch:
                    results[page_num] = ""
        
        return results


def extract_text_from_pdf(pdf_path: str, file_type: str = "unknown") -> str:
    """Extract text from PDF using Fast OCR with GPT fallback.
    
    Args:
        pdf_path: Path to PDF file
        file_type: Type of file (drawing, spec, etc.)
        
    Returns:
        Combined text from all pages
    """
    # Check if file has enough native text
    doc = fitz.open(pdf_path)
    total_chars = 0
    for page in doc:
        total_chars += len(page.get_text().strip())
    doc.close()
    
    # If file has substantial text, use native extraction
    if total_chars > 1000:
        print(f"[FastOCR] Using native text extraction ({total_chars} chars)")
        text_parts = []
        doc = fitz.open(pdf_path)
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts)
    
    # For scanned files, use OCR
    print(f"[FastOCR] Using OCR for scanned file")
    extractor = FastOCRWithGPTFallback()
    results = extractor.process_pdf(pdf_path)
    
    text_parts = []
    for result in results:
        if result.text.strip():
            text_parts.append(f"--- Page {result.page_num} ({result.source}, {result.confidence:.0f}%) ---\n{result.text}")
    
    return "\n\n".join(text_parts)
