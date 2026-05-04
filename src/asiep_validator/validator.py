from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from .error_codes import get_error_code


SHA256_RE = re.compile(r"^[a-fA-F0-9]{64}$")

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"CANDIDATE"},
    "CANDIDATE": {"EVALUATED"},
    "EVALUATED": {"GATED"},
    "GATED": {"PROMOTED", "REJECTED"},
    "PROMOTED": {"ROLLED_BACK"},
    "REJECTED": set(),
    "ROLLED_BACK": set(),
}


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    path: str = ""
    invariant_id: str | None = None
    agent_code: str | None = None
    remediation_hint: str | None = None

    @property
    def json_code(self) -> str:
        return self.agent_code or self.code

    @property
    def json_path(self) -> str:
        return _as_json_path(self.path)

    @property
    def json_pointer(self) -> str:
        return _json_path_to_pointer(self.json_path)

    def to_agent_error(self) -> dict[str, str]:
        spec = get_error_code(self.json_code)
        error = {
            "code": self.json_code,
            "severity": spec.severity,
            "message": self.message,
            "json_path": self.json_path,
            "json_pointer": self.json_pointer,
            "remediation_hint": self.remediation_hint or spec.remediation_hint,
            "repairability": spec.repairability,
        }
        invariant_id = self.invariant_id or spec.invariant_id
        if invariant_id:
            error["invariant_id"] = invariant_id
        return error


@dataclass(frozen=True)
class ValidationReport:
    valid: bool
    issues: tuple[ValidationIssue, ...]
    record_id: str | None = None

    @property
    def codes(self) -> list[str]:
        seen: set[str] = set()
        codes: list[str] = []
        for issue in self.issues:
            if issue.code not in seen:
                seen.add(issue.code)
                codes.append(issue.code)
        return codes if codes else ["VALID"]

    def to_agent_dict(self) -> dict[str, Any]:
        return {
            "profile": "ASIEP",
            "profile_version": "0.1.0",
            "valid": self.valid,
            "record_id": self.record_id or "",
            "errors": [issue.to_agent_error() for issue in self.issues],
            "warnings": [],
        }


def validate_file(profile_path: str | Path) -> ValidationReport:
    path = Path(profile_path)
    with path.open("r", encoding="utf-8") as handle:
        profile = json.load(handle)
    return validate_profile(profile)


def validate_profile(profile: Mapping[str, Any]) -> ValidationReport:
    record_id = str(profile.get("profile_id", "")) if isinstance(profile, Mapping) else ""
    schema_issues = _validate_schema(profile)
    if schema_issues:
        return ValidationReport(False, tuple(schema_issues), record_id=record_id)

    checks = (
        _check_state_machine,
        _check_evidence_refs,
        _check_gate_decisions,
        _check_rollback_evidence,
        _check_reference_digests,
    )
    for check in checks:
        issues = check(profile)
        if issues:
            return ValidationReport(False, tuple(issues), record_id=record_id)
    return ValidationReport(True, tuple(), record_id=record_id)


def _validate_schema(profile: Mapping[str, Any]) -> list[ValidationIssue]:
    schema_path = _schema_path()
    with schema_path.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(profile), key=lambda error: list(error.path))
    if not errors:
        return []

    first = errors[0]
    return [_schema_issue(first)]


def _schema_issue(error: Any) -> ValidationIssue:
    path = _format_path(error.path)
    if error.validator == "required":
        missing_field = _missing_required_field(error.message)
        missing_path = _append_json_path(path, missing_field) if missing_field else path
        if missing_field == "gate_report_ref":
            return ValidationIssue(
                "SCHEMA",
                error.message,
                missing_path,
                invariant_id="I5",
                agent_code="INV_MISSING_GATE_REPORT",
                remediation_hint="Add gates[].gate_report_ref pointing to gate_report evidence.",
            )
        return ValidationIssue(
            "SCHEMA",
            error.message,
            missing_path,
            invariant_id="I1",
            agent_code="SCHEMA_REQUIRED_FIELD",
        )
    if error.validator == "type":
        return ValidationIssue("SCHEMA", error.message, path, invariant_id="I1", agent_code="SCHEMA_TYPE_MISMATCH")
    if error.validator == "const":
        return ValidationIssue("SCHEMA", error.message, path, invariant_id="I1", agent_code="SCHEMA_CONST_MISMATCH")
    return ValidationIssue("SCHEMA", error.message, path, invariant_id="I1")


def _schema_path() -> Path:
    override = os.environ.get("ASIEP_SCHEMA_PATH")
    if override:
        return Path(override)

    repo_schema = Path(__file__).resolve().parents[2] / "schemas" / "asiep.schema.json"
    if repo_schema.exists():
        return repo_schema

    cwd_schema = Path.cwd() / "schemas" / "asiep.schema.json"
    if cwd_schema.exists():
        return cwd_schema

    raise FileNotFoundError("schemas/asiep.schema.json not found")


def _check_state_machine(profile: Mapping[str, Any]) -> list[ValidationIssue]:
    lifecycle = profile["lifecycle"]
    states = [event["state"] for event in lifecycle]
    if states[0] != "DRAFT":
        return [
            ValidationIssue(
                "STATE_TRANSITION",
                "lifecycle must start at DRAFT",
                "$.lifecycle[0].state",
                invariant_id="I2",
            )
        ]

    for index, (previous, current) in enumerate(zip(states, states[1:]), start=1):
        if current not in ALLOWED_TRANSITIONS[previous]:
            return [
                ValidationIssue(
                    "STATE_TRANSITION",
                    f"invalid transition {previous} -> {current}",
                    f"$.lifecycle[{index}].state",
                    invariant_id="I3",
                )
            ]
    return []


def _check_evidence_refs(profile: Mapping[str, Any]) -> list[ValidationIssue]:
    evidence_ids = {item["id"] for item in profile["evidence"]}
    refs: list[tuple[str, str]] = []

    for index, item in enumerate(profile["evidence"]):
        refs.extend((ref, f"$.evidence[{index}].refs") for ref in item.get("refs", []))

    for index, event in enumerate(profile["lifecycle"]):
        refs.extend((ref, f"$.lifecycle[{index}].evidence_refs") for ref in event["evidence_refs"])

    for index, check in enumerate(profile["safety_checks"]):
        refs.append((check["evidence_ref"], f"$.safety_checks[{index}].evidence_ref"))

    for metric, record in profile["flip_counts"].items():
        refs.append((record["evidence_ref"], f"$.flip_counts.{metric}.evidence_ref"))

    for index, gate in enumerate(profile["gates"]):
        refs.append((gate["gate_report_ref"], f"$.gates[{index}].gate_report_ref"))
        refs.extend((ref, f"$.gates[{index}].evidence_refs") for ref in gate["evidence_refs"])

    rollback = profile.get("rollback")
    if rollback:
        refs.append((rollback["evidence_ref"], "$.rollback.evidence_ref"))

    for ref, path in refs:
        if ref not in evidence_ids:
            return [
                ValidationIssue(
                    "REF_UNRESOLVED",
                    f"evidence reference {ref} is not defined",
                    path,
                    invariant_id="I4",
                )
            ]
    return []


def _check_gate_decisions(profile: Mapping[str, Any]) -> list[ValidationIssue]:
    promotes = [gate for gate in profile["gates"] if gate["decision"] == "promote"]
    if not promotes:
        return []

    for index, check in enumerate(profile["safety_checks"]):
        if check["regression"]:
            return [
                ValidationIssue(
                    "INV_SAFETY_REGRESSION",
                    "promotion is not allowed with a safety regression",
                    f"$.safety_checks[{index}].regression",
                    invariant_id="I6",
                )
            ]
        if not check["passed"] and check["severity"] in {"p2", "p1", "p0"}:
            return [
                ValidationIssue(
                    "INV_SAFETY_REGRESSION",
                    "promotion is not allowed with an unresolved p2-or-higher safety failure",
                    f"$.safety_checks[{index}].passed",
                    invariant_id="I7",
                )
            ]

    for metric, record in profile["flip_counts"].items():
        if record["count"] > record["threshold"]:
            return [
                ValidationIssue(
                    "INV_FLIP_THRESHOLD",
                    f"{metric} count {record['count']} exceeds threshold {record['threshold']}",
                    f"$.flip_counts.{metric}.count",
                    invariant_id="I8",
                )
            ]
    return []


def _check_rollback_evidence(profile: Mapping[str, Any]) -> list[ValidationIssue]:
    has_rollback_state = any(event["state"] == "ROLLED_BACK" for event in profile["lifecycle"])
    has_rollback_gate = any(gate["decision"] == "rollback" for gate in profile["gates"])
    if not has_rollback_state and not has_rollback_gate:
        return []

    rollback = profile.get("rollback")
    if not rollback:
        return [
            ValidationIssue(
                "ROLLBACK_EVIDENCE",
                "rollback state or decision requires rollback evidence",
                "$.rollback",
                invariant_id="I9",
                agent_code="INV_ROLLBACK_EVIDENCE",
            )
        ]

    evidence_by_id = {item["id"]: item for item in profile["evidence"]}
    item = evidence_by_id.get(rollback["evidence_ref"])
    if not item or item["type"] != "rollback_report":
        return [
            ValidationIssue(
                "ROLLBACK_EVIDENCE",
                "rollback evidence_ref must point to rollback_report evidence",
                "$.rollback.evidence_ref",
                invariant_id="I9",
                agent_code="INV_ROLLBACK_EVIDENCE",
            )
        ]
    return []


def _check_reference_digests(profile: Mapping[str, Any]) -> list[ValidationIssue]:
    for index, evidence in enumerate(profile["evidence"]):
        digest = evidence["digest"]
        if digest["algorithm"] != "sha256" or not SHA256_RE.fullmatch(digest["value"]):
            return [
                ValidationIssue(
                    "DIGEST_BASIC",
                    "evidence digest must be sha256 with a 64-character hex value",
                    f"$.evidence[{index}].digest",
                    invariant_id="I10",
                    agent_code="REF_DIGEST_FORMAT",
                )
            ]

    for index, reference in enumerate(profile["references"]):
        digest = reference["digest"]
        if digest["algorithm"] != "sha256" or not SHA256_RE.fullmatch(digest["value"]):
            return [
                ValidationIssue(
                    "DIGEST_BASIC",
                    "reference digest must be sha256 with a 64-character hex value",
                    f"$.references[{index}].digest",
                    invariant_id="I10",
                    agent_code="REF_DIGEST_FORMAT",
                )
            ]
    return []


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


def _as_json_path(path: str) -> str:
    if not path:
        return "$"
    if path.startswith("$"):
        return path
    return f"$.{path}"


def _append_json_path(path: str, field: str | None) -> str:
    if not field:
        return path
    if path == "$":
        return f"$.{field}"
    return f"{path}.{field}"


def _missing_required_field(message: str) -> str | None:
    match = re.search(r"'([^']+)' is a required property", message)
    if not match:
        return None
    return match.group(1)


def _json_path_to_pointer(path: str) -> str:
    if path in {"", "$"}:
        return ""
    body = path[2:] if path.startswith("$.") else path.lstrip("$")
    pointer_parts: list[str] = []
    index = 0
    token = ""
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
