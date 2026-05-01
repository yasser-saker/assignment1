"""Chunked OCR processing with checkpoint/resume support."""
import json
import logging
import tempfile
from pathlib import Path
from typing import List, Tuple, Dict, Any
from PIL import Image

from src.ingestion.parallel_ocr import ParallelOCR

logger = logging.getLogger(__name__)


class ChunkedOCR:
    """Process PDF pages in chunks with checkpoint support.
    
    If processing is interrupted, can resume from last checkpoint.
    """
    
    def __init__(self, chunk_size: int = 10, max_workers: int = 4):
        self.chunk_size = chunk_size
        self.parallel_ocr = ParallelOCR(max_workers=max_workers)
    
    def process_pages_with_checkpoint(
        self,
        pages: List[Tuple[int, Image.Image]],
        checkpoint_path: str = None,
    ) -> List[Dict[str, Any]]:
        """Process pages in chunks, saving progress after each chunk.
        
        Args:
            pages: List of (page_number, PIL_Image) tuples
            checkpoint_path: Path to save/load checkpoint JSON
            
        Returns:
            List of OCR results for all pages
        """
        # Load existing checkpoint if available
        completed_pages = set()
        results = []
        
        if checkpoint_path and Path(checkpoint_path).exists():
            try:
                with open(checkpoint_path, 'r') as f:
                    checkpoint = json.load(f)
                completed_pages = set(checkpoint.get('completed_pages', []))
                results = checkpoint.get('results', [])
                logger.info(f"Resumed from checkpoint: {len(completed_pages)} pages already done")
            except Exception as e:
                logger.warning(f"Failed to load checkpoint: {e}")
        
        # Filter out already completed pages
        pending_pages = [(pn, img) for pn, img in pages if pn not in completed_pages]
        
        if not pending_pages:
            logger.info("All pages already processed!")
            return results
        
        # Process in chunks
        total_pending = len(pending_pages)
        for chunk_start in range(0, total_pending, self.chunk_size):
            chunk_end = min(chunk_start + self.chunk_size, total_pending)
            chunk = pending_pages[chunk_start:chunk_end]
            
            logger.info(f"Processing chunk {chunk_start//self.chunk_size + 1}: pages {chunk_start+1}-{chunk_end} of {total_pending} pending")
            
            try:
                chunk_results = self.parallel_ocr.process_pages(chunk)
                results.extend(chunk_results)
                
                # Mark pages as completed
                for result in chunk_results:
                    completed_pages.add(result['page_number'])
                
                # Save checkpoint
                if checkpoint_path:
                    self._save_checkpoint(checkpoint_path, list(completed_pages), results)
                    
            except Exception as e:
                logger.error(f"Chunk failed: {e}")
                # Save checkpoint even on failure so we can resume
                if checkpoint_path:
                    self._save_checkpoint(checkpoint_path, list(completed_pages), results)
                raise
        
        return results
    
    def _save_checkpoint(self, path: str, completed_pages: List[int], results: List[Dict]):
        """Save checkpoint to disk."""
        try:
            with open(path, 'w') as f:
                json.dump({
                    'completed_pages': completed_pages,
                    'results': results,
                }, f)
        except Exception as e:
            logger.warning(f"Failed to save checkpoint: {e}")
