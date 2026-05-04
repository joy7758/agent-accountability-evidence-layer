from __future__ import annotations

import json
from pathlib import Path

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
