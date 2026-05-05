from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from asiep_validator.error_codes import get_error_code


ROOT = Path(__file__).resolve().parents[2]


def lint_paper(profile_path: str | Path) -> dict[str, Any]:
    profile_file = _resolve_path(profile_path)
    profile = _load_json(profile_file)
    policy = _load_json(ROOT / profile["paper_policy_path"])
    claim_registry_path = ROOT / policy["claim_registry_path"]
    evidence_map_path = ROOT / policy["evidence_map_path"]
    paper_path = ROOT / policy["paper_draft_path"]

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    claims_registry = _load_json(claim_registry_path)
    evidence_map = _load_json(evidence_map_path)
    _extend_schema_errors(errors, claims_registry, ROOT / profile["paper_claim_registry_schema_path"], "$.claims_registry")
    _extend_schema_errors(errors, evidence_map, ROOT / profile["paper_evidence_map_schema_path"], "$.evidence_map")

    if not errors:
        _check_claims(errors, claims_registry, evidence_map)
        _check_evidence_map(errors, claims_registry, evidence_map)
        _check_paper_text(errors, policy, paper_path)
        _check_required_assets(errors, policy, evidence_map)

    claims = claims_registry.get("claims", [])
    evidence_refs_checked = _count_refs(claims, ("evidence_refs", "artifact_refs", "related_work_refs"))
    claims_with_evidence = sum(1 for claim in claims if claim.get("claim_type") == "limitation_claim" or claim.get("evidence_refs") or claim.get("artifact_refs"))
    summary = {
        "claims_with_evidence": claims_with_evidence,
        "sections": len(evidence_map.get("sections", [])),
        "tables": len(evidence_map.get("tables", [])),
        "figures": len(evidence_map.get("figures", [])),
        "forbidden_phrase_count": len(policy.get("forbidden_phrases", [])),
    }

    return {
        "profile": profile["profile_name"],
        "profile_version": profile["profile_version"],
        "valid": not errors,
        "paper_id": claims_registry.get("paper_id", "unknown"),
        "claims_checked": len(claims),
        "evidence_refs_checked": evidence_refs_checked,
        "errors": errors,
        "warnings": warnings,
        "summary": summary,
    }


def _check_claims(errors: list[dict[str, Any]], claims_registry: dict[str, Any], evidence_map: dict[str, Any]) -> None:
    mapped_claims = {item["claim_id"] for item in evidence_map.get("claims", [])}
    for index, claim in enumerate(claims_registry.get("claims", [])):
        claim_path = f"$.claims[{index}]"
        claim_pointer = f"/claims/{index}"
        evidence_refs = claim.get("evidence_refs", [])
        artifact_refs = claim.get("artifact_refs", [])
        if claim.get("claim_type") != "limitation_claim" and not evidence_refs and not artifact_refs:
            errors.append(_error("PAPER_CLAIM_WITHOUT_EVIDENCE", f"{claim['claim_id']} has no repository evidence.", f"{claim_path}.evidence_refs", f"{claim_pointer}/evidence_refs"))
        if claim.get("claim_type") == "evaluation_claim" and not claim.get("metric_refs"):
            errors.append(_error("PAPER_EVALUATION_CLAIM_WITHOUT_METRIC", f"{claim['claim_id']} is an evaluation claim without metric_refs.", f"{claim_path}.metric_refs", f"{claim_pointer}/metric_refs"))
        if claim.get("claim_strength") == "strong" and len(evidence_refs) < 2:
            errors.append(_error("PAPER_STRONG_CLAIM_UNDERSUPPORTED", f"{claim['claim_id']} is strong but has fewer than two evidence_refs.", f"{claim_path}.evidence_refs", f"{claim_pointer}/evidence_refs"))
        if claim["claim_id"] not in mapped_claims:
            errors.append(_error("PAPER_ORPHAN_CLAIM", f"{claim['claim_id']} is not referenced by the evidence map.", claim_path, claim_pointer))
        for key in ("evidence_refs", "artifact_refs", "related_work_refs"):
            for ref_index, ref in enumerate(claim.get(key, [])):
                _check_repo_ref(errors, ref, f"{claim_path}.{key}[{ref_index}]", f"{claim_pointer}/{key}/{ref_index}")


def _check_evidence_map(errors: list[dict[str, Any]], claims_registry: dict[str, Any], evidence_map: dict[str, Any]) -> None:
    claim_ids = {claim["claim_id"] for claim in claims_registry.get("claims", [])}
    section_ids = {section["section_id"] for section in evidence_map.get("sections", [])}
    for group_name in ("sections", "tables", "figures"):
        for index, item in enumerate(evidence_map.get(group_name, [])):
            base_path = f"$.{group_name}[{index}]"
            base_pointer = f"/{group_name}/{index}"
            for key in ("source_files", "required_artifacts"):
                for ref_index, ref in enumerate(item.get(key, [])):
                    _check_repo_ref(errors, ref, f"{base_path}.{key}[{ref_index}]", f"{base_pointer}/{key}/{ref_index}")
            if "output_path" in item:
                _check_repo_ref(errors, item["output_path"], f"{base_path}.output_path", f"{base_pointer}/output_path", asset_code="PAPER_ASSET_MISSING")
            for claim_index, claim_id in enumerate(item.get("claim_ids", [])):
                if claim_id not in claim_ids:
                    errors.append(_error("PAPER_ORPHAN_CLAIM", f"{claim_id} is referenced by evidence_map but missing from claims_registry.", f"{base_path}.claim_ids[{claim_index}]", f"{base_pointer}/claim_ids/{claim_index}"))
    for index, item in enumerate(evidence_map.get("claims", [])):
        if item["claim_id"] not in claim_ids:
            errors.append(_error("PAPER_ORPHAN_CLAIM", f"{item['claim_id']} is listed in evidence_map claims but missing from claims_registry.", f"$.claims[{index}].claim_id", f"/claims/{index}/claim_id"))
        for section_id in item.get("section_ids", []):
            if section_id not in section_ids:
                errors.append(_error("PAPER_MISSING_SECTION", f"{item['claim_id']} references missing section {section_id}.", f"$.claims[{index}].section_ids", f"/claims/{index}/section_ids"))
        for ref_index, ref in enumerate(item.get("evidence_refs", [])):
            _check_repo_ref(errors, ref, f"$.claims[{index}].evidence_refs[{ref_index}]", f"/claims/{index}/evidence_refs/{ref_index}")


def _check_paper_text(errors: list[dict[str, Any]], policy: dict[str, Any], paper_path: Path) -> None:
    if not paper_path.exists():
        errors.append(_error("PAPER_ASSET_MISSING", "paper_v0.1.md is missing.", "$.paper_draft_path", "/paper_draft_path"))
        return
    text = paper_path.read_text(encoding="utf-8")
    headings = _paper_headings(text)
    for title in policy["required_sections"]:
        if title == "Title":
            if not any(line.startswith("# ") for line in text.splitlines()):
                errors.append(_error("PAPER_MISSING_SECTION", "Paper title heading is missing.", "$.paper", "/paper"))
        elif title.lower() not in headings:
            errors.append(_error("PAPER_MISSING_SECTION", f"Paper section missing: {title}.", "$.paper", "/paper"))
    lower_text = text.lower()
    for phrase in policy.get("forbidden_phrases", []):
        if phrase.lower() in lower_text:
            errors.append(_error("PAPER_FORBIDDEN_CLAIM", f"Forbidden high-risk phrase appears in paper_v0.1.md: {phrase}.", "$.paper", "/paper"))


def _check_required_assets(errors: list[dict[str, Any]], policy: dict[str, Any], evidence_map: dict[str, Any]) -> None:
    mapped_tables = {table["output_path"] for table in evidence_map.get("tables", [])}
    mapped_figures = {figure["output_path"] for figure in evidence_map.get("figures", [])}
    for path in policy["required_paper_assets"].get("tables", []):
        if path not in mapped_tables:
            errors.append(_error("PAPER_MISSING_TABLE", f"Required table is not referenced by evidence_map: {path}.", "$.required_paper_assets.tables", "/required_paper_assets/tables"))
        _check_repo_ref(errors, path, "$.required_paper_assets.tables", "/required_paper_assets/tables", asset_code="PAPER_MISSING_TABLE")
    for path in policy["required_paper_assets"].get("figures", []):
        if path not in mapped_figures:
            errors.append(_error("PAPER_MISSING_FIGURE", f"Required figure is not referenced by evidence_map: {path}.", "$.required_paper_assets.figures", "/required_paper_assets/figures"))
        _check_repo_ref(errors, path, "$.required_paper_assets.figures", "/required_paper_assets/figures", asset_code="PAPER_MISSING_FIGURE")
    for path in policy["required_paper_assets"].get("manuscript", []):
        _check_repo_ref(errors, path, "$.required_paper_assets.manuscript", "/required_paper_assets/manuscript", asset_code="PAPER_ASSET_MISSING")


def _check_repo_ref(errors: list[dict[str, Any]], ref: str, json_path: str, json_pointer: str, asset_code: str = "PAPER_EVIDENCE_REF_MISSING") -> None:
    if "://" in ref:
        errors.append(_error(asset_code, f"External URL is not allowed as sole paper evidence: {ref}.", json_path, json_pointer))
        return
    if not (ROOT / ref).exists():
        errors.append(_error(asset_code, f"Referenced paper evidence is missing: {ref}.", json_path, json_pointer))


def _extend_schema_errors(errors: list[dict[str, Any]], payload: dict[str, Any], schema_path: Path, json_path: str) -> None:
    schema = _load_json(schema_path)
    schema_errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=str)
    for schema_error in schema_errors:
        pointer = "/" + "/".join(str(part) for part in schema_error.absolute_path)
        errors.append(_error("PAPER_LINTER_FAILED", schema_error.message, json_path, pointer if pointer != "/" else ""))


def _paper_headings(text: str) -> set[str]:
    headings = set()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            headings.add(title.lower())
    return headings


def _count_refs(claims: list[dict[str, Any]], keys: tuple[str, ...]) -> int:
    return sum(len(claim.get(key, [])) for claim in claims for key in keys)


def _error(code: str, message: str, json_path: str, json_pointer: str) -> dict[str, Any]:
    spec = get_error_code(code)
    return {
        "code": code,
        "severity": spec.severity,
        "message": message,
        "json_path": json_path,
        "json_pointer": json_pointer,
        "remediation_hint": spec.remediation_hint,
        "repairability": spec.repairability,
    }


def _resolve_path(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)
