from __future__ import annotations

import copy
import hashlib
import json
import mimetypes
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from asiep_validator.error_codes import get_error_code


ROOT = Path(__file__).resolve().parents[2]
BUNDLE_SCHEMA_PATH = ROOT / "interfaces" / "asiep_evidence_bundle.schema.json"
EMPTY_MANIFEST_HASH = "sha256:" + ("0" * 64)


def resolve_bundle(bundle_path: str | Path, expected_record_path: str | Path | None = None) -> dict[str, Any]:
    bundle_file = Path(bundle_path)
    if not bundle_file.exists():
        return _empty_result(
            bundle_id="",
            bundle_root=str(bundle_file.parent),
            errors=[
                _error(
                    "BUNDLE_RECORD_MISSING",
                    f"bundle manifest not found: {bundle_file}",
                    "$",
                )
            ],
        )

    try:
        bundle = _load_json(bundle_file)
    except json.JSONDecodeError as exc:
        return _empty_result(
            bundle_id="",
            bundle_root=str(bundle_file.parent),
            errors=[_error("BUNDLE_SCHEMA", f"bundle manifest is not valid JSON: {exc}", "$")],
        )

    bundle_id = str(bundle.get("bundle_id", ""))
    bundle_root = _bundle_root(bundle_file, bundle)
    schema_errors = _validate_bundle_schema(bundle)
    if schema_errors:
        return _empty_result(bundle_id=bundle_id, bundle_root=str(bundle_root), errors=schema_errors)

    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    resolved_refs: list[dict[str, Any]] = []
    unresolved_refs: list[dict[str, str]] = []
    digest_checks: list[dict[str, Any]] = []

    manifest_digest_actual = _manifest_hash(bundle)
    manifest_digest_expected = bundle["integrity"]["bundle_manifest_hash"]
    if manifest_digest_actual != manifest_digest_expected:
        errors.append(
            _error(
                "BUNDLE_MANIFEST_HASH_MISMATCH",
                f"bundle manifest hash {manifest_digest_actual} does not match expected {manifest_digest_expected}",
                "$.integrity.bundle_manifest_hash",
            )
        )

    record_path = _safe_join(bundle_root, bundle["evidence_record_path"])
    if record_path is None:
        errors.append(
            _error(
                "BUNDLE_PATH_ESCAPE",
                f"evidence_record_path escapes bundle_root: {bundle['evidence_record_path']}",
                "$.evidence_record_path",
            )
        )
        record = None
    elif not record_path.exists():
        errors.append(
            _error(
                "BUNDLE_RECORD_MISSING",
                f"evidence record not found: {bundle['evidence_record_path']}",
                "$.evidence_record_path",
            )
        )
        record = None
    elif expected_record_path and record_path.resolve() != Path(expected_record_path).resolve():
        errors.append(
            _error(
                "BUNDLE_RECORD_MISSING",
                "bundle evidence_record_path does not match validator input path",
                "$.evidence_record_path",
            )
        )
        record = None
    else:
        record = _load_json(record_path)

    artifact_by_uri = {artifact["uri"]: (index, artifact) for index, artifact in enumerate(bundle["artifacts"])}
    referenced = _extract_evidence_uris(record) if record else []
    referenced_uris = {ref["uri"] for ref in referenced}

    for ref in referenced:
        match = artifact_by_uri.get(ref["uri"])
        if not match:
            unresolved_refs.append(
                {
                    "uri": ref["uri"],
                    "json_path": ref["json_path"],
                    "json_pointer": _json_path_to_pointer(ref["json_path"]),
                    "reason": "evidence URI is not declared in bundle artifacts",
                }
            )
            errors.append(
                _error(
                    "BUNDLE_REF_UNDECLARED",
                    f"evidence URI {ref['uri']} is not declared in bundle artifacts",
                    ref["json_path"],
                )
            )
            continue

        artifact_index, artifact = match
        artifact_path = _safe_join(bundle_root, artifact["path"])
        artifact_json_path = f"$.artifacts[{artifact_index}].path"
        if artifact_path is None:
            unresolved_refs.append(
                {
                    "uri": ref["uri"],
                    "json_path": artifact_json_path,
                    "json_pointer": _json_path_to_pointer(artifact_json_path),
                    "reason": "artifact path escapes bundle_root",
                }
            )
            errors.append(
                _error(
                    "BUNDLE_PATH_ESCAPE",
                    f"artifact path escapes bundle_root: {artifact['path']}",
                    artifact_json_path,
                )
            )
            continue
        if not artifact_path.exists():
            unresolved_refs.append(
                {
                    "uri": ref["uri"],
                    "json_path": artifact_json_path,
                    "json_pointer": _json_path_to_pointer(artifact_json_path),
                    "reason": "artifact file is missing",
                }
            )
            errors.append(
                _error(
                    "BUNDLE_ARTIFACT_MISSING",
                    f"artifact file missing for {ref['uri']}: {artifact['path']}",
                    artifact_json_path,
                )
            )
            continue

        digest_actual = _file_digest(artifact_path)
        digest_expected = ref.get("digest_expected") or artifact["digest"]
        digest_match = digest_actual == digest_expected
        digest_check = {
            "uri": ref["uri"],
            "path": artifact["path"],
            "digest_expected": digest_expected,
            "digest_actual": digest_actual,
            "digest_match": digest_match,
        }
        digest_checks.append(digest_check)
        resolved_refs.append(
            {
                "uri": ref["uri"],
                "path": artifact["path"],
                "role": artifact["role"],
                "media_type": artifact["media_type"],
                "digest_expected": digest_expected,
                "digest_actual": digest_actual,
                "digest_match": digest_match,
            }
        )
        if not digest_match:
            errors.append(
                _error(
                    "BUNDLE_DIGEST_MISMATCH",
                    f"artifact digest mismatch for {ref['uri']}",
                    f"$.artifacts[{artifact_index}].digest",
                )
            )
        if artifact["digest"] != digest_expected:
            errors.append(
                _error(
                    "BUNDLE_DIGEST_MISMATCH",
                    f"bundle digest for {ref['uri']} does not match evidence record digest",
                    f"$.artifacts[{artifact_index}].digest",
                )
            )

        expected_media_type = mimetypes.guess_type(artifact_path.name)[0]
        if expected_media_type and artifact["media_type"] != expected_media_type:
            errors.append(
                _error(
                    "BUNDLE_MEDIA_TYPE_MISMATCH",
                    f"artifact media_type {artifact['media_type']} does not match detected {expected_media_type}",
                    f"$.artifacts[{artifact_index}].media_type",
                )
            )

    for artifact_index, artifact in enumerate(bundle["artifacts"]):
        if artifact["uri"] not in referenced_uris:
            warnings.append(
                _warning(
                    "BUNDLE_REF_UNUSED",
                    f"bundle artifact {artifact['uri']} is not referenced by the ASIEP evidence record",
                    f"$.artifacts[{artifact_index}].uri",
                )
            )

    return {
        "profile": "ASIEP",
        "profile_version": "0.1.0",
        "bundle_id": bundle_id,
        "valid": not errors,
        "bundle_root": str(bundle_root),
        "resolved_refs": resolved_refs,
        "unresolved_refs": unresolved_refs,
        "digest_checks": digest_checks,
        "errors": errors,
        "warnings": warnings,
    }


def _validate_bundle_schema(bundle: dict[str, Any]) -> list[dict[str, str]]:
    with BUNDLE_SCHEMA_PATH.open(encoding="utf-8") as handle:
        schema = json.load(handle)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(bundle), key=lambda error: list(error.path))
    if not errors:
        return []
    first = errors[0]
    return [_error("BUNDLE_SCHEMA", first.message, _format_path(first.path))]


def _bundle_root(bundle_file: Path, bundle: dict[str, Any]) -> Path:
    root_value = str(bundle.get("bundle_root", "."))
    root = Path(root_value)
    if root.is_absolute():
        return root.resolve()
    return (bundle_file.parent / root).resolve()


def _safe_join(root: Path, relative_path: str) -> Path | None:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def _extract_evidence_uris(record: dict[str, Any]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for index, item in enumerate(record.get("evidence", [])):
        uri = item.get("uri")
        if uri:
            digest = item.get("digest", {})
            digest_expected = ""
            if digest.get("algorithm") == "sha256" and digest.get("value"):
                digest_expected = f"sha256:{digest['value']}"
            refs.append(
                {
                    "uri": str(uri),
                    "json_path": f"$.evidence[{index}].uri",
                    "digest_expected": digest_expected,
                }
            )
    return refs


def _manifest_hash(bundle: dict[str, Any]) -> str:
    normalized = copy.deepcopy(bundle)
    normalized["integrity"]["bundle_manifest_hash"] = EMPTY_MANIFEST_HASH
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _empty_result(bundle_id: str, bundle_root: str, errors: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "profile": "ASIEP",
        "profile_version": "0.1.0",
        "bundle_id": bundle_id,
        "valid": False,
        "bundle_root": bundle_root,
        "resolved_refs": [],
        "unresolved_refs": [],
        "digest_checks": [],
        "errors": errors,
        "warnings": [],
    }


def _error(code: str, message: str, json_path: str) -> dict[str, str]:
    spec = get_error_code(code)
    return {
        "code": code,
        "severity": spec.severity,
        "message": message,
        "json_path": json_path,
        "json_pointer": _json_path_to_pointer(json_path),
        "remediation_hint": spec.remediation_hint,
        "repairability": spec.repairability,
    }


def _warning(code: str, message: str, json_path: str) -> dict[str, str]:
    spec = get_error_code(code)
    return {
        "code": code,
        "severity": "warning",
        "message": message,
        "json_path": json_path,
        "json_pointer": _json_path_to_pointer(json_path),
        "remediation_hint": spec.remediation_hint,
        "repairability": spec.repairability,
    }


def _format_path(path: Any) -> str:
    parts = list(path)
    if not parts:
        return "$"
    rendered = "$"
    for part in parts:
        if isinstance(part, int):
            rendered += f"[{part}]"
        else:
            rendered += f".{part}"
    return rendered


def _json_path_to_pointer(path: str) -> str:
    if path in {"", "$"}:
        return ""
    body = path[2:] if path.startswith("$.") else path.lstrip("$")
    pointer_parts: list[str] = []
    token = ""
    index = 0
    while index < len(body):
        char = body[index]
        if char == ".":
            if token:
                pointer_parts.append(_escape_pointer_token(token))
                token = ""
            index += 1
            continue
        if char == "[":
            if token:
                pointer_parts.append(_escape_pointer_token(token))
                token = ""
            end = body.find("]", index)
            if end == -1:
                break
            pointer_parts.append(_escape_pointer_token(body[index + 1 : end]))
            index = end + 1
            continue
        token += char
        index += 1
    if token:
        pointer_parts.append(_escape_pointer_token(token))
    return "/" + "/".join(pointer_parts)


def _escape_pointer_token(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")
