"""Process a single project file by file with progress saving."""
import argparse
import json
from pathlib import Path

from src.ingestion.pdf_extractor import PDFExtractor
from src.ingestion.file_classifier import FileClassifier
from src.extraction.extraction_engine import ExtractionEngine
from src.models import LineItem, AIRun, ProjectOutput


def process_project(project_id: str, input_dir: str, output_dir: str):
    """Process project files one by one with intermediate saves."""
    project_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    pdf_files = list(project_path.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files")
    
    extractor = PDFExtractor()
    classifier = FileClassifier()
    engine = ExtractionEngine()
    
    all_items = []
    
    for i, pdf_file in enumerate(pdf_files):
        print(f"\n[{i+1}/{len(pdf_files)}] Processing: {pdf_file.name}")
        
        file_id = f"{project_id}_file_{i}"
        ingested = extractor.extract(str(pdf_file), project_id, file_id)
        ingested.file_type = classifier.classify(pdf_file.name)
        
        items = engine.extract_from_file(ingested)
        print(f"  Extracted {len(items)} line items")
        all_items.extend(items)
        
        # Save intermediate results
        temp_file = output_path / f"{project_id}_temp_{i}.json"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump([item.model_dump() for item in items], f, indent=2, ensure_ascii=False)
    
    # Create final output
    ai_run = AIRun(
        run_id="llm-extraction",
        tools_or_models_used=["gpt-4o", "PyMuPDF"],
        assumptions=["Extracted using LLM with chunked processing"],
        warnings=[]
    )
    
    trade_scope = " | ".join(sorted(set(item.trade for item in all_items if item.trade)))
    
    output = ProjectOutput(
        project_id=project_id,
        trade_scope=trade_scope,
        input_files_used=[f.name for f in pdf_files],
        ai_run=ai_run,
        line_items=all_items
    )
    
    final_path = output_path / f"{project_id}_prediction.json"
    output.save(str(final_path))
    print(f"\nFinal output saved to: {final_path}")
    print(f"Total line items: {len(all_items)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", default="outputs")
    args = parser.parse_args()
    
    process_project(args.project_id, args.input_dir, args.output_dir)
