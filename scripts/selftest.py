from __future__ import annotations

from pathlib import Path

from asiep_resolver import resolve_bundle
from asiep_validator import validate_file


ROOT = Path(__file__).resolve().parents[1]

CASES = [
    ("valid_chatbot_improvement.json", ["VALID"]),
    ("invalid_missing_gate_report.json", ["SCHEMA"]),
    ("invalid_promote_with_regression.json", ["INV_SAFETY_REGRESSION"]),
    ("invalid_hash_chain_break.json", ["REF_UNRESOLVED"]),
    ("invalid_promote_with_p2f_threshold_violation.json", ["INV_FLIP_THRESHOLD"]),
    ("invalid_transition_order.json", ["STATE_TRANSITION"]),
]

BUNDLE_CASES = [
    ("valid_chatbot_bundle", True, []),
    ("invalid_missing_artifact_bundle", False, ["BUNDLE_ARTIFACT_MISSING"]),
    ("invalid_digest_mismatch_bundle", False, ["BUNDLE_DIGEST_MISMATCH"]),
    ("invalid_path_escape_bundle", False, ["BUNDLE_PATH_ESCAPE"]),
]


def main() -> int:
    for filename, expected in CASES:
        report = validate_file(ROOT / "examples" / filename)
        codes = report.codes
        status = "PASS" if codes == expected else "FAIL"
        print(f"{status} {filename}: {codes}")
        if codes != expected:
            return 1
    for dirname, expected_valid, expected_codes in BUNDLE_CASES:
        result = resolve_bundle(ROOT / "examples" / "bundles" / dirname / "bundle.json")
        codes = [error["code"] for error in result["errors"]]
        valid_matches = result["valid"] is expected_valid
        codes_match = codes == expected_codes
        status = "PASS" if valid_matches and codes_match else "FAIL"
        print(f"{status} {dirname}/bundle.json: {codes if codes else ['VALID']}")
        if not valid_matches or not codes_match:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
