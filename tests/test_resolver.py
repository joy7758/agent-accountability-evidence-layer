from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from asiep_resolver import resolve_bundle
from asiep_validator import ERROR_CODES, validate_file


ROOT = Path(__file__).resolve().parents[1]
BUNDLES = ROOT / "examples" / "bundles"
M3_CODES = {
    "BUNDLE_SCHEMA",
    "BUNDLE_ARTIFACT_MISSING",
    "BUNDLE_DIGEST_MISMATCH",
    "BUNDLE_MEDIA_TYPE_MISMATCH",
    "BUNDLE_PATH_ESCAPE",
    "BUNDLE_RECORD_MISSING",
    "BUNDLE_REF_UNDECLARED",
    "BUNDLE_REF_UNUSED",
    "BUNDLE_MANIFEST_HASH_MISMATCH",
}


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _assert_schema_valid(payload: dict, schema_path: Path) -> None:
    schema = _load_json(schema_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=str)
    assert errors == []


def test_valid_bundle_matches_evidence_bundle_schema() -> None:
    bundle = _load_json(BUNDLES / "valid_chatbot_bundle" / "bundle.json")
    _assert_schema_valid(bundle, ROOT / "interfaces" / "asiep_evidence_bundle.schema.json")


def test_resolver_output_matches_resolution_schema() -> None:
    for bundle_path in sorted(BUNDLES.glob("*/bundle.json")):
        result = resolve_bundle(bundle_path)
        _assert_schema_valid(result, ROOT / "interfaces" / "asiep_bundle_resolution.schema.json")


def test_valid_chatbot_bundle_resolves_cleanly() -> None:
    result = resolve_bundle(BUNDLES / "valid_chatbot_bundle" / "bundle.json")
    assert result["valid"] is True
    assert len(result["resolved_refs"]) == 6
    assert result["unresolved_refs"] == []
    assert all(check["digest_match"] for check in result["digest_checks"])


def test_valid_chatbot_bundle_validator_bundle_root_passes() -> None:
    report = validate_file(
        BUNDLES / "valid_chatbot_bundle" / "evidence.json",
        bundle_root=BUNDLES / "valid_chatbot_bundle",
    )
    assert report.valid
    assert report.codes == ["VALID"]


def test_invalid_missing_artifact_bundle_reports_missing_artifact() -> None:
    result = resolve_bundle(BUNDLES / "invalid_missing_artifact_bundle" / "bundle.json")
    assert result["valid"] is False
    error = result["errors"][0]
    assert error["code"] == "BUNDLE_ARTIFACT_MISSING"
    assert error["repairability"] == "external_evidence_required"


def test_invalid_digest_mismatch_bundle_reports_digest_mismatch() -> None:
    result = resolve_bundle(BUNDLES / "invalid_digest_mismatch_bundle" / "bundle.json")
    assert result["valid"] is False
    assert [error["code"] for error in result["errors"]] == ["BUNDLE_DIGEST_MISMATCH"]
    assert any(not check["digest_match"] for check in result["digest_checks"])


def test_invalid_path_escape_bundle_reports_path_escape_without_reading_outside() -> None:
    result = resolve_bundle(BUNDLES / "invalid_path_escape_bundle" / "bundle.json")
    assert result["valid"] is False
    assert [error["code"] for error in result["errors"]] == ["BUNDLE_PATH_ESCAPE"]
    assert result["errors"][0]["repairability"] == "human_required"
    assert all("feedback.json" not in check["uri"] for check in result["digest_checks"])
    assert result["unresolved_refs"][0]["reason"] == "artifact path escapes bundle_root"


def test_validator_without_bundle_root_keeps_m2_behavior() -> None:
    report = validate_file(BUNDLES / "invalid_digest_mismatch_bundle" / "evidence.json")
    assert report.valid
    assert report.codes == ["VALID"]


def test_validator_with_bundle_root_merges_resolver_errors() -> None:
    report = validate_file(
        BUNDLES / "invalid_digest_mismatch_bundle" / "evidence.json",
        bundle_root=BUNDLES / "invalid_digest_mismatch_bundle",
    )
    payload = report.to_agent_dict()
    assert payload["valid"] is False
    assert payload["errors"][0]["code"] == "BUNDLE_DIGEST_MISMATCH"
    _assert_schema_valid(payload, ROOT / "interfaces" / "asiep_validator_output.schema.json")


def test_profile_manifest_indexes_bundle_resolver() -> None:
    manifest = _load_json(ROOT / "profiles" / "asiep" / "v0.1" / "profile.json")
    for key in ("evidence_bundle_schema_path", "bundle_resolution_schema_path"):
        assert key in manifest
        assert (ROOT / manifest[key]).exists()
    assert manifest["bundle_resolver_supported"] is True
    assert manifest["resolver_entrypoint"]["module"] == "asiep_resolver"
    assert set(manifest["supported_reference_schemes"]) >= {"bundle://", "file-relative", "repo-relative"}


def test_repair_policy_and_error_registry_cover_m3_codes() -> None:
    policy = _load_json(ROOT / "profiles" / "asiep" / "v0.1" / "repair_policy.json")
    policy_codes = {item["code"] for item in policy["error_code_repair_map"]}
    assert M3_CODES <= policy_codes
    assert M3_CODES <= set(ERROR_CODES)


def test_resolver_cli_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "asiep_resolver",
            "examples/bundles/valid_chatbot_bundle/bundle.json",
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
