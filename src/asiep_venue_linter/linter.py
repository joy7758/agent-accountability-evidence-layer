from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from asiep_validator.error_codes import get_error_code


ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "profiles" / "asiep" / "v0.1" / "profile.json"


def lint_venue(venue_path: str | Path, paper_path: str | Path) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    profile = _load_json(PROFILE_PATH)
    venue_file = _resolve_path(venue_path)
    paper_file = _resolve_path(paper_path)

    venue_policy = _load_json(venue_file)
    _extend_schema_errors(errors, venue_policy, ROOT / profile["venue_policy_schema_path"], "VENUE_POLICY_INVALID")

    if not paper_file.exists():
        errors.append(_issue("VENUE_PAPER_MISSING", f"Paper file not found: {paper_file}."))
        text = ""
    else:
        text = paper_file.read_text(encoding="utf-8")

    claims_registry = _load_json(ROOT / "manuscript" / "claims_registry.json")
    evidence_map = _load_json(ROOT / "manuscript" / "evidence_map.json")
    citation_map = _load_json(ROOT / "references" / "citation_claim_map.json")
    source_registry = _load_json(ROOT / "references" / "source_registry.json")

    section_checks = _check_sections(errors, venue_policy, text)
    limitation_checks = _check_positioning(errors, venue_policy, text)
    ai_checks = _check_ai_policy(errors, warnings, venue_policy, text)
    claim_checks, evidence_checks = _check_claim_evidence(errors, claims_registry, evidence_map)
    citation_checks = _check_citations(errors, citation_map, source_registry)
    _check_forbidden_claims(errors, venue_policy, text)
    page_budget = _estimate_page_budget(text, venue_policy)
    if page_budget["likely_over_budget"]:
        warnings.append(_issue("VENUE_PAGE_BUDGET_RISK", "Rough page estimate exceeds the venue page limit.", severity="warning"))

    recommended_human_actions = _recommended_actions(venue_policy, errors, warnings)
    readiness_score = max(0, 100 - (20 * len(errors)) - (5 * len(warnings)))
    return {
        "venue_id": venue_policy.get("venue_id", "unknown"),
        "paper_id": paper_file.stem,
        "paper_version": _paper_version(paper_file),
        "valid": not errors,
        "readiness_score": readiness_score,
        "section_checks": section_checks,
        "claim_checks": claim_checks,
        "citation_checks": citation_checks,
        "evidence_checks": evidence_checks,
        "limitation_checks": limitation_checks,
        "ai_use_policy_checks": ai_checks,
        "page_budget_estimate": page_budget,
        "errors": errors,
        "warnings": warnings,
        "recommended_human_actions": recommended_human_actions,
    }


def _check_sections(errors: list[dict[str, Any]], policy: dict[str, Any], text: str) -> list[dict[str, Any]]:
    headings = _headings(text)
    checks = []
    has_title = any(line.startswith("# ") for line in text.splitlines())
    for section in policy.get("required_sections", []):
        if section == "Title":
            passed = has_title
        else:
            passed = section.lower() in headings
        checks.append({"check_id": f"section:{section}", "passed": passed, "message": "present" if passed else "missing"})
        if not passed:
            errors.append(_issue("VENUE_REQUIRED_SECTION_MISSING", f"Required section missing: {section}."))
    return checks


def _check_positioning(errors: list[dict[str, Any]], policy: dict[str, Any], text: str) -> list[dict[str, Any]]:
    lower_text = text.lower()
    checks = []
    for phrase in policy.get("required_positioning", []):
        passed = phrase.lower() in lower_text
        checks.append({"check_id": f"positioning:{phrase}", "passed": passed, "message": "present" if passed else "missing"})
        if not passed and phrase.lower() in {"local fixture", "minimal implementation", "not external certification"}:
            errors.append(_issue("VENUE_LIMITATION_MISSING", f"Required limitation or positioning phrase missing: {phrase}."))
    return checks


def _check_ai_policy(errors: list[dict[str, Any]], warnings: list[dict[str, Any]], policy: dict[str, Any], text: str) -> list[dict[str, Any]]:
    lower_text = text.lower()
    checks = []
    for phrase in policy.get("required_disclosures", []):
        passed = phrase.lower() in lower_text
        checks.append({"check_id": f"disclosure:{phrase}", "passed": passed, "message": "present" if passed else "missing"})
        if not passed and policy.get("ai_use_policy", {}).get("disclosure_required", False):
            errors.append(_issue("VENUE_AI_USE_DISCLOSURE_MISSING", f"Required AI-use disclosure phrase missing: {phrase}."))
    if policy.get("ai_use_policy", {}).get("human_final_authoring_required", False):
        checks.append({"check_id": "human_final_authoring_required", "passed": True, "message": "human final authoring is required by policy"})
        warnings.append(_issue("VENUE_AI_POLICY_RISK", "Human authors must verify venue policy and rewrite final prose.", severity="warning"))
    if not policy.get("ai_use_policy", {}).get("ai_text_allowed", True):
        checks.append({"check_id": "ai_text_not_allowed_for_direct_submission", "passed": True, "message": "brief-only artifact must not be submitted as final text"})
        warnings.append(_issue("VENUE_AI_POLICY_RISK", "Venue policy says AI-generated text is not allowed for direct submission; use this as a planning brief only.", severity="warning"))
    return checks


def _check_claim_evidence(errors: list[dict[str, Any]], claims_registry: dict[str, Any], evidence_map: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    mapped_claims = {item["claim_id"] for item in evidence_map.get("claims", [])}
    claim_checks = []
    evidence_checks = []
    for claim in claims_registry.get("claims", []):
        has_evidence = claim.get("claim_type") == "limitation_claim" or bool(claim.get("evidence_refs") or claim.get("artifact_refs"))
        mapped = claim["claim_id"] in mapped_claims
        claim_checks.append({"check_id": f"claim:{claim['claim_id']}", "passed": has_evidence and mapped, "message": "evidence mapped" if has_evidence and mapped else "evidence or map missing"})
        if not has_evidence or not mapped:
            errors.append(_issue("VENUE_EVIDENCE_GAP", f"{claim['claim_id']} lacks repository evidence or evidence-map coverage."))
        for key in ("evidence_refs", "artifact_refs"):
            for ref in claim.get(key, []):
                exists = "://" not in ref and (ROOT / ref).exists()
                evidence_checks.append({"check_id": f"evidence:{claim['claim_id']}:{ref}", "passed": exists, "message": "exists" if exists else "missing"})
                if not exists:
                    errors.append(_issue("VENUE_EVIDENCE_GAP", f"Missing repository evidence ref: {ref}."))
    return claim_checks, evidence_checks


def _check_citations(errors: list[dict[str, Any]], citation_map: dict[str, Any], source_registry: dict[str, Any]) -> list[dict[str, Any]]:
    source_ids = {source["source_id"] for source in source_registry.get("sources", [])}
    citation_keys = {source["citation_key"] for source in source_registry.get("sources", [])}
    checks = []
    for item in citation_map.get("claim_citations", []):
        if item.get("required_citation"):
            passed = bool(item.get("citation_keys")) and bool(item.get("source_ids"))
            passed = passed and set(item["source_ids"]) <= source_ids and set(item["citation_keys"]) <= citation_keys
        else:
            passed = True
        checks.append({"check_id": f"citation:{item['claim_id']}", "passed": passed, "message": "ready" if passed else "citation gap"})
        if not passed:
            errors.append(_issue("VENUE_CITATION_GAP", f"{item['claim_id']} has an unresolved citation gap."))
    return checks


def _check_forbidden_claims(errors: list[dict[str, Any]], policy: dict[str, Any], text: str) -> None:
    lower_text = text.lower()
    for phrase in policy.get("forbidden_claims", []):
        if phrase.lower() in lower_text:
            errors.append(_issue("VENUE_FORBIDDEN_CLAIM", f"Forbidden venue phrase appears: {phrase}."))


def _estimate_page_budget(text: str, policy: dict[str, Any]) -> dict[str, Any]:
    words = re.findall(r"[A-Za-z0-9_:@./-]+", text)
    table_count = sum(1 for line in text.splitlines() if line.strip().startswith("|"))
    figure_count = text.count("```mermaid") + len(re.findall(r"!\[[^\]]*\]\(", text))
    estimated_pages = len(words) / 620 + (table_count / 25) + (figure_count * 0.25)
    return {
        "word_count": len(words),
        "table_count": table_count,
        "figure_count": figure_count,
        "estimated_pages": round(estimated_pages, 2),
        "page_limit": policy["page_limit"],
        "likely_over_budget": math.ceil(estimated_pages) > policy["page_limit"],
        "method": "word_count/620 + table_rows/25 + 0.25 pages per markdown figure marker",
    }


def _recommended_actions(policy: dict[str, Any], errors: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> list[str]:
    actions = [
        "Human authors must verify the current venue CFP, deadline, template, and AI-use policy before submission.",
        "Rewrite final prose manually; treat M9 markdown as a structured draft and checklist.",
        "Keep local fixture, minimal implementation, and no external certification limitations visible.",
    ]
    if policy["venue_id"] == "aies2026":
        actions.append("Do not submit the AIES brief as final text; add sociotechnical analysis and human-authored prose.")
    if errors:
        actions.append("Resolve venue linter errors before using the draft for venue planning.")
    if warnings:
        actions.append("Review venue linter warnings, especially AI-use and page-budget risks.")
    return actions


def _paper_version(path: Path) -> str:
    if "v0.4" in path.name:
        return "0.4.0"
    if "v0.3" in path.name:
        return "0.3.0"
    if "v0.2" in path.name:
        return "0.2.0"
    return "draft"


def _headings(text: str) -> set[str]:
    return {line.lstrip("#").strip().lower() for line in text.splitlines() if line.startswith("#")}


def _extend_schema_errors(errors: list[dict[str, Any]], payload: dict[str, Any], schema_path: Path, code: str) -> None:
    schema_errors = sorted(Draft202012Validator(_load_json(schema_path)).iter_errors(payload), key=str)
    for schema_error in schema_errors:
        errors.append(_issue(code, schema_error.message))


def _issue(code: str, message: str, severity: str | None = None) -> dict[str, Any]:
    spec = get_error_code(code)
    return {
        "code": code,
        "severity": severity or spec.severity,
        "message": message,
        "remediation_hint": spec.remediation_hint,
        "repairability": spec.repairability,
    }


def _resolve_path(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)
