"""Run context extraction + fusion only (no LLM) for any project."""
import sys
import os
sys.path.insert(0, '.')

from pathlib import Path
from src.ingestion.pdf_extractor import PDFExtractor
from src.extraction.context_extractor_v2 import ContextExtractorV2
from src.extraction.context_fusion_engine import ContextFusionEngine
from src.output.serializer import ProjectOutput, AIRun
import json

def run_context_only(project_id: str):
    pdf_dir = Path(f'test_data/{project_id}')
    pdf_files = list(pdf_dir.glob('*.pdf'))
    
    print(f'\n{"="*60}')
    print(f'PROJECT: {project_id}')
    print(f'PDF Files: {len(pdf_files)}')
    print(f'{"="*60}\n')
    
    # Step 1: Extract context
    print('=== STEP 1: Extracting Context ===')
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
    
    # Step 2: Fusion
    print('\n=== STEP 2: Context Fusion ===')
    fusion_engine = ContextFusionEngine()
    fusion_engine.load_context(all_context)
    context_items = fusion_engine.aggregate_by_finish_code()
    print(f'Generated {len(context_items)} items from context fusion')
    
    # Save output
    output_dir = Path(f'outputs/{project_id}')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    project_output = ProjectOutput(
        project_id=project_id,
        input_files_used=[p.name for p in pdf_files],
        ai_run=AIRun(
            run_id=f'{project_id}_context_only',
            tools_or_models_used=['ContextExtractorV2', 'ContextFusionEngine'],
            assumptions=['No LLM extraction - context fusion only'],
            warnings=['OpenAI API quota exceeded']
        ),
        line_items=[{'description': i.description, 'trade': i.trade, 'quantity': i.quantity, 'unit': i.unit, 'confidence': i.confidence, 'source_reference': i.source_reference} for i in context_items]
    )
    
    output_path = output_dir / f'{project_id}_context_only.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(project_output.model_dump(), f, indent=2, ensure_ascii=False)
    print(f'\nSaved to: {output_path}')
    
    return context_items

if __name__ == '__main__':
    project_id = sys.argv[1] if len(sys.argv) > 1 else 'TAKEOFF-50'
    run_context_only(project_id)
