from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from asiep_evaluator import evaluate_profile
from asiep_validator import ERROR_CODES


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "profiles" / "asiep" / "v0.1" / "profile.json"
M6_CODES = {
    "EVAL_SCHEMA",
    "EVAL_CORPUS_MISSING",
    "EVAL_CROSSWALK_INCOMPLETE",
    "EVAL_PIPELINE_STEP_FAILED",
    "EVAL_METRIC_COMPUTATION_FAILED",
    "EVAL_REPORT_INVALID",
    "EVAL_EXPECTED_RESULT_MISMATCH",
    "EVAL_PAPER_ASSET_WRITE_FAILED",
    "EVAL_POLICY_VIOLATION",
}
CORE_FIELD_GROUPS = {
    "profile",
    "record",
    "lineage",
    "trigger",
    "actors",
    "runtime",
    "evidence",
    "evaluation",
    "gate",
    "integrity",
    "compliance",
    "bundle",
    "import",
    "package",
    "repair",
}


@pytest.fixture(scope="module")
def evaluation_report() -> dict:
    return evaluate_profile(PROFILE_PATH)


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _assert_schema_valid(payload: dict, schema_path: Path) -> None:
    schema = _load_json(schema_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=str)
    assert errors == []


def test_evaluation_inputs_match_schemas() -> None:
    _assert_schema_valid(
        _load_json(ROOT / "evaluation" / "crosswalk" / "asiep_v0.1_crosswalk.json"),
        ROOT / "interfaces" / "asiep_crosswalk_matrix.schema.json",
    )
    _assert_schema_valid(
        _load_json(ROOT / "evaluation" / "corpus" / "asiep_v0.1_corpus.json"),
        ROOT / "interfaces" / "asiep_corpus_manifest.schema.json",
    )
    policy = _load_json(ROOT / "profiles" / "asiep" / "v0.1" / "evaluation_policy.json")
    assert policy["profile_name"] == "ASIEP"
    assert set(policy["required_pipeline_steps"]) >= {
        "validate_examples",
        "generate_repair_plans",
        "resolve_bundles",
        "import_traces",
        "package_bundles",
        "verify_crosswalk_coverage",
        "generate_paper_tables",
    }


def test_profile_manifest_indexes_evaluator_and_assets() -> None:
    manifest = _load_json(PROFILE_PATH)
    for key in (
        "evaluation_policy_path",
        "evaluation_report_schema_path",
        "crosswalk_matrix_schema_path",
        "corpus_manifest_schema_path",
        "crosswalk_matrix_path",
        "corpus_manifest_path",
        "paper_assets_path",
    ):
        assert key in manifest
        assert (ROOT / manifest[key]).exists()
    assert manifest["evaluator_supported"] is True
    assert manifest["evaluator_entrypoint"]["module"] == "asiep_evaluator"


def test_crosswalk_matrix_covers_core_groups_and_invariants() -> None:
    crosswalk = _load_json(ROOT / "evaluation" / "crosswalk" / "asiep_v0.1_crosswalk.json")
    field_groups = {mapping["field_group"] for mapping in crosswalk["mappings"]}
    assert CORE_FIELD_GROUPS <= field_groups

    covered_invariants = {invariant for mapping in crosswalk["mappings"] for invariant in mapping["invariant_ids"]}
    assert {f"I{index}" for index in range(1, 11)} <= covered_invariants


def test_corpus_manifest_covers_m0_to_m5_sample_types() -> None:
    corpus = _load_json(ROOT / "evaluation" / "corpus" / "asiep_v0.1_corpus.json")
    target_types = {item["target_type"] for item in corpus["expected_results"]}
    assert {
        "evidence_example",
        "bundle",
        "import_request",
        "package_request",
        "repair_case",
        "generated_package",
    } <= target_types
    assert any(not item["expected_valid"] for item in corpus["expected_results"])
    assert any(item["expected_valid"] for item in corpus["expected_results"])


def test_evaluator_outputs_valid_report_and_paper_assets(evaluation_report: dict) -> None:
    _assert_schema_valid(evaluation_report, ROOT / "interfaces" / "asiep_evaluation_report.schema.json")
    _assert_schema_valid(
        _load_json(ROOT / "reports" / "asiep_v0.1_evaluation_report.json"),
        ROOT / "interfaces" / "asiep_evaluation_report.schema.json",
    )
    for path in (
        "paper_assets/README.md",
        "paper_assets/tables/crosswalk_matrix.md",
        "paper_assets/tables/evaluation_metrics.md",
        "paper_assets/tables/attack_corpus_results.md",
        "paper_assets/figures/pipeline_flow.mmd",
        "paper_assets/figures/state_machine.mmd",
        "paper_assets/paper_outline.md",
        "paper_assets/abstract_draft.md",
    ):
        assert (ROOT / path).exists()


def test_evaluator_metrics_meet_m6_acceptance(evaluation_report: dict) -> None:
    metrics = {metric["metric_id"]: metric for metric in evaluation_report["metric_results"]}
    assert metrics["tamper_detection_recall"]["value"] > 0
    assert metrics["false_positive_rate"]["value"] == 0
    assert metrics["privacy_policy_compliance"]["value"] == 1.0
    assert metrics["agent_readability"]["value"] == 1.0
    assert evaluation_report["attack_corpus_results"]["detected_attack_samples"] == evaluation_report["attack_corpus_results"]["total_attack_samples"]
    assert all(result["passed"] for result in evaluation_report["pipeline_results"])


def test_repair_policy_and_error_registry_cover_m6_codes() -> None:
    policy = _load_json(ROOT / "profiles" / "asiep" / "v0.1" / "repair_policy.json")
    policy_codes = {item["code"] for item in policy["error_code_repair_map"]}
    assert M6_CODES <= policy_codes
    assert M6_CODES <= set(ERROR_CODES)


def test_evaluate_profile_demo_script() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/evaluate_profile_demo.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "evaluation_id=evaluation:asiep-v0.1-m6" in result.stdout
    assert "false_positive_rate=0.0" in result.stdout
