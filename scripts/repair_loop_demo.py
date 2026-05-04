from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_SCHEMA = ROOT / "interfaces" / "asiep_validator_output.schema.json"
REPAIR_PLAN_SCHEMA = ROOT / "interfaces" / "asiep_repair_plan.schema.json"


def main() -> int:
    validator_schema = _load_json(VALIDATOR_SCHEMA)
    repair_plan_schema = _load_json(REPAIR_PLAN_SCHEMA)
    exit_code = 0

    for example in sorted((ROOT / "examples").glob("invalid_*.json")):
        validator_output = _run_json(
            [sys.executable, "-m", "asiep_validator", str(example), "--format", "json"],
            expect_success=False,
        )
        repair_plan = _run_json(
            [sys.executable, "-m", "asiep_repairer", str(example), "--format", "json"],
            expect_success=True,
        )

        validator_errors = sorted(Draft202012Validator(validator_schema).iter_errors(validator_output), key=str)
        repair_errors = sorted(Draft202012Validator(repair_plan_schema).iter_errors(repair_plan), key=str)
        if validator_errors or repair_errors:
            exit_code = 1
            print(f"FAIL {example.name}: schema validation failed")
            for error in validator_errors + repair_errors:
                print(f"  {error.message}")
            continue

        error_codes = [error["code"] for error in repair_plan["errors"]]
        external_count = sum(1 for action in repair_plan["repair_actions"] if action["requires_external_evidence"])
        print(
            f"input={example.name} "
            f"error_codes={error_codes} "
            f"repairable={repair_plan['repairable']} "
            f"repair_actions={len(repair_plan['repair_actions'])} "
            f"blocked_actions={len(repair_plan['blocked_actions'])} "
            f"requires_external_evidence={external_count}"
        )
    return exit_code


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _run_json(command: list[str], *, expect_success: bool) -> dict:
    env = dict(os.environ)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = "src" if not existing else f"src{os.pathsep}{existing}"
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    if expect_success and result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    if not expect_success and result.returncode == 0:
        raise RuntimeError(f"expected command to fail validation: {' '.join(command)}")
    return json.loads(result.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
