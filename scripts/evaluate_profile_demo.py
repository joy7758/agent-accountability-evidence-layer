from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from asiep_evaluator import evaluate_profile


ROOT = Path(__file__).resolve().parents[1]
REPORT_SCHEMA = ROOT / "interfaces" / "asiep_evaluation_report.schema.json"


def main() -> int:
    report = evaluate_profile(ROOT / "profiles" / "asiep" / "v0.1" / "profile.json")
    schema = _load_json(REPORT_SCHEMA)
    errors = sorted(Draft202012Validator(schema).iter_errors(report), key=str)
    if errors:
        print(f"FAIL evaluation report schema: {errors[0].message}")
        return 1

    metrics = {metric["metric_id"]: metric for metric in report["metric_results"]}
    attack = report["attack_corpus_results"]
    paper_assets = [artifact["path"] for artifact in report["generated_artifacts"] if artifact["path"].startswith("paper_assets/")]
    print(
        f"evaluation_id={report['evaluation_id']} "
        f"evaluated_components={len(report['evaluated_components'])} "
        f"metrics={len(report['metric_results'])} "
        f"attack_detected={attack['detected_attack_samples']}/{attack['total_attack_samples']} "
        f"false_positive_rate={metrics['false_positive_rate']['value']} "
        f"cross_standard_coverage={metrics['cross_standard_coverage']['value']} "
        f"generated_paper_assets={len(paper_assets)}"
    )
    return 0


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    raise SystemExit(main())
