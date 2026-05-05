from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FINAL_FILES = [
    ROOT / "submission" / "escience2026" / "deadline_verification.json",
    ROOT / "submission" / "escience2026" / "repository_policy_decision.json",
    ROOT / "submission" / "escience2026" / "license_decision.json",
    ROOT / "submission" / "escience2026" / "sensitive_content_review.json",
    ROOT / "submission" / "escience2026" / "layout_review.json",
    ROOT / "submission" / "escience2026" / "author_final_approval.json",
]


def main() -> int:
    final_files_before = {str(path.relative_to(ROOT)) for path in FINAL_FILES if path.exists()}
    missing_flags = _run_json([sys.executable, "scripts/promote_recommended_gates.py"])
    missing_flags_check_passed = (
        missing_flags["returncode"] == 1
        and missing_flags["payload"].get("promoted") is False
        and "human_confirm_final_gates" in missing_flags["payload"].get("missing_required_flags", [])
    )

    dry_run = _run_json(
        [
            sys.executable,
            "scripts/promote_recommended_gates.py",
            "--human-confirm-final-gates",
            "--approved-by",
            "DRY RUN HUMAN AUTHOR",
            "--confirm-deadline",
            "--confirm-repository-policy",
            "--confirm-license",
            "--confirm-sensitive-scan",
            "--confirm-layout",
            "--confirm-ai-disclosure",
            "--confirm-final-pdf",
            "--dry-run",
            "--format",
            "json",
        ]
    )
    dry_run_success = (
        dry_run["returncode"] == 0
        and dry_run["payload"].get("dry_run") is True
        and dry_run["payload"].get("promoted") is False
        and bool(dry_run["payload"].get("would_create_files"))
    )

    final_files_after = {str(path.relative_to(ROOT)) for path in FINAL_FILES if path.exists()}
    dry_run_created_final_gate_files = final_files_after != final_files_before
    final_gate_files_present = bool(final_files_after)
    final_check = _run_json([sys.executable, "scripts/final_submission_check.py"])
    final_submission_check_valid = final_check["payload"].get("valid") is True
    final_submission_ready = _load_final_submission_ready()

    summary = {
        "missing_flags_check_passed": missing_flags_check_passed,
        "dry_run_success": dry_run_success,
        "dry_run_created_final_gate_files": dry_run_created_final_gate_files,
        "final_gate_files_present": final_gate_files_present,
        "final_submission_ready": final_submission_ready,
        "final_submission_check_valid": final_submission_check_valid,
        "would_create_files": dry_run["payload"].get("would_create_files", []),
        "final_submission_check_errors": final_check["payload"].get("errors", []),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if missing_flags_check_passed and dry_run_success and not dry_run_created_final_gate_files else 1


def _run_json(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {"raw_stdout": result.stdout, "raw_stderr": result.stderr}
    return {"returncode": result.returncode, "payload": payload}


def _load_final_submission_ready() -> bool:
    status_path = ROOT / "submission" / "escience2026" / "final_gate_status.json"
    with status_path.open(encoding="utf-8") as handle:
        return json.load(handle).get("final_submission_ready") is True


if __name__ == "__main__":
    raise SystemExit(main())
