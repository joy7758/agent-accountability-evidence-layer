from __future__ import annotations

import argparse
import json
from pathlib import Path

from .packager import package_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Package a local ASIEP evidence bundle.")
    parser.add_argument("request", type=Path, help="Path to an ASIEP package request JSON file.")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format. Use json for agent-readable package results.",
    )
    args = parser.parse_args(argv)

    result = package_bundle(args.request)
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            f"{'PASS' if result['valid'] else 'FAIL'} "
            f"{result['package_id']} "
            f"errors={[error['code'] for error in result['errors']]}"
        )
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
