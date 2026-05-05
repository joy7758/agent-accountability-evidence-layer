from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from asiep_submission_linter import lint_submission
from asiep_validator import ERROR_CODES


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "profiles" / "asiep" / "v0.1" / "profile.json"
MANIFEST_PATH = ROOT / "submission" / "escience2026" / "submission_manifest.json"
PROTOCOL_PATH = ROOT / "submission" / "escience2026" / "human_authoring_protocol.json"
VENUE_POLICY_PATH = ROOT / "venues" / "escience2026" / "venue_policy.json"
PAPER_V04 = ROOT / "manuscript" / "paper_v0.4_escience_human_editable.md"
M10_CODES = {
    "SUBMISSION_MANIFEST_INVALID",
    "SUBMISSION_HUMAN_PROTOCOL_INVALID",
    "SUBMISSION_MANUSCRIPT_MISSING",
    "SUBMISSION_AUTHOR_VERIFY_MARKERS_MISSING",
    "SUBMISSION_AUTHOR_VERIFY_MARKERS_REMAIN",
    "SUBMISSION_LATEX_SCAFFOLD_MISSING",
    "SUBMISSION_AI_DISCLOSURE_MISSING",
    "SUBMISSION_ARTIFACT_STATEMENT_MISSING",
    "SUBMISSION_DEADLINE_VERIFICATION_MISSING",
    "SUBMISSION_PAGE_BUDGET_RISK",
    "SUBMISSION_FINAL_CHECKLIST_MISSING",
    "SUBMISSION_LINTER_FAILED",
}
M12_CODES = {
    "LATEX_COMPILE_POLICY_INVALID",
    "LATEX_ROOT_MISSING",
    "LATEX_MAIN_MISSING",
    "LATEX_COMPILE_FAILED",
    "LATEX_PDF_MISSING",
    "LATEX_PAGE_COUNT_FAILED",
    "LATEX_PAGE_BUDGET_EXCEEDED",
    "LATEX_REFERENCE_BOUNDARY_UNCHECKED",
    "LATEX_BIBTEX_FAILED",
    "LATEX_UNRESOLVED_CITATION",
    "LATEX_UNRESOLVED_REFERENCE",
    "LATEX_LAYOUT_CHECK_REQUIRED",
    "FINAL_APPROVAL_MISSING",
    "FINAL_REPOSITORY_POLICY_UNDECIDED",
    "FINAL_DEADLINE_UNVERIFIED",
}


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _assert_schema_valid(payload: dict, schema_path: Path) -> None:
    errors = sorted(Draft202012Validator(_load_json(schema_path)).iter_errors(payload), key=str)
    assert errors == []


def test_m10_schemas_and_assets_are_valid() -> None:
    profile = _load_json(PROFILE_PATH)
    _assert_schema_valid(_load_json(PROTOCOL_PATH), ROOT / profile["human_authoring_protocol_schema_path"])
    _assert_schema_valid(_load_json(MANIFEST_PATH), ROOT / profile["submission_manifest_schema_path"])
    report = lint_submission(MANIFEST_PATH)
    _assert_schema_valid(report, ROOT / profile["submission_lint_report_schema_path"])


def test_escience_policy_records_m10_constraints() -> None:
    policy = _load_json(VENUE_POLICY_PATH)
    _assert_schema_valid(policy, ROOT / "interfaces" / "asiep_venue_policy.schema.json")
    assert policy["page_limit"] == 8
    assert policy["reference_exclusion_policy"] == "references_excluded"
    assert policy["format"] == "IEEE 8.5x11 double-column, single-spaced 10-point font"
    assert policy["review_mode"] == "single-blind"
    assert policy["paper_submission_deadline_raw"] == "Monday, May 18, 2026 / Tuesday, May 19, 2026 11:59 PM AoE as shown on CFP"
    assert policy["requires_human_deadline_verification"] is True
    assert "IEEE conference proceedings" in policy["proceedings_policy"]


def test_paper_v04_is_human_editable_not_final_submission() -> None:
    text = PAPER_V04.read_text(encoding="utf-8")
    lower = text.lower()
    assert "author_verify" not in lower
    assert "local fixture" in lower
    assert "minimal implementation" in lower
    assert "not external certification" in lower


def test_ieee_ai_disclosure_and_latex_scaffold_are_present() -> None:
    disclosure = (ROOT / "submission" / "escience2026" / "author_ai_use_disclosure_draft.md").read_text(encoding="utf-8").lower()
    assert "acknowledgements" in disclosure
    assert "codex" in disclosure and "openai" in disclosure
    assert "sections" in disclosure
    assert "level of use" in disclosure
    assert "human authors" in disclosure and "responsible" in disclosure
    latex = (ROOT / "submission" / "escience2026" / "latex" / "main.tex").read_text(encoding="utf-8").lower()
    assert "ieeetran" in latex
    assert "conference" in latex


def test_submission_linter_outputs_valid_human_rewrite_package() -> None:
    result = lint_submission(MANIFEST_PATH)
    assert result["valid"] is True
    assert result["stage"] == "rewrite"
    assert result["human_rewrite_required"] is True
    assert result["final_submission_ready"] is False
    assert result["summary"]["author_verify_markers"] == 0
    assert result["summary"]["deadline_requires_human_verification"] is True
    assert result["summary"]["ieee_ai_disclosure_ready"] is True
    assert result["summary"]["latex_scaffold_ready"] is True
    assert result["errors"] == []


def test_submission_linter_final_stage_passes_after_human_final_gates() -> None:
    result = lint_submission(profile_path=PROFILE_PATH, stage="final")
    assert result["valid"] is True
    assert result["stage"] == "final"
    assert result["summary"]["paper_author_verify_markers"] == 0
    assert result["summary"]["latex_author_verify_markers"] == 0
    assert result["summary"]["citation_required_markers"] == 0
    assert result["final_submission_ready"] is False
    assert result["errors"] == []


def test_profile_manifest_indexes_m10_submission_layer() -> None:
    manifest = _load_json(PROFILE_PATH)
    for key in (
        "human_authoring_protocol_schema_path",
        "submission_manifest_schema_path",
        "submission_lint_report_schema_path",
        "latex_compile_report_schema_path",
        "author_final_approval_schema_path",
        "manuscript_v04_escience_path",
        "human_authoring_protocol_path",
        "submission_manifest_path",
        "latex_scaffold_path",
        "artifact_availability_statement_path",
        "final_human_checklist_path",
        "latex_compile_report_path",
        "sensitive_content_scan_report_path",
        "license_decision_template_path",
        "license_decision_support_path",
        "sensitive_content_scan_script",
        "governance_drafts_path",
        "final_gate_status_path",
        "ai_assisted_submission_notes_path",
        "repository_policy_decision_template_path",
        "deadline_verification_template_path",
        "author_final_approval_template_path",
    ):
        assert key in manifest
        assert (ROOT / manifest[key]).exists()
    assert manifest["submission_linter_supported"] is True
    assert manifest["submission_linter_entrypoint"]["module"] == "asiep_submission_linter"


def test_repair_policy_and_error_registry_cover_m10_codes() -> None:
    policy = _load_json(ROOT / "profiles" / "asiep" / "v0.1" / "repair_policy.json")
    policy_codes = {item["code"] for item in policy["error_code_repair_map"]}
    assert M10_CODES <= policy_codes
    assert M12_CODES <= policy_codes
    assert M10_CODES <= set(ERROR_CODES)
    assert M12_CODES <= set(ERROR_CODES)


def test_submission_linter_cli_and_demo_script() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "asiep_submission_linter",
            "--profile",
            str(PROFILE_PATH),
            "--stage",
            "rewrite",
            "--format",
            "json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    demo = subprocess.run([sys.executable, "scripts/submission_demo.py"], cwd=ROOT, check=True, capture_output=True, text=True)
    assert "submission_linter_valid=True" in demo.stdout
    assert "final_submission_ready=False" in demo.stdout


def test_human_rewrite_board_and_section_packets_exist() -> None:
    board = _load_json(ROOT / "submission" / "escience2026" / "human_rewrite_board.json")
    assert board["current_status"] == "integrated_pending_final_verification"
    assert len(board["sections"]) >= 12
    assert all(section["status"] == "human_rewritten" for section in board["sections"])
    assert all(section["author_verify_markers_count"] == 0 for section in board["sections"])
    packets = list((ROOT / "submission" / "escience2026" / "section_packets").glob("*_packet.md"))
    assert len(packets) >= 12
    for packet in packets:
        text = packet.read_text(encoding="utf-8").lower()
        assert "human rewrite checklist" in text
        assert "claims to preserve" in text
        assert "overclaim phrases to avoid" in text


def test_final_human_checklist_contains_m11_gates() -> None:
    text = (ROOT / "submission" / "escience2026" / "final_human_checklist.md").read_text(encoding="utf-8").lower()
    assert "m11 final gates" in text
    assert "m12 latex and final submission gates" in text
    assert "all `author_verify` markers removed" in text
    assert "all citation keys checked" in text
    assert "latex compiled" in text
    assert "8-page limit" in text
    assert "unresolved citations = 0" in text
    assert "repository/anonymization policy decided" in text


def test_final_check_script_requires_reapproval_after_editorial_fix() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/final_submission_check.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["valid"] is False
    assert payload["remaining_author_verify_markers"] == 0
    assert any("predates the latest editorial fix" in error["message"] for error in payload["errors"])
    assert payload["checks"]["author_final_approval_exists"] is True
    assert payload["checks"]["repository_decision_exists"] is True
    assert payload["checks"]["deadline_verification_exists"] is True
    assert payload["checks"]["license_decision_final_ready"] is True
    assert payload["checks"]["sensitive_content_review_final_ready"] is True
    assert payload["checks"]["layout_review_final_ready"] is True
    assert payload["checks"]["editorial_fix_completed"] is True
    assert payload["checks"]["final_approval_after_editorial_fix"] is False


def test_full_paper_integration_report_records_nonready_status() -> None:
    report = _load_json(ROOT / "submission" / "escience2026" / "full_paper_integration_report.json")
    assert report["remaining_author_verify_markers"] == 0
    assert report["remaining_citation_required_markers"] == 0
    assert report["missing_citation_keys"] == []
    assert report["forbidden_claims_found"] == []
    assert report["latex_synced"] is True
    assert report["final_submission_ready"] is False
    assert report["author_final_approval_exists"] is True
    assert report["latex_compile_report_path"] == "submission/escience2026/latex_compile_report.json"
    assert report["final_repository_policy_decided"] is True
    assert report["final_deadline_verified"] is True
    assert report["reapproval_required_after_editorial_fix"] is True


def test_m12_latex_compile_report_and_templates_exist() -> None:
    profile = _load_json(PROFILE_PATH)
    compile_report = _load_json(ROOT / "submission" / "escience2026" / "latex_compile_report.json")
    _assert_schema_valid(compile_report, ROOT / profile["latex_compile_report_schema_path"])
    assert compile_report["final_submission_ready"] is False
    assert compile_report["page_limit"] == 8
    assert compile_report["references_excluded"] is True
    assert "overfull_boxes" in compile_report
    assert compile_report["author_placeholders_present"] is False
    assert compile_report["author_block_verified"] is True
    assert compile_report["author_block_requires_final_human_review"] is True
    assert compile_report["author_block_missing_strings"] == []
    assert compile_report["pdf_metadata_present"] is True
    assert compile_report["author_layout_placeholders_present"] is False
    assert compile_report["repository_url_present"] is True
    assert compile_report["acknowledgement_ai_use_disclosure_present"] is True
    assert compile_report["editorial_fix_completed"] is True
    assert (ROOT / "submission" / "escience2026" / "repository_policy_decision.template.json").exists()
    assert (ROOT / "submission" / "escience2026" / "deadline_verification.template.json").exists()
    assert (ROOT / "submission" / "escience2026" / "license_decision.template.json").exists()
    assert (ROOT / "submission" / "escience2026" / "license_decision.json").exists()
    approval_template = _load_json(ROOT / "submission" / "escience2026" / "author_final_approval.template.json")
    _assert_schema_valid(approval_template, ROOT / profile["author_final_approval_schema_path"])
    assert approval_template["approved_by_human_author"] is False
    final_approval = _load_json(ROOT / "submission" / "escience2026" / "author_final_approval.json")
    _assert_schema_valid(final_approval, ROOT / profile["author_final_approval_schema_path"])
    assert final_approval["approved_by_human_author"] is True
    assert (ROOT / "submission" / "escience2026" / "repository_policy_decision.json").exists()
    assert (ROOT / "submission" / "escience2026" / "deadline_verification.json").exists()
    assert (ROOT / "submission" / "escience2026" / "sensitive_content_review.json").exists()
    assert (ROOT / "submission" / "escience2026" / "layout_review.json").exists()


def test_governance_drafts_are_nonfinal_and_do_not_satisfy_final_gate() -> None:
    drafts = ROOT / "submission" / "escience2026" / "governance_drafts"
    assert (drafts / "README.md").exists()
    assert (drafts / "deadline_verification.draft.json").exists()
    assert (drafts / "repository_policy_decision.draft.json").exists()
    author_draft = _load_json(drafts / "author_final_approval.draft.json")
    assert author_draft["approval_status"]["approved_by_human_author"] is False
    assert author_draft["approval_status"]["status"] == "pending_author_final_confirmation"
    final_gate_status = _load_json(ROOT / "submission" / "escience2026" / "final_gate_status.json")
    assert final_gate_status["governance_drafts_present"] is True
    assert final_gate_status["final_submission_ready"] is False
    assert final_gate_status["author_final_approval_status"]["final_file_present"] is True
    assert final_gate_status["author_final_approval_status"]["approved_by_human_author"] is True


def test_sensitive_content_scan_report_is_nonfinal_until_human_review() -> None:
    report = _load_json(ROOT / "submission" / "escience2026" / "sensitive_content_scan_report.json")
    assert report["scan_completed"] is True
    assert report["requires_human_review"] is True
    assert report["final_ready"] is False
    assert "not full data-loss prevention" in " ".join(report["limitations"]).lower()
    final_gate_status = _load_json(ROOT / "submission" / "escience2026" / "final_gate_status.json")
    assert final_gate_status["sensitive_content_scan_status"]["scan_completed"] is True
    assert final_gate_status["sensitive_content_scan_status"]["final_ready"] is True
    assert final_gate_status["license_status"]["final_ready"] is True
    review = _load_json(ROOT / "submission" / "escience2026" / "sensitive_content_review.json")
    assert review["final_ready"] is True
    assert review["possible_sensitive_content_unresolved"] is False


def test_latex_submission_demo_runs_and_preserves_final_ready_status() -> None:
    demo = subprocess.run([sys.executable, "scripts/latex_submission_demo.py"], cwd=ROOT, check=True, capture_output=True, text=True)
    payload = json.loads(demo.stdout)
    assert payload["paper_linter_valid"] is True
    assert payload["citation_linter_valid"] is True
    assert payload["submission_linter_rewrite_valid"] is True
    assert payload["final_submission_ready"] is False
    assert payload["final_submission_check_valid"] is False


def test_final_gate_recommendations_remain_pending_after_final_promotion() -> None:
    recommendations = ROOT / "submission" / "escience2026" / "final_gate_recommendations"
    assert (recommendations / "README.md").exists()
    index = _load_json(recommendations / "index.json")
    assert index["current_final_submission_ready"] is False
    assert index["pending_final_human_review"] is True
    assert index["promotion_required_for_final_submission"] is True
    assert len(index["recommended_decisions"]) == 8
    for path in (
        "author_identity.recommended.json",
        "license_decision.recommended.json",
        "repository_policy_decision.recommended.json",
        "deadline_verification.recommended.json",
        "layout_review.recommended.json",
        "sensitive_content_review.recommended.json",
        "ai_use_disclosure_review.recommended.json",
        "author_final_approval.recommended_plan.json",
    ):
        payload = _load_json(recommendations / path)
        assert payload["pending_final_human_review"] is True
        if "final_ready" in payload:
            assert payload["final_ready"] is False
        else:
            assert payload["final_submission_ready"] is False
    assert (ROOT / "submission" / "escience2026" / "deadline_verification.json").exists()
    assert (ROOT / "submission" / "escience2026" / "repository_policy_decision.json").exists()
    assert (ROOT / "submission" / "escience2026" / "license_decision.json").exists()
    assert (ROOT / "submission" / "escience2026" / "sensitive_content_review.json").exists()
    assert (ROOT / "submission" / "escience2026" / "layout_review.json").exists()
    assert (ROOT / "submission" / "escience2026" / "author_final_approval.json").exists()


def test_final_gate_status_records_promotion_with_final_readiness() -> None:
    status = _load_json(ROOT / "submission" / "escience2026" / "final_gate_status.json")
    assert status["final_gate_recommendations_present"] is True
    assert status["author_block_status"] == "fixed_pending_final_human_review"
    assert status["author_identity_recommendation_present"] is True
    assert status["author_placeholders_present"] is False
    assert status["recommended_decisions_count"] == 8
    assert status["recommended_license"] == "Apache-2.0 code + CC-BY-4.0 manuscript/artifacts"
    assert status["recommended_repository_policy"] == "public_repo_allowed"
    assert status["recommended_planning_deadline"] == "2026-05-18T23:59:00-12:00"
    assert status["recommended_layout_status"] == "provisionally_acceptable_pending_pdf_review"
    assert status["recommended_sensitive_scan_status"] == "expected_fixture_or_documentation_markers_pending_final_review"
    assert status["recommended_ai_disclosure_status"] == "recommended_acceptable_pending_final_author_review"
    assert status["promotion_required_for_final_submission"] is False
    assert len(status["final_gate_files_present"]) == 6
    assert status["final_gate_files_missing"] == []
    assert status["final_submission_ready"] is False
    assert status["final_submission_check_passed"] is False
    assert status["editorial_fix_completed"] is True
    assert status["reapproval_required_after_editorial_fix"] is True


def test_promote_recommended_gates_requires_explicit_human_confirmation() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/promote_recommended_gates.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["valid"] is False
    assert payload["promoted"] is False
    assert "human_confirm_final_gates" in payload["missing_confirmations"]
    assert "approved_by" in payload["missing_confirmations"]


def test_final_submission_check_blocks_until_editorial_reapproval() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/final_submission_check.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["valid"] is False
    assert payload["checks"]["final_gate_recommendations_present"] is True
    assert payload["checks"]["sensitive_content_review_exists"] is True
    assert payload["checks"]["layout_review_exists"] is True
    assert "final author approval predates the latest editorial fix" in payload["blocking_items"]


def test_final_review_packet_exists_and_keeps_submission_nonfinal() -> None:
    packet = ROOT / "submission" / "escience2026" / "final_review_packet"
    dashboard = _load_json(packet / "final_review_dashboard.json")
    pdf_packet = _load_json(packet / "pdf_review_packet.json")
    sensitive_packet = _load_json(packet / "sensitive_scan_review_packet.json")
    assert (packet / "README.md").exists()
    assert (packet / "final_review_dashboard.md").exists()
    assert (packet / "promotion_command_preview.sh").exists()
    assert (packet / "promotion_command_preview.md").exists()
    assert dashboard["final_submission_ready"] is False
    assert dashboard["page_count"] == 8
    assert dashboard["unresolved_citations_count"] == 0
    assert dashboard["unresolved_references_count"] == 0
    assert dashboard["overfull_boxes_count"] == 4
    assert dashboard["recommended_decisions"]["license"] == "Apache-2.0 code + CC-BY-4.0 manuscript/artifacts"
    assert dashboard["final_gate_files_present"] == []
    assert pdf_packet["final_pdf_approved"] is False
    assert pdf_packet["pdf_generated"] is True
    assert pdf_packet["within_8_page_limit"] is True
    assert sensitive_packet["final_ready"] is False
    assert sensitive_packet["findings_count"] == 7
    assert sensitive_packet["human_review_required"] is True


def test_promote_recommended_gates_dry_run_does_not_create_final_files() -> None:
    final_files = [
        ROOT / "submission" / "escience2026" / "deadline_verification.json",
        ROOT / "submission" / "escience2026" / "repository_policy_decision.json",
        ROOT / "submission" / "escience2026" / "license_decision.json",
        ROOT / "submission" / "escience2026" / "sensitive_content_review.json",
        ROOT / "submission" / "escience2026" / "layout_review.json",
        ROOT / "submission" / "escience2026" / "author_final_approval.json",
    ]
    result = subprocess.run(
        [
            sys.executable,
            "scripts/promote_recommended_gates.py",
            "--human-confirm-final-gates",
            "--approved-by",
            "DRY RUN HUMAN AUTHOR",
            "--confirm-deadline",
            "--confirm-repository-policy",
            "--confirm-license",
            "--confirm-sensitive-scan",
            "--confirm-layout",
            "--confirm-ai-disclosure",
            "--confirm-final-pdf",
            "--dry-run",
            "--format",
            "json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    assert payload["dry_run"] is True
    assert payload["promoted"] is False
    assert payload["missing_required_flags"] == []
    assert len(payload["would_create_files"]) == 6
    assert all(path.exists() for path in final_files)
    assert payload["existing_files"] == [str(path.relative_to(ROOT)) for path in final_files]


def test_promotion_dry_run_demo_succeeds_after_final_promotion() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/promotion_dry_run_demo.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["missing_flags_check_passed"] is True
    assert payload["dry_run_success"] is True
    assert payload["dry_run_created_final_gate_files"] is False
    assert payload["final_gate_files_present"] is True
    assert payload["final_submission_ready"] is False
    assert payload["final_submission_check_valid"] is False


def test_final_gate_status_records_m13_review_packet_and_dry_run() -> None:
    status = _load_json(ROOT / "submission" / "escience2026" / "final_gate_status.json")
    assert status["final_review_packet_present"] is True
    assert status["final_review_packet_path"] == "submission/escience2026/final_review_packet"
    assert status["promotion_dry_run_supported"] is True
    assert status["promotion_dry_run_completed"] is True
    assert status["final_submission_ready"] is False


def test_final_submission_packet_exists_after_promotion() -> None:
    packet = ROOT / "submission" / "escience2026" / "final_submission_packet"
    summary = _load_json(packet / "final_submission_summary.json")
    index = _load_json(packet / "final_gate_files_index.json")
    assert (packet / "README.md").exists()
    assert (packet / "final_submission_summary.md").exists()
    assert (packet / "final_checks_report.md").exists()
    assert summary["final_submission_ready"] is False
    assert summary["reapproval_required_after_editorial_fix"] is True
    assert summary["actual_easychair_submission_completed"] is False
    assert summary["page_count"] == 8
    assert summary["unresolved_citations"] == []
    assert summary["unresolved_references"] == []
    assert summary["author_block_verified"] is True
    assert index["all_present"] is True
    assert len(index["final_gate_files"]) == 6
