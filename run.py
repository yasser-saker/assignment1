"""Main runner script for AI Takeoff Builder."""
import argparse
import json
import sys
from pathlib import Path

from src.config import OUTPUTS_DIR
from src.ingestion.ingestion_pipeline import IngestionPipeline
from src.extraction.extraction_engine import ExtractionEngine
from src.extraction.rule_based_extractor import RuleBasedExtractor
from src.extraction.rule_based_extractor_v2 import RuleBasedExtractorV2
from src.output.serializer import OutputSerializer
from src.evaluation.evaluator import Evaluator


def ingest_project_files(project_dir: str, project_id: str) -> list:
    """Ingest all PDF files from a project directory using the unified pipeline."""
    pipeline = IngestionPipeline()
    
    ingested_files = pipeline.process_project(
        project_dir=project_dir,
        project_id=project_id,
    )
    
    for ingested in ingested_files:
        print(f"Processing: {ingested.file_name}")
        print(f"  Extracted {len(ingested.pages)} pages, {sum(len(p.text) for p in ingested.pages)} chars")
        scanned_count = sum(1 for p in ingested.pages if p.is_scanned)
        ocr_count = sum(1 for p in ingested.pages if p.ocr_used)
        if scanned_count:
            print(f"  Scanned pages: {scanned_count}, OCR'd: {ocr_count}")
    
    # Print OCR stats
    stats = pipeline.get_ocr_stats(ingested_files)
    if stats["ocr_pages"] > 0:
        print(f"\nOCR Summary: {stats['ocr_pages']}/{stats['total_pages']} pages OCR'd "
              f"(avg confidence: {stats['avg_ocr_confidence']}%)")
    
    return ingested_files


def find_expected_output(project_id: str, expected_dir: str = None) -> Path:
    """Find expected output Excel file for a sample project."""
    if expected_dir:
        p = Path(expected_dir)
        if p.is_file() and p.suffix == ".xlsx":
            return p
        if p.is_dir():
            xlsx_files = list(p.glob("*.xlsx"))
            if xlsx_files:
                return xlsx_files[0]
        return None
    
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
                auto_expected_dir = proj_dir / "Expected Manual Output"
                if auto_expected_dir.exists():
                    xlsx_files = list(auto_expected_dir.glob("*.xlsx"))
                    if xlsx_files:
                        return xlsx_files[0]
    
    return None


def main():
    parser = argparse.ArgumentParser(description="AI Takeoff Builder")
    parser.add_argument("--project-id", required=True, help="Project ID (e.g., TAKEOFF-28)")
    parser.add_argument("--input-dir", required=True, help="Path to project files directory")
    parser.add_argument("--evaluate", action="store_true", help="Run evaluation against expected output")
    parser.add_argument("--expected-dir", type=str, default=None, help="Path to expected output directory or .xlsx file")
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
        print("  Using LLM extraction (GPT-4o / Kimi)")
        engine = ExtractionEngine()
        line_items, ai_run = engine.extract_from_project(ingested_files)
    else:
        print("  Using rule-based extraction V2 (no API key required)")
        engine = RuleBasedExtractorV2()
        line_items = engine.extract_from_project(ingested_files)
        
        from src.models import AIRun
        ai_run = AIRun(
            run_id="rule-based-v2",
            tools_or_models_used=["rule-based-extractor-v2", "PyMuPDF", "pdfplumber", "context-extractor"],
            assumptions=["Extracted using advanced regex patterns, context extraction (finish legends, room schedules, equipment schedules), and specification parsing"],
            warnings=["Quantities are approximate or null when not explicitly stated in text"]
        )
        
        for ingested in ingested_files:
            file_items = [item for item in line_items if item.source_reference == ingested.file_name]
            print(f"  {ingested.file_name}: {len(file_items)} items")
    
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
        expected_xlsx = find_expected_output(args.project_id, args.expected_dir)
        
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
