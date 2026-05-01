"""Parallel OCR processing for multiple pages/images."""
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Tuple, Dict, Any
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


def _ocr_single_page(args: Dict[str, Any]) -> Dict[str, Any]:
    """Worker function for parallel OCR (must be top-level for pickling).
    
    Args:
        args: dict with 'image_bytes', 'page_number', 'config', 'lang', 'preprocess'
    
    Returns:
        dict with 'page_number', 'text', 'confidence'
    """
    import pytesseract
    from PIL import Image, ImageFilter, ImageEnhance, ImageOps
    import io
    
    image = Image.open(io.BytesIO(args['image_bytes']))
    
    # Preprocess
    if args.get('preprocess', True):
        img = image.convert("L")
        img = img.filter(ImageFilter.MedianFilter(size=3))
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        img = ImageOps.autocontrast(img)
        # Adaptive threshold using PIL
        img = img.point(lambda x: 0 if x < 128 else 255, '1')
        img = img.convert("L")
    else:
        img = image.convert("L")
    
    # Run OCR
    try:
        data = pytesseract.image_to_data(
            img,
            lang=args.get('lang', 'eng'),
            config=args.get('config', '--psm 11 --oem 3'),
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
        
        return {
            'page_number': args['page_number'],
            'text': full_text,
            'confidence': avg_confidence,
        }
    except Exception as e:
        logger.error(f"OCR failed for page {args['page_number']}: {e}")
        return {
            'page_number': args['page_number'],
            'text': '',
            'confidence': 0.0,
        }


class ParallelOCR:
    """Run OCR on multiple pages in parallel using process pool."""
    
    def __init__(self, max_workers: int = 4, lang: str = 'eng', 
                 psm: int = 11, oem: int = 3, preprocess: bool = True):
        self.max_workers = max_workers
        self.lang = lang
        self.config = f'--psm {psm} --oem {oem}'
        self.preprocess = preprocess
    
    def process_pages(self, pages: List[Tuple[int, Image.Image]]) -> List[Dict[str, Any]]:
        """Process multiple pages in parallel.
        
        Args:
            pages: List of (page_number, PIL_Image) tuples
            
        Returns:
            List of dicts with 'page_number', 'text', 'confidence'
        """
        import io
        
        # Convert images to bytes for pickling
        args_list = []
        for page_num, img in pages:
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            args_list.append({
                'image_bytes': buffer.getvalue(),
                'page_number': page_num,
                'config': self.config,
                'lang': self.lang,
                'preprocess': self.preprocess,
            })
        
        results = []
        
        # Use ProcessPoolExecutor for true parallelism
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(_ocr_single_page, args): args['page_number'] 
                      for args in args_list}
            
            for future in as_completed(futures):
                page_num = futures[future]
                try:
                    result = future.result(timeout=120)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Parallel OCR failed for page {page_num}: {e}")
                    results.append({
                        'page_number': page_num,
                        'text': '',
                        'confidence': 0.0,
                    })
        
        # Sort by page number
        results.sort(key=lambda x: x['page_number'])
        return results
