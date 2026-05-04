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
    "BUNDLE_SCHEMA": ErrorCodeSpec(
        code="BUNDLE_SCHEMA",
        title="Evidence bundle schema validation failed",
        severity="error",
        description="The local evidence bundle manifest does not satisfy the ASIEP evidence bundle schema.",
        remediation_hint="Repair bundle.json so it conforms to interfaces/asiep_evidence_bundle.schema.json.",
        repairability="agent_fixable",
        invariant_id="I1",
    ),
    "BUNDLE_ARTIFACT_MISSING": ErrorCodeSpec(
        code="BUNDLE_ARTIFACT_MISSING",
        title="Bundle artifact file missing",
        severity="error",
        description="A bundle artifact declared by URI and path is missing from the local bundle.",
        remediation_hint="Provide the real artifact file at the declared bundle-relative path or correct the artifact declaration.",
        repairability="external_evidence_required",
        invariant_id="I4",
    ),
    "BUNDLE_DIGEST_MISMATCH": ErrorCodeSpec(
        code="BUNDLE_DIGEST_MISMATCH",
        title="Bundle artifact digest mismatch",
        severity="error",
        description="The artifact file exists, but its computed SHA-256 digest does not match the bundle declaration.",
        remediation_hint="Verify the evidence version; do not replace expected digest with actual digest unless an external review confirms the artifact is correct.",
        repairability="external_evidence_required",
        invariant_id="I10",
    ),
    "BUNDLE_MEDIA_TYPE_MISMATCH": ErrorCodeSpec(
        code="BUNDLE_MEDIA_TYPE_MISMATCH",
        title="Bundle artifact media type mismatch",
        severity="error",
        description="The artifact media type declaration is inconsistent with resolver expectations.",
        remediation_hint="Correct the media_type declaration or provide the artifact in the declared media type.",
        repairability="agent_fixable",
        invariant_id="I4",
    ),
    "BUNDLE_PATH_ESCAPE": ErrorCodeSpec(
        code="BUNDLE_PATH_ESCAPE",
        title="Bundle path escapes root",
        severity="error",
        description="A bundle-relative path attempts to resolve outside bundle_root.",
        remediation_hint="Reject this bundle path and require a safe path inside bundle_root.",
        repairability="human_required",
        invariant_id="I4",
    ),
    "BUNDLE_RECORD_MISSING": ErrorCodeSpec(
        code="BUNDLE_RECORD_MISSING",
        title="Evidence record missing",
        severity="error",
        description="The bundle evidence_record_path does not resolve to a local ASIEP evidence record.",
        remediation_hint="Provide the real ASIEP evidence record at evidence_record_path or correct the bundle manifest.",
        repairability="external_evidence_required",
        invariant_id="I1",
    ),
    "BUNDLE_REF_UNDECLARED": ErrorCodeSpec(
        code="BUNDLE_REF_UNDECLARED",
        title="Evidence URI not declared in bundle",
        severity="error",
        description="The ASIEP evidence record references a URI that is not declared in bundle artifacts.",
        remediation_hint="Declare the real artifact in bundle artifacts or correct the evidence URI.",
        repairability="agent_fixable",
        invariant_id="I4",
    ),
    "BUNDLE_REF_UNUSED": ErrorCodeSpec(
        code="BUNDLE_REF_UNUSED",
        title="Bundle artifact unused by evidence record",
        severity="warning",
        description="The bundle declares an artifact URI that is not referenced by the ASIEP evidence record.",
        remediation_hint="Remove the unused artifact declaration if it is not needed by the evidence record.",
        repairability="auto_fixable",
        invariant_id="I4",
    ),
    "BUNDLE_MANIFEST_HASH_MISMATCH": ErrorCodeSpec(
        code="BUNDLE_MANIFEST_HASH_MISMATCH",
        title="Bundle manifest hash mismatch",
        severity="error",
        description="The computed canonical bundle manifest hash does not match integrity.bundle_manifest_hash.",
        remediation_hint="Review bundle.json changes and update the manifest hash only after confirming the manifest is correct.",
        repairability="human_required",
        invariant_id="I10",
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
