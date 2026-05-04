from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from asiep_repairer import generate_repair_plan
from asiep_validator import validate_file


ROOT = Path(__file__).resolve().parents[1]
INVALID_EXAMPLES = sorted((ROOT / "examples").glob("invalid_*.json"))


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _assert_schema_valid(payload: dict, schema_path: Path) -> None:
    schema = _load_json(schema_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=str)
    assert errors == []


def test_validator_json_output_matches_interface_schema() -> None:
    schema_path = ROOT / "interfaces" / "asiep_validator_output.schema.json"
    paths = [ROOT / "examples" / "valid_chatbot_improvement.json", *INVALID_EXAMPLES]
    for path in paths:
        payload = validate_file(path).to_agent_dict()
        _assert_schema_valid(payload, schema_path)
        for error in payload["errors"]:
            assert error["code"]
            assert error["severity"]
            assert error["message"]
            assert error["json_path"] or error["invariant_id"]
            assert error["json_pointer"] is not None
            assert error["remediation_hint"]
            assert error["repairability"]


def test_repair_plan_matches_interface_schema_for_each_invalid_example() -> None:
    schema_path = ROOT / "interfaces" / "asiep_repair_plan.schema.json"
    for path in INVALID_EXAMPLES:
        plan = generate_repair_plan(path)
        _assert_schema_valid(plan, schema_path)
        assert plan["valid_before"] is False
        assert plan["repairable"] is True
        assert plan["errors"]
        assert plan["repair_actions"]


def test_safety_regression_plan_does_not_falsify_regression() -> None:
    plan = generate_repair_plan(ROOT / "examples" / "invalid_promote_with_regression.json")
    patch_ops = [op for action in plan["repair_actions"] for op in action["json_patch"]]
    assert {"op": "replace", "path": "/gates/0/decision", "value": "reject"} in patch_ops
    assert not any(op["path"].endswith("/regression") and op.get("value") is False for op in patch_ops)
    assert any("regression from true to false" in item for blocked in plan["blocked_actions"] for item in blocked["forbidden_patch_patterns"])


def test_flip_threshold_plan_does_not_relax_threshold() -> None:
    plan = generate_repair_plan(ROOT / "examples" / "invalid_promote_with_p2f_threshold_violation.json")
    patch_ops = [op for action in plan["repair_actions"] for op in action["json_patch"]]
    assert {"op": "replace", "path": "/gates/0/decision", "value": "reject"} in patch_ops
    assert not any("threshold" in op["path"] for op in patch_ops)
    assert any("increase threshold" in item for blocked in plan["blocked_actions"] for item in blocked["forbidden_patch_patterns"])


def test_missing_gate_report_requires_external_evidence() -> None:
    plan = generate_repair_plan(ROOT / "examples" / "invalid_missing_gate_report.json")
    action = plan["repair_actions"][0]
    assert action["error_code"] == "INV_MISSING_GATE_REPORT"
    assert action["requires_external_evidence"] is True
    assert action["evidence_requirements"]
    assert action["json_patch"][0]["value"] == "TODO:ev:real-gate-report"


def test_repairer_does_not_modify_input_file() -> None:
    path = ROOT / "examples" / "invalid_promote_with_regression.json"
    before = path.read_bytes()
    generate_repair_plan(path)
    after = path.read_bytes()
    assert after == before


def test_profile_manifest_indexes_repair_loop_artifacts() -> None:
    registry = _load_json(ROOT / "profiles" / "index.json")
    assert registry["profiles"][0]["manifest_path"] == "profiles/asiep/v0.1/profile.json"
    assert "repair_loop" in registry["profiles"][0]["capabilities"]

    manifest = _load_json(ROOT / "profiles" / "asiep" / "v0.1" / "profile.json")
    for key in ("validator_output_schema_path", "repair_plan_schema_path", "repair_policy_path"):
        assert key in manifest
        assert (ROOT / manifest[key]).exists()

    assert manifest["repair_loop_supported"] is True
    assert manifest["repairer_entrypoint"]["module"] == "asiep_repairer"
    assert "asiep_repairer" in manifest["repairer_entrypoint"]["json_command_template"]
    assert "discovery" in manifest
    assert manifest["discovery"]["registry_path"] == "profiles/index.json"


def test_repairer_cli_json_and_output_file(tmp_path: Path) -> None:
    output_path = tmp_path / "repair_plan.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "asiep_repairer",
            "examples/invalid_promote_with_regression.json",
            "--format",
            "json",
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    stdout_payload = json.loads(result.stdout)
    file_payload = _load_json(output_path)
    assert stdout_payload == file_payload
    assert stdout_payload["repair_actions"]
