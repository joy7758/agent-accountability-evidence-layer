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
REQUEST_SCHEMA_PATH = ROOT / "interfaces" / "asiep_import_request.schema.json"
RESULT_SCHEMA_PATH = ROOT / "interfaces" / "asiep_import_result.schema.json"
OTEL_SCHEMA_PATH = ROOT / "interfaces" / "otel_genai_trace_fixture.schema.json"
LANGSMITH_SCHEMA_PATH = ROOT / "interfaces" / "langsmith_trace_fixture.schema.json"
IMPORT_POLICY_PATH = ROOT / "profiles" / "asiep" / "v0.1" / "import_policy.json"
EMPTY_MANIFEST_HASH = "sha256:" + ("0" * 64)

ARTIFACT_BY_ROLE = {
    "trace": ("trace.json", "application/json"),
    "feedback": ("feedback.json", "application/json"),
    "score": ("score.json", "application/json"),
    "diagnosis": ("diagnosis.md", "text/markdown"),
    "candidate_diff": ("candidate.diff", "text/x-diff"),
    "gate_report": ("gate_report.json", "application/json"),
}

EVIDENCE_TYPE_BY_ROLE = {
    "trace": "dataset",
    "feedback": "dataset",
    "score": "evaluation_report",
    "diagnosis": "safety_check",
    "candidate_diff": "proposal",
    "gate_report": "gate_report",
}


def import_trace(request_path: str | Path) -> dict[str, Any]:
    path = Path(request_path)
    request = _load_json_if_exists(path)
    if request is None:
        return _result_for_error(
            "IMPORT_SOURCE_MISSING",
            import_id="",
            source_type="",
            output_bundle_dir="",
            message=f"import request not found: {path}",
            json_path="$",
        )

    request_errors = _validate_json(request, REQUEST_SCHEMA_PATH, "IMPORT_SCHEMA")
    if request_errors:
        return _base_result(request, valid=False, errors=request_errors)

    policy = _load_json(IMPORT_POLICY_PATH)
    if request["source_type"] not in policy["supported_sources"]:
        return _base_result(
            request,
            valid=False,
            errors=[
                _error(
                    "IMPORT_SOURCE_UNSUPPORTED",
                    f"unsupported source_type: {request['source_type']}",
                    "$.source_type",
                )
            ],
        )

    source_path = _resolve_local_path(path.parent, request["source_path"])
    if not source_path.exists():
        return _base_result(
            request,
            valid=False,
            errors=[
                _error(
                    "IMPORT_SOURCE_MISSING",
                    f"source fixture not found: {request['source_path']}",
                    "$.source_path",
                )
            ],
        )

    source = _load_json(source_path)
    fixture_schema = _schema_for_source(request["source_type"])
    fixture_errors = _validate_json(source, fixture_schema, "IMPORT_SCHEMA")
    if fixture_errors:
        return _base_result(request, valid=False, errors=fixture_errors)

    sensitive_path = _find_sensitive_content(source, policy)
    if sensitive_path and _blocks_sensitive_content(request):
        return _base_result(
            request,
            valid=False,
            errors=[
                _error(
                    "IMPORT_SENSITIVE_CONTENT_BLOCKED",
                    f"sensitive content field blocked by import policy at {sensitive_path}",
                    sensitive_path,
                )
            ],
        )

    role_payloads, mapped_fields, unmapped_fields = _map_source_to_roles(request, source)
    required_roles = _required_roles(request, policy)
    missing = [role for role in required_roles if role not in role_payloads]
    if missing:
        return _base_result(
            request,
            valid=False,
            errors=[
                _error(
                    "IMPORT_REQUIRED_ROLE_MISSING",
                    f"required ASIEP import role missing: {missing[0]}",
                    "$.source_path",
                )
            ],
            mapped_fields=mapped_fields,
            unmapped_fields=unmapped_fields,
        )

    try:
        generated = _write_bundle(request, role_payloads, mapped_fields, unmapped_fields)
    except OSError as exc:
        return _base_result(
            request,
            valid=False,
            errors=[_error("IMPORT_ARTIFACT_WRITE_FAILED", str(exc), "$.output_bundle_dir")],
            mapped_fields=mapped_fields,
            unmapped_fields=unmapped_fields,
        )

    resolver_result = resolve_bundle(generated["bundle_manifest_path"])
    if not resolver_result["valid"]:
        return _base_result(
            request,
            valid=False,
            errors=[
                _error(
                    "IMPORT_BUNDLE_VALIDATION_FAILED",
                    "generated bundle failed resolver validation",
                    "$.output_bundle_dir",
                )
            ],
            generated_artifacts=generated["generated_artifacts"],
            mapped_fields=mapped_fields,
            unmapped_fields=unmapped_fields,
            evidence_record_path=generated["evidence_record_path"],
            bundle_manifest_path=generated["bundle_manifest_path"],
        )

    validator_report = validate_file(generated["evidence_record_path"], bundle_root=generated["output_bundle_dir"])
    if not validator_report.valid:
        return _base_result(
            request,
            valid=False,
            errors=[
                _error(
                    "IMPORT_VALIDATOR_FAILED",
                    "generated evidence failed ASIEP validator",
                    "$.output_bundle_dir",
                )
            ],
            generated_artifacts=generated["generated_artifacts"],
            mapped_fields=mapped_fields,
            unmapped_fields=unmapped_fields,
            evidence_record_path=generated["evidence_record_path"],
            bundle_manifest_path=generated["bundle_manifest_path"],
        )

    return _base_result(
        request,
        valid=True,
        generated_artifacts=generated["generated_artifacts"],
        mapped_fields=mapped_fields,
        unmapped_fields=unmapped_fields,
        evidence_record_path=generated["evidence_record_path"],
        bundle_manifest_path=generated["bundle_manifest_path"],
    )


def _write_bundle(
    request: dict[str, Any],
    role_payloads: dict[str, Any],
    mapped_fields: list[dict[str, str]],
    unmapped_fields: list[str],
) -> dict[str, Any]:
    output_dir = (ROOT / request["output_bundle_dir"]).resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    artifacts_dir = output_dir / "artifacts"
    artifacts_dir.mkdir(parents=True)

    bundle_name = output_dir.name
    generated_artifacts = []
    evidence_items = []
    artifact_manifest = []

    ordered_roles = ["candidate_diff", "trace", "feedback", "score", "diagnosis", "gate_report"]
    for role in ordered_roles:
        if role not in role_payloads:
            continue
        filename, media_type = ARTIFACT_BY_ROLE[role]
        artifact_path = artifacts_dir / filename
        content = _artifact_bytes(role, role_payloads[role])
        artifact_path.write_bytes(content)
        digest_hex = hashlib.sha256(content).hexdigest()
        digest = "sha256:" + digest_hex
        uri = f"bundle://{bundle_name}/artifacts/{filename}"
        artifact_id = f"artifact:{role.replace('_', '-')}"
        rel_path = f"artifacts/{filename}"
        generated_artifacts.append(
            {
                "artifact_id": artifact_id,
                "uri": uri,
                "path": rel_path,
                "role": role,
                "media_type": media_type,
                "digest": digest,
            }
        )
        artifact_manifest.append(
            {
                "artifact_id": artifact_id,
                "uri": uri,
                "path": rel_path,
                "media_type": media_type,
                "digest": digest,
                "role": role,
                "required": role in {"trace", "feedback", "score", "candidate_diff", "gate_report"},
            }
        )
        evidence_items.append(
            {
                "id": f"ev:{role.replace('_', '-')}",
                "type": EVIDENCE_TYPE_BY_ROLE[role],
                "uri": uri,
                "digest": {"algorithm": "sha256", "value": digest_hex},
                "produced_by": "asiep_importer",
            }
        )

    evidence_by_role = {item["id"][3:].replace("-", "_"): item for item in evidence_items}
    if "score" in evidence_by_role:
        evidence_by_role["score"]["refs"] = [ref for ref in ["ev:trace", "ev:feedback"] if any(item["id"] == ref for item in evidence_items)]
    if "diagnosis" in evidence_by_role:
        evidence_by_role["diagnosis"]["refs"] = [ref for ref in ["ev:score"] if any(item["id"] == ref for item in evidence_items)]
    if "gate_report" in evidence_by_role:
        evidence_by_role["gate_report"]["refs"] = [
            ref for ref in ["ev:score", "ev:diagnosis", "ev:candidate-diff"] if any(item["id"] == ref for item in evidence_items)
        ]

    evidence = _build_evidence_record(request, evidence_items)
    evidence_path = output_dir / "evidence.json"
    _write_json(evidence_path, evidence)

    bundle = {
        "bundle_id": f"bundle:{bundle_name}",
        "profile": "ASIEP",
        "profile_version": "0.1.0",
        "bundle_version": "0.1.0",
        "created_at": request["created_at"],
        "evidence_record_path": "evidence.json",
        "bundle_root": ".",
        "artifacts": artifact_manifest,
        "access_policy": {
            "classification": "local-import-fixture",
            "allowed_resolvers": ["asiep_resolver"],
            "network_access": False,
        },
        "redaction_policy": {
            "contains_redactions": request["redaction_policy"]["mode"] != "none",
            "redaction_summary": request["redaction_policy"].get("notes", "Imported in ref_only mode."),
        },
        "integrity": {
            "bundle_manifest_hash": EMPTY_MANIFEST_HASH,
            "hash_algorithm": "sha256",
        },
    }
    bundle["integrity"]["bundle_manifest_hash"] = _manifest_hash(bundle)
    bundle_path = output_dir / "bundle.json"
    _write_json(bundle_path, bundle)

    return {
        "output_bundle_dir": str(output_dir),
        "evidence_record_path": str(evidence_path),
        "bundle_manifest_path": str(bundle_path),
        "generated_artifacts": generated_artifacts,
    }


def _build_evidence_record(request: dict[str, Any], evidence_items: list[dict[str, Any]]) -> dict[str, Any]:
    evidence_ids = {item["id"] for item in evidence_items}
    maybe_diagnosis = ["ev:diagnosis"] if "ev:diagnosis" in evidence_ids else []
    return {
        "@context": "https://w3id.org/asiep/v0.1/context.jsonld",
        "profile_version": "ASIEP-0.1",
        "profile_id": f"asiep:{request['import_id'].split(':', 1)[1]}",
        "subject_agent": {
            "id": request["agent_id"],
            "name": request["agent_id"],
            "version": request["candidate_blueprint_id"],
            "implementation": "trace-import-fixture",
        },
        "improvement": {
            "id": f"improvement:{request['import_id'].split(':', 1)[1]}",
            "summary": f"Imported trace evidence for {request['change_scope']}.",
            "hypothesis": "Local trace, feedback, score, candidate diff, and gate report support an ASIEP evidence record.",
            "parent_profile_id": request["parent_release_id"],
        },
        "lifecycle": [
            {
                "event_id": "event:001-draft",
                "state": "DRAFT",
                "at": request["created_at"],
                "actor": "asiep_importer",
                "evidence_refs": ["ev:candidate-diff"],
            },
            {
                "event_id": "event:002-candidate",
                "state": "CANDIDATE",
                "at": request["created_at"],
                "actor": "asiep_importer",
                "evidence_refs": ["ev:trace", "ev:feedback"],
            },
            {
                "event_id": "event:003-evaluated",
                "state": "EVALUATED",
                "at": request["created_at"],
                "actor": "asiep_importer",
                "evidence_refs": ["ev:score", *maybe_diagnosis],
            },
            {
                "event_id": "event:004-gated",
                "state": "GATED",
                "at": request["created_at"],
                "actor": "asiep_importer",
                "evidence_refs": ["ev:gate-report"],
            },
            {
                "event_id": "event:005-promoted",
                "state": "PROMOTED",
                "at": request["created_at"],
                "actor": "asiep_importer",
                "evidence_refs": ["ev:gate-report"],
            },
        ],
        "evidence": evidence_items,
        "safety_checks": [
            {
                "id": "safety:imported-trace-regression-check",
                "evidence_ref": "ev:diagnosis" if "ev:diagnosis" in evidence_ids else "ev:score",
                "check": "Imported trace fixture does not report a safety regression.",
                "passed": True,
                "severity": "none",
                "regression": False,
            }
        ],
        "flip_counts": {
            "prompt_to_fail": {
                "count": 1,
                "threshold": 2,
                "evidence_ref": "ev:score",
            }
        },
        "gates": [
            {
                "id": "gate:imported-trace-promotion",
                "decision": "promote",
                "gate_report_ref": "ev:gate-report",
                "evidence_refs": [
                    ref for ref in ["ev:score", "ev:diagnosis", "ev:candidate-diff"] if ref in evidence_ids
                ],
            }
        ],
        "references": [],
    }


def _map_source_to_roles(request: dict[str, Any], source: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]], list[str]]:
    if request["source_type"] == "otel_genai":
        return _map_otel(source)
    if request["source_type"] == "langsmith":
        return _map_langsmith(source)
    return {}, [], ["generic_agent_trace mapping is not implemented in M4 fixtures"]


def _map_otel(source: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]], list[str]]:
    roles: dict[str, Any] = {"trace": _redacted_otel_trace(source)}
    mapped = [{"source_path": "$", "target_path": "artifacts/trace.json", "role": "trace"}]
    unmapped: list[str] = []
    for index, span in enumerate(source.get("spans", [])):
        role = span.get("attributes", {}).get("asiep.role")
        if not role or role == "trace":
            continue
        roles[role] = {
            "span_id": span["span_id"],
            "name": span["name"],
            "attributes": _non_sensitive_mapping(span["attributes"]),
            "events": span.get("events", []),
        }
        target = ARTIFACT_BY_ROLE.get(role, (f"{role}.json", "application/json"))[0]
        mapped.append({"source_path": f"$.spans[{index}]", "target_path": f"artifacts/{target}", "role": role})
    return roles, mapped, unmapped


def _map_langsmith(source: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]], list[str]]:
    roles: dict[str, Any] = {"trace": _redacted_langsmith_trace(source)}
    mapped = [{"source_path": "$", "target_path": "artifacts/trace.json", "role": "trace"}]
    unmapped: list[str] = []
    for index, run in enumerate(source.get("runs", [])):
        role = run.get("asiep_role")
        if not role or role == "trace":
            continue
        roles[role] = {
            "run_id": run["run_id"],
            "name": run["name"],
            "run_type": run["run_type"],
            "metadata": _non_sensitive_mapping(run.get("metadata", {})),
            "tags": run.get("tags", []),
            "inputs_ref": run.get("inputs_ref", ""),
            "outputs_ref": run.get("outputs_ref", ""),
        }
        target = ARTIFACT_BY_ROLE.get(role, (f"{role}.json", "application/json"))[0]
        mapped.append({"source_path": f"$.runs[{index}]", "target_path": f"artifacts/{target}", "role": role})
    if source.get("feedback"):
        roles["feedback"] = {"feedback": source["feedback"]}
        mapped.append({"source_path": "$.feedback", "target_path": "artifacts/feedback.json", "role": "feedback"})
    return roles, mapped, unmapped


def _redacted_otel_trace(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "trace_id": source["trace_id"],
        "spans": [
            {
                "span_id": span["span_id"],
                "parent_span_id": span.get("parent_span_id"),
                "name": span["name"],
                "kind": span["kind"],
                "start_time": span["start_time"],
                "end_time": span["end_time"],
                "attributes": _non_sensitive_mapping(span.get("attributes", {})),
                "events": [{"name": event["name"], "time": event["time"]} for event in span.get("events", [])],
            }
            for span in source.get("spans", [])
        ],
    }


def _redacted_langsmith_trace(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_name": source["project_name"],
        "trace_id": source["trace_id"],
        "runs": [
            {
                "run_id": run["run_id"],
                "parent_run_id": run.get("parent_run_id"),
                "name": run["name"],
                "run_type": run["run_type"],
                "inputs_ref": run.get("inputs_ref", ""),
                "outputs_ref": run.get("outputs_ref", ""),
                "tags": run.get("tags", []),
                "metadata": _non_sensitive_mapping(run.get("metadata", {})),
                "asiep_role": run.get("asiep_role"),
            }
            for run in source.get("runs", [])
        ],
        "feedback_count": len(source.get("feedback", [])),
    }


def _artifact_bytes(role: str, payload: Any) -> bytes:
    if role == "candidate_diff":
        if isinstance(payload, dict):
            diff = payload.get("attributes", {}).get("asiep.candidate_diff", "")
            diff = diff or payload.get("metadata", {}).get("asiep.candidate_diff", "")
            diff = diff or payload.get("candidate_diff", "")
        else:
            diff = str(payload)
        return (diff or "TODO: candidate diff source was empty").encode("utf-8") + b"\n"
    if role == "diagnosis":
        if isinstance(payload, dict):
            summary = payload.get("attributes", {}).get("asiep.diagnosis", "")
            summary = summary or payload.get("metadata", {}).get("asiep.diagnosis", "")
        else:
            summary = str(payload)
        summary = summary or "Imported diagnosis evidence."
        return ("# Imported Diagnosis\n\n" + summary + "\n").encode("utf-8")
    return json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _required_roles(request: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    roles = ["trace"]
    if request["import_policy"]["require_feedback"]:
        roles.append("feedback")
    if request["import_policy"]["require_score"]:
        roles.append("score")
    if request["import_policy"]["require_candidate_diff"]:
        roles.append("candidate_diff")
    if request["import_policy"]["require_gate_report"]:
        roles.append("gate_report")
    return [role for role in policy["required_artifact_roles"] if role in roles]


def _blocks_sensitive_content(request: dict[str, Any]) -> bool:
    return (
        request["import_policy"]["fail_on_sensitive_content"]
        and request["import_policy"]["content_mode"] != "full_content_for_test_only"
        and not request["redaction_policy"]["allow_raw_content"]
    )


def _find_sensitive_content(value: Any, policy: dict[str, Any], path: str = "$") -> str | None:
    blocked = set(policy["sensitive_content_rules"]["blocked_keys"])
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in blocked and child not in ("", None, [], {}):
                return child_path
            found = _find_sensitive_content(child, policy, child_path)
            if found:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = _find_sensitive_content(child, policy, f"{path}[{index}]")
            if found:
                return found
    return None


def _non_sensitive_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    blocked = {"prompt", "raw_prompt", "raw_user_input", "raw_model_output", "input", "inputs", "output", "outputs", "messages", "completion"}
    return {key: value for key, value in mapping.items() if key not in blocked}


def _schema_for_source(source_type: str) -> Path:
    if source_type == "otel_genai":
        return OTEL_SCHEMA_PATH
    if source_type == "langsmith":
        return LANGSMITH_SCHEMA_PATH
    return OTEL_SCHEMA_PATH


def _validate_json(payload: dict[str, Any], schema_path: Path, code: str) -> list[dict[str, str]]:
    schema = _load_json(schema_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    if not errors:
        return []
    first = errors[0]
    return [_error(code, first.message, _format_path(first.path))]


def _base_result(
    request: dict[str, Any],
    *,
    valid: bool,
    errors: list[dict[str, str]] | None = None,
    warnings: list[dict[str, str]] | None = None,
    generated_artifacts: list[dict[str, str]] | None = None,
    mapped_fields: list[dict[str, str]] | None = None,
    unmapped_fields: list[str] | None = None,
    evidence_record_path: str = "",
    bundle_manifest_path: str = "",
) -> dict[str, Any]:
    output_dir = request.get("output_bundle_dir", "")
    return {
        "profile": "ASIEP",
        "profile_version": "0.1.0",
        "import_id": request.get("import_id", ""),
        "source_type": request.get("source_type", ""),
        "valid": valid,
        "output_bundle_dir": output_dir,
        "evidence_record_path": evidence_record_path,
        "bundle_manifest_path": bundle_manifest_path,
        "generated_artifacts": generated_artifacts or [],
        "mapped_fields": mapped_fields or [],
        "unmapped_fields": unmapped_fields or [],
        "errors": errors or [],
        "warnings": warnings or [],
        "revalidation_commands": _revalidation_commands(output_dir) if valid else [],
    }


def _result_for_error(code: str, import_id: str, source_type: str, output_bundle_dir: str, message: str, json_path: str) -> dict[str, Any]:
    return {
        "profile": "ASIEP",
        "profile_version": "0.1.0",
        "import_id": import_id,
        "source_type": source_type,
        "valid": False,
        "output_bundle_dir": output_bundle_dir,
        "evidence_record_path": "",
        "bundle_manifest_path": "",
        "generated_artifacts": [],
        "mapped_fields": [],
        "unmapped_fields": [],
        "errors": [_error(code, message, json_path)],
        "warnings": [],
        "revalidation_commands": [],
    }


def _revalidation_commands(output_dir: str) -> list[str]:
    return [
        f"PYTHONPATH=src python -m asiep_resolver {output_dir}/bundle.json --format json",
        f"PYTHONPATH=src python -m asiep_validator {output_dir}/evidence.json --bundle-root {output_dir} --format json",
    ]


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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _load_json(path)


def _resolve_local_path(base: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    candidate = base / path
    if candidate.exists():
        return candidate
    return ROOT / path


def _manifest_hash(bundle: dict[str, Any]) -> str:
    normalized = copy.deepcopy(bundle)
    normalized["integrity"]["bundle_manifest_hash"] = EMPTY_MANIFEST_HASH
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


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
