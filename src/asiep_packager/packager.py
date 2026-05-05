from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from asiep_resolver import resolve_bundle
from asiep_validator import validate_file
from asiep_validator.error_codes import get_error_code


ROOT = Path(__file__).resolve().parents[2]
REQUEST_SCHEMA_PATH = ROOT / "interfaces" / "asiep_package_request.schema.json"
RESULT_SCHEMA_PATH = ROOT / "interfaces" / "asiep_package_result.schema.json"
MANIFEST_SCHEMA_PATH = ROOT / "interfaces" / "asiep_package_manifest.schema.json"
FDO_SCHEMA_PATH = ROOT / "interfaces" / "asiep_fdo_record.schema.json"
ROCRATE_SCHEMA_PATH = ROOT / "interfaces" / "asiep_rocrate_metadata.schema.json"
PROV_SCHEMA_PATH = ROOT / "interfaces" / "asiep_prov_jsonld.schema.json"
PACKAGE_POLICY_PATH = ROOT / "profiles" / "asiep" / "v0.1" / "package_policy.json"
EMPTY_MANIFEST_HASH = "sha256:" + ("0" * 64)


class PackageBuildError(Exception):
    def __init__(self, code: str, message: str, json_path: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.json_path = json_path


def package_bundle(request_path: str | Path) -> dict[str, Any]:
    path = Path(request_path)
    request = _load_json_if_exists(path)
    if request is None:
        return _result_for_error(
            "PACKAGE_INPUT_BUNDLE_MISSING",
            package_id="",
            package_type="",
            output_package_dir="",
            input_bundle_manifest_path=str(path),
            message=f"package request not found: {path}",
            json_path="$",
        )

    request_errors = _validate_json(request, REQUEST_SCHEMA_PATH, "PACKAGE_SCHEMA")
    if request_errors:
        return _base_result(request, valid=False, errors=request_errors)

    policy = _load_json(PACKAGE_POLICY_PATH)
    policy_error = _check_policy(request, policy)
    if policy_error:
        return _base_result(request, valid=False, errors=[policy_error])

    bundle_manifest_path = _resolve_local_path(path.parent, request["input_bundle_manifest_path"])
    bundle_root = _resolve_local_path(path.parent, request["input_bundle_root"])
    if not bundle_manifest_path.exists() or not bundle_root.exists():
        return _base_result(
            request,
            valid=False,
            errors=[
                _error(
                    "PACKAGE_INPUT_BUNDLE_MISSING",
                    "input bundle manifest or root does not exist",
                    "$.input_bundle_manifest_path",
                )
            ],
        )

    resolver_result = resolve_bundle(bundle_manifest_path)
    resolver_summary = _resolver_summary(resolver_result)
    if request["package_policy"]["require_resolver_valid"] and not resolver_result["valid"]:
        return _base_result(
            request,
            valid=False,
            errors=[
                _error(
                    "PACKAGE_RESOLVER_FAILED",
                    "input bundle resolver validation failed",
                    "$.input_bundle_manifest_path",
                )
            ],
            resolver_result_summary=resolver_summary,
        )

    bundle = _load_json(bundle_manifest_path)
    evidence_path = _safe_join(bundle_root.resolve(), bundle["evidence_record_path"])
    if evidence_path is None or not evidence_path.exists():
        return _base_result(
            request,
            valid=False,
            errors=[
                _error(
                    "PACKAGE_INPUT_BUNDLE_MISSING",
                    "input bundle evidence record is missing or outside bundle root",
                    "$.input_bundle_root",
                )
            ],
            resolver_result_summary=resolver_summary,
        )

    validator_report = validate_file(evidence_path, bundle_root=bundle_root)
    validator_summary = _validator_summary(validator_report)
    if request["package_policy"]["require_validator_valid"] and not validator_report.valid:
        return _base_result(
            request,
            valid=False,
            errors=[
                _error(
                    "PACKAGE_VALIDATOR_FAILED",
                    "input bundle evidence validator check failed",
                    "$.input_bundle_root",
                )
            ],
            resolver_result_summary=resolver_summary,
            validator_result_summary=validator_summary,
        )

    try:
        generated = _write_package(
            request=request,
            bundle=bundle,
            bundle_manifest_path=bundle_manifest_path,
            bundle_root=bundle_root,
            evidence_path=evidence_path,
            resolver_summary=resolver_summary,
            validator_summary=validator_summary,
        )
    except PackageBuildError as exc:
        return _base_result(
            request,
            valid=False,
            errors=[_error(exc.code, exc.message, exc.json_path)],
            resolver_result_summary=resolver_summary,
            validator_result_summary=validator_summary,
        )
    except OSError as exc:
        return _base_result(
            request,
            valid=False,
            errors=[_error("PACKAGE_WRITE_FAILED", str(exc), "$.output_package_dir")],
            resolver_result_summary=resolver_summary,
            validator_result_summary=validator_summary,
        )

    schema_checks = [
        (generated["package_manifest"], MANIFEST_SCHEMA_PATH, "PACKAGE_MANIFEST_INVALID"),
        (generated["fdo_record"], FDO_SCHEMA_PATH, "PACKAGE_FDO_RECORD_INVALID"),
        (generated["rocrate_metadata"], ROCRATE_SCHEMA_PATH, "PACKAGE_ROCRATE_INVALID"),
        (generated["prov_jsonld"], PROV_SCHEMA_PATH, "PACKAGE_PROV_INVALID"),
    ]
    for payload, schema_path, code in schema_checks:
        errors = _validate_json(payload, schema_path, code)
        if errors:
            return _base_result(
                request,
                valid=False,
                errors=errors,
                generated_files=generated["generated_files"],
                copied_artifacts=generated["copied_artifacts"],
                resolver_result_summary=resolver_summary,
                validator_result_summary=validator_summary,
                fdo_record_path=generated["fdo_record_path"],
                rocrate_metadata_path=generated["rocrate_metadata_path"],
                prov_jsonld_path=generated["prov_jsonld_path"],
                package_manifest_path=generated["package_manifest_path"],
            )

    return _base_result(
        request,
        valid=True,
        generated_files=generated["generated_files"],
        copied_artifacts=generated["copied_artifacts"],
        resolver_result_summary=resolver_summary,
        validator_result_summary=validator_summary,
        fdo_record_path=generated["fdo_record_path"],
        rocrate_metadata_path=generated["rocrate_metadata_path"],
        prov_jsonld_path=generated["prov_jsonld_path"],
        package_manifest_path=generated["package_manifest_path"],
    )


def _write_package(
    *,
    request: dict[str, Any],
    bundle: dict[str, Any],
    bundle_manifest_path: Path,
    bundle_root: Path,
    evidence_path: Path,
    resolver_summary: dict[str, Any],
    validator_summary: dict[str, Any],
) -> dict[str, Any]:
    output_dir = (ROOT / request["output_package_dir"]).resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    evidence_dir = output_dir / "evidence"
    bundle_dir = output_dir / "bundle"
    artifact_dir = output_dir / "artifacts"
    evidence_dir.mkdir(parents=True)
    bundle_dir.mkdir(parents=True)
    artifact_dir.mkdir(parents=True)

    copied_evidence_path = evidence_dir / "evidence.json"
    shutil.copy2(evidence_path, copied_evidence_path)
    evidence = _load_json(copied_evidence_path)

    copied_artifacts: list[dict[str, str]] = []
    package_artifacts: list[dict[str, Any]] = []
    for index, artifact in enumerate(bundle["artifacts"]):
        source = _safe_join(bundle_root.resolve(), artifact["path"])
        if source is None or not source.exists():
            raise PackageBuildError(
                "PACKAGE_ARTIFACT_COPY_FAILED",
                f"cannot copy artifact outside or missing from bundle root: {artifact['path']}",
                f"$.artifacts[{index}].path",
            )
        target = output_dir / artifact["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        digest = _file_digest(target)
        if digest != artifact["digest"]:
            raise PackageBuildError(
                "PACKAGE_DIGEST_MISMATCH",
                f"copied artifact digest mismatch for {artifact['uri']}",
                f"$.artifacts[{index}].digest",
            )
        copied_artifacts.append(
            {
                "artifact_id": artifact["artifact_id"],
                "role": artifact["role"],
                "source_path": str(source),
                "target_path": artifact["path"],
                "digest": digest,
            }
        )
        package_artifacts.append(
            {
                "artifact_id": artifact["artifact_id"],
                "role": artifact["role"],
                "path": artifact["path"],
                "media_type": artifact["media_type"],
                "digest": digest,
                "copied_from": str(source),
                "required": artifact["required"],
            }
        )

    package_bundle = copy.deepcopy(bundle)
    package_bundle["bundle_root"] = ".."
    package_bundle["evidence_record_path"] = "evidence/evidence.json"
    package_bundle["integrity"]["bundle_manifest_hash"] = EMPTY_MANIFEST_HASH
    package_bundle["integrity"]["bundle_manifest_hash"] = _manifest_hash(package_bundle, "bundle_manifest_hash")
    package_bundle_path = bundle_dir / "bundle.json"
    _write_json(package_bundle_path, package_bundle)

    source_bundle_hash = _file_digest(bundle_manifest_path)
    evidence_record_hash = _file_digest(copied_evidence_path)
    created_at = request["created_at"]
    package_id = request["package_id"]
    package_type = request["package_type"]
    local_package_pid = f"urn:asiep:package:{_package_slug(package_id)}"
    local_fdo_pid = f"urn:asiep:fdo:{package_id}"

    fdo_path = output_dir / "fdo_record.json"
    rocrate_path = output_dir / "ro-crate-metadata.json"
    prov_path = output_dir / "prov.jsonld"
    manifest_path = output_dir / "package_manifest.json"

    fdo_record = _build_fdo_record(
        request=request,
        evidence=evidence,
        local_pid=local_fdo_pid,
        source_bundle_hash=source_bundle_hash,
        evidence_record_hash=evidence_record_hash,
    )
    rocrate_metadata = _build_rocrate_metadata(
        request=request,
        evidence=evidence,
        package_artifacts=package_artifacts,
        local_package_pid=local_package_pid,
    )
    prov_jsonld = _build_prov_jsonld(
        request=request,
        evidence=evidence,
        package_artifacts=package_artifacts,
        local_package_pid=local_package_pid,
    )
    _write_json(fdo_path, fdo_record)
    _write_json(rocrate_path, rocrate_metadata)
    _write_json(prov_path, prov_jsonld)

    manifest = {
        "package_id": package_id,
        "package_type": package_type,
        "profile": "ASIEP",
        "profile_version": "0.1.0",
        "package_version": "0.1.0",
        "created_at": created_at,
        "local_pid": local_package_pid,
        "source_bundle": {
            "path": str(bundle_manifest_path),
            "package_copy_path": "bundle/bundle.json",
            "digest": source_bundle_hash,
        },
        "evidence_record": {
            "path": "evidence/evidence.json",
            "source_path": str(evidence_path),
            "digest": evidence_record_hash,
            "record_id": evidence["profile_id"],
        },
        "fdo_record": {
            "path": "fdo_record.json",
            "digest": _file_digest(fdo_path),
            "local_pid": local_fdo_pid,
        },
        "rocrate_metadata": {
            "path": "ro-crate-metadata.json",
            "digest": _file_digest(rocrate_path),
        },
        "prov_jsonld": {
            "path": "prov.jsonld",
            "digest": _file_digest(prov_path),
        },
        "artifacts": package_artifacts,
        "validation": {
            "resolver_valid": resolver_summary["valid"],
            "validator_valid": validator_summary["valid"],
            "resolver_error_codes": resolver_summary["error_codes"],
            "validator_error_codes": validator_summary["error_codes"],
        },
        "integrity": {
            "package_manifest_hash": EMPTY_MANIFEST_HASH,
            "hash_algorithm": "sha256",
            "source_bundle_hash": source_bundle_hash,
            "evidence_record_hash": evidence_record_hash,
        },
        "access_policy": {
            "classification": "local-asiep-package",
            "network_access": False,
            "registry_submission": False,
            "global_resolution_claim": False,
        },
        "redaction_policy": {
            "contains_redactions": bool(bundle.get("redaction_policy", {}).get("contains_redactions", True)),
            "inline_sensitive_content": False,
            "content_mode": request["package_policy"]["content_mode"],
        },
    }
    manifest["integrity"]["package_manifest_hash"] = _manifest_hash(manifest, "package_manifest_hash")
    _write_json(manifest_path, manifest)

    generated_files = [
        _file_entry(manifest_path, output_dir, "package_manifest"),
        _file_entry(fdo_path, output_dir, "fdo_record"),
        _file_entry(rocrate_path, output_dir, "rocrate_metadata"),
        _file_entry(prov_path, output_dir, "prov_jsonld"),
        _file_entry(copied_evidence_path, output_dir, "evidence_record"),
        _file_entry(package_bundle_path, output_dir, "bundle_manifest"),
    ]
    return {
        "package_manifest": manifest,
        "fdo_record": fdo_record,
        "rocrate_metadata": rocrate_metadata,
        "prov_jsonld": prov_jsonld,
        "generated_files": generated_files,
        "copied_artifacts": copied_artifacts,
        "fdo_record_path": str(fdo_path),
        "rocrate_metadata_path": str(rocrate_path),
        "prov_jsonld_path": str(prov_path),
        "package_manifest_path": str(manifest_path),
    }


def _build_fdo_record(
    *,
    request: dict[str, Any],
    evidence: dict[str, Any],
    local_pid: str,
    source_bundle_hash: str,
    evidence_record_hash: str,
) -> dict[str, Any]:
    return {
        "local_pid": local_pid,
        "object_type": "local_fdo_like_asiep_package",
        "profile": "ASIEP",
        "profile_version": "0.1.0",
        "record_version": "0.1.0",
        "created_at": request["created_at"],
        "refers_to": {
            "package_manifest": "package_manifest.json",
            "evidence_record": "evidence/evidence.json",
            "bundle_manifest": "bundle/bundle.json",
        },
        "metadata": {
            "evidence_record_id": evidence["profile_id"],
            "agent_id": evidence["subject_agent"]["id"],
            "cycle_id": evidence["improvement"]["id"],
            "state": evidence["lifecycle"][-1]["state"],
            "package_id": request["package_id"],
            "content_type": "application/asiep-package+json",
            "conforms_to": [
                "https://w3id.org/asiep/v0.1",
                "interfaces/asiep_package_manifest.schema.json",
            ],
            "mappings": [
                "mappings/prov_mapping.md",
                "mappings/fdo_mapping.md",
                "mappings/ro_crate_mapping.md",
            ],
        },
        "operations": {
            "validate": {
                "command": "PYTHONPATH=src python -m asiep_validator {package_dir}/evidence/evidence.json --bundle-root {package_dir}/bundle --format json",
                "target_path": "evidence/evidence.json",
                "description": "Validate the packaged ASIEP evidence record with package-local bundle refs.",
            },
            "resolve_bundle": {
                "command": "PYTHONPATH=src python -m asiep_resolver {package_dir}/bundle/bundle.json --format json",
                "target_path": "bundle/bundle.json",
                "description": "Resolve package-local evidence artifact refs and recompute digests.",
            },
            "inspect_prov": {
                "command": "python -m json.tool {package_dir}/prov.jsonld",
                "target_path": "prov.jsonld",
                "description": "Inspect package-local PROV JSON-LD.",
            },
            "inspect_rocrate": {
                "command": "python -m json.tool {package_dir}/ro-crate-metadata.json",
                "target_path": "ro-crate-metadata.json",
                "description": "Inspect package-local RO-Crate-like metadata.",
            },
        },
        "integrity": {
            "hash_algorithm": "sha256",
            "source_bundle_hash": source_bundle_hash,
            "evidence_record_hash": evidence_record_hash,
        },
        "access_policy": {
            "scope": "local",
            "network_access": False,
            "registry_submission": False,
            "global_resolution_claim": False,
        },
    }


def _build_rocrate_metadata(
    *,
    request: dict[str, Any],
    evidence: dict[str, Any],
    package_artifacts: list[dict[str, Any]],
    local_package_pid: str,
) -> dict[str, Any]:
    graph: list[dict[str, Any]] = [
        {
            "@id": "./",
            "@type": "Dataset",
            "identifier": local_package_pid,
            "name": request["package_id"],
            "conformsTo": {"@id": "https://w3id.org/asiep/v0.1"},
            "hasPart": [{"@id": "evidence/evidence.json"}, {"@id": "bundle/bundle.json"}],
        },
        {
            "@id": "evidence/evidence.json",
            "@type": "File",
            "encodingFormat": "application/json",
            "about": {"@id": evidence["profile_id"]},
        },
        {
            "@id": "bundle/bundle.json",
            "@type": "File",
            "encodingFormat": "application/json",
            "about": {"@id": "bundle:package-local"},
        },
        {
            "@id": "asiep_packager",
            "@type": "SoftwareApplication",
            "name": "asiep_packager",
            "softwareVersion": "0.1.0",
        },
        {
            "@id": "action:package",
            "@type": "asiep:PackagingAction",
            "agent": {"@id": "asiep_packager"},
            "object": {"@id": "bundle/bundle.json"},
            "result": {"@id": "package_manifest.json"},
        },
        {
            "@id": "https://w3id.org/asiep/v0.1",
            "@type": "CreativeWork",
            "name": "ASIEP v0.1 profile conformance",
        },
    ]
    for artifact in package_artifacts:
        graph[0]["hasPart"].append({"@id": artifact["path"]})
        graph.append(
            {
                "@id": artifact["path"],
                "@type": "File",
                "encodingFormat": artifact["media_type"],
                "asiep:role": artifact["role"],
                "sha256": artifact["digest"],
            }
        )
    return {
        "@context": {
            "@vocab": "https://schema.org/",
            "asiep": "https://w3id.org/asiep/v0.1#",
        },
        "@graph": graph,
    }


def _build_prov_jsonld(
    *,
    request: dict[str, Any],
    evidence: dict[str, Any],
    package_artifacts: list[dict[str, Any]],
    local_package_pid: str,
) -> dict[str, Any]:
    graph: list[dict[str, Any]] = [
        {
            "@id": evidence["improvement"]["id"],
            "@type": "prov:Activity",
            "prov:wasAssociatedWith": {"@id": evidence["subject_agent"]["id"]},
            "prov:used": [{"@id": "entity:base-blueprint"}, {"@id": "entity:candidate-blueprint"}],
        },
        {
            "@id": evidence["subject_agent"]["id"],
            "@type": "prov:Agent",
            "asiep:version": evidence["subject_agent"]["version"],
        },
        {
            "@id": "entity:base-blueprint",
            "@type": "prov:Entity",
            "asiep:source": evidence["improvement"].get("parent_profile_id", ""),
        },
        {
            "@id": "entity:candidate-blueprint",
            "@type": "prov:Entity",
            "asiep:source": evidence["subject_agent"]["version"],
        },
        {
            "@id": "activity:package",
            "@type": "prov:Activity",
            "prov:used": {"@id": evidence["profile_id"]},
            "prov:generated": {"@id": "package_manifest.json"},
        },
        {
            "@id": "package_manifest.json",
            "@type": "prov:Entity",
            "asiep:localPid": local_package_pid,
            "asiep:packageId": request["package_id"],
        },
    ]
    for item in evidence["evidence"]:
        graph.append(
            {
                "@id": item["id"],
                "@type": "prov:Entity",
                "asiep:evidenceType": item["type"],
                "prov:atLocation": item.get("uri", ""),
            }
        )
    for artifact in package_artifacts:
        graph.append(
            {
                "@id": artifact["path"],
                "@type": "prov:Entity",
                "asiep:role": artifact["role"],
                "asiep:digest": artifact["digest"],
            }
        )
    return {
        "@context": {
            "prov": "http://www.w3.org/ns/prov#",
            "asiep": "https://w3id.org/asiep/v0.1#",
        },
        "@graph": graph,
    }


def _check_policy(request: dict[str, Any], policy: dict[str, Any]) -> dict[str, str] | None:
    if request["package_type"] not in policy["supported_package_types"]:
        return _error("PACKAGE_POLICY_VIOLATION", f"unsupported package_type: {request['package_type']}", "$.package_type")
    req_policy = request["package_policy"]
    required_true = [
        "forbid_remote_fetch",
        "forbid_fake_pid",
        "forbid_inline_sensitive_content",
    ]
    for key in required_true:
        if not req_policy[key]:
            return _error("PACKAGE_POLICY_VIOLATION", f"package policy must keep {key}=true", f"$.package_policy.{key}")
    if policy["pid_rules"]["global_pid_claim_allowed"] or policy["pid_rules"]["registry_submission_allowed"]:
        return _error("PACKAGE_PID_CLAIM_FORBIDDEN", "package policy cannot claim global PID registration", "$.package_policy")
    if "resolver_valid" in policy["required_preconditions"] and not req_policy["require_resolver_valid"]:
        return _error("PACKAGE_POLICY_VIOLATION", "resolver precondition cannot be disabled", "$.package_policy.require_resolver_valid")
    if "validator_valid" in policy["required_preconditions"] and not req_policy["require_validator_valid"]:
        return _error("PACKAGE_POLICY_VIOLATION", "validator precondition cannot be disabled", "$.package_policy.require_validator_valid")
    return None


def _resolver_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "valid": bool(result["valid"]),
        "error_codes": [error["code"] for error in result["errors"]],
        "warning_codes": [warning["code"] for warning in result["warnings"]],
    }


def _validator_summary(report: Any) -> dict[str, Any]:
    payload = report.to_agent_dict()
    return {
        "valid": bool(payload["valid"]),
        "error_codes": [error["code"] for error in payload["errors"]],
        "warning_codes": [warning["code"] for warning in payload["warnings"]],
    }


def _base_result(
    request: dict[str, Any],
    *,
    valid: bool,
    errors: list[dict[str, str]] | None = None,
    warnings: list[dict[str, str]] | None = None,
    generated_files: list[dict[str, str]] | None = None,
    copied_artifacts: list[dict[str, str]] | None = None,
    resolver_result_summary: dict[str, Any] | None = None,
    validator_result_summary: dict[str, Any] | None = None,
    fdo_record_path: str = "",
    rocrate_metadata_path: str = "",
    prov_jsonld_path: str = "",
    package_manifest_path: str = "",
) -> dict[str, Any]:
    output_dir = request.get("output_package_dir", "")
    result = {
        "profile": "ASIEP",
        "profile_version": "0.1.0",
        "package_id": request.get("package_id", ""),
        "package_type": request.get("package_type", ""),
        "valid": valid,
        "output_package_dir": output_dir,
        "input_bundle_manifest_path": request.get("input_bundle_manifest_path", ""),
        "generated_files": generated_files or [],
        "copied_artifacts": copied_artifacts or [],
        "resolver_result_summary": resolver_result_summary or _empty_summary(),
        "validator_result_summary": validator_result_summary or _empty_summary(),
        "fdo_record_path": fdo_record_path,
        "rocrate_metadata_path": rocrate_metadata_path,
        "prov_jsonld_path": prov_jsonld_path,
        "package_manifest_path": package_manifest_path,
        "errors": errors or [],
        "warnings": warnings or [],
        "revalidation_commands": _revalidation_commands(output_dir) if valid else [],
    }
    return result


def _result_for_error(
    code: str,
    package_id: str,
    package_type: str,
    output_package_dir: str,
    input_bundle_manifest_path: str,
    message: str,
    json_path: str,
) -> dict[str, Any]:
    return {
        "profile": "ASIEP",
        "profile_version": "0.1.0",
        "package_id": package_id,
        "package_type": package_type,
        "valid": False,
        "output_package_dir": output_package_dir,
        "input_bundle_manifest_path": input_bundle_manifest_path,
        "generated_files": [],
        "copied_artifacts": [],
        "resolver_result_summary": _empty_summary(),
        "validator_result_summary": _empty_summary(),
        "fdo_record_path": "",
        "rocrate_metadata_path": "",
        "prov_jsonld_path": "",
        "package_manifest_path": "",
        "errors": [_error(code, message, json_path)],
        "warnings": [],
        "revalidation_commands": [],
    }


def _empty_summary() -> dict[str, Any]:
    return {"valid": False, "error_codes": [], "warning_codes": []}


def _revalidation_commands(output_dir: str) -> list[str]:
    return [
        f"PYTHONPATH=src python -m asiep_resolver {output_dir}/bundle/bundle.json --format json",
        f"PYTHONPATH=src python -m asiep_validator {output_dir}/evidence/evidence.json --bundle-root {output_dir}/bundle --format json",
        f"python -m json.tool {output_dir}/fdo_record.json",
        f"python -m json.tool {output_dir}/ro-crate-metadata.json",
        f"python -m json.tool {output_dir}/prov.jsonld",
    ]


def _validate_json(payload: dict[str, Any], schema_path: Path, code: str) -> list[dict[str, str]]:
    schema = _load_json(schema_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    if not errors:
        return []
    first = errors[0]
    return [_error(code, first.message, _format_path(first.path))]


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


def _file_entry(path: Path, root: Path, role: str) -> dict[str, str]:
    return {
        "path": str(path.relative_to(root)),
        "media_type": _media_type(path),
        "digest": _file_digest(path),
        "role": role,
    }


def _media_type(path: Path) -> str:
    if path.suffix == ".jsonld":
        return "application/ld+json"
    if path.suffix == ".json":
        return "application/json"
    return "application/octet-stream"


def _package_slug(package_id: str) -> str:
    return package_id.split(":", 1)[1] if package_id.startswith("package:") else package_id


def _safe_join(root: Path, relative_path: str) -> Path | None:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def _resolve_local_path(base: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    candidate = base / path
    if candidate.exists():
        return candidate
    return ROOT / path


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _manifest_hash(payload: dict[str, Any], hash_field: str) -> str:
    normalized = copy.deepcopy(payload)
    normalized["integrity"][hash_field] = EMPTY_MANIFEST_HASH
    data = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _load_json(path)


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
