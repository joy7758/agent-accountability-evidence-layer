from __future__ import annotations

import argparse
import json
from pathlib import Path

from .resolver import resolve_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve a local ASIEP evidence bundle.")
    parser.add_argument("bundle", type=Path, help="Path to bundle.json.")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format. Use json for agent-readable resolution output.",
    )
    args = parser.parse_args(argv)

    result = resolve_bundle(args.bundle)
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            f"{'PASS' if result['valid'] else 'FAIL'} "
            f"{result['bundle_id']} "
            f"errors={[error['code'] for error in result['errors']]}"
        )
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
