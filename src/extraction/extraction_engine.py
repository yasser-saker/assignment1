"""Main extraction engine."""
from typing import List, Optional
import uuid

from src.models import IngestedFile, LineItem, AIRun
from src.extraction.llm_client import LLMClient
from src.extraction.prompt_templates import build_extraction_prompt


class ExtractionEngine:
    """Orchestrates extraction from ingested files."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()

    def _chunk_pages(self, ingested: IngestedFile, max_chars: int = 30000) -> List[str]:
        """Group pages into chunks for efficient LLM processing."""
        chunks = []
        current_chunk = []
        current_length = 0
        start_page = 1
        
        for page in ingested.pages:
            if not page.text.strip() or len(page.text.strip()) < 200:
                continue
                
            page_text = f"--- Page {page.page_number} ---\n{page.text}\n"
            
            if current_length + len(page_text) > max_chars and current_chunk:
                # Save current chunk
                chunk_text = f"FILE: {ingested.file_name} (pages {start_page}-{page.page_number - 1})\n\n"
                chunk_text += "".join(current_chunk)
                chunks.append(chunk_text)
                
                # Start new chunk
                current_chunk = [page_text]
                current_length = len(page_text)
                start_page = page.page_number
            else:
                current_chunk.append(page_text)
                current_length += len(page_text)
        
        # Don't forget the last chunk
        if current_chunk:
            end_page = ingested.pages[-1].page_number
            chunk_text = f"FILE: {ingested.file_name} (pages {start_page}-{end_page})\n\n"
            chunk_text += "".join(current_chunk)
            chunks.append(chunk_text)
        
        return chunks

    def extract_from_file(self, ingested: IngestedFile, use_mini: bool = False) -> List[LineItem]:
        """Extract line items from a single ingested file using chunking."""
        all_items = []
        
        # Skip files with no text
        total_text = sum(len(p.text) for p in ingested.pages)
        if total_text < 100:
            print(f"  Skipping {ingested.file_name} - too little text")
            return []
        
        # Use smaller context model for large files if provider supports it
        original_model = self.llm_client.model
        if use_mini or len(ingested.pages) > 50:
            if self.llm_client.provider == "kimi":
                # Kimi does not have gpt-4o-mini; keep current model or use a fast variant
                print(f"  Using {self.llm_client.model} for large file: {ingested.file_name}")
            else:
                self.llm_client.model = "gpt-4o-mini"
                print(f"  Using gpt-4o-mini for large file: {ingested.file_name}")
        
        chunks = self._chunk_pages(ingested)
        print(f"  Processing {ingested.file_name}: {len(ingested.pages)} pages -> {len(chunks)} chunks")
        
        for chunk in chunks:
            prompt = build_extraction_prompt(
                project_name=ingested.project_id,
                file_name=ingested.file_name,
                page_number=0,  # Multi-page chunk
                file_type=ingested.file_type,
                content=chunk
            )
            
            try:
                items = self.llm_client.extract_line_items(prompt)
                for item_data in items:
                    line_item = LineItem(
                        description=item_data.get("description", ""),
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
        
        # Restore original model
        self.llm_client.model = original_model
        
        return all_items

    def extract_from_project(self, ingested_files: List[IngestedFile]) -> tuple[List[LineItem], AIRun]:
        """Extract line items from all files in a project."""
        all_items = []
        run_id = str(uuid.uuid4())[:8]
        
        for ingested in ingested_files:
            items = self.extract_from_file(ingested)
            all_items.extend(items)
        
        ai_run = AIRun(
            run_id=run_id,
            tools_or_models_used=["gpt-4o", "pdfplumber", "PyMuPDF"],
            assumptions=["Extracted from text-based PDFs using chunked processing"],
            warnings=[]
        )
        
        return all_items, ai_run
