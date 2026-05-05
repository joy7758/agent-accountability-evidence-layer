from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from asiep_citation_linter import lint_citations
from asiep_paper_linter import lint_paper
from asiep_venue_linter import lint_venue


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "profiles" / "asiep" / "v0.1" / "profile.json"
ESC_REPORT_PATH = ROOT / "submission" / "escience2026" / "readiness_report.json"


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _assert_schema_valid(payload: dict, schema_path: Path) -> None:
    errors = sorted(Draft202012Validator(_load_json(schema_path)).iter_errors(payload), key=str)
    if errors:
        messages = "; ".join(error.message for error in errors)
        raise SystemExit(f"schema validation failed for {schema_path}: {messages}")


def main() -> int:
    paper_result = lint_paper(PROFILE_PATH)
    citation_result = lint_citations(PROFILE_PATH)
    escience = lint_venue(
        ROOT / "venues" / "escience2026" / "venue_policy.json",
        ROOT / "manuscript" / "paper_v0.3_escience.md",
    )
    aies = lint_venue(
        ROOT / "venues" / "aies2026" / "venue_policy.json",
        ROOT / "manuscript" / "paper_v0.3_aies_positioning_brief.md",
    )
    ESC_REPORT_PATH.write_text(json.dumps(escience, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _assert_schema_valid(escience, ROOT / "interfaces" / "asiep_venue_readiness_report.schema.json")

    aies_policy_risks = [warning for warning in aies["warnings"] if warning["code"] == "VENUE_AI_POLICY_RISK"]
    print(
        "venue_demo "
        "venue_count=2 "
        f"escience_readiness_score={escience['readiness_score']} "
        f"escience_errors={len(escience['errors'])} "
        f"escience_warnings={len(escience['warnings'])} "
        f"aies_policy_risks={len(aies_policy_risks)} "
        f"required_human_actions={len(escience['recommended_human_actions']) + len(aies['recommended_human_actions'])} "
        "target_recommendation=escience2026 "
        f"paper_linter_valid={paper_result['valid']} "
        f"citation_linter_valid={citation_result['valid']}"
    )
    return 0 if paper_result["valid"] and citation_result["valid"] and escience["valid"] and aies["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
