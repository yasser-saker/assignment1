"""Combo extractor: Rule-Based V2 + targeted LLM on critical pages.

Strategy:
1. RuleBasedExtractorV2 extracts all items fast (local, deterministic)
2. LLM processes ONLY 1-2 critical pages with dense schedules (mechanical, electrical)
   to extract items that regex cannot reliably parse from tabular data.
3. Merge and deduplicate.
"""
import re
from typing import List, Tuple, Optional
from collections import Counter

from src.models import LineItem, IngestedFile
from src.extraction.rule_based_extractor_v2 import RuleBasedExtractorV2
from src.extraction.llm_client import LLMClient


class ComboExtractor:
    """Hybrid extractor: fast rule-based + targeted LLM on schedule pages."""

    # Page content patterns that indicate high-value schedule pages
    CRITICAL_PAGE_INDICATORS = [
        "VAV TERMINAL UNIT SCHEDULE",
        "AC/HP SCHEDULE",  # if present
        "LIGHTING FIXTURE SCHEDULE",
        "ELECTRICAL PANEL SCHEDULE",
    ]

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.rule_engine = RuleBasedExtractorV2()
        self.llm_client = llm_client or LLMClient()

    def extract_from_project(self, ingested_files: List[IngestedFile]) -> List[LineItem]:
        """Extract using combo approach."""
        print("[Combo] Phase 1: Rule-Based V2 extraction...")
        rule_items = self.rule_engine.extract_from_project(ingested_files)
        print(f"[Combo] Rule-based extracted: {len(rule_items)} items")

        # Phase 2: Identify critical pages for LLM
        critical_pages = self._find_critical_pages(ingested_files)
        print(f"[Combo] Found {len(critical_pages)} critical pages for LLM")

        llm_items: List[LineItem] = []
        if critical_pages and not self.llm_client.demo_mode:
            for i, (file_name, page_text, page_num, indicator) in enumerate(critical_pages, 1):
                print(f"  [{i}/{len(critical_pages)}] LLM on {file_name} page {page_num} ({indicator})...")
                items = self._llm_extract_page(page_text, file_name, page_num, indicator)
                llm_items.extend(items)
                print(f"    -> {len(items)} items")
        else:
            print("[Combo] Phase 2: Skipping LLM (no API key or no critical pages)")

        # Phase 3: Merge and deduplicate
        print("[Combo] Phase 3: Merging...")
        merged = self._smart_merge(rule_items, llm_items)
        print(f"[Combo] Final unique items: {len(merged)}")
        return merged

    def _find_critical_pages(self, ingested_files: List[IngestedFile]) -> List[Tuple[str, str, int, str]]:
        """Find pages containing dense schedules that regex cannot parse well."""
        pages = []
        for ingested in ingested_files:
            for page in ingested.pages:
                if not page.text:
                    continue
                for indicator in self.CRITICAL_PAGE_INDICATORS:
                    if indicator.upper() in page.text.upper():
                        pages.append((
                            ingested.file_name,
                            page.text,
                            page.page_number,
                            indicator
                        ))
                        break  # Only add page once
        return pages

    def _llm_extract_page(self, text: str, file_name: str, page_num: int, schedule_type: str) -> List[LineItem]:
        """Send ONE critical page to LLM for structured extraction."""
        prompt = self._build_schedule_prompt(text, file_name, page_num, schedule_type)
        try:
            items_data = self.llm_client.extract_line_items(prompt)
            items = []
            for d in items_data:
                items.append(LineItem(
                    description=d.get("description", ""),
                    trade=d.get("trade", "Other"),
                    quantity=d.get("quantity"),
                    unit=d.get("unit"),
                    confidence=d.get("confidence", 0.85),
                    source_reference=f"{file_name} p{page_num}"
                ))
            return items
        except Exception as e:
            print(f"    LLM error: {e}")
            return []

    def _build_schedule_prompt(self, text: str, file_name: str, page_num: int, schedule_type: str) -> str:
        return f"""You are an expert construction estimator extracting a {schedule_type}.

TASK: Extract EVERY line item from the schedule below. Do not skip any row. Be thorough.

OUTPUT: JSON with key "line_items" containing array of objects with:
- description: detailed description including tag, manufacturer, model, size, type
- trade: appropriate trade category
- quantity: count if shown or 1 for each equipment/fixture, else null
- unit: EA, FT, SF, or null
- confidence: 0.0-1.0
- source_reference: "{file_name} p{page_num}"

RULES:
1. For VAV boxes include: tag, CFM, inlet size, manufacturer/model
2. For AC/HP units include: tag, manufacturer, model, capacity
3. For lighting fixtures include: tag (Light A/B/C/etc.), type, manufacturer, model, wattage
4. For diffusers include: tag, CFM range, size, manufacturer
5. Return AS MANY items as there are rows in the schedule.

CONTENT:
{text[:12000]}

Extract ALL line items."""

    def _smart_merge(self, rule_items: List[LineItem], llm_items: List[LineItem]) -> List[LineItem]:
        """Merge rule-based and LLM items with deduplication."""
        seen = set()
        merged = []
        # Prefer LLM items for same key
        for item in llm_items + rule_items:
            key = f"{item.trade}|{item.description[:60].lower().strip()}"
            if key not in seen:
                seen.add(key)
                merged.append(item)
        return merged
