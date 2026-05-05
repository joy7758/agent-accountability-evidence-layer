from __future__ import annotations

import json
import shutil
from pathlib import Path

from jsonschema import Draft202012Validator

from asiep_importer import import_trace
from asiep_packager import package_bundle


ROOT = Path(__file__).resolve().parents[1]
GENERATED_BUNDLES = ROOT / "examples" / "generated_bundles"
GENERATED_PACKAGES = ROOT / "examples" / "generated_packages"
RESULT_SCHEMA = ROOT / "interfaces" / "asiep_package_result.schema.json"
MANIFEST_SCHEMA = ROOT / "interfaces" / "asiep_package_manifest.schema.json"
FDO_SCHEMA = ROOT / "interfaces" / "asiep_fdo_record.schema.json"
ROCRATE_SCHEMA = ROOT / "interfaces" / "asiep_rocrate_metadata.schema.json"
PROV_SCHEMA = ROOT / "interfaces" / "asiep_prov_jsonld.schema.json"

IMPORT_CASES = [
    "otel_chatbot_request.json",
    "langsmith_chatbot_request.json",
]

PACKAGE_CASES = [
    ("otel_chatbot_package_request.json", True, []),
    ("langsmith_chatbot_package_request.json", True, []),
    ("invalid_unvalidated_bundle_package_request.json", False, ["PACKAGE_RESOLVER_FAILED"]),
]


def main() -> int:
    for path in (GENERATED_BUNDLES, GENERATED_PACKAGES):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)

    for filename in IMPORT_CASES:
        result = import_trace(ROOT / "examples" / "import_requests" / filename)
        if not result["valid"]:
            print(f"FAIL import {filename}: {[error['code'] for error in result['errors']]}")
            return 1

    result_schema = _load_json(RESULT_SCHEMA)
    exit_code = 0
    for filename, expected_valid, expected_codes in PACKAGE_CASES:
        result = package_bundle(ROOT / "examples" / "package_requests" / filename)
        schema_errors = sorted(Draft202012Validator(result_schema).iter_errors(result), key=str)
        if schema_errors:
            exit_code = 1
            print(f"FAIL {filename}: package result schema failed")
            for error in schema_errors:
                print(f"  {error.message}")
            continue

        if result["valid"]:
            _validate_generated_package(result)

        error_codes = [error["code"] for error in result["errors"]]
        status = "PASS" if result["valid"] is expected_valid and error_codes == expected_codes else "FAIL"
        if status == "FAIL":
            exit_code = 1
        print(
            f"{status} package_id={result['package_id']} "
            f"valid={result['valid']} "
            f"generated_files={len(result['generated_files'])} "
            f"copied_artifacts={len(result['copied_artifacts'])} "
            f"fdo_record_path={result['fdo_record_path']} "
            f"rocrate_metadata_path={result['rocrate_metadata_path']} "
            f"prov_jsonld_path={result['prov_jsonld_path']} "
            f"error_codes={error_codes}"
        )
    return exit_code


def _validate_generated_package(result: dict) -> None:
    checks = [
        (Path(result["package_manifest_path"]), MANIFEST_SCHEMA),
        (Path(result["fdo_record_path"]), FDO_SCHEMA),
        (Path(result["rocrate_metadata_path"]), ROCRATE_SCHEMA),
        (Path(result["prov_jsonld_path"]), PROV_SCHEMA),
    ]
    for payload_path, schema_path in checks:
        payload = _load_json(payload_path)
        schema = _load_json(schema_path)
        errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=str)
        if errors:
            raise AssertionError(f"{payload_path} failed {schema_path}: {errors[0].message}")


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    raise SystemExit(main())
