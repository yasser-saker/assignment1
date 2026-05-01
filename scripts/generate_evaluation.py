#!/usr/bin/env python3
"""Generate evaluation reports for sample projects.

Usage:
    python scripts/generate_evaluation.py \
        --prediction outputs/TAKEOFF-28/prediction.json \
        --expected "client_files/.../Expected Manual Output/*.xlsx"
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.evaluator import Evaluator


def main():
    parser = argparse.ArgumentParser(description="Generate evaluation report")
    parser.add_argument("--prediction", required=True, help="Path to prediction JSON")
    parser.add_argument("--expected", required=True, help="Path to expected .xlsx file")
    parser.add_argument("--output", help="Path to write evaluation_report.json (default: same dir as prediction)")
    args = parser.parse_args()

    pred_path = Path(args.prediction)
    expected_path = Path(args.expected)

    if not pred_path.exists():
        print(f"ERROR: Prediction not found: {pred_path}")
        sys.exit(1)
    if not expected_path.exists():
        print(f"ERROR: Expected output not found: {expected_path}")
        sys.exit(1)

    evaluator = Evaluator()
    report = evaluator.evaluate(str(pred_path), str(expected_path))

    out_path = args.output
    if not out_path:
        out_path = pred_path.parent / "evaluation_report.json"
    else:
        out_path = Path(out_path)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report.dict(), f, indent=2, ensure_ascii=False)

    print(f"Evaluation report saved to: {out_path}")
    print(f"\n{report.overall_notes}")

    # Print sample diffs
    if report.quantity_differences:
        print(f"\nQuantity differences (showing first 5):")
        for qd in report.quantity_differences[:5]:
            print(f"  {qd.description}: predicted={qd.predicted}, expected={qd.expected}, diff={qd.pct_diff}%")


if __name__ == "__main__":
    main()
