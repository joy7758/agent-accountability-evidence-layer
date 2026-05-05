from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from asiep_importer import import_trace
from asiep_packager import package_bundle
from asiep_validator import ERROR_CODES


ROOT = Path(__file__).resolve().parents[1]
IMPORT_REQUESTS = ROOT / "examples" / "import_requests"
PACKAGE_REQUESTS = ROOT / "examples" / "package_requests"
FIXTURES = ROOT / "examples" / "fixtures"
M5_CODES = {
    "PACKAGE_SCHEMA",
    "PACKAGE_INPUT_BUNDLE_MISSING",
    "PACKAGE_RESOLVER_FAILED",
    "PACKAGE_VALIDATOR_FAILED",
    "PACKAGE_POLICY_VIOLATION",
    "PACKAGE_ARTIFACT_COPY_FAILED",
    "PACKAGE_DIGEST_MISMATCH",
    "PACKAGE_MANIFEST_INVALID",
    "PACKAGE_FDO_RECORD_INVALID",
    "PACKAGE_ROCRATE_INVALID",
    "PACKAGE_PROV_INVALID",
    "PACKAGE_WRITE_FAILED",
    "PACKAGE_PID_CLAIM_FORBIDDEN",
}


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _assert_schema_valid(payload: dict, schema_path: Path) -> None:
    schema = _load_json(schema_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=str)
    assert errors == []


def _import_request_copy(tmp_path: Path, filename: str, fixture_name: str, bundle_name: str) -> Path:
    request = _load_json(IMPORT_REQUESTS / filename)
    request["source_path"] = str((FIXTURES / fixture_name).resolve())
    request["output_bundle_dir"] = str(tmp_path / bundle_name)
    path = tmp_path / filename
    _write_json(path, request)
    return path


def _package_request_copy(tmp_path: Path, filename: str, bundle_dir: Path, package_name: str) -> Path:
    request = _load_json(PACKAGE_REQUESTS / filename)
    request["input_bundle_manifest_path"] = str(bundle_dir / "bundle.json")
    request["input_bundle_root"] = str(bundle_dir)
    request["output_package_dir"] = str(tmp_path / package_name)
    path = tmp_path / filename
    _write_json(path, request)
    return path


def _prepare_otel_bundle(tmp_path: Path) -> Path:
    request_path = _import_request_copy(tmp_path, "otel_chatbot_request.json", "otel_genai_chatbot_trace.json", "otel_bundle")
    result = import_trace(request_path)
    assert result["valid"] is True
    return tmp_path / "otel_bundle"


def _prepare_langsmith_bundle(tmp_path: Path) -> Path:
    request_path = _import_request_copy(
        tmp_path,
        "langsmith_chatbot_request.json",
        "langsmith_chatbot_trace.json",
        "langsmith_bundle",
    )
    result = import_trace(request_path)
    assert result["valid"] is True
    return tmp_path / "langsmith_bundle"


def test_package_request_examples_match_schema() -> None:
    schema_path = ROOT / "interfaces" / "asiep_package_request.schema.json"
    for request_path in sorted(PACKAGE_REQUESTS.glob("*.json")):
        _assert_schema_valid(_load_json(request_path), schema_path)


def test_otel_package_request_packages_successfully(tmp_path: Path) -> None:
    bundle_dir = _prepare_otel_bundle(tmp_path)
    request_path = _package_request_copy(tmp_path, "otel_chatbot_package_request.json", bundle_dir, "otel_package")
    result = package_bundle(request_path)
    _assert_schema_valid(result, ROOT / "interfaces" / "asiep_package_result.schema.json")
    assert result["valid"] is True
    assert result["resolver_result_summary"]["valid"] is True
    assert result["validator_result_summary"]["valid"] is True
    assert len(result["copied_artifacts"]) == 6


def test_langsmith_package_request_packages_successfully(tmp_path: Path) -> None:
    bundle_dir = _prepare_langsmith_bundle(tmp_path)
    request_path = _package_request_copy(tmp_path, "langsmith_chatbot_package_request.json", bundle_dir, "langsmith_package")
    result = package_bundle(request_path)
    _assert_schema_valid(result, ROOT / "interfaces" / "asiep_package_result.schema.json")
    assert result["valid"] is True
    assert len(result["copied_artifacts"]) == 6


def test_generated_package_documents_match_schemas(tmp_path: Path) -> None:
    bundle_dir = _prepare_otel_bundle(tmp_path)
    request_path = _package_request_copy(tmp_path, "otel_chatbot_package_request.json", bundle_dir, "otel_package")
    result = package_bundle(request_path)
    assert result["valid"] is True

    checks = [
        (Path(result["package_manifest_path"]), ROOT / "interfaces" / "asiep_package_manifest.schema.json"),
        (Path(result["fdo_record_path"]), ROOT / "interfaces" / "asiep_fdo_record.schema.json"),
        (Path(result["rocrate_metadata_path"]), ROOT / "interfaces" / "asiep_rocrate_metadata.schema.json"),
        (Path(result["prov_jsonld_path"]), ROOT / "interfaces" / "asiep_prov_jsonld.schema.json"),
    ]
    for payload_path, schema_path in checks:
        _assert_schema_valid(_load_json(payload_path), schema_path)


def test_package_output_contains_required_files_and_dirs(tmp_path: Path) -> None:
    bundle_dir = _prepare_otel_bundle(tmp_path)
    request_path = _package_request_copy(tmp_path, "otel_chatbot_package_request.json", bundle_dir, "otel_package")
    result = package_bundle(request_path)
    package_dir = Path(result["output_package_dir"])
    for path in (
        "package_manifest.json",
        "fdo_record.json",
        "ro-crate-metadata.json",
        "prov.jsonld",
        "evidence",
        "bundle",
        "artifacts",
    ):
        assert (package_dir / path).exists()


def test_package_output_does_not_claim_global_pid(tmp_path: Path) -> None:
    bundle_dir = _prepare_otel_bundle(tmp_path)
    request_path = _package_request_copy(tmp_path, "otel_chatbot_package_request.json", bundle_dir, "otel_package")
    result = package_bundle(request_path)
    assert result["valid"] is True
    package_text = "".join(
        path.read_text(encoding="utf-8")
        for path in (
            Path(result["package_manifest_path"]),
            Path(result["fdo_record_path"]),
            Path(result["rocrate_metadata_path"]),
            Path(result["prov_jsonld_path"]),
        )
    )
    assert "global_pid" not in package_text
    assert "global_resolution_claim" in package_text
    assert "registry_submission" in package_text
    assert "urn:asiep:fdo:" in package_text


def test_package_output_does_not_inline_sensitive_content(tmp_path: Path) -> None:
    bundle_dir = _prepare_otel_bundle(tmp_path)
    request_path = _package_request_copy(tmp_path, "otel_chatbot_package_request.json", bundle_dir, "otel_package")
    result = package_bundle(request_path)
    metadata_text = "".join(
        Path(path).read_text(encoding="utf-8")
        for path in (
            result["package_manifest_path"],
            result["fdo_record_path"],
            result["rocrate_metadata_path"],
            result["prov_jsonld_path"],
        )
    )
    assert "raw_prompt" not in metadata_text
    assert "raw_user_input" not in metadata_text
    assert "raw_model_output" not in metadata_text
    assert "SYNTHETIC_SECRET_PROMPT_DO_NOT_IMPORT" not in metadata_text


def test_invalid_unvalidated_bundle_request_fails_resolver_precondition(tmp_path: Path) -> None:
    invalid_bundle = tmp_path / "invalid_bundle"
    shutil.copytree(ROOT / "examples" / "bundles" / "invalid_digest_mismatch_bundle", invalid_bundle)
    request_path = _package_request_copy(
        tmp_path,
        "invalid_unvalidated_bundle_package_request.json",
        invalid_bundle,
        "invalid_package",
    )
    result = package_bundle(request_path)
    _assert_schema_valid(result, ROOT / "interfaces" / "asiep_package_result.schema.json")
    assert result["valid"] is False
    assert [error["code"] for error in result["errors"]] == ["PACKAGE_RESOLVER_FAILED"]


def test_validator_precondition_failure_is_reported(tmp_path: Path) -> None:
    bundle_dir = _prepare_otel_bundle(tmp_path)
    evidence_path = bundle_dir / "evidence.json"
    evidence = _load_json(evidence_path)
    evidence["safety_checks"][0]["regression"] = True
    _write_json(evidence_path, evidence)
    request_path = _package_request_copy(tmp_path, "otel_chatbot_package_request.json", bundle_dir, "validator_fail_package")
    result = package_bundle(request_path)
    assert result["valid"] is False
    assert [error["code"] for error in result["errors"]] == ["PACKAGE_VALIDATOR_FAILED"]
    assert result["resolver_result_summary"]["valid"] is True
    assert result["validator_result_summary"]["valid"] is False


def test_profile_manifest_indexes_packager() -> None:
    manifest = _load_json(ROOT / "profiles" / "asiep" / "v0.1" / "profile.json")
    for key in (
        "package_request_schema_path",
        "package_result_schema_path",
        "package_manifest_schema_path",
        "fdo_record_schema_path",
        "rocrate_metadata_schema_path",
        "prov_jsonld_schema_path",
        "package_policy_path",
    ):
        assert key in manifest
        assert (ROOT / manifest[key]).exists()
    assert manifest["packager_supported"] is True
    assert manifest["packager_entrypoint"]["module"] == "asiep_packager"
    assert set(manifest["supported_package_types"]) >= {"fdo_rocrate_local", "rocrate_local", "fdo_local"}


def test_repair_policy_and_error_registry_cover_m5_codes() -> None:
    policy = _load_json(ROOT / "profiles" / "asiep" / "v0.1" / "repair_policy.json")
    policy_codes = {item["code"] for item in policy["error_code_repair_map"]}
    assert M5_CODES <= policy_codes
    assert M5_CODES <= set(ERROR_CODES)


def test_packager_cli_json(tmp_path: Path) -> None:
    bundle_dir = _prepare_otel_bundle(tmp_path)
    request_path = _package_request_copy(tmp_path, "otel_chatbot_package_request.json", bundle_dir, "cli_package")
    result = subprocess.run(
        [sys.executable, "-m", "asiep_packager", str(request_path), "--format", "json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    _assert_schema_valid(payload, ROOT / "interfaces" / "asiep_package_result.schema.json")


def test_package_demo_script() -> None:
    subprocess.run([sys.executable, "scripts/package_demo.py"], cwd=ROOT, check=True, capture_output=True, text=True)
