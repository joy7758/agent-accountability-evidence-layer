from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from asiep_validator.error_codes import get_error_code


ROOT = Path(__file__).resolve().parents[2]


def lint_citations(profile_path: str | Path) -> dict[str, Any]:
    profile = _load_json(_resolve_path(profile_path))
    policy = _load_json(ROOT / profile["reference_policy_path"])
    source_registry = _load_json(ROOT / profile["source_registry_path"])
    citation_map = _load_json(ROOT / profile["citation_claim_map_path"])
    bib_path = ROOT / profile["bibliography_path"]
    paper_v02_path = ROOT / profile["manuscript_v02_path"]

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    _extend_schema_errors(
        errors,
        source_registry,
        ROOT / profile["source_registry_schema_path"],
        "$.source_registry",
        "CITATION_SOURCE_REGISTRY_INVALID",
    )
    _extend_schema_errors(
        errors,
        citation_map,
        ROOT / profile["citation_claim_map_schema_path"],
        "$.citation_claim_map",
        "CITATION_CLAIM_MAP_INVALID",
    )

    sources = source_registry.get("sources", [])
    source_by_id = {source["source_id"]: source for source in sources}
    source_by_key = {source["citation_key"]: source for source in sources}
    _check_unique(errors, [source["source_id"] for source in sources], "CITATION_SOURCE_REGISTRY_INVALID", "$.sources.source_id", "/sources")
    _check_unique(errors, [source["citation_key"] for source in sources], "CITATION_SOURCE_REGISTRY_INVALID", "$.sources.citation_key", "/sources")

    bib_keys = _bibtex_keys(bib_path)
    if not bib_path.exists():
        errors.append(_error("CITATION_BIBTEX_MISSING", "references/asiep_references.bib is missing.", "$.bibliography_path", "/bibliography_path"))

    for index, item in enumerate(citation_map.get("claim_citations", [])):
        base_path = f"$.claim_citations[{index}]"
        base_pointer = f"/claim_citations/{index}"
        if item["required_citation"] and not item["citation_keys"]:
            errors.append(_error("CITATION_EXTERNAL_CLAIM_WITHOUT_SOURCE", f"{item['claim_id']} requires citation but has no citation_keys.", f"{base_path}.citation_keys", f"{base_pointer}/citation_keys"))
        if item["support_level"] == "unsupported" or item["citation_status"] == "unsupported":
            errors.append(_error("CITATION_UNSUPPORTED_CLAIM", f"{item['claim_id']} is marked unsupported.", base_path, base_pointer))
        for source_index, source_id in enumerate(item["source_ids"]):
            source = source_by_id.get(source_id)
            if source is None:
                errors.append(_error("CITATION_SOURCE_MISSING", f"{item['claim_id']} references missing source_id {source_id}.", f"{base_path}.source_ids[{source_index}]", f"{base_pointer}/source_ids/{source_index}"))
                continue
            if source["verification_status"] == "unverified" and item["citation_status"] == "ready":
                errors.append(_error("CITATION_UNVERIFIED_SOURCE_USED_AS_VERIFIED", f"{item['claim_id']} uses unverified source {source_id} as ready.", f"{base_path}.source_ids[{source_index}]", f"{base_pointer}/source_ids/{source_index}"))
            if source["authority_level"] == "secondary" and any(candidate["citation_key"] in item["citation_keys"] for candidate in sources if candidate["authority_level"] in {"primary", "canonical"} and candidate["source_type"] == source["source_type"]):
                warnings.append(_warning("CITATION_SECONDARY_USED_WHEN_PRIMARY_AVAILABLE", f"{item['claim_id']} includes secondary source {source_id} while a primary/canonical source of the same type is also cited.", f"{base_path}.source_ids[{source_index}]", f"{base_pointer}/source_ids/{source_index}"))
        for key_index, key in enumerate(item["citation_keys"]):
            if key not in source_by_key:
                errors.append(_error("CITATION_SOURCE_MISSING", f"{item['claim_id']} references missing citation_key {key}.", f"{base_path}.citation_keys[{key_index}]", f"{base_pointer}/citation_keys/{key_index}"))
            if key not in bib_keys:
                errors.append(_error("CITATION_BIBTEX_MISSING", f"BibTeX entry missing for {key}.", f"{base_path}.citation_keys[{key_index}]", f"{base_pointer}/citation_keys/{key_index}"))
        if _is_research_or_related_work_claim(item) and not _has_primary_research_source(item, source_by_id):
            errors.append(_error("CITATION_FORBIDDEN_PRACTICE", f"{item['claim_id']} makes a research or related-work claim without a primary paper or preprint source.", base_path, base_pointer))
        if _is_standard_status_claim(item) and not _has_official_source(item, source_by_id):
            errors.append(_error("CITATION_FORBIDDEN_PRACTICE", f"{item['claim_id']} makes a standard/status claim without official or canonical source.", base_path, base_pointer))

    if paper_v02_path.exists():
        text = paper_v02_path.read_text(encoding="utf-8")
        lower_text = text.lower()
        if "citation_required" in lower_text:
            errors.append(_error("CITATION_REQUIRED_MARKER_REMAINS", "paper_v0.2.md still contains citation_required.", "$.paper_v0.2", "/paper_v0.2"))
        for phrase in policy.get("forbidden_overclaim_phrases", []):
            if phrase.lower() in lower_text:
                errors.append(_error("CITATION_FORBIDDEN_PRACTICE", f"Forbidden overclaim phrase remains in paper_v0.2.md: {phrase}.", "$.paper_v0.2", "/paper_v0.2"))
        for citation_key in citation_map_keys(citation_map):
            if f"@{citation_key}" not in text:
                warnings.append(_warning("CITATION_SOURCE_MISSING", f"paper_v0.2.md does not visibly cite @{citation_key}.", "$.paper_v0.2", "/paper_v0.2"))
    else:
        errors.append(_error("CITATION_SOURCE_MISSING", "manuscript/paper_v0.2.md is missing.", "$.manuscript_v02_path", "/manuscript_v02_path"))

    unverified_sources = [source for source in sources if source["verification_status"] == "unverified"]
    unsupported_claims = [item for item in citation_map.get("claim_citations", []) if item["support_level"] == "unsupported"]
    summary = {
        "verified_sources": sum(1 for source in sources if source["verification_status"] == "verified"),
        "partially_verified_sources": sum(1 for source in sources if source["verification_status"] == "partially_verified"),
        "unverified_sources": len(unverified_sources),
        "unsupported_claims": len(unsupported_claims),
        "bibtex_entries": len(bib_keys),
    }
    return {
        "profile": profile["profile_name"],
        "profile_version": profile["profile_version"],
        "valid": not errors,
        "paper_id": citation_map.get("paper_id", "unknown"),
        "sources_checked": len(sources),
        "citations_checked": len(citation_map.get("claim_citations", [])),
        "claims_checked": len(citation_map.get("claim_citations", [])),
        "errors": errors,
        "warnings": warnings,
        "summary": summary,
    }


def citation_map_keys(citation_map: dict[str, Any]) -> set[str]:
    return {key for item in citation_map.get("claim_citations", []) for key in item.get("citation_keys", [])}


def _is_standard_status_claim(item: dict[str, Any]) -> bool:
    text = f"{item['claim_text']} {item['notes']}".lower()
    patterns = (
        r"\bstandard\b",
        r"\bcertification\b",
        r"\bdevelopment\b",
        r"\bregulation\b",
        r"\bfdo\b",
        r"\bro-crate\b",
        r"\bprov\b",
        r"\bprov-o\b",
        r"\bopentelemetry\b",
        r"\bnist\b",
        r"\beu ai act\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def _has_official_source(item: dict[str, Any], source_by_id: dict[str, dict[str, Any]]) -> bool:
    return any(
        source_by_id.get(source_id, {}).get("source_type") in {"official_standard", "official_documentation", "regulation", "security_guidance", "product_documentation"}
        and source_by_id.get(source_id, {}).get("authority_level") in {"primary", "canonical"}
        for source_id in item["source_ids"]
    )


def _is_research_or_related_work_claim(item: dict[str, Any]) -> bool:
    text = f"{item['claim_text']} {item['notes']}".lower()
    return any(token in text for token in ("related work", "agentdevel", "self-refine", "reflexion", "voyager", "self-improvement method"))


def _has_primary_research_source(item: dict[str, Any], source_by_id: dict[str, dict[str, Any]]) -> bool:
    return any(
        source_by_id.get(source_id, {}).get("source_type") in {"academic_paper", "preprint"}
        and source_by_id.get(source_id, {}).get("authority_level") == "primary"
        for source_id in item["source_ids"]
    )


def _bibtex_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return set(re.findall(r"@\w+\s*\{\s*([^,\s]+)", path.read_text(encoding="utf-8")))


def _check_unique(errors: list[dict[str, Any]], values: list[str], code: str, json_path: str, json_pointer: str) -> None:
    seen: set[str] = set()
    duplicates = sorted({value for value in values if value in seen or seen.add(value)})
    if duplicates:
        errors.append(_error(code, f"Duplicate values: {', '.join(duplicates)}.", json_path, json_pointer))


def _extend_schema_errors(errors: list[dict[str, Any]], payload: dict[str, Any], schema_path: Path, json_path: str, code: str) -> None:
    schema = _load_json(schema_path)
    schema_errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=str)
    for schema_error in schema_errors:
        pointer = "/" + "/".join(str(part) for part in schema_error.absolute_path)
        errors.append(_error(code, schema_error.message, json_path, pointer if pointer != "/" else ""))


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


def _warning(code: str, message: str, json_path: str, json_pointer: str) -> dict[str, Any]:
    payload = _error(code, message, json_path, json_pointer)
    payload["severity"] = "warning"
    return payload


def _resolve_path(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)
