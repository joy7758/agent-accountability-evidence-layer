from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from asiep_validator.error_codes import get_error_code


ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "profiles" / "asiep" / "v0.1" / "profile.json"


def lint_submission(manifest_path: str | Path) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    profile = _load_json(PROFILE_PATH)
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
    author_verify_markers = paper_text.count(marker) + latex_text.count(marker)
    _record(
        checks,
        "author_verify_markers_present",
        author_verify_markers > 0,
        f"{author_verify_markers} markers found",
    )
    if author_verify_markers == 0:
        errors.append(_issue("SUBMISSION_AUTHOR_VERIFY_MARKERS_MISSING", "M10 draft must retain AUTHOR_VERIFY markers for M11 human rewrite."))

    disclosure_ready = _check_ai_disclosure(errors, checks, disclosure_text)
    latex_ready = _check_latex(errors, checks, latex_text)
    artifact_ready = _check_text_asset(errors, checks, artifact_text, "artifact_availability_statement", "SUBMISSION_ARTIFACT_STATEMENT_MISSING")
    checklist_ready = _check_text_asset(errors, checks, checklist_text, "final_human_checklist", "SUBMISSION_FINAL_CHECKLIST_MISSING")
    deadline_ready = _check_deadline(errors, checks, manifest, venue_policy)

    if manifest.get("final_submission_ready") is True:
        warnings.append(_issue("SUBMISSION_LINTER_FAILED", "M10 package should not mark final_submission_ready=true before human rewrite.", severity="warning"))
    if manifest.get("human_rewrite_required") is not True:
        errors.append(_issue("SUBMISSION_HUMAN_PROTOCOL_INVALID", "M10 package must mark human_rewrite_required=true."))

    return {
        "profile": profile["profile_name"],
        "profile_version": profile["profile_version"],
        "valid": not errors,
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
        "latex_10pt": "10pt" in text.lower(),
    }
    for check_id, passed in requirements.items():
        _record(checks, check_id, passed, "present" if passed else "missing")
    if not all(requirements.values()):
        errors.append(_issue("SUBMISSION_LATEX_SCAFFOLD_MISSING", "IEEE-style LaTeX scaffold is missing IEEEtran conference 10pt cues."))
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
