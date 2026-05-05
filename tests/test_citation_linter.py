from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from asiep_citation_linter import lint_citations
from asiep_validator import ERROR_CODES


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "profiles" / "asiep" / "v0.1" / "profile.json"
M8_CODES = {
    "CITATION_SOURCE_REGISTRY_INVALID",
    "CITATION_CLAIM_MAP_INVALID",
    "CITATION_SOURCE_MISSING",
    "CITATION_UNVERIFIED_SOURCE_USED_AS_VERIFIED",
    "CITATION_EXTERNAL_CLAIM_WITHOUT_SOURCE",
    "CITATION_UNSUPPORTED_CLAIM",
    "CITATION_SECONDARY_USED_WHEN_PRIMARY_AVAILABLE",
    "CITATION_BIBTEX_MISSING",
    "CITATION_FORBIDDEN_PRACTICE",
    "CITATION_LINTER_FAILED",
    "CITATION_REQUIRED_MARKER_REMAINS",
}
REQUIRED_SOURCE_KEYS = {
    "self_refine_2023",
    "reflexion_2023",
    "voyager_2023",
    "agentdevel_2026",
    "otel_genai_semconv",
    "otel_genai_agent_spans",
    "langsmith_observability_concepts",
    "langsmith_feedback_docs",
    "w3c_prov_dm",
    "w3c_prov_o",
    "workflow_run_rocrate",
    "process_run_crate",
    "fdo_architecture_spec",
    "nist_ai_agent_standards",
    "eu_ai_act_article_12",
    "eu_ai_act_article_72",
    "owasp_llm_top10",
    "slsa_provenance_v1_1",
}


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _assert_schema_valid(payload: dict, schema_path: Path) -> None:
    schema = _load_json(schema_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=str)
    assert errors == []


def _bibtex_keys() -> set[str]:
    text = (ROOT / "references" / "asiep_references.bib").read_text(encoding="utf-8")
    return set(re.findall(r"@\w+\s*\{\s*([^,\s]+)", text))


def test_reference_policy_and_citation_schemas_are_valid() -> None:
    policy = _load_json(ROOT / "profiles" / "asiep" / "v0.1" / "reference_policy.json")
    assert policy["profile_name"] == "ASIEP"
    assert "fabricate_citation" in policy["forbidden_citation_practices"]
    _assert_schema_valid(
        _load_json(ROOT / "references" / "source_registry.json"),
        ROOT / "interfaces" / "asiep_source_registry.schema.json",
    )
    _assert_schema_valid(
        _load_json(ROOT / "references" / "citation_claim_map.json"),
        ROOT / "interfaces" / "asiep_citation_claim_map.schema.json",
    )


def test_source_registry_ids_and_keys_are_unique() -> None:
    registry = _load_json(ROOT / "references" / "source_registry.json")
    source_ids = [source["source_id"] for source in registry["sources"]]
    citation_keys = [source["citation_key"] for source in registry["sources"]]
    assert len(source_ids) == len(set(source_ids))
    assert len(citation_keys) == len(set(citation_keys))
    assert REQUIRED_SOURCE_KEYS <= set(citation_keys)


def test_citation_claim_map_sources_exist_and_required_claims_have_keys() -> None:
    registry = _load_json(ROOT / "references" / "source_registry.json")
    citation_map = _load_json(ROOT / "references" / "citation_claim_map.json")
    source_ids = {source["source_id"] for source in registry["sources"]}
    citation_keys = {source["citation_key"] for source in registry["sources"]}
    for item in citation_map["claim_citations"]:
        assert set(item["source_ids"]) <= source_ids, item["claim_id"]
        assert set(item["citation_keys"]) <= citation_keys, item["claim_id"]
        if item["required_citation"]:
            assert item["citation_keys"], item["claim_id"]
            assert item["source_ids"], item["claim_id"]


def test_paper_v02_has_citations_and_no_forbidden_markers() -> None:
    paper = (ROOT / "manuscript" / "paper_v0.2.md").read_text(encoding="utf-8")
    lower_paper = paper.lower()
    assert "citation_required" not in lower_paper
    policy = _load_json(ROOT / "profiles" / "asiep" / "v0.1" / "reference_policy.json")
    for phrase in policy["forbidden_overclaim_phrases"]:
        assert phrase.lower() not in lower_paper
    for key in REQUIRED_SOURCE_KEYS:
        assert f"@{key}" in paper


def test_related_work_and_reviewer_matrices_are_citation_hardened() -> None:
    related = (ROOT / "manuscript" / "related_work_matrix.md").read_text(encoding="utf-8")
    reviewer = (ROOT / "manuscript" / "reviewer_attack_defense_matrix.md").read_text(encoding="utf-8")
    assert "citation_key" in related
    assert "source_status" in related
    assert "ASIEP non-claim boundary" in related
    for key in REQUIRED_SOURCE_KEYS:
        assert key in related or key in reviewer
    assert "citation_keys" in reviewer
    assert "repository_evidence" in reviewer
    assert "next_strengthening_step" in reviewer


def test_bibtex_contains_all_source_registry_keys() -> None:
    registry = _load_json(ROOT / "references" / "source_registry.json")
    registry_keys = {source["citation_key"] for source in registry["sources"]}
    assert registry_keys <= _bibtex_keys()


def test_citation_linter_output_is_valid() -> None:
    result = lint_citations(PROFILE_PATH)
    assert result["valid"] is True
    assert result["sources_checked"] >= len(REQUIRED_SOURCE_KEYS)
    assert result["citations_checked"] >= 12
    assert result["summary"]["unverified_sources"] == 0
    assert result["errors"] == []


def test_profile_manifest_indexes_citation_layer() -> None:
    manifest = _load_json(PROFILE_PATH)
    for key in (
        "reference_policy_path",
        "source_registry_schema_path",
        "citation_claim_map_schema_path",
        "source_registry_path",
        "citation_claim_map_path",
        "bibliography_path",
        "manuscript_v02_path",
    ):
        assert key in manifest
        assert (ROOT / manifest[key]).exists()
    assert manifest["citation_linter_supported"] is True
    assert manifest["citation_linter_entrypoint"]["module"] == "asiep_citation_linter"


def test_repair_policy_and_error_registry_cover_m8_codes() -> None:
    policy = _load_json(ROOT / "profiles" / "asiep" / "v0.1" / "repair_policy.json")
    policy_codes = {item["code"] for item in policy["error_code_repair_map"]}
    assert M8_CODES <= policy_codes
    assert M8_CODES <= set(ERROR_CODES)


def test_citation_linter_cli_json_and_demo_script() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "asiep_citation_linter", "--profile", str(PROFILE_PATH), "--format", "json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    demo = subprocess.run([sys.executable, "scripts/citation_demo.py"], cwd=ROOT, check=True, capture_output=True, text=True)
    assert "citation_linter_valid=True" in demo.stdout
