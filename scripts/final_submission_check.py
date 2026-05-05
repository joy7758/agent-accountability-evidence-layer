from __future__ import annotations

import json
from pathlib import Path

from asiep_citation_linter import lint_citations
from asiep_paper_linter import lint_paper
from asiep_submission_linter import lint_submission
from asiep_venue_linter import lint_venue


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "profiles" / "asiep" / "v0.1" / "profile.json"
PAPER_PATH = ROOT / "manuscript" / "paper_v0.4_escience_human_editable.md"


def main() -> int:
    paper_text = PAPER_PATH.read_text(encoding="utf-8")
    remaining_author_verify = paper_text.count("AUTHOR_VERIFY")
    remaining_citation_required = paper_text.lower().count("citation_required")
    submission = lint_submission(profile_path=PROFILE_PATH, stage="final")
    paper = lint_paper(PROFILE_PATH)
    citation = lint_citations(PROFILE_PATH)
    venue = lint_venue(
        ROOT / "venues" / "escience2026" / "venue_policy.json",
        PAPER_PATH,
    )
    ai_disclosure_exists = (ROOT / "submission" / "escience2026" / "author_ai_use_disclosure_draft.md").exists()
    artifact_statement_exists = (ROOT / "submission" / "escience2026" / "artifact_availability_statement.md").exists()
    errors = []
    if remaining_author_verify:
        errors.append(
            {
                "code": "SUBMISSION_AUTHOR_VERIFY_MARKERS_REMAIN",
                "severity": "error",
                "message": f"{remaining_author_verify} AUTHOR_VERIFY markers remain in {PAPER_PATH.relative_to(ROOT)}.",
                "remediation_hint": "Human authors must rewrite and verify each marked section before final submission checks can pass.",
                "repairability": "human_required",
            }
        )
    if remaining_citation_required:
        errors.append(
            {
                "code": "CITATION_REQUIRED_MARKER_REMAINS",
                "severity": "error",
                "message": f"{remaining_citation_required} citation_required markers remain in {PAPER_PATH.relative_to(ROOT)}.",
                "remediation_hint": "Replace unresolved citation markers with verified citation keys or remove the unsupported claim.",
                "repairability": "human_required",
            }
        )
    if not ai_disclosure_exists:
        errors.append(
            {
                "code": "SUBMISSION_AI_DISCLOSURE_MISSING",
                "severity": "error",
                "message": "AI-use disclosure draft is missing.",
                "remediation_hint": "Restore submission/escience2026/author_ai_use_disclosure_draft.md.",
                "repairability": "agent_fixable",
            }
        )
    if not artifact_statement_exists:
        errors.append(
            {
                "code": "SUBMISSION_ARTIFACT_STATEMENT_MISSING",
                "severity": "error",
                "message": "Artifact availability statement is missing.",
                "remediation_hint": "Restore submission/escience2026/artifact_availability_statement.md.",
                "repairability": "agent_fixable",
            }
        )

    valid = (
        submission["valid"]
        and paper["valid"]
        and citation["valid"]
        and venue["valid"]
        and not errors
    )
    combined_errors = _dedupe_issues(errors + submission["errors"])
    result = {
        "profile": "ASIEP",
        "profile_version": "0.1.0",
        "stage": "final",
        "valid": valid,
        "paper_path": str(PAPER_PATH.relative_to(ROOT)),
        "remaining_author_verify_markers": remaining_author_verify,
        "remaining_latex_author_verify_markers": submission["summary"]["latex_author_verify_markers"],
        "remaining_citation_required_markers": remaining_citation_required,
        "checks": {
            "submission_linter_valid": submission["valid"],
            "paper_linter_valid": paper["valid"],
            "citation_linter_valid": citation["valid"],
            "venue_linter_valid": venue["valid"],
            "ai_disclosure_exists": ai_disclosure_exists,
            "artifact_statement_exists": artifact_statement_exists,
        },
        "errors": combined_errors,
        "warnings": submission["warnings"] + venue["warnings"],
        "required_human_actions": [
            "rewrite sections using submission/escience2026/section_packets/",
            "remove every AUTHOR_VERIFY marker only after human verification",
            "verify citation keys and metric values",
            "compile IEEE LaTeX and confirm page budget",
            "complete submission/escience2026/final_human_checklist.md",
        ],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if valid else 1


def _dedupe_issues(issues: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for issue in issues:
        key = (issue.get("code"), issue.get("message"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(issue)
    return unique


if __name__ == "__main__":
    raise SystemExit(main())
