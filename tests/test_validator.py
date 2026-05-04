from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from asiep_validator import ERROR_CODES
from asiep_validator import validate_file, validate_profile


ROOT = Path(__file__).resolve().parents[1]


def test_valid_example_passes() -> None:
    report = validate_file(ROOT / "examples" / "valid_chatbot_improvement.json")
    assert report.valid
    assert report.codes == ["VALID"]


def test_negative_examples_return_expected_codes() -> None:
    expected = {
        "invalid_missing_gate_report.json": ["SCHEMA"],
        "invalid_promote_with_regression.json": ["INV_SAFETY_REGRESSION"],
        "invalid_hash_chain_break.json": ["REF_UNRESOLVED"],
        "invalid_promote_with_p2f_threshold_violation.json": ["INV_FLIP_THRESHOLD"],
        "invalid_transition_order.json": ["STATE_TRANSITION"],
    }
    for filename, codes in expected.items():
        report = validate_file(ROOT / "examples" / filename)
        assert not report.valid
        assert report.codes == codes


def test_rollback_state_requires_rollback_evidence() -> None:
    with (ROOT / "examples" / "valid_chatbot_improvement.json").open(encoding="utf-8") as handle:
        profile = json.load(handle)

    profile["lifecycle"].append(
        {
            "event_id": "event:006-rolled-back",
            "state": "ROLLED_BACK",
            "at": "2026-05-05T00:25:00Z",
            "actor": "agent:gatekeeper",
            "evidence_refs": ["ev:gate-report"],
        }
    )

    report = validate_profile(profile)
    assert not report.valid
    assert report.codes == ["ROLLBACK_EVIDENCE"]


def test_digest_basic_check_is_validator_layer() -> None:
    with (ROOT / "examples" / "valid_chatbot_improvement.json").open(encoding="utf-8") as handle:
        profile = json.load(handle)

    profile["references"][0]["digest"]["value"] = "not-a-sha256"

    report = validate_profile(profile)
    assert not report.valid
    assert report.codes == ["DIGEST_BASIC"]


def test_profile_manifest_is_agent_readable() -> None:
    manifest_path = ROOT / "profiles" / "asiep" / "v0.1" / "profile.json"
    with manifest_path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)

    required = {
        "profile_name",
        "profile_version",
        "profile_uri",
        "schema_path",
        "jsonld_context_path",
        "state_machine_doc",
        "invariants_doc",
        "validator_entrypoint",
        "examples",
        "expected_error_codes",
        "supported_output_formats",
        "conformance_matrix_path",
    }
    assert required <= set(manifest)
    assert manifest["profile_name"] == "ASIEP"
    assert manifest["profile_version"] == "0.1.0"

    for key in ("schema_path", "jsonld_context_path", "state_machine_doc", "invariants_doc", "conformance_matrix_path"):
        assert (ROOT / manifest[key]).exists()

    for group in ("valid_examples", "invalid_examples"):
        for example in manifest["examples"][group]:
            assert (ROOT / example["path"]).exists()

    assert set(manifest["expected_error_codes"]) <= set(ERROR_CODES)


def test_conformance_matrix_covers_all_invariants() -> None:
    with (ROOT / "conformance" / "asiep_v0.1_matrix.yaml").open(encoding="utf-8") as handle:
        matrix = json.load(handle)

    invariants = matrix["invariants"]
    assert {item["invariant_id"] for item in invariants} == {f"I{index}" for index in range(1, 11)}

    for item in invariants:
        assert item["invariant_text"]
        assert item["required_fields"]
        assert item["schema_json_pointers"]
        assert item["validator_function_or_rule"] or item["expected_error_codes"]
        assert item["positive_examples"]
        assert item["negative_examples"]
        assert set(item["expected_error_codes"]) <= set(ERROR_CODES)
        assert set(item["related_standard_mapping"]) == {"PROV", "OpenTelemetry", "FDO", "RO-Crate"}


def test_validator_json_output_valid_example() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "asiep_validator",
            "examples/valid_chatbot_improvement.json",
            "--format",
            "json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["profile"] == "ASIEP"
    assert payload["profile_version"] == "0.1.0"
    assert payload["valid"] is True
    assert payload["record_id"] == "asiep:chatbot-improvement-001"
    assert payload["errors"] == []
    assert payload["warnings"] == []


def test_validator_json_output_invalid_example_has_agent_error() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "asiep_validator",
            "examples/invalid_promote_with_regression.json",
            "--format",
            "json",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1

    payload = json.loads(result.stdout)
    assert payload["valid"] is False
    assert payload["record_id"] == "asiep:invalid-promote-with-regression"
    assert len(payload["errors"]) == 1
    error = payload["errors"][0]
    for key in ("code", "severity", "message", "remediation_hint"):
        assert error[key]
    assert error["code"] == "INV_SAFETY_REGRESSION"
    assert error["severity"] == "error"
    assert error["json_path"] or error["invariant_id"]


def test_schema_missing_gate_report_is_agent_specific_error() -> None:
    report = validate_file(ROOT / "examples" / "invalid_missing_gate_report.json")
    assert report.codes == ["SCHEMA"]

    payload = report.to_agent_dict()
    assert payload["errors"][0]["code"] == "INV_MISSING_GATE_REPORT"
    assert payload["errors"][0]["invariant_id"] == "I5"
    assert payload["errors"][0]["remediation_hint"]


def test_state_machine_start_rule_has_agent_error() -> None:
    with (ROOT / "examples" / "valid_chatbot_improvement.json").open(encoding="utf-8") as handle:
        profile = json.load(handle)

    profile["lifecycle"][0]["state"] = "CANDIDATE"

    report = validate_profile(profile)
    assert not report.valid
    assert report.codes == ["STATE_TRANSITION"]
    assert report.issues[0].invariant_id == "I2"


def test_failed_p2_safety_check_has_agent_error() -> None:
    with (ROOT / "examples" / "valid_chatbot_improvement.json").open(encoding="utf-8") as handle:
        profile = json.load(handle)

    profile["safety_checks"][0]["passed"] = False
    profile["safety_checks"][0]["severity"] = "p2"
    profile["safety_checks"][0]["regression"] = False

    report = validate_profile(profile)
    assert not report.valid
    assert report.codes == ["INV_SAFETY_REGRESSION"]
    assert report.issues[0].invariant_id == "I7"
