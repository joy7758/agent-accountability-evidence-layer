from __future__ import annotations

import argparse
import json
from pathlib import Path

from .repairer import generate_repair_plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate an ASIEP repair plan.")
    parser.add_argument("profile", type=Path, help="Path to an ASIEP JSON profile.")
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Output format. JSON is the agent-native default.",
    )
    parser.add_argument("--output", type=Path, help="Optional path to write the JSON repair plan.")
    args = parser.parse_args(argv)

    plan = generate_repair_plan(args.profile)
    if args.output:
        args.output.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.format == "json":
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        print(
            f"repairable={plan['repairable']} "
            f"errors={len(plan['errors'])} "
            f"repair_actions={len(plan['repair_actions'])} "
            f"blocked_actions={len(plan['blocked_actions'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
