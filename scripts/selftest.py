from __future__ import annotations

from pathlib import Path

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


def main() -> int:
    for filename, expected in CASES:
        report = validate_file(ROOT / "examples" / filename)
        codes = report.codes
        status = "PASS" if codes == expected else "FAIL"
        print(f"{status} {filename}: {codes}")
        if codes != expected:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
