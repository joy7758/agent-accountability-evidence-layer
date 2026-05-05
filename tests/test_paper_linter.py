from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from asiep_paper_linter import lint_paper
from asiep_validator import ERROR_CODES


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "profiles" / "asiep" / "v0.1" / "profile.json"
M7_CODES = {
    "PAPER_POLICY_VIOLATION",
    "PAPER_CLAIM_WITHOUT_EVIDENCE",
    "PAPER_EVALUATION_CLAIM_WITHOUT_METRIC",
    "PAPER_STRONG_CLAIM_UNDERSUPPORTED",
    "PAPER_FORBIDDEN_CLAIM",
    "PAPER_ORPHAN_CLAIM",
    "PAPER_MISSING_SECTION",
    "PAPER_MISSING_TABLE",
    "PAPER_MISSING_FIGURE",
    "PAPER_EVIDENCE_REF_MISSING",
    "PAPER_ASSET_MISSING",
    "PAPER_LINTER_FAILED",
}
REQUIRED_SECTIONS = [
    "Title",
    "Abstract",
    "Introduction",
    "Problem Statement",
    "Related Work",
    "Design Goals",
    "ASIEP Profile",
    "Lifecycle State Machine and Invariants",
    "Agent-native Toolchain",
    "Evaluation",
    "Attack Corpus and Robustness",
    "Cross-standard Mapping",
    "Discussion",
    "Limitations",
    "Standardization Path",
    "Conclusion",
]


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _assert_schema_valid(payload: dict, schema_path: Path) -> None:
    schema = _load_json(schema_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=str)
    assert errors == []


def _repo_ref_exists(ref: str) -> bool:
    return "://" not in ref and (ROOT / ref).exists()


def test_paper_policy_and_manuscript_schemas_are_valid() -> None:
    policy = _load_json(ROOT / "profiles" / "asiep" / "v0.1" / "paper_policy.json")
    assert policy["profile_name"] == "ASIEP"
    assert set(policy["allowed_claim_types"]) >= {
        "design_claim",
        "implementation_claim",
        "evaluation_claim",
        "mapping_claim",
        "limitation_claim",
        "positioning_claim",
    }
    _assert_schema_valid(
        _load_json(ROOT / "manuscript" / "claims_registry.json"),
        ROOT / "interfaces" / "asiep_paper_claim_registry.schema.json",
    )
    _assert_schema_valid(
        _load_json(ROOT / "manuscript" / "evidence_map.json"),
        ROOT / "interfaces" / "asiep_paper_evidence_map.schema.json",
    )


def test_claim_registry_evidence_rules() -> None:
    registry = _load_json(ROOT / "manuscript" / "claims_registry.json")
    for claim in registry["claims"]:
        if claim["claim_type"] != "limitation_claim":
            assert claim["evidence_refs"] or claim["artifact_refs"], claim["claim_id"]
        if claim["claim_type"] == "evaluation_claim":
            assert claim["metric_refs"], claim["claim_id"]
        if claim["claim_strength"] == "strong":
            assert len(claim["evidence_refs"]) >= 2, claim["claim_id"]
        for key in ("evidence_refs", "artifact_refs", "related_work_refs"):
            for ref in claim[key]:
                assert _repo_ref_exists(ref), f"{claim['claim_id']} missing {ref}"


def test_evidence_map_has_no_orphan_claims_and_existing_refs() -> None:
    registry = _load_json(ROOT / "manuscript" / "claims_registry.json")
    evidence_map = _load_json(ROOT / "manuscript" / "evidence_map.json")
    claim_ids = {claim["claim_id"] for claim in registry["claims"]}
    mapped_claims = {item["claim_id"] for item in evidence_map["claims"]}
    assert claim_ids == mapped_claims
    for group in ("sections", "tables", "figures"):
        for item in evidence_map[group]:
            assert set(item["claim_ids"]) <= claim_ids
            for ref in item.get("source_files", []) + item.get("required_artifacts", []):
                assert _repo_ref_exists(ref), ref
            if "output_path" in item:
                assert _repo_ref_exists(item["output_path"]), item["output_path"]


def test_paper_contains_required_sections_and_no_forbidden_phrases() -> None:
    paper_text = (ROOT / "manuscript" / "paper_v0.1.md").read_text(encoding="utf-8")
    headings = {line.lstrip("#").strip().lower() for line in paper_text.splitlines() if line.startswith("#")}
    assert any(line.startswith("# ") for line in paper_text.splitlines())
    for section in REQUIRED_SECTIONS:
        if section != "Title":
            assert section.lower() in headings
    policy = _load_json(ROOT / "profiles" / "asiep" / "v0.1" / "paper_policy.json")
    lower_text = paper_text.lower()
    for phrase in policy["forbidden_phrases"]:
        assert phrase.lower() not in lower_text


def test_paper_linter_output_is_valid() -> None:
    result = lint_paper(PROFILE_PATH)
    assert result["valid"] is True
    assert result["claims_checked"] >= 12
    assert result["summary"]["sections"] == 16
    assert result["summary"]["tables"] == 3
    assert result["summary"]["figures"] == 2
    assert result["errors"] == []


def test_profile_manifest_indexes_paper_layer() -> None:
    manifest = _load_json(PROFILE_PATH)
    for key in (
        "paper_policy_path",
        "paper_claim_registry_schema_path",
        "paper_evidence_map_schema_path",
        "paper_assets_path",
        "manuscript_path",
    ):
        assert key in manifest
        assert (ROOT / manifest[key]).exists()
    assert manifest["paper_linter_supported"] is True
    assert manifest["paper_linter_entrypoint"]["module"] == "asiep_paper_linter"


def test_repair_policy_and_error_registry_cover_m7_codes() -> None:
    policy = _load_json(ROOT / "profiles" / "asiep" / "v0.1" / "repair_policy.json")
    policy_codes = {item["code"] for item in policy["error_code_repair_map"]}
    assert M7_CODES <= policy_codes
    assert M7_CODES <= set(ERROR_CODES)


def test_paper_linter_cli_json_and_demo_script() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "asiep_paper_linter", "--profile", str(PROFILE_PATH), "--format", "json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    demo = subprocess.run([sys.executable, "scripts/paper_demo.py"], cwd=ROOT, check=True, capture_output=True, text=True)
    assert "linter_valid=True" in demo.stdout
