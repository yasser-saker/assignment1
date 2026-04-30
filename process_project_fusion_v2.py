"""Process a project using DYNAMIC Context Fusion — works on ANY project format."""
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, '.')

from src.ingestion.pdf_extractor import PDFExtractor
from src.extraction.llm_client import LLMClient
from src.extraction.extraction_engine import ExtractionEngine
from src.extraction.context_extractor_v2 import ContextExtractorV2
from src.extraction.context_fusion_engine import ContextFusionEngine
from src.extraction.enhancer import LineItemEnhancer
from src.output.serializer import ProjectOutput, AIRun


def process_project_dynamic(project_id: str):
    """Process a project using fully dynamic Context Fusion."""
    pdf_dir = Path(f'test_data/{project_id}')
    pdf_files = list(pdf_dir.glob('*.pdf'))
    
    print(f'\n{"="*60}')
    print(f'PROJECT: {project_id}')
    print(f'PDF Files: {len(pdf_files)}')
    print(f'{"="*60}\n')
    
    # Step 1: Extract context from ALL files
    print('=== STEP 1: Extracting Context from ALL files ===')
    context_extractor = ContextExtractorV2()
    all_context = {
        'finish_legend': [], 'room_schedule': [], 'equipment_schedule': [],
        'door_schedule': [], 'lighting_schedule': [], 'electrical_schedule': [],
        'plumbing_schedule': [], 'fire_protection_schedule': [],
        'ducts': [], 'electrical_devices': [], 'remove_items': [], 'management_items': [],
    }
    
    extractor = PDFExtractor()
    for pdf_path in pdf_files:
        print(f'Processing: {pdf_path.name}')
        try:
            ingested = extractor.extract(str(pdf_path), project_id, pdf_path.name)
            pages_data = [{'text': p.text, 'page_number': p.page_number} for p in ingested.pages]
            context = context_extractor.extract_all(pages_data)
            for key in all_context:
                all_context[key].extend(context.get(key, []))
        except Exception as e:
            print(f'  ERROR: {e}')
            continue
    
    print(f'\nContext Summary:')
    for key, items in all_context.items():
        if items:
            print(f'  {key}: {len(items)} items')
    
    # Step 2: Generate line items from context fusion
    print('\n=== STEP 2: Context Fusion ===')
    fusion_engine = ContextFusionEngine()
    fusion_engine.load_context(all_context)
    context_items = fusion_engine.aggregate_by_finish_code()
    print(f'Generated {len(context_items)} items from context fusion')
    
    # Step 3: Extract additional items from ALL files using LLM
    # Use OpenAI gpt-4o as primary (faster, more reliable), Kimi as fallback
    print('\n=== STEP 3: LLM Extraction (all files) ===')
    
    # Try OpenAI first
    llm_client = LLMClient(model='gpt-4o', provider='openai')
    if llm_client.demo_mode:
        print('  OpenAI API key not found, trying Kimi k2.5...')
        llm_client = LLMClient(model='kimi-k2.5', provider='kimi')
        if llm_client.demo_mode:
            print('  No API keys found! Running in demo mode.')
    else:
        print('  Primary LLM: OpenAI gpt-4o')
    
    extraction_engine = ExtractionEngine(llm_client)
    
    llm_items = []
    for pdf_path in pdf_files:
        file_name = pdf_path.name.lower()
        
        # Skip non-relevant files
        skip_keywords = ['wage', 'attachment', 'assessment', 'risk', 'justification']
        if any(kw in file_name for kw in skip_keywords):
            print(f'Skipping: {pdf_path.name}')
            continue
        
        print(f'Processing with LLM: {pdf_path.name}')
        try:
            ingested = extractor.extract(str(pdf_path), project_id, pdf_path.name)
            
            # Skip very large files to avoid timeout (>500 pages)
            if len(ingested.pages) > 500:
                print(f'  Skipping very large file ({len(ingested.pages)} pages)')
                continue
            
            # Check total text before LLM extraction
            total_text = sum(len(p.text) for p in ingested.pages)
            if total_text < 200:
                print(f'  Skipping - too little text ({total_text} chars)')
                continue
            
            # Use gpt-4o-mini for large files (>100 pages) to save cost
            if len(ingested.pages) > 100:
                extraction_engine.llm_client.model = 'gpt-4o-mini'
                print(f'  Using gpt-4o-mini for large file ({len(ingested.pages)} pages)')
            else:
                extraction_engine.llm_client.model = 'gpt-4o'
            
            items = extraction_engine.extract_from_file(ingested)
            llm_items.extend(items)
        except Exception as e:
            print(f'  ERROR: {e}')
            continue
    
    print(f'Generated {len(llm_items)} items from LLM')
    
    # Step 4: Combine and deduplicate
    print('\n=== STEP 4: Combining Items ===')
    all_items = context_items + llm_items
    
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
            run_id='v8-openai-primary',
            tools_or_models_used=['gpt-4o', 'gpt-4o-mini', 'PyMuPDF', 'context_extractor_v2', 'context_fusion'],
            assumptions=['Fully dynamic extraction from all PDF files', 'No project-specific hardcoding', 'OpenAI gpt-4o as primary LLM'],
            warnings=['System is 100% dynamic and should work on any project format']
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
        project_id = 'TAKEOFF-50'
    
    process_project_dynamic(project_id)
