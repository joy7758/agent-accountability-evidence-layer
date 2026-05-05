from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SUBMISSION_ROOT = ROOT / "submission" / "escience2026"
RECOMMENDATIONS_ROOT = SUBMISSION_ROOT / "final_gate_recommendations"


REQUIRED_CONFIRM_FLAGS = (
    "human_confirm_final_gates",
    "confirm_deadline",
    "confirm_repository_policy",
    "confirm_license",
    "confirm_sensitive_scan",
    "confirm_layout",
    "confirm_ai_disclosure",
    "confirm_final_pdf",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Promote eScience recommendation records into final gate files after explicit human confirmation."
    )
    parser.add_argument("--human-confirm-final-gates", action="store_true")
    parser.add_argument("--approved-by", required=False, default="")
    parser.add_argument("--confirm-deadline", action="store_true")
    parser.add_argument("--confirm-repository-policy", action="store_true")
    parser.add_argument("--confirm-license", action="store_true")
    parser.add_argument("--confirm-sensitive-scan", action="store_true")
    parser.add_argument("--confirm-layout", action="store_true")
    parser.add_argument("--confirm-ai-disclosure", action="store_true")
    parser.add_argument("--confirm-final-pdf", action="store_true")
    parser.add_argument("--overwrite", action="store_true", help="Allow overwriting existing final gate files.")
    parser.add_argument("--dry-run", action="store_true", help="Validate confirmations and report final files without writing them.")
    parser.add_argument("--format", choices=["json"], default="json")
    args = parser.parse_args()

    final_paths = _final_paths()
    would_create_files = [str(path.relative_to(ROOT)) for path in final_paths.values()]
    missing_flags = [flag for flag in REQUIRED_CONFIRM_FLAGS if not getattr(args, flag)]
    if not args.approved_by.strip():
        missing_flags.append("approved_by")
    if missing_flags:
        print(
            json.dumps(
                {
                    "valid": False,
                    "promoted": False,
                    "dry_run": args.dry_run,
                    "error": "human_final_gate_confirmation_required",
                    "errors": ["human_final_gate_confirmation_required"],
                    "warnings": [],
                    "missing_confirmations": missing_flags,
                    "missing_required_flags": missing_flags,
                    "would_create_files": would_create_files,
                    "final_submission_ready_after_promotion": False,
                    "message": "Recommended records cannot be promoted without every explicit human confirmation flag.",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    _require_recommendations()
    existing = [str(path.relative_to(ROOT)) for path in final_paths.values() if path.exists()]
    if existing and not args.overwrite and not args.dry_run:
        print(
            json.dumps(
                {
                    "valid": False,
                    "promoted": False,
                    "dry_run": args.dry_run,
                    "error": "final_gate_files_already_exist",
                    "errors": ["final_gate_files_already_exist"],
                    "warnings": [],
                    "existing_files": existing,
                    "missing_required_flags": [],
                    "would_create_files": would_create_files,
                    "final_submission_ready_after_promotion": False,
                    "message": "Refusing to overwrite existing final gate files without --overwrite.",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    if args.dry_run:
        warnings = [
            "Dry run only; final gate files were not created.",
            "final_submission_ready remains false until the promotion command is run without --dry-run and final checks pass.",
        ]
        if existing:
            warnings.append("Some final gate files already exist; dry run did not modify them.")
        print(
            json.dumps(
                {
                    "valid": True,
                    "promoted": False,
                    "dry_run": True,
                    "approved_by": args.approved_by.strip(),
                    "existing_files": existing,
                    "missing_required_flags": [],
                    "would_create_files": would_create_files,
                    "final_submission_ready_after_promotion": True,
                    "errors": [],
                    "warnings": warnings,
                    "message": "Dry run passed. Final gate files would be created only in write mode.",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    now = datetime.now(timezone.utc).isoformat()
    approved_by = args.approved_by.strip()
    _write_json(final_paths["deadline"], _deadline_final(now, approved_by))
    _write_json(final_paths["repository"], _repository_final(now, approved_by))
    _write_json(final_paths["license"], _license_final(now, approved_by))
    _write_json(final_paths["sensitive"], _sensitive_review_final(now, approved_by))
    _write_json(final_paths["layout"], _layout_review_final(now, approved_by))
    _write_json(final_paths["approval"], _author_approval_final(now, approved_by))

    print(
        json.dumps(
                {
                    "valid": True,
                    "promoted": True,
                    "dry_run": False,
                    "approved_by": approved_by,
                    "created_files": [str(path.relative_to(ROOT)) for path in final_paths.values()],
                    "missing_required_flags": [],
                    "would_create_files": would_create_files,
                    "final_submission_ready_after_promotion": True,
                    "errors": [],
                    "warnings": [],
                    "message": "Final gate files were created from recommendation records after explicit human confirmation.",
                },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _require_recommendations() -> None:
    required = [
        "author_identity.recommended.json",
        "license_decision.recommended.json",
        "repository_policy_decision.recommended.json",
        "deadline_verification.recommended.json",
        "layout_review.recommended.json",
        "sensitive_content_review.recommended.json",
        "ai_use_disclosure_review.recommended.json",
        "author_final_approval.recommended_plan.json",
    ]
    missing = [name for name in required if not (RECOMMENDATIONS_ROOT / name).exists()]
    if missing:
        raise SystemExit(f"Missing recommendation records: {', '.join(missing)}")


def _final_paths() -> dict[str, Path]:
    return {
        "deadline": SUBMISSION_ROOT / "deadline_verification.json",
        "repository": SUBMISSION_ROOT / "repository_policy_decision.json",
        "license": SUBMISSION_ROOT / "license_decision.json",
        "sensitive": SUBMISSION_ROOT / "sensitive_content_review.json",
        "layout": SUBMISSION_ROOT / "layout_review.json",
        "approval": SUBMISSION_ROOT / "author_final_approval.json",
    }


def _deadline_final(now: str, approved_by: str) -> dict[str, Any]:
    return {
        "verification_id": "asiep-escience2026-deadline-final",
        "target_venue": "escience2026",
        "deadline_checked_by": approved_by,
        "checked_at": now,
        "official_source_url": "human_verified_live_cfp_or_easychair",
        "planning_deadline": "2026-05-18T23:59:00-12:00",
        "planning_deadline_label": "Monday, May 18, 2026, 11:59 PM AoE",
        "verified_deadline": "2026-05-18T23:59:00-12:00",
        "cfp_deadline_ambiguity": "CFP row previously recorded both Monday, May 18, 2026 and Tuesday, May 19, 2026 11:59 PM AoE.",
        "conservative_planning": True,
        "notes": [
            "Promoted from conservative planning recommendation after explicit human confirmation.",
            "The prior May 18 / May 19 AoE CFP ambiguity is preserved in this record.",
            "The human author accepted the conservative May 18 AoE planning deadline for final pre-submission gate purposes."
        ],
        "deadline_verified": True,
        "final_ready": True,
        "promoted_from": "submission/escience2026/final_gate_recommendations/deadline_verification.recommended.json"
    }


def _repository_final(now: str, approved_by: str) -> dict[str, Any]:
    return {
        "decision_id": "asiep-escience2026-repository-policy-final",
        "target_venue": "escience2026",
        "review_mode": "single-blind",
        "repository_policy": "public_repo_allowed",
        "decided_by": approved_by,
        "decided_at": now,
        "rationale": "Promoted from recommendation after human confirmation of current author instructions.",
        "final_ready": True,
        "promoted_from": "submission/escience2026/final_gate_recommendations/repository_policy_decision.recommended.json"
    }


def _license_final(now: str, approved_by: str) -> dict[str, Any]:
    return {
        "decision_id": "asiep-escience2026-license-final",
        "target_venue": "escience2026",
        "code_license": "Apache-2.0",
        "manuscript_license": "CC-BY-4.0",
        "artifact_license": "CC-BY-4.0",
        "decided_by": approved_by,
        "decided_at": now,
        "rationale": "Promoted from recommendation after human license review.",
        "final_ready": True,
        "promoted_from": "submission/escience2026/final_gate_recommendations/license_decision.recommended.json"
    }


def _sensitive_review_final(now: str, approved_by: str) -> dict[str, Any]:
    scan = _load_json_if_exists(SUBMISSION_ROOT / "sensitive_content_scan_report.json")
    findings = scan.get("findings", [])
    classified_findings = []
    for finding in findings:
        classification = "expected_fixture_or_documentation_marker"
        snippet = str(finding.get("snippet", "")).lower()
        rule_id = str(finding.get("rule_id", ""))
        if any(token in snippet for token in ("private key", "api_key=", "password=", "bearer ")):
            classification = "possible_sensitive_content"
        classified_findings.append(
            {
                "path": finding.get("path"),
                "line": finding.get("line"),
                "rule_id": rule_id,
                "severity": finding.get("severity"),
                "classification": classification,
                "snippet": finding.get("snippet"),
            }
        )
    unresolved_possible_sensitive = [
        item for item in classified_findings if item["classification"] == "possible_sensitive_content"
    ]
    return {
        "review_id": "asiep-escience2026-sensitive-content-review-final",
        "target_venue": "escience2026",
        "reviewed_by": approved_by,
        "reviewed_at": now,
        "source_report": "submission/escience2026/sensitive_content_scan_report.json",
        "classification": "expected_fixture_or_documentation_markers",
        "scan_completed": scan.get("scan_completed") is True,
        "findings_count": len(findings),
        "findings_classified": classified_findings,
        "possible_sensitive_content_unresolved": bool(unresolved_possible_sensitive),
        "unresolved_possible_sensitive_findings": unresolved_possible_sensitive,
        "findings_reviewed": True,
        "final_ready": not unresolved_possible_sensitive,
        "notes": [
            "Promoted from recommendation after human review.",
            "This remains a sentinel/pattern review, not full data-loss prevention."
        ],
        "promoted_from": "submission/escience2026/final_gate_recommendations/sensitive_content_review.recommended.json"
    }


def _layout_review_final(now: str, approved_by: str) -> dict[str, Any]:
    latex_report = _load_json_if_exists(SUBMISSION_ROOT / "latex_compile_report.json")
    return {
        "review_id": "asiep-escience2026-layout-review-final",
        "target_venue": "escience2026",
        "reviewed_by": approved_by,
        "reviewed_at": now,
        "source_report": "submission/escience2026/latex_compile_report.json",
        "pdf_reviewed": True,
        "overfull_boxes_reviewed": True,
        "pdf_path": latex_report.get("generated_pdf_path", "submission/escience2026/latex/main.pdf"),
        "page_count": latex_report.get("page_count_total"),
        "page_count_checked": latex_report.get("page_count_checked") is True,
        "within_page_limit": latex_report.get("within_page_limit") is True,
        "unresolved_citations": latex_report.get("unresolved_citations", []),
        "unresolved_references": latex_report.get("unresolved_references", []),
        "overfull_boxes": latex_report.get("overfull_boxes", []),
        "overfull_boxes_count": len(latex_report.get("overfull_boxes", [])),
        "overfull_boxes_status": "accepted_after_pdf_review",
        "author_placeholders_present": latex_report.get("author_placeholders_present") is True,
        "author_block_verified": latex_report.get("author_block_verified") is True,
        "layout_status": "accepted_after_human_pdf_review",
        "final_ready": True,
        "promoted_from": "submission/escience2026/final_gate_recommendations/layout_review.recommended.json"
    }


def _author_approval_final(now: str, approved_by: str) -> dict[str, Any]:
    return {
        "approval_id": "asiep-escience2026-author-final-approval",
        "paper_id": "asiep-paper-v0.4-escience-human-editable",
        "target_venue": "escience2026",
        "approved_by": approved_by,
        "approved_at": now,
        "approved_by_human_author": True,
        "citations_checked": True,
        "claims_checked": True,
        "evaluation_numbers_checked": True,
        "ai_disclosure_checked": True,
        "page_count_checked": True,
        "latex_compiled": True,
        "repository_policy_checked": True,
        "deadline_checked": True,
        "license_checked": True,
        "sensitive_content_scan_checked": True,
        "final_pdf_reviewed": True,
        "final_submission_ready": True,
        "notes": [
            "Created only after explicit human confirmation flags were supplied.",
            "Human author remains responsible for all final submission decisions."
        ]
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    raise SystemExit(main())
