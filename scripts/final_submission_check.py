from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from asiep_citation_linter import lint_citations
from asiep_paper_linter import lint_paper
from asiep_submission_linter import lint_submission
from asiep_validator.error_codes import get_error_code
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
    final_approval_path = ROOT / "submission" / "escience2026" / "author_final_approval.json"
    latex_compile_report_path = ROOT / "submission" / "escience2026" / "latex_compile_report.json"
    deadline_verification_path = ROOT / "submission" / "escience2026" / "deadline_verification.json"
    repository_decision_path = ROOT / "submission" / "escience2026" / "repository_policy_decision.json"
    license_decision_path = ROOT / "submission" / "escience2026" / "license_decision.json"
    sensitive_scan_report_path = ROOT / "submission" / "escience2026" / "sensitive_content_scan_report.json"
    sensitive_review_path = ROOT / "submission" / "escience2026" / "sensitive_content_review.json"
    layout_review_path = ROOT / "submission" / "escience2026" / "layout_review.json"
    governance_drafts_dir = ROOT / "submission" / "escience2026" / "governance_drafts"
    recommendations_dir = ROOT / "submission" / "escience2026" / "final_gate_recommendations"
    final_gate_status = _load_json_if_exists(ROOT / "submission" / "escience2026" / "final_gate_status.json")
    final_approval = _load_json_if_exists(final_approval_path)
    latex_compile_report = _load_json_if_exists(latex_compile_report_path)
    deadline_verification = _load_json_if_exists(deadline_verification_path)
    repository_decision = _load_json_if_exists(repository_decision_path)
    license_decision = _load_json_if_exists(license_decision_path)
    sensitive_scan_report = _load_json_if_exists(sensitive_scan_report_path)
    sensitive_review = _load_json_if_exists(sensitive_review_path)
    layout_review = _load_json_if_exists(layout_review_path)
    final_approval_exists = bool(final_approval)
    latex_compile_report_exists = bool(latex_compile_report)
    deadline_verification_exists = bool(deadline_verification)
    repository_decision_exists = bool(repository_decision)
    license_decision_exists = bool(license_decision)
    sensitive_scan_report_exists = bool(sensitive_scan_report)
    sensitive_review_exists = bool(sensitive_review)
    layout_review_exists = bool(layout_review)
    governance_draft_files = sorted(str(path.relative_to(ROOT)) for path in governance_drafts_dir.glob("*.draft.json")) if governance_drafts_dir.exists() else []
    governance_drafts_present = bool(governance_draft_files)
    recommendation_files = sorted(str(path.relative_to(ROOT)) for path in recommendations_dir.glob("*.json")) if recommendations_dir.exists() else []
    recommendations_present = bool(recommendation_files)
    errors = []
    if remaining_author_verify:
        errors.append(_issue("SUBMISSION_AUTHOR_VERIFY_MARKERS_REMAIN", f"{remaining_author_verify} AUTHOR_VERIFY markers remain in {PAPER_PATH.relative_to(ROOT)}."))
    if remaining_citation_required:
        errors.append(_issue("CITATION_REQUIRED_MARKER_REMAINS", f"{remaining_citation_required} citation_required markers remain in {PAPER_PATH.relative_to(ROOT)}."))
    if not ai_disclosure_exists:
        errors.append(_issue("SUBMISSION_AI_DISCLOSURE_MISSING", "AI-use disclosure draft is missing."))
    if not artifact_statement_exists:
        errors.append(_issue("SUBMISSION_ARTIFACT_STATEMENT_MISSING", "Artifact availability statement is missing."))

    if latex_compile_report:
        _extend_schema_errors(errors, latex_compile_report, ROOT / "interfaces" / "asiep_latex_compile_report.schema.json", "LATEX_COMPILE_POLICY_INVALID")
        if latex_compile_report.get("compile_success") is not True:
            errors.append(_issue("LATEX_COMPILE_FAILED", "LaTeX compile report exists but compile_success is not true."))
        if latex_compile_report.get("page_count_checked") is not True:
            errors.append(_issue("LATEX_PAGE_COUNT_FAILED", "LaTeX compile report exists but page_count_checked is not true."))
        if latex_compile_report.get("page_count_checked") is True and latex_compile_report.get("within_page_limit") is not True:
            errors.append(_issue("LATEX_PAGE_BUDGET_EXCEEDED", "LaTeX compile report exists but within_page_limit is not true."))
    else:
        errors.append(_issue("LATEX_PDF_MISSING", "LaTeX compile report is missing."))

    if final_approval:
        _extend_schema_errors(errors, final_approval, ROOT / "interfaces" / "asiep_author_final_approval.schema.json", "FINAL_APPROVAL_MISSING")
        if final_approval.get("approved_by_human_author") is not True:
            errors.append(_issue("FINAL_APPROVAL_MISSING", "Final author approval exists but approved_by_human_author is not true."))
        if final_approval.get("final_submission_ready") is not True:
            errors.append(_issue("FINAL_APPROVAL_MISSING", "Final author approval exists but final_submission_ready is not true."))
    else:
        errors.append(_issue("FINAL_APPROVAL_MISSING", "Final author approval is missing."))

    if not repository_decision or repository_decision.get("final_ready") is not True:
        errors.append(_issue("FINAL_REPOSITORY_POLICY_UNDECIDED", "Repository/anonymization decision is missing or not final-ready."))
    if not deadline_verification or deadline_verification.get("deadline_verified") is not True:
        errors.append(_issue("FINAL_DEADLINE_UNVERIFIED", "Deadline ambiguity verification is missing or not verified."))
    if not license_decision or license_decision.get("final_ready") is not True:
        errors.append(_issue("SUBMISSION_LINTER_FAILED", "License decision is missing or not final-ready."))
    if not sensitive_scan_report:
        errors.append(_issue("SUBMISSION_LINTER_FAILED", "Sensitive content scan report is missing."))
    elif sensitive_scan_report.get("scan_completed") is not True:
        errors.append(_issue("SUBMISSION_LINTER_FAILED", "Sensitive content scan report exists but scan_completed is not true."))
    if not sensitive_review or sensitive_review.get("final_ready") is not True:
        errors.append(_issue("SUBMISSION_LINTER_FAILED", "Sensitive content review is missing or not final-ready."))
    if not layout_review or layout_review.get("final_ready") is not True:
        errors.append(_issue("SUBMISSION_LINTER_FAILED", "Layout review is missing or not final-ready."))

    valid = (
        submission["valid"]
        and paper["valid"]
        and citation["valid"]
        and venue["valid"]
        and not errors
    )
    combined_errors = _dedupe_issues(errors + submission["errors"])
    blocking_items = list(final_gate_status.get("blocking_items", [])) if final_gate_status else []
    if governance_drafts_present and not (final_approval_exists and deadline_verification_exists and repository_decision_exists):
        blocking_items = _dedupe_strings(
            blocking_items
            + [
                "governance drafts are present but final gate files are not created",
                "draft files must not be used as final approval records",
            ]
        )
    if recommendations_present and not (sensitive_review_exists and layout_review_exists and final_approval_exists and deadline_verification_exists and repository_decision_exists and license_decision_exists):
        blocking_items = _dedupe_strings(
            blocking_items
            + [
                "recommended final gate records are present but have not been promoted",
                "promotion required before final submission",
            ]
        )
    required_human_actions = []
    if remaining_author_verify:
        required_human_actions.insert(0, "remove every AUTHOR_VERIFY marker only after human verification")
    if not latex_compile_report or latex_compile_report.get("compile_success") is not True:
        required_human_actions.append("compile IEEE LaTeX and generate the PDF")
    if not latex_compile_report or latex_compile_report.get("page_count_checked") is not True or latex_compile_report.get("within_page_limit") is not True:
        required_human_actions.append("confirm page count against 8 pages excluding references")
    if not license_decision or license_decision.get("final_ready") is not True:
        required_human_actions.append("create license_decision.json after human license decision")
    if not sensitive_review or sensitive_review.get("final_ready") is not True:
        required_human_actions.append("review sensitive_content_scan_report.json and create sensitive_content_review.json only after human review")
    if not layout_review or layout_review.get("final_ready") is not True:
        required_human_actions.append("review the compiled PDF and create layout_review.json only after human review")
    if not repository_decision or repository_decision.get("final_ready") is not True:
        required_human_actions.append("create repository_policy_decision.json after human repository/anonymization decision")
    if not deadline_verification or deadline_verification.get("deadline_verified") is not True:
        required_human_actions.append("create deadline_verification.json after checking the official venue deadline")
    if not final_approval or final_approval.get("approved_by_human_author") is not True:
        required_human_actions.append("create author_final_approval.json only after human approval")
    if not valid:
        required_human_actions.append("complete submission/escience2026/final_human_checklist.md")
    if valid:
        required_human_actions.extend(
            [
                "log in to EasyChair and verify the final live deadline before upload",
                "upload the generated PDF manually",
                "check title, author, abstract, keywords, AI-use disclosure, and repository-link policy in the submission system",
            ]
        )
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
            "author_final_approval_exists": final_approval_exists,
            "governance_drafts_present": governance_drafts_present,
            "latex_compile_report_exists": latex_compile_report_exists,
            "latex_compile_success": latex_compile_report.get("compile_success") is True if latex_compile_report else False,
            "page_count_checked": latex_compile_report.get("page_count_checked") is True if latex_compile_report else False,
            "within_page_limit": latex_compile_report.get("within_page_limit") is True if latex_compile_report else False,
            "deadline_verification_exists": deadline_verification_exists,
            "repository_decision_exists": repository_decision_exists,
            "license_decision_exists": license_decision_exists,
            "license_decision_final_ready": license_decision.get("final_ready") is True if license_decision else False,
            "sensitive_content_scan_report_exists": sensitive_scan_report_exists,
            "sensitive_content_scan_completed": sensitive_scan_report.get("scan_completed") is True if sensitive_scan_report else False,
            "sensitive_content_review_exists": sensitive_review_exists,
            "sensitive_content_review_final_ready": sensitive_review.get("final_ready") is True if sensitive_review else False,
            "layout_review_exists": layout_review_exists,
            "layout_review_final_ready": layout_review.get("final_ready") is True if layout_review else False,
            "final_gate_recommendations_present": recommendations_present,
        },
        "errors": combined_errors,
        "warnings": submission["warnings"] + venue["warnings"],
        "governance_draft_files": governance_draft_files,
        "recommendation_files": recommendation_files,
        "blocking_items": blocking_items,
        "required_human_actions": required_human_actions,
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


def _dedupe_strings(items: list[str]) -> list[str]:
    seen = set()
    unique = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def _issue(code: str, message: str) -> dict:
    spec = get_error_code(code)
    return {
        "code": code,
        "severity": spec.severity,
        "message": message,
        "remediation_hint": spec.remediation_hint,
        "repairability": spec.repairability,
    }


def _load_json_if_exists(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _extend_schema_errors(errors: list[dict], payload: dict, schema_path: Path, code: str) -> None:
    with schema_path.open(encoding="utf-8") as handle:
        schema = json.load(handle)
    for schema_error in sorted(Draft202012Validator(schema).iter_errors(payload), key=str):
        errors.append(_issue(code, schema_error.message))


if __name__ == "__main__":
    raise SystemExit(main())
