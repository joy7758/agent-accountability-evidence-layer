from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from asiep_validator import ERROR_CODES
from asiep_venue_linter import lint_venue


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "profiles" / "asiep" / "v0.1" / "profile.json"
ESC_POLICY = ROOT / "venues" / "escience2026" / "venue_policy.json"
AIES_POLICY = ROOT / "venues" / "aies2026" / "venue_policy.json"
ESC_PAPER = ROOT / "manuscript" / "paper_v0.4_escience_human_editable.md"
AIES_BRIEF = ROOT / "manuscript" / "paper_v0.3_aies_positioning_brief.md"
M9_CODES = {
    "VENUE_POLICY_INVALID",
    "VENUE_PAPER_MISSING",
    "VENUE_REQUIRED_SECTION_MISSING",
    "VENUE_FORBIDDEN_CLAIM",
    "VENUE_CITATION_GAP",
    "VENUE_EVIDENCE_GAP",
    "VENUE_LIMITATION_MISSING",
    "VENUE_AI_USE_DISCLOSURE_MISSING",
    "VENUE_AI_POLICY_RISK",
    "VENUE_PAGE_BUDGET_RISK",
    "VENUE_READINESS_REPORT_INVALID",
    "VENUE_LINTER_FAILED",
}


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _assert_schema_valid(payload: dict, schema_path: Path) -> None:
    errors = sorted(Draft202012Validator(_load_json(schema_path)).iter_errors(payload), key=str)
    assert errors == []


def test_venue_policy_schema_and_policies_are_valid() -> None:
    schema_path = ROOT / "interfaces" / "asiep_venue_policy.schema.json"
    escience = _load_json(ESC_POLICY)
    aies = _load_json(AIES_POLICY)
    _assert_schema_valid(escience, schema_path)
    _assert_schema_valid(aies, schema_path)
    assert escience["venue_id"] == "escience2026"
    assert escience["page_limit"] == 8
    assert aies["venue_id"] == "aies2026"
    assert aies["ai_use_policy"]["ai_text_allowed"] is False


def test_paper_v04_escience_required_sections_and_boundaries() -> None:
    policy = _load_json(ESC_POLICY)
    text = ESC_PAPER.read_text(encoding="utf-8")
    headings = {line.lstrip("#").strip().lower() for line in text.splitlines() if line.startswith("#")}
    assert any(line.startswith("# ") for line in text.splitlines())
    for section in policy["required_sections"]:
        if section != "Title":
            assert section.lower() in headings
    lower_text = text.lower()
    for phrase in policy["forbidden_claims"]:
        assert phrase.lower() not in lower_text
    assert "local fixture" in lower_text
    assert "minimal implementation" in lower_text
    assert "not external certification" in lower_text
    assert "ai-use disclosure" in lower_text
    assert "ai-assisted planning" in lower_text


def test_aies_brief_is_caution_only() -> None:
    text = AIES_BRIEF.read_text(encoding="utf-8").lower()
    assert "manual rewrite required" in text
    assert "codex-generated draft should not be submitted directly" in text
    assert "human-authored prose" in text
    assert "sociotechnical" in text


def test_venue_linter_outputs_valid_escience_and_policy_risk_for_aies() -> None:
    escience = lint_venue(ESC_POLICY, ESC_PAPER)
    aies = lint_venue(AIES_POLICY, AIES_BRIEF)
    _assert_schema_valid(escience, ROOT / "interfaces" / "asiep_venue_readiness_report.schema.json")
    _assert_schema_valid(aies, ROOT / "interfaces" / "asiep_venue_readiness_report.schema.json")
    assert escience["valid"] is True
    assert escience["readiness_score"] >= 80
    assert escience["errors"] == []
    assert aies["valid"] is True
    assert any(warning["code"] == "VENUE_AI_POLICY_RISK" for warning in aies["warnings"])


def test_submission_assets_exist_and_readiness_report_schema_valid() -> None:
    subprocess.run([sys.executable, "scripts/venue_demo.py"], cwd=ROOT, check=True, capture_output=True, text=True)
    required_escience_assets = [
        "readiness_report.json",
        "submission_checklist.md",
        "author_ai_use_disclosure_draft.md",
        "abstract_200words.md",
        "contribution_box.md",
        "limitations_box.md",
        "reviewer_response_seed.md",
        "page_budget_notes.md",
    ]
    for name in required_escience_assets:
        assert (ROOT / "submission" / "escience2026" / name).exists(), name
    for name in (
        "positioning_notes.md",
        "ai_use_policy_risk.md",
        "manual_rewrite_required.md",
        "governance_reframing.md",
    ):
        assert (ROOT / "submission" / "aies2026" / name).exists(), name
    _assert_schema_valid(
        _load_json(ROOT / "submission" / "escience2026" / "readiness_report.json"),
        ROOT / "interfaces" / "asiep_venue_readiness_report.schema.json",
    )


def test_profile_manifest_indexes_venue_layer() -> None:
    manifest = _load_json(PROFILE_PATH)
    for key in (
        "venue_policy_schema_path",
        "venue_readiness_report_schema_path",
        "manuscript_v03_escience_path",
        "manuscript_v03_aies_brief_path",
    ):
        assert key in manifest
        assert (ROOT / manifest[key]).exists()
    assert manifest["venue_linter_supported"] is True
    assert manifest["venue_linter_entrypoint"]["module"] == "asiep_venue_linter"
    assert "escience2026" in manifest["target_venue_assets"]
    assert "aies2026" in manifest["target_venue_assets"]


def test_repair_policy_and_error_registry_cover_m9_codes() -> None:
    policy = _load_json(ROOT / "profiles" / "asiep" / "v0.1" / "repair_policy.json")
    policy_codes = {item["code"] for item in policy["error_code_repair_map"]}
    assert M9_CODES <= policy_codes
    assert M9_CODES <= set(ERROR_CODES)


def test_venue_linter_cli_json_and_demo_script() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "asiep_venue_linter",
            "--venue",
            str(ESC_POLICY),
            "--paper",
            str(ESC_PAPER),
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
    demo = subprocess.run([sys.executable, "scripts/venue_demo.py"], cwd=ROOT, check=True, capture_output=True, text=True)
    assert "target_recommendation=escience2026" in demo.stdout
