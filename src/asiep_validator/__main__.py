from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .validator import validate_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an ASIEP v0.1 profile.")
    parser.add_argument("profile", type=Path, help="Path to an ASIEP JSON profile.")
    args = parser.parse_args(argv)

    report = validate_file(args.profile)
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
