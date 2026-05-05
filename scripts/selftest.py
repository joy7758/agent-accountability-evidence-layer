from __future__ import annotations

from pathlib import Path

from asiep_evaluator import evaluate_profile
from asiep_importer import import_trace
from asiep_packager import package_bundle
from asiep_paper_linter import lint_paper
from asiep_citation_linter import lint_citations
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

IMPORT_CASES = [
    ("otel_chatbot_request.json", True, []),
    ("langsmith_chatbot_request.json", True, []),
    ("invalid_missing_gate_report_request.json", False, ["IMPORT_REQUIRED_ROLE_MISSING"]),
    ("invalid_sensitive_content_request.json", False, ["IMPORT_SENSITIVE_CONTENT_BLOCKED"]),
]

PACKAGE_CASES = [
    ("otel_chatbot_package_request.json", True, []),
    ("langsmith_chatbot_package_request.json", True, []),
    ("invalid_unvalidated_bundle_package_request.json", False, ["PACKAGE_RESOLVER_FAILED"]),
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
    for filename, expected_valid, expected_codes in IMPORT_CASES:
        result = import_trace(ROOT / "examples" / "import_requests" / filename)
        codes = [error["code"] for error in result["errors"]]
        valid_matches = result["valid"] is expected_valid
        codes_match = codes == expected_codes
        status = "PASS" if valid_matches and codes_match else "FAIL"
        print(f"{status} {filename}: {codes if codes else ['VALID']}")
        if not valid_matches or not codes_match:
            return 1
    for filename, expected_valid, expected_codes in PACKAGE_CASES:
        result = package_bundle(ROOT / "examples" / "package_requests" / filename)
        codes = [error["code"] for error in result["errors"]]
        valid_matches = result["valid"] is expected_valid
        codes_match = codes == expected_codes
        status = "PASS" if valid_matches and codes_match else "FAIL"
        print(f"{status} {filename}: {codes if codes else ['VALID']}")
        if not valid_matches or not codes_match:
            return 1
    report = evaluate_profile(ROOT / "profiles" / "asiep" / "v0.1" / "profile.json")
    metrics = {metric["metric_id"]: metric["value"] for metric in report["metric_results"]}
    status = "PASS" if metrics["false_positive_rate"] == 0 and metrics["privacy_policy_compliance"] == 1 else "FAIL"
    print(f"{status} asiep_v0.1_evaluation: false_positive_rate={metrics['false_positive_rate']} privacy_policy_compliance={metrics['privacy_policy_compliance']}")
    if status != "PASS":
        return 1
    lint_result = lint_paper(ROOT / "profiles" / "asiep" / "v0.1" / "profile.json")
    status = "PASS" if lint_result["valid"] and lint_result["claims_checked"] >= 12 else "FAIL"
    print(f"{status} asiep_paper_v0.1: claims={lint_result['claims_checked']} errors={len(lint_result['errors'])}")
    if status != "PASS":
        return 1
    citation_result = lint_citations(ROOT / "profiles" / "asiep" / "v0.1" / "profile.json")
    status = "PASS" if citation_result["valid"] and citation_result["sources_checked"] >= 10 else "FAIL"
    print(f"{status} asiep_paper_v0.2_citations: sources={citation_result['sources_checked']} errors={len(citation_result['errors'])}")
    if status != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
