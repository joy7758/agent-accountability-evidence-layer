from __future__ import annotations

import argparse
import json
from pathlib import Path

from .linter import lint_citations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint ASIEP paper citations against source registry.")
    parser.add_argument(
        "--profile",
        type=Path,
        default=Path("profiles/asiep/v0.1/profile.json"),
        help="Path to the ASIEP profile manifest.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format. Use json for agent-readable citation lint reports.",
    )
    args = parser.parse_args(argv)

    result = lint_citations(args.profile)
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        status = "PASS" if result["valid"] else "FAIL"
        print(f"{status} {result['paper_id']}: sources={result['sources_checked']} citations={result['citations_checked']} errors={len(result['errors'])}")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
