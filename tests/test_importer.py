from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from asiep_importer import import_trace
from asiep_resolver import resolve_bundle
from asiep_validator import ERROR_CODES, validate_file


ROOT = Path(__file__).resolve().parents[1]
REQUESTS = ROOT / "examples" / "import_requests"
FIXTURES = ROOT / "examples" / "fixtures"
M4_CODES = {
    "IMPORT_SCHEMA",
    "IMPORT_SOURCE_UNSUPPORTED",
    "IMPORT_SOURCE_MISSING",
    "IMPORT_REQUIRED_ROLE_MISSING",
    "IMPORT_SENSITIVE_CONTENT_BLOCKED",
    "IMPORT_MAPPING_INCOMPLETE",
    "IMPORT_ARTIFACT_WRITE_FAILED",
    "IMPORT_BUNDLE_VALIDATION_FAILED",
    "IMPORT_VALIDATOR_FAILED",
    "IMPORT_POLICY_VIOLATION",
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


def _request_copy(tmp_path: Path, filename: str, fixture_name: str, bundle_name: str) -> Path:
    request = _load_json(REQUESTS / filename)
    request["source_path"] = str((FIXTURES / fixture_name).resolve())
    request["output_bundle_dir"] = str(tmp_path / bundle_name)
    path = tmp_path / filename
    _write_json(path, request)
    return path


def test_import_request_examples_match_schema() -> None:
    schema_path = ROOT / "interfaces" / "asiep_import_request.schema.json"
    for request_path in sorted(REQUESTS.glob("*.json")):
        _assert_schema_valid(_load_json(request_path), schema_path)


def test_source_fixtures_match_schemas() -> None:
    _assert_schema_valid(
        _load_json(FIXTURES / "otel_genai_chatbot_trace.json"),
        ROOT / "interfaces" / "otel_genai_trace_fixture.schema.json",
    )
    _assert_schema_valid(
        _load_json(FIXTURES / "invalid_missing_gate_report_trace.json"),
        ROOT / "interfaces" / "otel_genai_trace_fixture.schema.json",
    )
    _assert_schema_valid(
        _load_json(FIXTURES / "invalid_sensitive_content_trace.json"),
        ROOT / "interfaces" / "otel_genai_trace_fixture.schema.json",
    )
    _assert_schema_valid(
        _load_json(FIXTURES / "langsmith_chatbot_trace.json"),
        ROOT / "interfaces" / "langsmith_trace_fixture.schema.json",
    )


def test_otel_chatbot_request_imports_valid_bundle(tmp_path: Path) -> None:
    request_path = _request_copy(tmp_path, "otel_chatbot_request.json", "otel_genai_chatbot_trace.json", "otel_bundle")
    result = import_trace(request_path)
    _assert_schema_valid(result, ROOT / "interfaces" / "asiep_import_result.schema.json")
    assert result["valid"] is True
    assert len(result["generated_artifacts"]) == 6

    resolver_result = resolve_bundle(result["bundle_manifest_path"])
    assert resolver_result["valid"] is True

    validator_report = validate_file(result["evidence_record_path"], bundle_root=result["output_bundle_dir"])
    assert validator_report.valid is True


def test_langsmith_chatbot_request_imports_valid_bundle(tmp_path: Path) -> None:
    request_path = _request_copy(
        tmp_path,
        "langsmith_chatbot_request.json",
        "langsmith_chatbot_trace.json",
        "langsmith_bundle",
    )
    result = import_trace(request_path)
    _assert_schema_valid(result, ROOT / "interfaces" / "asiep_import_result.schema.json")
    assert result["valid"] is True
    assert len(result["generated_artifacts"]) == 6
    assert resolve_bundle(result["bundle_manifest_path"])["valid"] is True
    assert validate_file(result["evidence_record_path"], bundle_root=result["output_bundle_dir"]).valid is True


def test_import_result_schema_for_invalid_requests(tmp_path: Path) -> None:
    cases = [
        (
            "invalid_missing_gate_report_request.json",
            "invalid_missing_gate_report_trace.json",
            "missing_gate",
            "IMPORT_REQUIRED_ROLE_MISSING",
        ),
        (
            "invalid_sensitive_content_request.json",
            "invalid_sensitive_content_trace.json",
            "sensitive",
            "IMPORT_SENSITIVE_CONTENT_BLOCKED",
        ),
    ]
    for filename, fixture_name, bundle_name, expected_code in cases:
        request_path = _request_copy(tmp_path, filename, fixture_name, bundle_name)
        result = import_trace(request_path)
        _assert_schema_valid(result, ROOT / "interfaces" / "asiep_import_result.schema.json")
        assert result["valid"] is False
        assert [error["code"] for error in result["errors"]] == [expected_code]


def test_missing_gate_report_is_not_fabricated(tmp_path: Path) -> None:
    request_path = _request_copy(
        tmp_path,
        "invalid_missing_gate_report_request.json",
        "invalid_missing_gate_report_trace.json",
        "missing_gate_bundle",
    )
    result = import_trace(request_path)
    assert result["valid"] is False
    assert result["generated_artifacts"] == []
    assert not (tmp_path / "missing_gate_bundle").exists()


def test_sensitive_content_blocked_and_not_embedded(tmp_path: Path) -> None:
    invalid_request = _request_copy(
        tmp_path,
        "invalid_sensitive_content_request.json",
        "invalid_sensitive_content_trace.json",
        "sensitive_bundle",
    )
    invalid_result = import_trace(invalid_request)
    assert invalid_result["valid"] is False
    assert invalid_result["errors"][0]["code"] == "IMPORT_SENSITIVE_CONTENT_BLOCKED"
    assert invalid_result["generated_artifacts"] == []
    assert not (tmp_path / "sensitive_bundle").exists()

    valid_request = _request_copy(tmp_path, "otel_chatbot_request.json", "otel_genai_chatbot_trace.json", "otel_bundle")
    valid_result = import_trace(valid_request)
    evidence_text = Path(valid_result["evidence_record_path"]).read_text(encoding="utf-8")
    trace_text = (tmp_path / "otel_bundle" / "artifacts" / "trace.json").read_text(encoding="utf-8")
    combined = evidence_text + trace_text
    assert "raw_prompt" not in combined
    assert "raw_user_input" not in combined
    assert "raw_model_output" not in combined
    assert "SYNTHETIC_SECRET_PROMPT_DO_NOT_IMPORT" not in combined


def test_profile_manifest_indexes_importer() -> None:
    manifest = _load_json(ROOT / "profiles" / "asiep" / "v0.1" / "profile.json")
    for key in ("import_request_schema_path", "import_result_schema_path", "import_policy_path"):
        assert key in manifest
        assert (ROOT / manifest[key]).exists()
    assert manifest["importer_supported"] is True
    assert manifest["importer_entrypoint"]["module"] == "asiep_importer"
    assert set(manifest["supported_import_sources"]) >= {"otel_genai", "langsmith", "generic_agent_trace"}


def test_repair_policy_and_error_registry_cover_m4_codes() -> None:
    policy = _load_json(ROOT / "profiles" / "asiep" / "v0.1" / "repair_policy.json")
    policy_codes = {item["code"] for item in policy["error_code_repair_map"]}
    assert M4_CODES <= policy_codes
    assert M4_CODES <= set(ERROR_CODES)


def test_importer_cli_json(tmp_path: Path) -> None:
    request_path = _request_copy(tmp_path, "otel_chatbot_request.json", "otel_genai_chatbot_trace.json", "cli_bundle")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "asiep_importer",
            str(request_path),
            "--format",
            "json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    _assert_schema_valid(payload, ROOT / "interfaces" / "asiep_import_result.schema.json")


def test_import_trace_demo_and_selftest_scripts() -> None:
    for script in ("scripts/import_trace_demo.py", "scripts/selftest.py"):
        subprocess.run([sys.executable, script], cwd=ROOT, check=True, capture_output=True, text=True)
