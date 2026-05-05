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


def test_submission_linter_final_stage_passes_marker_gate_after_integration() -> None:
    result = lint_submission(profile_path=PROFILE_PATH, stage="final")
    assert result["valid"] is True
    assert result["stage"] == "final"
    assert result["summary"]["paper_author_verify_markers"] == 0
    assert result["summary"]["latex_author_verify_markers"] == 0
    assert result["summary"]["citation_required_markers"] == 0


def test_profile_manifest_indexes_m10_submission_layer() -> None:
    manifest = _load_json(PROFILE_PATH)
    for key in (
        "human_authoring_protocol_schema_path",
        "submission_manifest_schema_path",
        "submission_lint_report_schema_path",
        "manuscript_v04_escience_path",
        "human_authoring_protocol_path",
        "submission_manifest_path",
        "latex_scaffold_path",
        "artifact_availability_statement_path",
        "final_human_checklist_path",
    ):
        assert key in manifest
        assert (ROOT / manifest[key]).exists()
    assert manifest["submission_linter_supported"] is True
    assert manifest["submission_linter_entrypoint"]["module"] == "asiep_submission_linter"


def test_repair_policy_and_error_registry_cover_m10_codes() -> None:
    policy = _load_json(ROOT / "profiles" / "asiep" / "v0.1" / "repair_policy.json")
    policy_codes = {item["code"] for item in policy["error_code_repair_map"]}
    assert M10_CODES <= policy_codes
    assert M10_CODES <= set(ERROR_CODES)


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
    assert "all `author_verify` markers removed" in text
    assert "all citation keys checked" in text
    assert "latex compiled" in text
    assert "8-page limit" in text


def test_final_check_script_fails_until_final_human_approval_and_layout_gates() -> None:
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
    assert any("Final author approval is missing" in error["message"] for error in payload["errors"])


def test_full_paper_integration_report_records_nonready_status() -> None:
    report = _load_json(ROOT / "submission" / "escience2026" / "full_paper_integration_report.json")
    assert report["remaining_author_verify_markers"] == 0
    assert report["remaining_citation_required_markers"] == 0
    assert report["missing_citation_keys"] == []
    assert report["forbidden_claims_found"] == []
    assert report["latex_synced"] is True
    assert report["final_submission_ready"] is False
    assert report["author_final_approval_exists"] is False
