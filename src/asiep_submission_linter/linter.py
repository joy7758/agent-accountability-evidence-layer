from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from asiep_validator.error_codes import get_error_code


ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "profiles" / "asiep" / "v0.1" / "profile.json"


def lint_submission(
    manifest_path: str | Path | None = None,
    *,
    profile_path: str | Path = PROFILE_PATH,
    stage: str = "rewrite",
) -> dict[str, Any]:
    if stage not in {"rewrite", "final"}:
        raise ValueError("stage must be 'rewrite' or 'final'")
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    profile_file = _resolve_path(profile_path)
    profile = _load_json(profile_file)
    if manifest_path is None:
        manifest_path = profile.get("submission_manifest_path", "submission/escience2026/submission_manifest.json")
    manifest_file = _resolve_path(manifest_path)
    manifest = _load_json(manifest_file)

    _extend_schema_errors(
        errors,
        manifest,
        ROOT / profile["submission_manifest_schema_path"],
        "SUBMISSION_MANIFEST_INVALID",
    )

    protocol_file = _resolve_path(manifest.get("human_authoring_protocol_path", ""))
    protocol = _load_json(protocol_file) if protocol_file.exists() else {}
    if protocol:
        _extend_schema_errors(
            errors,
            protocol,
            ROOT / profile["human_authoring_protocol_schema_path"],
            "SUBMISSION_HUMAN_PROTOCOL_INVALID",
        )
    else:
        errors.append(_issue("SUBMISSION_HUMAN_PROTOCOL_INVALID", f"Human authoring protocol missing: {protocol_file}."))

    venue_policy = _load_json(_resolve_path(manifest.get("venue_policy_path", "")))
    required_files_checked = _check_required_files(errors, checks, manifest)
    paper_text = _read_text(_resolve_path(manifest.get("manuscript_path", "")))
    disclosure_text = _read_text(_resolve_path(manifest.get("ai_use_disclosure_path", "")))
    latex_text = _read_text(_resolve_path(manifest.get("latex_scaffold_path", "")))
    artifact_text = _read_text(_resolve_path(manifest.get("artifact_availability_statement_path", "")))
    checklist_text = _read_text(_resolve_path(manifest.get("final_human_checklist_path", "")))

    marker = protocol.get("author_verify_marker", "AUTHOR_VERIFY")
    paper_author_verify_markers = paper_text.count(marker)
    latex_author_verify_markers = latex_text.count(marker)
    author_verify_markers = paper_author_verify_markers + latex_author_verify_markers
    citation_required_markers = paper_text.lower().count("citation_required")
    _record(
        checks,
        "author_verify_markers_present",
        author_verify_markers > 0,
        f"{author_verify_markers} markers found",
    )
    if stage == "rewrite" and author_verify_markers == 0:
        warnings.append(_issue("SUBMISSION_AUTHOR_VERIFY_MARKERS_MISSING", "No AUTHOR_VERIFY markers remain; run final submission checks before treating the paper as final.", severity="warning"))
    if stage == "final":
        _record(
            checks,
            "author_verify_markers_removed",
            paper_author_verify_markers == 0,
            f"{paper_author_verify_markers} paper markers remain",
        )
        _record(
            checks,
            "citation_required_markers_removed",
            citation_required_markers == 0,
            f"{citation_required_markers} citation_required markers remain",
        )
        if paper_author_verify_markers > 0:
            errors.append(
                _issue(
                    "SUBMISSION_AUTHOR_VERIFY_MARKERS_REMAIN",
                    f"{paper_author_verify_markers} AUTHOR_VERIFY markers remain in the human-editable manuscript.",
                    json_path="$.manuscript_path",
                    json_pointer="/manuscript_path",
                )
            )
        if latex_author_verify_markers > 0:
            errors.append(
                _issue(
                    "SUBMISSION_AUTHOR_VERIFY_MARKERS_REMAIN",
                    f"{latex_author_verify_markers} AUTHOR_VERIFY markers remain in the LaTeX scaffold.",
                    json_path="$.latex_scaffold_path",
                    json_pointer="/latex_scaffold_path",
                )
            )
        if citation_required_markers > 0:
            errors.append(
                _issue(
                    "CITATION_REQUIRED_MARKER_REMAINS",
                    f"{citation_required_markers} citation_required markers remain in the human-editable manuscript.",
                    json_path="$.manuscript_path",
                    json_pointer="/manuscript_path",
                )
            )

    disclosure_ready = _check_ai_disclosure(errors, checks, disclosure_text)
    latex_ready = _check_latex(errors, checks, latex_text)
    artifact_ready = _check_text_asset(errors, checks, artifact_text, "artifact_availability_statement", "SUBMISSION_ARTIFACT_STATEMENT_MISSING")
    checklist_ready = _check_text_asset(errors, checks, checklist_text, "final_human_checklist", "SUBMISSION_FINAL_CHECKLIST_MISSING")
    deadline_ready = _check_deadline(errors, checks, manifest, venue_policy)
    if stage == "final":
        _check_final_submission_gates(errors, checks, profile, manifest)

    if stage != "final" and manifest.get("final_submission_ready") is True:
        warnings.append(_issue("SUBMISSION_LINTER_FAILED", "M10 package should not mark final_submission_ready=true before human rewrite.", severity="warning"))
    if manifest.get("human_rewrite_required") is not True:
        errors.append(_issue("SUBMISSION_HUMAN_PROTOCOL_INVALID", "M10 package must mark human_rewrite_required=true."))

    return {
        "profile": profile["profile_name"],
        "profile_version": profile["profile_version"],
        "valid": not errors,
        "stage": stage,
        "submission_id": manifest.get("submission_id", "unknown"),
        "venue_id": manifest.get("venue_id", "unknown"),
        "paper_id": manifest.get("paper_id", "unknown"),
        "human_rewrite_required": manifest.get("human_rewrite_required", False),
        "final_submission_ready": manifest.get("final_submission_ready", False),
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "required_files_checked": required_files_checked,
            "author_verify_markers": author_verify_markers,
            "paper_author_verify_markers": paper_author_verify_markers,
            "latex_author_verify_markers": latex_author_verify_markers,
            "citation_required_markers": citation_required_markers,
            "final_stage_blocked": stage == "final" and bool(errors),
            "deadline_requires_human_verification": deadline_ready,
            "ieee_ai_disclosure_ready": disclosure_ready,
            "latex_scaffold_ready": latex_ready,
            "artifact_statement_ready": artifact_ready,
            "human_checklist_ready": checklist_ready,
        },
    }


def _check_required_files(errors: list[dict[str, Any]], checks: list[dict[str, Any]], manifest: dict[str, Any]) -> int:
    count = 0
    for item in manifest.get("package_files", []):
        count += 1
        path = _resolve_path(item["path"])
        exists = path.exists()
        _record(checks, f"file:{item['role']}", exists, "exists" if exists else f"missing: {path}")
        if item.get("required", False) and not exists:
            errors.append(_issue("SUBMISSION_MANUSCRIPT_MISSING", f"Required submission package file missing: {path}."))
    return count


def _check_ai_disclosure(errors: list[dict[str, Any]], checks: list[dict[str, Any]], text: str) -> bool:
    lower = text.lower()
    requirements = {
        "ai_disclosure_acknowledgements": "acknowledgements" in lower,
        "ai_disclosure_identifies_system": "codex" in lower or "openai" in lower or "ai system" in lower,
        "ai_disclosure_identifies_sections": "sections" in lower and "used" in lower,
        "ai_disclosure_describes_level": "level of use" in lower or "level at which" in lower,
        "ai_disclosure_author_responsibility": "human authors" in lower and "responsible" in lower,
    }
    for check_id, passed in requirements.items():
        _record(checks, check_id, passed, "present" if passed else "missing")
    if not all(requirements.values()):
        errors.append(_issue("SUBMISSION_AI_DISCLOSURE_MISSING", "IEEE-style AI-use disclosure is missing one or more required fields."))
    return all(requirements.values())


def _check_latex(errors: list[dict[str, Any]], checks: list[dict[str, Any]], text: str) -> bool:
    requirements = {
        "latex_ieeetran": "ieeetran" in text.lower(),
        "latex_conference": "conference" in text.lower(),
    }
    for check_id, passed in requirements.items():
        _record(checks, check_id, passed, "present" if passed else "missing")
    if not all(requirements.values()):
        errors.append(_issue("SUBMISSION_LATEX_SCAFFOLD_MISSING", "IEEE-style LaTeX scaffold is missing IEEEtran conference cues."))
    return all(requirements.values())


def _check_text_asset(errors: list[dict[str, Any]], checks: list[dict[str, Any]], text: str, check_id: str, code: str) -> bool:
    passed = bool(text.strip())
    _record(checks, check_id, passed, "present" if passed else "missing")
    if not passed:
        errors.append(_issue(code, f"Required text asset missing or empty: {check_id}."))
    return passed


def _check_deadline(errors: list[dict[str, Any]], checks: list[dict[str, Any]], manifest: dict[str, Any], venue_policy: dict[str, Any]) -> bool:
    raw = manifest.get("venue_constraints", {}).get("paper_submission_deadline_raw", "")
    policy_raw = venue_policy.get("paper_submission_deadline_raw", "")
    requires = manifest.get("venue_constraints", {}).get("requires_human_deadline_verification", False)
    policy_requires = venue_policy.get("requires_human_deadline_verification", False)
    passed = bool(raw) and raw == policy_raw and requires is True and policy_requires is True
    _record(checks, "deadline_human_verification_recorded", passed, "recorded" if passed else "missing or inconsistent")
    if not passed:
        errors.append(_issue("SUBMISSION_DEADLINE_VERIFICATION_MISSING", "Deadline ambiguity must be recorded and marked for human verification."))
    return passed


def _check_final_submission_gates(errors: list[dict[str, Any]], checks: list[dict[str, Any]], profile: dict[str, Any], manifest: dict[str, Any]) -> None:
    latex_report_path = _resolve_path(profile.get("latex_compile_report_path", "submission/escience2026/latex_compile_report.json"))
    approval_path = ROOT / "submission" / "escience2026" / "author_final_approval.json"
    repository_decision_path = ROOT / "submission" / "escience2026" / "repository_policy_decision.json"
    deadline_verification_path = ROOT / "submission" / "escience2026" / "deadline_verification.json"
    license_decision_path = ROOT / "submission" / "escience2026" / "license_decision.json"
    sensitive_scan_report_path = ROOT / "submission" / "escience2026" / "sensitive_content_scan_report.json"
    sensitive_review_path = ROOT / "submission" / "escience2026" / "sensitive_content_review.json"
    layout_review_path = ROOT / "submission" / "escience2026" / "layout_review.json"

    latex_report = _load_json_if_exists(latex_report_path)
    latex_report_valid = bool(latex_report)
    if latex_report:
        before = len(errors)
        _extend_schema_errors(
            errors,
            latex_report,
            ROOT / profile["latex_compile_report_schema_path"],
            "LATEX_COMPILE_POLICY_INVALID",
        )
        latex_report_valid = len(errors) == before
    else:
        errors.append(_issue("LATEX_PDF_MISSING", f"LaTeX compile report missing: {latex_report_path}."))
    _record(checks, "latex_compile_report_exists", bool(latex_report), "present" if latex_report else "missing")

    compile_success = latex_report_valid and latex_report.get("compile_success") is True
    page_count_checked = latex_report_valid and latex_report.get("page_count_checked") is True
    within_page_limit = latex_report_valid and latex_report.get("within_page_limit") is True
    _record(checks, "latex_compile_success", compile_success, "passed" if compile_success else "missing or failed")
    _record(checks, "latex_page_count_checked", page_count_checked, "checked" if page_count_checked else "not checked")
    _record(checks, "latex_within_page_limit", within_page_limit, "within limit" if within_page_limit else "not verified")
    if latex_report and not compile_success:
        errors.append(_issue("LATEX_COMPILE_FAILED", "Final submission gate requires compile_success=true in latex_compile_report.json."))
    if latex_report and not page_count_checked:
        errors.append(_issue("LATEX_PAGE_COUNT_FAILED", "Final submission gate requires page_count_checked=true in latex_compile_report.json."))
    if latex_report and page_count_checked and not within_page_limit:
        errors.append(_issue("LATEX_PAGE_BUDGET_EXCEEDED", "Final submission gate requires within_page_limit=true for eScience."))

    approval = _load_json_if_exists(approval_path)
    if approval:
        _extend_schema_errors(errors, approval, ROOT / profile["author_final_approval_schema_path"], "FINAL_APPROVAL_MISSING")
    approval_ready = bool(approval) and approval.get("approved_by_human_author") is True and approval.get("final_submission_ready") is True
    _record(checks, "author_final_approval_exists", bool(approval), "present" if approval else "missing")
    _record(checks, "author_final_approval_ready", approval_ready, "ready" if approval_ready else "not ready")
    if not approval_ready:
        errors.append(_issue("FINAL_APPROVAL_MISSING", "Final author approval is missing, not signed by a human author, or final_submission_ready is not true."))

    repository_decision = _load_json_if_exists(repository_decision_path)
    repository_ready = bool(repository_decision) and repository_decision.get("final_ready") is True
    _record(checks, "repository_policy_decision_exists", bool(repository_decision), "present" if repository_decision else "missing")
    _record(checks, "repository_policy_final_ready", repository_ready, "ready" if repository_ready else "not ready")
    if not repository_ready:
        errors.append(_issue("FINAL_REPOSITORY_POLICY_UNDECIDED", "Repository/anonymization policy is missing or not final-ready."))

    deadline_verification = _load_json_if_exists(deadline_verification_path)
    deadline_ready = bool(deadline_verification) and deadline_verification.get("deadline_verified") is True
    _record(checks, "deadline_verification_exists", bool(deadline_verification), "present" if deadline_verification else "missing")
    _record(checks, "deadline_verified", deadline_ready, "verified" if deadline_ready else "not verified")
    if not deadline_ready:
        errors.append(_issue("FINAL_DEADLINE_UNVERIFIED", "Deadline verification is missing or deadline_verified is not true."))

    license_decision = _load_json_if_exists(license_decision_path)
    license_ready = bool(license_decision) and license_decision.get("final_ready") is True
    _record(checks, "license_decision_exists", bool(license_decision), "present" if license_decision else "missing")
    _record(checks, "license_decision_final_ready", license_ready, "ready" if license_ready else "not ready")
    if not license_ready:
        errors.append(_issue("SUBMISSION_LINTER_FAILED", "License decision is missing or not final-ready."))

    sensitive_scan = _load_json_if_exists(sensitive_scan_report_path)
    sensitive_scan_completed = bool(sensitive_scan) and sensitive_scan.get("scan_completed") is True
    _record(checks, "sensitive_content_scan_report_exists", bool(sensitive_scan), "present" if sensitive_scan else "missing")
    _record(checks, "sensitive_content_scan_completed", sensitive_scan_completed, "completed" if sensitive_scan_completed else "not completed")
    if not sensitive_scan_completed:
        errors.append(_issue("SUBMISSION_LINTER_FAILED", "Sensitive content scan report is missing or scan_completed is not true."))

    sensitive_review = _load_json_if_exists(sensitive_review_path)
    sensitive_review_ready = bool(sensitive_review) and sensitive_review.get("final_ready") is True
    _record(checks, "sensitive_content_review_exists", bool(sensitive_review), "present" if sensitive_review else "missing")
    _record(checks, "sensitive_content_review_final_ready", sensitive_review_ready, "ready" if sensitive_review_ready else "not ready")
    if not sensitive_review_ready:
        errors.append(_issue("SUBMISSION_LINTER_FAILED", "Sensitive content review is missing or not final-ready."))

    layout_review = _load_json_if_exists(layout_review_path)
    layout_review_ready = bool(layout_review) and layout_review.get("final_ready") is True
    _record(checks, "layout_review_exists", bool(layout_review), "present" if layout_review else "missing")
    _record(checks, "layout_review_final_ready", layout_review_ready, "ready" if layout_review_ready else "not ready")
    if not layout_review_ready:
        errors.append(_issue("SUBMISSION_LINTER_FAILED", "Layout review is missing or not final-ready."))

    final_ready = (
        compile_success
        and page_count_checked
        and within_page_limit
        and approval_ready
        and repository_ready
        and deadline_ready
        and license_ready
        and sensitive_scan_completed
        and sensitive_review_ready
        and layout_review_ready
        and manifest.get("final_submission_ready") is True
    )
    _record(checks, "manifest_final_submission_ready", manifest.get("final_submission_ready") is True, "true" if manifest.get("final_submission_ready") is True else "false")
    if not final_ready and manifest.get("final_submission_ready") is True:
        errors.append(_issue("SUBMISSION_LINTER_FAILED", "submission_manifest.json marks final_submission_ready=true before every final gate passes."))
    if compile_success and page_count_checked and within_page_limit and approval_ready and repository_ready and deadline_ready and license_ready and sensitive_scan_completed and sensitive_review_ready and layout_review_ready and manifest.get("final_submission_ready") is not True:
        errors.append(_issue("SUBMISSION_LINTER_FAILED", "All final artifacts are present but submission_manifest.json is not marked final_submission_ready=true."))


def _extend_schema_errors(errors: list[dict[str, Any]], payload: dict[str, Any], schema_path: Path, code: str) -> None:
    schema_errors = sorted(Draft202012Validator(_load_json(schema_path)).iter_errors(payload), key=str)
    for schema_error in schema_errors:
        errors.append(_issue(code, schema_error.message, json_path=f"$.{'.'.join(str(part) for part in schema_error.path)}", json_pointer="/" + "/".join(str(part) for part in schema_error.path)))


def _issue(code: str, message: str, severity: str | None = None, json_path: str = "$", json_pointer: str = "") -> dict[str, Any]:
    spec = get_error_code(code)
    return {
        "code": code,
        "severity": severity or spec.severity,
        "message": message,
        "json_path": json_path,
        "json_pointer": json_pointer,
        "remediation_hint": spec.remediation_hint,
        "repairability": spec.repairability,
    }


def _record(checks: list[dict[str, Any]], check_id: str, passed: bool, message: str) -> None:
    checks.append({"check_id": check_id, "passed": passed, "message": message})


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _resolve_path(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _load_json(path)
