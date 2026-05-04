from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ErrorCodeSpec:
    code: str
    title: str
    severity: str
    description: str
    remediation_hint: str
    repairability: str
    invariant_id: str | None = None

    def to_dict(self) -> dict[str, str]:
        data = asdict(self)
        return {key: value for key, value in data.items() if value is not None}


ERROR_CODES: dict[str, ErrorCodeSpec] = {
    "SCHEMA": ErrorCodeSpec(
        code="SCHEMA",
        title="Schema validation failed",
        severity="error",
        description="The evidence object does not satisfy the ASIEP JSON Schema.",
        remediation_hint="Repair the JSON object so it conforms to schemas/asiep.schema.json.",
        repairability="agent_fixable",
        invariant_id="I1",
    ),
    "SCHEMA_REQUIRED_FIELD": ErrorCodeSpec(
        code="SCHEMA_REQUIRED_FIELD",
        title="Required field missing",
        severity="error",
        description="A field required by the ASIEP schema is missing.",
        remediation_hint="Add the missing required field at the reported json_path.",
        repairability="agent_fixable",
        invariant_id="I1",
    ),
    "SCHEMA_TYPE_MISMATCH": ErrorCodeSpec(
        code="SCHEMA_TYPE_MISMATCH",
        title="Schema type mismatch",
        severity="error",
        description="A field has a value type that is not allowed by the ASIEP schema.",
        remediation_hint="Change the field value to the schema-required type.",
        repairability="agent_fixable",
        invariant_id="I1",
    ),
    "SCHEMA_CONST_MISMATCH": ErrorCodeSpec(
        code="SCHEMA_CONST_MISMATCH",
        title="Schema constant mismatch",
        severity="error",
        description="A field does not match a fixed value required by the ASIEP schema.",
        remediation_hint="Set the field to the constant value required by the schema.",
        repairability="agent_fixable",
        invariant_id="I1",
    ),
    "STATE_TRANSITION": ErrorCodeSpec(
        code="STATE_TRANSITION",
        title="Invalid lifecycle transition",
        severity="error",
        description="The lifecycle does not follow the ASIEP state machine.",
        remediation_hint="Reorder lifecycle events to follow DRAFT -> CANDIDATE -> EVALUATED -> GATED -> PROMOTED or REJECTED.",
        repairability="agent_fixable",
    ),
    "REF_UNRESOLVED": ErrorCodeSpec(
        code="REF_UNRESOLVED",
        title="Unresolved evidence reference",
        severity="error",
        description="A referenced evidence id is not present in the evidence array.",
        remediation_hint="Add the missing evidence object or update the reference to an existing evidence id.",
        repairability="external_evidence_required",
        invariant_id="I4",
    ),
    "REF_DIGEST_FORMAT": ErrorCodeSpec(
        code="REF_DIGEST_FORMAT",
        title="Digest format invalid",
        severity="error",
        description="An evidence or external reference digest is not a sha256 64-character hex value.",
        remediation_hint="Set digest.algorithm to sha256 and digest.value to a 64-character hexadecimal SHA-256 digest.",
        repairability="external_evidence_required",
        invariant_id="I10",
    ),
    "DIGEST_BASIC": ErrorCodeSpec(
        code="DIGEST_BASIC",
        title="Digest format invalid",
        severity="error",
        description="Compatibility code for a basic digest format failure.",
        remediation_hint="Set digest.algorithm to sha256 and digest.value to a 64-character hexadecimal SHA-256 digest.",
        repairability="external_evidence_required",
        invariant_id="I10",
    ),
    "INV_MISSING_GATE_REPORT": ErrorCodeSpec(
        code="INV_MISSING_GATE_REPORT",
        title="Gate report missing",
        severity="error",
        description="A gate object is missing the evidence reference for its gate report.",
        remediation_hint="Add gates[].gate_report_ref pointing to gate_report evidence.",
        repairability="external_evidence_required",
        invariant_id="I5",
    ),
    "INV_SAFETY_REGRESSION": ErrorCodeSpec(
        code="INV_SAFETY_REGRESSION",
        title="Promotion blocked by safety regression",
        severity="error",
        description="The profile promotes an improvement while safety evidence records a regression or p2-or-higher failure.",
        remediation_hint="Do not promote when safety regression is true or a p2-or-higher safety check failed.",
        repairability="agent_fixable",
    ),
    "INV_FLIP_THRESHOLD": ErrorCodeSpec(
        code="INV_FLIP_THRESHOLD",
        title="Promotion blocked by flip threshold",
        severity="error",
        description="A flip-count metric exceeds the threshold while the gate decision promotes the improvement.",
        remediation_hint="Do not promote until flip_counts[].count is less than or equal to its threshold.",
        repairability="agent_fixable",
        invariant_id="I8",
    ),
    "INV_ROLLBACK_EVIDENCE": ErrorCodeSpec(
        code="INV_ROLLBACK_EVIDENCE",
        title="Rollback evidence missing",
        severity="error",
        description="A rollback state or rollback gate decision lacks rollback evidence.",
        remediation_hint="Add rollback.evidence_ref pointing to evidence with type rollback_report.",
        repairability="external_evidence_required",
        invariant_id="I9",
    ),
    "ROLLBACK_EVIDENCE": ErrorCodeSpec(
        code="ROLLBACK_EVIDENCE",
        title="Rollback evidence missing",
        severity="error",
        description="Compatibility code for missing rollback evidence.",
        remediation_hint="Add rollback.evidence_ref pointing to evidence with type rollback_report.",
        repairability="external_evidence_required",
        invariant_id="I9",
    ),
    "HASH_CHAIN_BROKEN": ErrorCodeSpec(
        code="HASH_CHAIN_BROKEN",
        title="Evidence hash chain broken",
        severity="error",
        description="An evidence link references a missing evidence object, breaking evidence-chain closure.",
        remediation_hint="Restore the referenced evidence object or update the evidence refs to close the chain.",
        repairability="external_evidence_required",
        invariant_id="I4",
    ),
}


def get_error_code(code: str) -> ErrorCodeSpec:
    return ERROR_CODES.get(
        code,
        ErrorCodeSpec(
            code=code,
            title="Unknown validation error",
            severity="error",
            description="The validator emitted an unregistered error code.",
            remediation_hint="Inspect the validator issue and register a stable remediation hint for this code.",
            repairability="human_required",
        ),
    )


def registry_as_dict() -> dict[str, dict[str, str]]:
    return {code: spec.to_dict() for code, spec in ERROR_CODES.items()}
