from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
RESOLUTION_SCHEMA = ROOT / "interfaces" / "asiep_bundle_resolution.schema.json"


def main() -> int:
    schema = _load_json(RESOLUTION_SCHEMA)
    exit_code = 0
    for bundle_path in sorted((ROOT / "examples" / "bundles").glob("*/bundle.json")):
        result = _run_resolver(bundle_path)
        schema_errors = sorted(Draft202012Validator(schema).iter_errors(result), key=str)
        if schema_errors:
            exit_code = 1
            print(f"FAIL {bundle_path.parent.name}: resolver output schema failed")
            for error in schema_errors:
                print(f"  {error.message}")
            continue
        mismatch_count = sum(1 for item in result["digest_checks"] if not item["digest_match"])
        error_codes = [error["code"] for error in result["errors"]]
        print(
            f"bundle_id={result['bundle_id']} "
            f"valid={result['valid']} "
            f"resolved_refs={len(result['resolved_refs'])} "
            f"unresolved_refs={len(result['unresolved_refs'])} "
            f"digest_mismatch={mismatch_count} "
            f"error_codes={error_codes}"
        )
    return exit_code


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _run_resolver(bundle_path: Path) -> dict:
    env = dict(os.environ)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = "src" if not existing else f"src{os.pathsep}{existing}"
    result = subprocess.run(
        [sys.executable, "-m", "asiep_resolver", str(bundle_path), "--format", "json"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
