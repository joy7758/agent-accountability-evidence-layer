from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from asiep_evaluator import evaluate_profile
from asiep_paper_linter import lint_paper


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    evaluate_profile(ROOT / "profiles" / "asiep" / "v0.1" / "profile.json")
    lint_result = lint_paper(ROOT / "profiles" / "asiep" / "v0.1" / "profile.json")
    claims_registry = _load_json(ROOT / "manuscript" / "claims_registry.json")
    evidence_map = _load_json(ROOT / "manuscript" / "evidence_map.json")
    _assert_schema_valid(claims_registry, ROOT / "interfaces" / "asiep_paper_claim_registry.schema.json")
    _assert_schema_valid(evidence_map, ROOT / "interfaces" / "asiep_paper_evidence_map.schema.json")

    claims_with_evidence = lint_result["summary"]["claims_with_evidence"]
    print(
        f"paper_id={lint_result['paper_id']} "
        f"claims={lint_result['claims_checked']} "
        f"claims_with_evidence={claims_with_evidence} "
        f"warnings={len(lint_result['warnings'])} "
        f"errors={len(lint_result['errors'])} "
        f"sections={len(evidence_map['sections'])} "
        f"tables={len(evidence_map['tables'])} "
        f"figures={len(evidence_map['figures'])} "
        f"linter_valid={lint_result['valid']}"
    )
    return 0 if lint_result["valid"] else 1


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _assert_schema_valid(payload: dict, schema_path: Path) -> None:
    schema = _load_json(schema_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=str)
    if errors:
        raise SystemExit(f"Schema validation failed for {schema_path}: {errors[0].message}")


if __name__ == "__main__":
    raise SystemExit(main())
