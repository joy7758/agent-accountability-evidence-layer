from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from asiep_validator import validate_file


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "profiles" / "asiep" / "v0.1" / "repair_policy.json"


def generate_repair_plan(input_path: str | Path) -> dict[str, Any]:
    path = Path(input_path)
    report = validate_file(path)
    validator_output = report.to_agent_dict()
    policy = _load_policy()
    policy_map = {item["code"]: item for item in policy["error_code_repair_map"]}

    profile = _load_profile(path)
    repair_actions: list[dict[str, Any]] = []
    blocked_actions: list[dict[str, Any]] = []

    for error in validator_output["errors"]:
        mapped_policy = _policy_for_error(error["code"], policy_map)
        action = _repair_action_for_error(path, profile, error, mapped_policy, len(repair_actions) + 1)
        if action:
            repair_actions.append(action)

        blocked = _blocked_action_for_policy(error, mapped_policy, len(blocked_actions) + 1)
        if blocked:
            blocked_actions.append(blocked)

    return {
        "profile": "ASIEP",
        "profile_version": "0.1.0",
        "input_path": str(path),
        "valid_before": validator_output["valid"],
        "repairable": bool(repair_actions) if not validator_output["valid"] else False,
        "strategy": "evidence-preserving repair plan; generate patches and evidence requests without modifying input",
        "errors": validator_output["errors"],
        "repair_actions": repair_actions,
        "blocked_actions": blocked_actions,
        "revalidation_command": f"PYTHONPATH=src python -m asiep_validator {path} --format json",
        "safety_notes": list(policy["evidence_preservation_rules"]),
    }


def _load_policy() -> dict[str, Any]:
    with POLICY_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _load_profile(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _policy_for_error(code: str, policy_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    aliases = {
        "DIGEST_BASIC": "REF_DIGEST_FORMAT",
        "ROLLBACK_EVIDENCE": "INV_ROLLBACK_EVIDENCE",
        "SCHEMA": "SCHEMA_REQUIRED_FIELD",
    }
    return policy_map.get(code) or policy_map.get(aliases.get(code, ""), _fallback_policy(code))


def _fallback_policy(code: str) -> dict[str, Any]:
    return {
        "code": code,
        "repairability": "human_required",
        "allowed_actions": [],
        "forbidden_actions": ["apply unregistered repair action"],
        "default_strategy": "Escalate to a human or profile maintainer because no repair policy is registered.",
        "remediation_hint": "Register this error code in profiles/asiep/v0.1/repair_policy.json before automated repair planning.",
        "requires_external_evidence": False,
    }


def _repair_action_for_error(
    input_path: Path,
    profile: dict[str, Any],
    error: dict[str, Any],
    policy: dict[str, Any],
    action_index: int,
) -> dict[str, Any] | None:
    code = error["code"]
    invariant_id = error.get("invariant_id", "I1")
    repairability = policy["repairability"]
    json_patch: list[dict[str, Any]]
    evidence_requirements: list[str] = []
    requires_external_evidence = bool(policy.get("requires_external_evidence", False))
    risk_level = "medium"
    description = policy["default_strategy"]
    agent_instruction = policy["remediation_hint"]

    if code == "INV_SAFETY_REGRESSION":
        json_patch = [_reject_first_promote_patch(profile)]
        evidence_requirements = [
            "If promotion is still desired, provide a new safety evaluation and a real gate_report evidence object."
        ]
        risk_level = "high"
        agent_instruction = "Change the unsafe promote decision to reject; do not edit safety_checks[].regression."
    elif code == "INV_FLIP_THRESHOLD":
        json_patch = [_reject_first_promote_patch(profile)]
        evidence_requirements = [
            "If promotion is still desired, provide new evaluation evidence showing flip counts within threshold."
        ]
        risk_level = "high"
        agent_instruction = "Change the unsafe promote decision to reject; do not increase thresholds or lower counts without new evidence."
    elif code == "INV_MISSING_GATE_REPORT":
        json_patch = [{"op": "add", "path": error["json_pointer"], "value": "TODO:ev:real-gate-report"}]
        evidence_requirements = [
            "Provide a real gate_report evidence object and set gate_report_ref to that evidence id."
        ]
        risk_level = "high"
        agent_instruction = "Request a real gate report from the gatekeeper agent; do not forge approval."
    elif code in {"REF_UNRESOLVED", "HASH_CHAIN_BROKEN"}:
        missing_ref = _missing_evidence_ref(error["message"])
        json_patch = [
            {
                "op": "add",
                "path": "/evidence/-",
                "value": {
                    "id": missing_ref or "TODO:ev:real-evidence-id",
                    "type": "reference_digest",
                    "uri": "TODO:provide-real-evidence-uri",
                    "digest": {
                        "algorithm": "sha256",
                        "value": "TODO:real-sha256-digest"
                    }
                },
            }
        ]
        evidence_requirements = [
            "Provide the real evidence object, URI, and SHA-256 digest for the unresolved evidence reference."
        ]
        requires_external_evidence = True
        risk_level = "high"
        agent_instruction = "Restore the missing evidence or correct the reference; do not invent URI or digest values."
    elif code in {"REF_DIGEST_FORMAT", "DIGEST_BASIC"}:
        json_patch = [
            {
                "op": "replace",
                "path": error["json_pointer"],
                "value": {
                    "algorithm": "sha256",
                    "value": "TODO:real-sha256-digest"
                },
            }
        ]
        evidence_requirements = ["Compute or obtain the real SHA-256 digest for the referenced evidence."]
        requires_external_evidence = True
        risk_level = "high"
        agent_instruction = "Replace the digest with the real SHA-256 value; do not randomly generate a hash."
    elif code in {"INV_ROLLBACK_EVIDENCE", "ROLLBACK_EVIDENCE"}:
        json_patch = [
            {
                "op": "add" if error["json_pointer"] == "/rollback" else "replace",
                "path": error["json_pointer"],
                "value": {
                    "reason": "TODO:provide-rollback-reason",
                    "evidence_ref": "TODO:ev:real-rollback-report"
                }
                if error["json_pointer"] == "/rollback"
                else "TODO:ev:real-rollback-report",
            }
        ]
        evidence_requirements = ["Provide a real rollback_report evidence object and digest."]
        requires_external_evidence = True
        risk_level = "high"
        agent_instruction = "Attach real rollback evidence; do not forge rollback_report evidence."
    elif code == "STATE_TRANSITION":
        json_patch = []
        risk_level = "medium"
        agent_instruction = (
            "Rebuild lifecycle order according to docs/state_machine.md while preserving event ids, actors, "
            "timestamps, and evidence_refs."
        )
    elif code in {"SCHEMA_REQUIRED_FIELD", "SCHEMA_TYPE_MISMATCH", "SCHEMA_CONST_MISMATCH", "SCHEMA"}:
        json_patch = _patch_from_policy_template(error, policy)
        agent_instruction = policy["remediation_hint"]
    else:
        if repairability in {"human_required", "not_fixable"}:
            return None
        json_patch = _patch_from_policy_template(error, policy)

    return {
        "action_id": f"repair-{action_index:03d}",
        "error_code": code,
        "invariant_id": invariant_id,
        "repairability": repairability,
        "description": description,
        "json_patch": json_patch,
        "requires_external_evidence": requires_external_evidence,
        "evidence_requirements": evidence_requirements,
        "risk_level": risk_level,
        "agent_instruction": f"{agent_instruction} Input file is not modified by this repairer: {input_path}.",
    }


def _blocked_action_for_policy(error: dict[str, Any], policy: dict[str, Any], action_index: int) -> dict[str, Any] | None:
    forbidden = policy.get("forbidden_actions", [])
    if not forbidden:
        return None
    return {
        "action_id": f"blocked-{action_index:03d}",
        "error_code": error["code"],
        "invariant_id": error.get("invariant_id", "I1"),
        "reason": "Repair policy forbids evidence-forging or audit-bypassing changes for this error.",
        "forbidden_patch_patterns": forbidden,
        "agent_instruction": "Do not apply these forbidden changes. Use repair_actions only as evidence-preserving skeletons.",
    }


def _reject_first_promote_patch(profile: dict[str, Any]) -> dict[str, Any]:
    for index, gate in enumerate(profile.get("gates", [])):
        if gate.get("decision") == "promote":
            return {"op": "replace", "path": f"/gates/{index}/decision", "value": "reject"}
    return {"op": "replace", "path": "/gates/0/decision", "value": "reject"}


def _patch_from_policy_template(error: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, Any]]:
    patches = []
    for patch in policy.get("safe_patch_template", []):
        rendered = dict(patch)
        rendered["path"] = rendered["path"].replace("{json_pointer}", error["json_pointer"])
        patches.append(rendered)
    return patches


def _missing_evidence_ref(message: str) -> str | None:
    match = re.search(r"evidence reference ([^ ]+) is not defined", message)
    if not match:
        return None
    return match.group(1)
