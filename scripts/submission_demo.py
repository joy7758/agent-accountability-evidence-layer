from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from asiep_citation_linter import lint_citations
from asiep_paper_linter import lint_paper
from asiep_submission_linter import lint_submission
from asiep_venue_linter import lint_venue


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "profiles" / "asiep" / "v0.1" / "profile.json"
MANIFEST_PATH = ROOT / "submission" / "escience2026" / "submission_manifest.json"
REPORT_PATH = ROOT / "submission" / "escience2026" / "submission_lint_report.json"


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _assert_schema_valid(payload: dict, schema_path: Path) -> None:
    errors = sorted(Draft202012Validator(_load_json(schema_path)).iter_errors(payload), key=str)
    if errors:
        messages = "; ".join(error.message for error in errors)
        raise SystemExit(f"schema validation failed for {schema_path}: {messages}")


def main() -> int:
    profile = _load_json(PROFILE_PATH)
    paper_result = lint_paper(PROFILE_PATH)
    citation_result = lint_citations(PROFILE_PATH)
    venue_result = lint_venue(
        ROOT / "venues" / "escience2026" / "venue_policy.json",
        ROOT / "manuscript" / "paper_v0.4_escience_human_editable.md",
    )
    submission_result = lint_submission(MANIFEST_PATH)
    REPORT_PATH.write_text(json.dumps(submission_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _assert_schema_valid(submission_result, ROOT / profile["submission_lint_report_schema_path"])
    _assert_schema_valid(_load_json(MANIFEST_PATH), ROOT / profile["submission_manifest_schema_path"])
    _assert_schema_valid(
        _load_json(ROOT / "submission" / "escience2026" / "human_authoring_protocol.json"),
        ROOT / profile["human_authoring_protocol_schema_path"],
    )

    summary = submission_result["summary"]
    print(
        "submission_demo "
        "venue=escience2026 "
        f"paper_linter_valid={paper_result['valid']} "
        f"citation_linter_valid={citation_result['valid']} "
        f"venue_linter_valid={venue_result['valid']} "
        f"submission_linter_valid={submission_result['valid']} "
        f"human_rewrite_required={submission_result['human_rewrite_required']} "
        f"final_submission_ready={submission_result['final_submission_ready']} "
        f"author_verify_markers={summary['author_verify_markers']} "
        f"latex_scaffold_ready={summary['latex_scaffold_ready']} "
        f"ai_disclosure_ready={summary['ieee_ai_disclosure_ready']} "
        f"deadline_requires_human_verification={summary['deadline_requires_human_verification']}"
    )
    return 0 if paper_result["valid"] and citation_result["valid"] and venue_result["valid"] and submission_result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
