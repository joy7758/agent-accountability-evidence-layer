from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluator import evaluate_profile


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate ASIEP v0.1 local toolchain coverage.")
    parser.add_argument(
        "--profile",
        type=Path,
        default=Path("profiles/asiep/v0.1/profile.json"),
        help="Path to the ASIEP profile manifest.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format. Use json for agent-readable evaluation reports.",
    )
    args = parser.parse_args(argv)

    report = evaluate_profile(args.profile)
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        metrics = {metric["metric_id"]: metric["value"] for metric in report["metric_results"]}
        print(
            f"PASS {report['evaluation_id']} "
            f"metrics={len(report['metric_results'])} "
            f"tamper_detection_recall={metrics['tamper_detection_recall']} "
            f"false_positive_rate={metrics['false_positive_rate']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
