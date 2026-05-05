from __future__ import annotations

import json
import shutil
from pathlib import Path

from jsonschema import Draft202012Validator

from asiep_importer import import_trace
from asiep_resolver import resolve_bundle
from asiep_validator import validate_file


ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "examples" / "generated_bundles"
IMPORT_RESULT_SCHEMA = ROOT / "interfaces" / "asiep_import_result.schema.json"

CASES = [
    ("otel_chatbot_request.json", True, []),
    ("langsmith_chatbot_request.json", True, []),
    ("invalid_missing_gate_report_request.json", False, ["IMPORT_REQUIRED_ROLE_MISSING"]),
    ("invalid_sensitive_content_request.json", False, ["IMPORT_SENSITIVE_CONTENT_BLOCKED"]),
]


def main() -> int:
    if GENERATED.exists():
        shutil.rmtree(GENERATED)
    GENERATED.mkdir(parents=True, exist_ok=True)

    schema = _load_json(IMPORT_RESULT_SCHEMA)
    exit_code = 0
    for filename, expected_valid, expected_codes in CASES:
        request_path = ROOT / "examples" / "import_requests" / filename
        result = import_trace(request_path)
        schema_errors = sorted(Draft202012Validator(schema).iter_errors(result), key=str)
        if schema_errors:
            exit_code = 1
            print(f"FAIL {filename}: import result schema failed")
            for error in schema_errors:
                print(f"  {error.message}")
            continue

        error_codes = [error["code"] for error in result["errors"]]
        resolver_valid = None
        validator_valid = None
        if result["valid"]:
            resolver_result = resolve_bundle(result["bundle_manifest_path"])
            validator_report = validate_file(result["evidence_record_path"], bundle_root=result["output_bundle_dir"])
            resolver_valid = resolver_result["valid"]
            validator_valid = validator_report.valid
            if not resolver_valid or not validator_valid:
                exit_code = 1

        valid_matches = result["valid"] is expected_valid
        codes_match = error_codes == expected_codes
        status = "PASS" if valid_matches and codes_match else "FAIL"
        if status == "FAIL":
            exit_code = 1
        print(
            f"{status} import_id={result['import_id']} "
            f"source_type={result['source_type']} "
            f"valid={result['valid']} "
            f"generated_artifacts={len(result['generated_artifacts'])} "
            f"resolver_valid={resolver_valid} "
            f"validator_valid={validator_valid} "
            f"error_codes={error_codes}"
        )
    return exit_code


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    raise SystemExit(main())
