from __future__ import annotations

import argparse
import json
from pathlib import Path

from .linter import lint_submission


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint the ASIEP eScience M10 submission package.")
    parser.add_argument("--manifest", type=Path, required=True, help="Path to submission_manifest.json.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    result = lint_submission(args.manifest)
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        status = "PASS" if result["valid"] else "FAIL"
        print(
            f"{status} {result['submission_id']}: "
            f"human_rewrite_required={result['human_rewrite_required']} "
            f"final_submission_ready={result['final_submission_ready']} "
            f"errors={len(result['errors'])} warnings={len(result['warnings'])}"
        )
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
