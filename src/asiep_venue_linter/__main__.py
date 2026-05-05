from __future__ import annotations

import argparse
import json
from pathlib import Path

from .linter import lint_venue


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint an ASIEP venue-targeted paper draft.")
    parser.add_argument("--venue", type=Path, required=True, help="Path to venue_policy.json.")
    parser.add_argument("--paper", type=Path, required=True, help="Path to the venue-targeted paper or brief.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    result = lint_venue(args.venue, args.paper)
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        status = "PASS" if result["valid"] else "FAIL"
        print(
            f"{status} {result['venue_id']} {result['paper_id']}: "
            f"score={result['readiness_score']} errors={len(result['errors'])} warnings={len(result['warnings'])}"
        )
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
