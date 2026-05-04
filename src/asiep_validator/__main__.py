from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .validator import validate_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an ASIEP v0.1 profile.")
    parser.add_argument("profile", type=Path, help="Path to an ASIEP JSON profile.")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format. Defaults to text for backward compatibility.",
    )
    args = parser.parse_args(argv)

    report = validate_file(args.profile)
    if args.format == "json":
        print(json.dumps(report.to_agent_dict(), indent=2, sort_keys=True))
        return 0 if report.valid else 1

    if report.valid:
        print("PASS")
        return 0

    print("FAIL " + ",".join(report.codes))
    for issue in report.issues:
        detail = f"{issue.code}: {issue.message}"
        if issue.path:
            detail += f" ({issue.path})"
        print(detail, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
