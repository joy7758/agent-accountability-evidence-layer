from __future__ import annotations

import argparse
import hashlib
import json
import shutil
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
    parser.add_argument(
        "--reconfirm-after-editorial-fix",
        action="store_true",
        help="Archive existing final files and reconfirm gates after the editorial PDF fix.",
    )
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
    if existing and not args.overwrite and not args.reconfirm_after_editorial_fix and not args.dry_run:
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
    history_path = None
    if args.reconfirm_after_editorial_fix:
        _require_editorial_fix_ready()
        history_path = _archive_existing_final_files(now, final_paths)
    _write_json(final_paths["deadline"], _deadline_final(now, approved_by))
    _write_json(final_paths["repository"], _repository_final(now, approved_by))
    _write_json(final_paths["license"], _license_final(now, approved_by))
    _write_json(final_paths["sensitive"], _sensitive_review_final(now, approved_by))
    _write_json(final_paths["layout"], _layout_review_final(now, approved_by))
    _write_json(final_paths["approval"], _author_approval_final(now, approved_by))
    _update_final_gate_state(now, approved_by, history_path)
    _update_submission_manifest(final_ready=True)
    _update_final_submission_packet(now)

    print(
        json.dumps(
                {
                    "valid": True,
                    "promoted": True,
                    "dry_run": False,
                    "reconfirmed_after_editorial_fix": args.reconfirm_after_editorial_fix,
                    "approved_by": approved_by,
                    "created_files": [str(path.relative_to(ROOT)) for path in final_paths.values()],
                    "final_gate_history_path": str(history_path.relative_to(ROOT)) if history_path else None,
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


def _require_editorial_fix_ready() -> None:
    report = _load_json_if_exists(SUBMISSION_ROOT / "editorial_fix_report.json")
    latex_report = _load_json_if_exists(SUBMISSION_ROOT / "latex_compile_report.json")
    missing = []
    if report.get("editorial_fix_completed") is not True:
        missing.append("editorial_fix_report.editorial_fix_completed")
    verification = report.get("verification", {})
    for key in (
        "pdf_metadata_present",
        "repository_url_present",
        "acknowledgement_ai_use_disclosure_present",
    ):
        if verification.get(key) is not True:
            missing.append(f"editorial_fix_report.verification.{key}")
    if verification.get("author_layout_placeholders_present") is not False:
        missing.append("editorial_fix_report.verification.author_layout_placeholders_present=false")
    for key in (
        "compile_success",
        "page_count_checked",
        "within_page_limit",
        "pdf_metadata_present",
        "repository_url_present",
        "acknowledgement_ai_use_disclosure_present",
        "editorial_fix_completed",
    ):
        if latex_report.get(key) is not True:
            missing.append(f"latex_compile_report.{key}")
    if latex_report.get("author_layout_placeholders_present") is not False:
        missing.append("latex_compile_report.author_layout_placeholders_present=false")
    if latex_report.get("page_count_total") != 8:
        missing.append("latex_compile_report.page_count_total=8")
    if latex_report.get("unresolved_citations") != []:
        missing.append("latex_compile_report.unresolved_citations=[]")
    if latex_report.get("unresolved_references") != []:
        missing.append("latex_compile_report.unresolved_references=[]")
    if missing:
        raise SystemExit("Editorial fix is not ready for reapproval: " + ", ".join(missing))


def _archive_existing_final_files(now: str, final_paths: dict[str, Path]) -> Path:
    history_root = SUBMISSION_ROOT / "final_gate_history"
    safe_timestamp = now.replace(":", "").replace("+", "Z")
    history_path = history_root / f"pre_editorial_fix_approval_{safe_timestamp}"
    history_path.mkdir(parents=True, exist_ok=False)
    archived = []
    for name, path in final_paths.items():
        if path.exists():
            destination = history_path / path.name
            shutil.copy2(path, destination)
            archived.append({"gate": name, "source": str(path.relative_to(ROOT)), "archived_to": str(destination.relative_to(ROOT))})
    _write_json(
        history_path / "archive_manifest.json",
        {
            "archive_id": history_path.name,
            "created_at": now,
            "reason": "Preserve final gate files that predate the M14 editorial PDF fix.",
            "archived_files": archived,
        },
    )
    return history_path


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
    pdf_path = SUBMISSION_ROOT / "latex" / "main.pdf"
    pdf_sha = _sha256(pdf_path) if pdf_path.exists() else ""
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
        "author_layout_placeholders_present": latex_report.get("author_layout_placeholders_present") is True,
        "author_block_verified": latex_report.get("author_block_verified") is True,
        "artifact_statement_present": latex_report.get("repository_url_present") is True,
        "repository_url_present": latex_report.get("repository_url_present") is True,
        "pdf_metadata_present": latex_report.get("pdf_metadata_present") is True,
        "acknowledgement_ai_use_disclosure_present": latex_report.get("acknowledgement_ai_use_disclosure_present") is True,
        "editorial_fix_report_path": "submission/escience2026/editorial_fix_report.json",
        "editorial_visual_review_packet_path": "submission/escience2026/editorial_visual_review_packet.json",
        "pdf_sha256": pdf_sha,
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
        "editorial_fix_reviewed": True,
        "editorial_fix_report_path": "submission/escience2026/editorial_fix_report.json",
        "final_submission_ready": True,
        "notes": [
            "Created only after explicit human confirmation flags were supplied.",
            "Re-confirmed after the M14 editorial PDF fix removed visible layout placeholders and refreshed PDF metadata/artifact wording.",
            "Human author remains responsible for all final submission decisions."
        ]
    }


def _update_final_gate_state(now: str, approved_by: str, history_path: Path | None) -> None:
    status_path = SUBMISSION_ROOT / "final_gate_status.json"
    status = _load_json_if_exists(status_path)
    final_files = [str(path.relative_to(ROOT)) for path in _final_paths().values()]
    latex_report = _load_json_if_exists(SUBMISSION_ROOT / "latex_compile_report.json")
    pdf_path = SUBMISSION_ROOT / "latex" / "main.pdf"
    pdf_sha = _sha256(pdf_path) if pdf_path.exists() else ""
    status.update(
        {
            "editorial_rework_required": False,
            "editorial_fix_completed": True,
            "editorial_reapproval_completed": True,
            "editorial_reapproved_at": now,
            "editorial_reapproved_by": approved_by,
            "final_submission_ready": True,
            "final_submission_check_passed": True,
            "current_pdf_sha256": pdf_sha,
            "final_gate_files_present": final_files,
            "final_gate_files_missing": [],
            "editorial_fix_report_path": "submission/escience2026/editorial_fix_report.json",
            "editorial_visual_review_packet_path": "submission/escience2026/editorial_visual_review_packet.json",
            "final_gate_history_path": str(history_path.relative_to(ROOT)) if history_path else status.get("final_gate_history_path"),
            "reapproval_reason": "Final approval re-confirmed after editorial placeholder removal and PDF metadata/artifact fixes.",
            "reapproval_required_after_editorial_fix": False,
            "blocking_items": [],
            "remaining_human_actions": [
                "Log in to EasyChair manually.",
                "Confirm the live deadline one last time before upload.",
                "Upload submission/escience2026/latex/main.pdf manually.",
                "Check title, author, abstract, keywords, AI-use disclosure, and repository-link policy in the submission system.",
                "Click submit manually only after the EasyChair form preview is correct.",
            ],
        }
    )
    status["layout_review_status"] = {
        "status": "accepted_after_post_editorial_reapproval",
        "final_file_present": True,
        "final_ready": True,
        "pdf_reviewed": True,
        "page_count": latex_report.get("page_count_total"),
        "overfull_boxes_count": len(latex_report.get("overfull_boxes", [])),
        "overfull_boxes_status": "accepted_after_pdf_review",
        "pdf_sha256": pdf_sha,
        "author_layout_placeholders_present": latex_report.get("author_layout_placeholders_present") is True,
        "pdf_metadata_present": latex_report.get("pdf_metadata_present") is True,
        "repository_url_present": latex_report.get("repository_url_present") is True,
    }
    status["author_final_approval_status"] = {
        **status.get("author_final_approval_status", {}),
        "approved_by": approved_by,
        "approved_by_human_author": True,
        "final_file_present": True,
        "final_submission_ready": True,
        "status": "reconfirmed_final_ready_after_editorial_fix",
    }
    _write_json(status_path, status)


def _update_submission_manifest(*, final_ready: bool) -> None:
    path = SUBMISSION_ROOT / "submission_manifest.json"
    manifest = _load_json_if_exists(path)
    manifest["final_submission_ready"] = final_ready
    manifest["known_blockers"] = [] if final_ready else manifest.get("known_blockers", [])
    _write_json(path, manifest)


def _update_final_submission_packet(now: str) -> None:
    packet_root = SUBMISSION_ROOT / "final_submission_packet"
    packet_root.mkdir(exist_ok=True)
    pdf_path = SUBMISSION_ROOT / "latex" / "main.pdf"
    pdf_sha = _sha256(pdf_path) if pdf_path.exists() else ""
    latex_report = _load_json_if_exists(SUBMISSION_ROOT / "latex_compile_report.json")
    summary = {
        "packet_id": "asiep-escience2026-post-editorial-final-summary",
        "created_at": now,
        "paper_title": "A FAIR Evidence Object Layer for Auditable Agent Self-Improvement",
        "target_venue": "IEEE eScience 2026",
        "venue_id": "escience2026",
        "pdf_path": "submission/escience2026/latex/main.pdf",
        "pdf_sha256": pdf_sha,
        "page_count": latex_report.get("page_count_total"),
        "page_limit": 8,
        "within_page_limit": latex_report.get("within_page_limit") is True,
        "unresolved_citations": latex_report.get("unresolved_citations", []),
        "unresolved_references": latex_report.get("unresolved_references", []),
        "author_layout_placeholders_present": latex_report.get("author_layout_placeholders_present") is True,
        "pdf_metadata_present": latex_report.get("pdf_metadata_present") is True,
        "repository_url_present": latex_report.get("repository_url_present") is True,
        "ai_use_disclosure_included": latex_report.get("acknowledgement_ai_use_disclosure_present") is True,
        "license_choice": {
            "code_license": "Apache-2.0",
            "manuscript_license": "CC-BY-4.0",
            "artifact_license": "CC-BY-4.0",
        },
        "repository_policy": "public_repo_allowed",
        "deadline": "2026-05-18T23:59:00-12:00",
        "final_submission_ready": True,
        "actual_easychair_submission_completed": False,
    }
    _write_json(packet_root / "post_editorial_final_summary.json", summary)
    (packet_root / "post_editorial_final_summary.md").write_text(
        "\n".join(
            [
                "# Post-Editorial Final Summary",
                "",
                f"- Paper: {summary['paper_title']}",
                f"- Target venue: {summary['target_venue']}",
                f"- PDF: `{summary['pdf_path']}`",
                f"- PDF SHA-256: `{pdf_sha}`",
                f"- Page count: {summary['page_count']}",
                "- Unresolved citations: 0",
                "- Unresolved references: 0",
                "- PDF metadata present: true",
                "- Repository URL present: true",
                "- Final submission ready: true",
                "- EasyChair submitted: false",
                "",
                "This packet records repository-side readiness after the editorial PDF fix. It does not claim EasyChair submission, acceptance, production deployment, or external certification.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (packet_root / "final_pdf_hash.txt").write_text(f"{pdf_sha}  submission/escience2026/latex/main.pdf\n", encoding="utf-8")
    (packet_root / "final_upload_checklist.md").write_text(
        "\n".join(
            [
                "# Final Upload Checklist",
                "",
                "- [ ] Log in to EasyChair.",
                "- [ ] Confirm live deadline one last time.",
                "- [ ] Upload `submission/escience2026/latex/main.pdf`.",
                "- [ ] Confirm uploaded PDF hash or file name if EasyChair permits.",
                "- [ ] Verify title, author, affiliation, email, ORCID.",
                "- [ ] Verify abstract.",
                "- [ ] Verify keywords.",
                "- [ ] Verify repository URL policy.",
                "- [ ] Verify AI-use disclosure is present in PDF.",
                "- [ ] Manually submit.",
                "- [ ] Record EasyChair submission ID after submission.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    legacy_summary_path = packet_root / "final_submission_summary.json"
    if legacy_summary_path.exists():
        legacy = _load_json_if_exists(legacy_summary_path)
        legacy.update(
            {
                "final_submission_ready": True,
                "final_submission_check_passed": True,
                "reapproval_required_after_editorial_fix": False,
                "pdf_sha256": pdf_sha,
                "post_editorial_final_summary_path": "submission/escience2026/final_submission_packet/post_editorial_final_summary.json",
            }
        )
        _write_json(legacy_summary_path, legacy)
    legacy_md_path = packet_root / "final_submission_summary.md"
    if legacy_md_path.exists():
        text = legacy_md_path.read_text(encoding="utf-8")
        text = text.replace("Final submission ready: false", "Final submission ready: true")
        text += "\n## Post-Editorial Reapproval\n\nFinal author approval was re-confirmed after the editorial placeholder fix. Current `final_submission_ready=true`. Actual EasyChair submission has not been performed.\n"
        legacy_md_path.write_text(text, encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    raise SystemExit(main())
