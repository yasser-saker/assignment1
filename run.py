"""Main runner script for AI Takeoff Builder."""
import argparse
import json
import sys
from pathlib import Path

from src.config import OUTPUTS_DIR
from src.ingestion.pdf_extractor import PDFExtractor
from src.ingestion.file_classifier import FileClassifier
from src.extraction.extraction_engine import ExtractionEngine
from src.extraction.rule_based_extractor import RuleBasedExtractor
from src.output.serializer import OutputSerializer
from src.evaluation.evaluator import Evaluator


def ingest_project_files(project_dir: str, project_id: str) -> list:
    """Ingest all PDF files from a project directory."""
    project_path = Path(project_dir)
    pdf_files = list(project_path.glob("*.pdf"))
    
    extractor = PDFExtractor()
    classifier = FileClassifier()
    
    ingested_files = []
    
    for i, pdf_file in enumerate(pdf_files):
        file_id = f"{project_id}_file_{i}"
        print(f"Processing: {pdf_file.name}")
        
        ingested = extractor.extract(str(pdf_file), project_id, file_id)
        ingested.file_type = classifier.classify(pdf_file.name)
        
        ingested_files.append(ingested)
        print(f"  Extracted {len(ingested.pages)} pages, {sum(len(p.text) for p in ingested.pages)} chars")
    
    return ingested_files


def find_expected_output(project_id: str) -> Path:
    """Find expected output Excel file for a sample project."""
    base = Path(__file__).parent
    prefixes = [
        "01_Sample_Projects_With_Expected_Output",
        "02_Challenge_Projects_Project_Files_Only",
    ]
    
    for prefix in prefixes:
        dir1 = base / "client_files" / prefix
        if not dir1.exists():
            continue
        candidates = list(dir1.iterdir())
        if len(candidates) == 1 and candidates[0].is_dir() and candidates[0].name == prefix:
            search_dir = candidates[0]
        else:
            search_dir = dir1
        
        for proj_dir in search_dir.iterdir():
            if not proj_dir.is_dir():
                continue
            if proj_dir.name.startswith(project_id):
                expected_dir = proj_dir / "Expected Manual Output"
                if expected_dir.exists():
                    xlsx_files = list(expected_dir.glob("*.xlsx"))
                    if xlsx_files:
                        return xlsx_files[0]
    
    return None


def main():
    parser = argparse.ArgumentParser(description="AI Takeoff Builder")
    parser.add_argument("--project-id", required=True, help="Project ID (e.g., TAKEOFF-28)")
    parser.add_argument("--input-dir", required=True, help="Path to project files directory")
    parser.add_argument("--evaluate", action="store_true", help="Run evaluation against expected output")
    parser.add_argument("--use-llm", action="store_true", help="Use LLM extraction (requires API key)")
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"AI Takeoff Builder - {args.project_id}")
    print(f"{'='*60}\n")
    
    # Step 1: Ingest
    print("Step 1: Ingesting PDF files...")
    ingested_files = ingest_project_files(args.input_dir, args.project_id)
    print(f"Ingested {len(ingested_files)} files\n")
    
    # Step 2: Extract
    print("Step 2: Extracting line items...")
    if args.use_llm:
        print("  Using LLM extraction (GPT-4o)")
        engine = ExtractionEngine()
    else:
        print("  Using rule-based extraction (no API key required)")
        engine = RuleBasedExtractor()
    
    line_items = []
    if args.use_llm:
        line_items, ai_run = engine.extract_from_project(ingested_files)
    else:
        ai_run = None
        for ingested in ingested_files:
            items = engine.extract_from_file(ingested)
            line_items.extend(items)
            print(f"  {ingested.file_name}: {len(items)} items")
        
        from src.models import AIRun
        ai_run = AIRun(
            run_id="rule-based",
            tools_or_models_used=["rule-based-extractor", "PyMuPDF"],
            assumptions=["Extracted using regex patterns and keyword matching"],
            warnings=["Limited accuracy compared to LLM extraction"]
        )
    
    print(f"\nTotal extracted: {len(line_items)} line items\n")
    
    # Step 3: Create Output
    print("Step 3: Generating output...")
    input_file_names = [f.file_name for f in ingested_files]
    trade_scope = " | ".join(sorted(set(item.trade for item in line_items if item.trade)))
    
    serializer = OutputSerializer()
    output = serializer.create_output(
        project_id=args.project_id,
        trade_scope=trade_scope,
        input_files=input_file_names,
        line_items=line_items,
        ai_run=ai_run
    )
    
    # Step 4: Save
    output_dir = OUTPUTS_DIR / args.project_id
    output_path = serializer.save(output, str(output_dir))
    print(f"Output saved to: {output_path}\n")
    
    # Step 5: Evaluation (if requested and sample project)
    if args.evaluate:
        print("Step 4: Running evaluation...")
        expected_xlsx = find_expected_output(args.project_id)
        
        if expected_xlsx:
            try:
                evaluator = Evaluator(fuzzy_threshold=60)
                eval_report = evaluator.evaluate(
                    prediction_path=output_path,
                    expected_path=str(expected_xlsx)
                )
                
                # Save evaluation report
                eval_path = output_dir / "evaluation_report.json"
                with open(eval_path, "w", encoding="utf-8") as f:
                    json.dump(eval_report.model_dump(), f, indent=2, ensure_ascii=False)
                
                print(f"Evaluation saved to: {eval_path}")
                print(f"  Matched: {eval_report.matched_items}")
                print(f"  Missing: {len(eval_report.missing_items)}")
                print(f"  Extra: {len(eval_report.extra_items)}")
                print(f"  Coverage: {eval_report.overall_notes}\n")
            except Exception as e:
                print(f"  Evaluation failed: {e}\n")
        else:
            print(f"  No expected output found for {args.project_id}\n")
    
    print(f"{'='*60}")
    print("Done!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
