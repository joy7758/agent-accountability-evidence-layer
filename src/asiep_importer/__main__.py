from __future__ import annotations

import argparse
import json
from pathlib import Path

from .importer import import_trace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import a local trace fixture into an ASIEP evidence bundle.")
    parser.add_argument("request", type=Path, help="Path to an ASIEP import request JSON file.")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format. Use json for agent-readable import results.",
    )
    args = parser.parse_args(argv)

    result = import_trace(args.request)
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            f"{'PASS' if result['valid'] else 'FAIL'} "
            f"{result['import_id']} "
            f"errors={[error['code'] for error in result['errors']]}"
        )
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
