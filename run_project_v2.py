"""Run project with RuleBasedExtractorV2."""
import argparse
import json
import sys
from pathlib import Path

from src.ingestion.ingestion_pipeline import IngestionPipeline
from src.extraction.rule_based_extractor_v2 import RuleBasedExtractorV2
from src.output.serializer import OutputSerializer
from src.models import AIRun


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", default="outputs")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"AI Takeoff Builder V2 - {args.project_id}")
    print(f"{'='*60}\n")

    # Step 1: Ingest
    print("Step 1: Ingesting PDF files...")
    pipeline = IngestionPipeline()
    ingested_files = pipeline.process_project(args.input_dir, args.project_id)
    print(f"Ingested {len(ingested_files)} files\n")

    # Step 2: Extract with RuleBased V2
    print("Step 2: Extracting line items with RuleBasedExtractorV2...")
    engine = RuleBasedExtractorV2()
    line_items = engine.extract_from_project(ingested_files)
    print(f"Total extracted: {len(line_items)} line items\n")

    # Step 3: Create output
    print("Step 3: Generating output...")
    input_file_names = [f.file_name for f in ingested_files]
    trade_scope = " | ".join(sorted(set(item.trade for item in line_items if item.trade)))

    ai_run = AIRun(
        run_id="rule-based-v2",
        tools_or_models_used=["rule-based-extractor-v2", "PyMuPDF", "pdfplumber"],
        assumptions=["Extracted using advanced regex patterns, context extraction (finish legends, room schedules, equipment schedules), and specification parsing"],
        warnings=["Quantities are approximate or null when not explicitly stated in text"]
    )

    serializer = OutputSerializer()
    output = serializer.create_output(
        project_id=args.project_id,
        trade_scope=trade_scope,
        input_files=input_file_names,
        line_items=line_items,
        ai_run=ai_run
    )

    # Step 4: Save
    output_dir = Path(args.output_dir) / args.project_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "prediction.json"
    output.save(str(output_path))
    print(f"Output saved to: {output_path}\n")

    # Save summary
    summary = {
        "project_id": args.project_id,
        "total_items": len(line_items),
        "trades": {}
    }
    for item in line_items:
        summary["trades"][item.trade] = summary["trades"].get(item.trade, 0) + 1

    summary_path = output_dir / "summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"Summary saved to: {summary_path}")

    print(f"\n{'='*60}")
    print("Done!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
