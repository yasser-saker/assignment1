#!/usr/bin/env python3
"""Batch process all projects in client_files/.

Usage:
    python scripts/batch_process.py --client-files-dir ./client_files

This will:
1. Discover all TAKEOFF-XX projects in the given directory
2. Run ingestion + extraction on each
3. Save predictions to outputs/TAKEOFF-XX/prediction.json
4. Run evaluation for sample projects (if expected output exists)

Expected client_files structure:
    client_files/
        01_Sample_Projects_With_Expected_Output/
            TAKEOFF-28 - Project Name/
                Project Files/
                Expected Manual Output/
            ...
        02_Challenge_Projects_Project_Files_Only/
            TAKEOFF-31 - Project Name/
                Project Files/
            ...
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.ingestion_pipeline import IngestionPipeline
from src.extraction.dynamic_rule_extractor import DynamicRuleExtractor
from src.output.serializer import OutputSerializer
from src.evaluation.evaluator import Evaluator
from src.models import AIRun


def discover_projects(base_dir: Path):
    """Find all project directories with Project Files/ inside."""
    projects = []
    for sub in base_dir.rglob("Project Files"):
        if sub.is_dir():
            project_dir = sub.parent
            project_name = project_dir.name
            # Try to find expected output
            expected_dir = project_dir / "Expected Manual Output"
            has_expected = expected_dir.exists()
            projects.append({
                "name": project_name,
                "project_files": sub,
                "expected_dir": expected_dir if has_expected else None,
            })
    return projects


def process_project(project: dict, outputs_dir: Path):
    """Run full pipeline on a single project."""
    name = project["name"]
    print(f"\n{'='*60}")
    print(f"Processing: {name}")
    print(f"{'='*60}")

    # Derive project ID from name (e.g., "TAKEOFF-28 - ..." -> "TAKEOFF-28")
    project_id = name.split()[0] if name.startswith("TAKEOFF-") else name.replace(" ", "_")
    project_output_dir = outputs_dir / project_id
    project_output_dir.mkdir(parents=True, exist_ok=True)

    # Ingest
    pipeline = IngestionPipeline()
    ingested = pipeline.process_project(
        project_dir=str(project["project_files"]),
        project_id=project_id,
    )
    print(f"  Ingested {len(ingested)} files")

    # Extract
    extractor = DynamicRuleExtractor()
    items = extractor.extract_from_project(ingested)
    ai_run = AIRun(
        run_id="dynamic-rule-based",
        tools_or_models_used=["dynamic-rule-extractor", "PyMuPDF", "pdfplumber", "context-extractor", "mechanical-parser", "electrical-parser"],
        assumptions=["Dynamic schedule detection with specialized parsers for HVAC and Electrical"],
        warnings=["Quantities are approximate, LLM post-filter may remove valid items"]
    )
    print(f"  Extracted {len(items)} line items")

    # Serialize
    serializer = OutputSerializer()
    input_files = [i.file_name for i in ingested]
    trade_scope = " | ".join(sorted(set(i.trade for i in items if i.trade)))
    output = serializer.create_output(
        project_id=project_id,
        trade_scope=trade_scope,
        input_files=input_files,
        line_items=items,
        ai_run=ai_run,
    )
    pred_path = project_output_dir / "prediction.json"
    serializer.save(output, str(project_output_dir))
    print(f"  Saved prediction to {pred_path}")

    # Evaluate if expected output exists
    if project["expected_dir"]:
        xlsx_files = list(project["expected_dir"].glob("*.xlsx"))
        if xlsx_files:
            evaluator = Evaluator()
            try:
                report = evaluator.evaluate(str(pred_path), str(xlsx_files[0]))
                eval_path = project_output_dir / "evaluation_report.json"
                with open(eval_path, "w", encoding="utf-8") as f:
                    json.dump(report.dict(), f, indent=2, ensure_ascii=False)
                print(f"  Saved evaluation to {eval_path}")
                print(f"  Match rate: {report.overall_notes}")
            except Exception as e:
                print(f"  Evaluation failed: {e}")

    return pred_path


def main():
    parser = argparse.ArgumentParser(description="Batch process all takeoff projects")
    parser.add_argument("--client-files-dir", default="./client_files", help="Path to client_files directory")
    parser.add_argument("--outputs-dir", default="./outputs", help="Path to outputs directory")
    args = parser.parse_args()

    base = Path(args.client_files_dir)
    if not base.exists():
        print(f"ERROR: client_files directory not found: {base}")
        print("\nDownload the dataset from Google Drive first:")
        print("  https://drive.google.com/open?id=1HH1VjyloFL-TwnOpplLiDw1iFt_1oECt")
        sys.exit(1)

    outputs = Path(args.outputs_dir)
    outputs.mkdir(parents=True, exist_ok=True)

    projects = discover_projects(base)
    print(f"Discovered {len(projects)} projects:")
    for p in projects:
        marker = "[SAMPLE]" if p["expected_dir"] else "[CHALLENGE]"
        print(f"  {marker} {p['name']}")

    for p in projects:
        try:
            process_project(p, outputs)
        except Exception as e:
            print(f"  FAILED: {e}")

    print(f"\n{'='*60}")
    print("Batch processing complete!")
    print(f"Outputs saved to: {outputs.absolute()}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
