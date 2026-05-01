"""Process a project using Context Fusion approach."""
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, '.')

from src.ingestion.pdf_extractor import PDFExtractor
from src.extraction.llm_client import LLMClient
from src.extraction.extraction_engine import ExtractionEngine
from src.extraction.context_extractor import ContextExtractor
from src.extraction.context_fusion_engine import ContextFusionEngine
from src.extraction.enhancer import LineItemEnhancer
from src.output.serializer import ProjectOutput, AIRun


def process_project_with_fusion(project_id: str):
    """Process a project using Context Fusion."""
    pdf_dir = Path(f'test_data/{project_id}')
    pdf_files = list(pdf_dir.glob('*.pdf'))
    
    print(f'\n{"="*60}')
    print(f'PROJECT: {project_id}')
    print(f'PDF Files: {len(pdf_files)}')
    print(f'{"="*60}\n')
    
    # Step 1: Extract context from all files first
    print('=== STEP 1: Extracting Context ===')
    context_extractor = ContextExtractor()
    all_context = {'finish_legend': [], 'room_schedule': [], 'equipment_schedule': []}
    
    extractor = PDFExtractor()
    for pdf_path in pdf_files:
        print(f'Processing: {pdf_path.name}')
        ingested = extractor.extract(str(pdf_path), project_id, pdf_path.name)
        pages_data = [{'text': p.text, 'page_number': p.page_number} for p in ingested.pages]
        context = context_extractor.extract_all(pages_data)
        all_context['finish_legend'].extend(context['finish_legend'])
        all_context['room_schedule'].extend(context['room_schedule'])
        all_context['equipment_schedule'].extend(context['equipment_schedule'])
    
    print(f'\nContext Summary:')
    print(f'  Finish Legend: {len(all_context["finish_legend"])} items')
    print(f'  Room Schedule: {len(all_context["room_schedule"])} items')
    print(f'  Equipment Schedule: {len(all_context["equipment_schedule"])} items')
    
    # Step 2: Generate line items from context fusion
    print('\n=== STEP 2: Context Fusion ===')
    fusion_engine = ContextFusionEngine()
    fusion_engine.load_context(all_context)
    context_items = fusion_engine.aggregate_by_finish_code()
    print(f'Generated {len(context_items)} items from context fusion')
    
    # Step 3: Extract additional items from SOW and Addendums using LLM
    # Skip Specifications (too large, causes timeout)
    print('\n=== STEP 3: LLM Extraction (SOW + Addendums only) ===')
    llm_client = LLMClient()
    extraction_engine = ExtractionEngine(llm_client)
    
    llm_items = []
    for pdf_path in pdf_files:
        file_name = pdf_path.name.lower()
        # Only process SOW and Addendums with LLM (skip large Specs)
        if any(kw in file_name for kw in ['scope', 'addendum']):
            print(f'Processing with LLM: {pdf_path.name}')
            ingested = extractor.extract(str(pdf_path), project_id, pdf_path.name)
            items = extraction_engine.extract_from_file(ingested)
            llm_items.extend(items)
    
    print(f'Generated {len(llm_items)} items from LLM')
    
    # Step 4: Combine and deduplicate
    print('\n=== STEP 4: Combining Items ===')
    all_items = context_items + llm_items
    
    # Deduplicate by description similarity
    unique_items = []
    seen_desc = set()
    for item in all_items:
        desc_lower = item.description.lower()[:50]
        if desc_lower not in seen_desc:
            seen_desc.add(desc_lower)
            unique_items.append(item)
    
    print(f'Total unique items: {len(unique_items)}')
    
    # Step 5: Enhance with domain knowledge
    print('\n=== STEP 5: Enhancing Items ===')
    enhancer = LineItemEnhancer()
    enhanced_items = enhancer.enhance(unique_items)
    
    # Step 6: Save output
    print('\n=== STEP 6: Saving Output ===')
    output_dir = Path(f'outputs/{project_id}')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output = ProjectOutput(
        project_id=project_id,
        trade_scope=' | '.join(sorted(set(i.trade for i in enhanced_items if i.trade))),
        input_files_used=[f.name for f in pdf_files],
        ai_run=AIRun(
            run_id='v6-context-fusion',
            tools_or_models_used=['gpt-4o', 'PyMuPDF', 'context_extractor', 'context_fusion'],
            assumptions=[
                'Finish codes extracted from INTERIOR FINISH LEGEND',
                'Room assignments extracted from ROOM FINISH SCHEDULE',
                'Quantities require geometric calculation from drawings'
            ],
            warnings=[
                'Quantities are not calculated - require room dimension extraction from drawings',
                'Some items may be missing if not listed in schedules'
            ]
        ),
        line_items=enhanced_items
    )
    
    output_path = output_dir / f'{project_id}_prediction.json'
    output.save(str(output_path))
    print(f'Saved to: {output_path}')
    
    return enhanced_items


if __name__ == '__main__':
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
    else:
        project_id = 'TAKEOFF-28'
    
    process_project_with_fusion(project_id)
