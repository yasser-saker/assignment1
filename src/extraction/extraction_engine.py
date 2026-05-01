"""Main extraction engine - Hybrid: Local classification + LLM reasoning."""
from typing import List, Optional
import uuid

from src.models import IngestedFile, LineItem, AIRun
from src.extraction.llm_client import LLMClient
from src.extraction.prompt_templates import build_extraction_prompt
from src.extraction.hybrid_extractor import HybridExtractor, StructureClassifier


class ExtractionEngine:
    """Orchestrates extraction from ingested files using hybrid approach."""

    def __init__(self, llm_client: Optional[LLMClient] = None, use_hybrid: bool = True):
        self.llm_client = llm_client or LLMClient()
        self.use_hybrid = use_hybrid
        self.hybrid = HybridExtractor() if use_hybrid else None
        self.classifier = StructureClassifier()

    def _chunk_pages(self, ingested: IngestedFile, max_chars: int = 12000) -> List[str]:
        """Group pages into smaller chunks for targeted LLM processing."""
        chunks = []
        current_chunk = []
        current_length = 0
        start_page = 1
        
        for page in ingested.pages:
            if not page.text.strip() or len(page.text.strip()) < 100:
                continue
                
            page_text = f"--- Page {page.page_number} ---\n{page.text}\n"
            
            if current_length + len(page_text) > max_chars and current_chunk:
                chunk_text = f"FILE: {ingested.file_name} (pages {start_page}-{page.page_number - 1})\n\n"
                chunk_text += "".join(current_chunk)
                chunks.append(chunk_text)
                
                current_chunk = [page_text]
                current_length = len(page_text)
                start_page = page.page_number
            else:
                current_chunk.append(page_text)
                current_length += len(page_text)
        
        if current_chunk:
            end_page = ingested.pages[-1].page_number
            chunk_text = f"FILE: {ingested.file_name} (pages {start_page}-{end_page})\n\n"
            chunk_text += "".join(current_chunk)
            chunks.append(chunk_text)
        
        return chunks

    def extract_from_file(self, ingested: IngestedFile, use_mini: bool = False) -> List[LineItem]:
        """Extract line items from a single ingested file using hybrid approach."""
        all_items = []
        
        # Skip files with no text
        total_text = sum(len(p.text) for p in ingested.pages)
        if total_text < 100:
            print(f"  Skipping {ingested.file_name} - too little text")
            return []
        
        # Phase 1: Try structure-aware schedule extraction (local detection + targeted LLM)
        if self.use_hybrid and self.hybrid and self.hybrid.llm.is_available():
            schedule_items = self.hybrid._extract_from_file(ingested)
            if schedule_items:
                all_items.extend(schedule_items)
                print(f"  {ingested.file_name}: {len(schedule_items)} items from hybrid schedule extraction")
        
        # Phase 2: General chunk-based extraction for any remaining content
        original_model = self.llm_client.model
        if use_mini or len(ingested.pages) > 50:
            if self.llm_client.provider != "kimi":
                self.llm_client.model = "gpt-4o-mini"
        
        chunks = self._chunk_pages(ingested)
        
        for chunk in chunks:
            # Classify chunk to use targeted prompt
            classification = self.classifier.classify(chunk)
            
            # Skip low-confidence chunks if we already have schedule items
            if all_items and classification["confidence"] < 0.3:
                continue
            
            prompt = build_extraction_prompt(
                project_name=ingested.project_id,
                file_name=ingested.file_name,
                page_number=0,
                file_type=ingested.file_type,
                content=chunk
            )
            
            try:
                items = self.llm_client.extract_line_items(prompt)
                for item_data in items:
                    # Skip placeholder/demo items
                    desc = item_data.get("description", "")
                    if "PLACEHOLDER" in desc or "API_KEY" in desc:
                        continue
                    
                    line_item = LineItem(
                        description=desc,
                        trade=item_data.get("trade", ""),
                        quantity=item_data.get("quantity"),
                        unit=item_data.get("unit"),
                        confidence=item_data.get("confidence", 0.0),
                        source_reference=f"{ingested.file_name}"
                    )
                    all_items.append(line_item)
            except Exception as e:
                print(f"  Error extracting from {ingested.file_name}: {e}")
                continue
        
        self.llm_client.model = original_model
        
        return all_items

    def extract_from_project(self, ingested_files: List[IngestedFile]) -> tuple[List[LineItem], AIRun]:
        """Extract line items from all files in a project."""
        all_items = []
        run_id = str(uuid.uuid4())[:8]
        
        for ingested in ingested_files:
            items = self.extract_from_file(ingested)
            all_items.extend(items)
        
        # Deduplicate
        seen = set()
        unique = []
        for item in all_items:
            key = f"{item.trade}|{item.description[:80].lower()}"
            if key not in seen:
                seen.add(key)
                unique.append(item)
        
        ai_run = AIRun(
            run_id=run_id,
            tools_or_models_used=["gpt-4o", "pdfplumber", "PyMuPDF", "HybridExtractor"],
            assumptions=["Hybrid extraction: local structure detection + LLM reasoning per chunk"],
            warnings=[]
        )
        
        return unique, ai_run
