import argparse

from .analysis import analyze


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze query benchmark runs.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze_parser = subparsers.add_parser("analyze", help="Validate and summarize runs.")
    analyze_parser.add_argument("--data", required=True, help="Path to observations CSV.")
    analyze_parser.add_argument(
        "--output", default="reports", help="Directory for generated reports."
    )
    args = parser.parse_args()

    csv_path, report_path = analyze(args.data, args.output)
    print(f"Wrote {csv_path}")
    print(f"Wrote {report_path}")
