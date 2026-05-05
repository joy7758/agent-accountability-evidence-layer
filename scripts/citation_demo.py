from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from asiep_citation_linter import lint_citations
from asiep_paper_linter import lint_paper


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "profiles" / "asiep" / "v0.1" / "profile.json"


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _assert_schema_valid(payload: dict, schema_path: Path) -> None:
    errors = sorted(Draft202012Validator(_load_json(schema_path)).iter_errors(payload), key=str)
    if errors:
        messages = "; ".join(error.message for error in errors)
        raise SystemExit(f"schema validation failed for {schema_path}: {messages}")


def main() -> int:
    paper_result = lint_paper(PROFILE_PATH)
    citation_result = lint_citations(PROFILE_PATH)
    source_registry = _load_json(ROOT / "references" / "source_registry.json")
    citation_map = _load_json(ROOT / "references" / "citation_claim_map.json")
    _assert_schema_valid(source_registry, ROOT / "interfaces" / "asiep_source_registry.schema.json")
    _assert_schema_valid(citation_map, ROOT / "interfaces" / "asiep_citation_claim_map.schema.json")

    bib_exists = (ROOT / "references" / "asiep_references.bib").exists()
    unsupported_claims = [item for item in citation_map["claim_citations"] if item["support_level"] == "unsupported"]
    required_without_keys = [item for item in citation_map["claim_citations"] if item["required_citation"] and not item["citation_keys"]]
    print(
        "citation_demo "
        f"sources={len(source_registry['sources'])} "
        f"verified={citation_result['summary']['verified_sources']} "
        f"unverified={citation_result['summary']['unverified_sources']} "
        f"citation_claims={len(citation_map['claim_citations'])} "
        f"unsupported_claims={len(unsupported_claims)} "
        f"citation_gaps={len(required_without_keys)} "
        f"paper_v0.2_exists={(ROOT / 'manuscript' / 'paper_v0.2.md').exists()} "
        f"bibtex_exists={bib_exists} "
        f"paper_linter_valid={paper_result['valid']} "
        f"citation_linter_valid={citation_result['valid']}"
    )
    return 0 if paper_result["valid"] and citation_result["valid"] and bib_exists else 1


if __name__ == "__main__":
    raise SystemExit(main())
