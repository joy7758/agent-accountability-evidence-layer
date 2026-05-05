from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "submission" / "escience2026" / "sensitive_content_scan_report.json"
FINAL_GATE_STATUS_PATH = ROOT / "submission" / "escience2026" / "final_gate_status.json"
SCAN_ROOTS = [
    ROOT / "manuscript",
    ROOT / "submission" / "escience2026",
    ROOT / "references",
    ROOT / "reports",
    ROOT / "paper_assets",
    ROOT / "examples",
]
SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "generated_bundles",
    "generated_packages",
    "latex_scaffold",
}
SKIP_SUFFIXES = {
    ".aux",
    ".bbl",
    ".blg",
    ".fdb_latexmk",
    ".fls",
    ".log",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".zip",
    ".pyc",
}

PATTERNS = [
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "error"),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "error"),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"), "error"),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "error"),
    (
        "credential_assignment",
        re.compile(r"(?i)\b(api[_-]?key|secret|password|access[_-]?token|refresh[_-]?token|credential)\b\s*[:=]\s*[\"']?[A-Za-z0-9_./+=-]{16,}"),
        "error",
    ),
    ("raw_prompt_marker", re.compile(r"(?i)\b(raw[_ -]?prompt|prompt[_ -]?raw)\b"), "warning"),
    ("raw_user_input_marker", re.compile(r"(?i)\b(raw[_ -]?user[_ -]?input|user[_ -]?input[_ -]?raw)\b"), "warning"),
    ("raw_model_output_marker", re.compile(r"(?i)\b(raw[_ -]?model[_ -]?output|model[_ -]?output[_ -]?raw)\b"), "warning"),
    ("absolute_private_local_path", re.compile(r"/Users/zhangbin/[^\s)\\]\"'<>]+"), "warning"),
]


def main() -> int:
    findings: list[dict[str, Any]] = []
    scanned_paths: list[str] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in _iter_text_files(root):
            scanned_paths.append(str(path.relative_to(ROOT)))
            _scan_file(path, findings)

    false_positive_notes = [
        "This is a sentinel/pattern scan, not full DLP.",
        "Mentions of ASIEP's ref-only policy or sensitive-content rules may be intentional documentation.",
        "Local absolute paths in generated logs or metadata require human review but are not automatically removed.",
    ]
    requires_human_review = True
    report = {
        "scan_id": "asiep-escience2026-sensitive-content-scan-m12-l1",
        "scanned_paths": scanned_paths,
        "scan_completed": True,
        "findings": findings,
        "false_positive_notes": false_positive_notes,
        "requires_human_review": requires_human_review,
        "final_ready": False,
        "limitations": [
            "Pattern and sentinel scan only; not full data-loss prevention.",
            "Does not inspect binary PDFs or generated LaTeX auxiliary files.",
            "Does not verify access-control policy, retention policy, or legal compliance.",
            "Does not guarantee that all sensitive content is absent.",
        ],
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _update_final_gate_status(report)
    print(json.dumps(_summary(report), indent=2, sort_keys=True))
    return 0


def _iter_text_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.name == "sensitive_content_scan_report.json":
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if path.name.endswith(".draft.json") or path.suffix.lower() in {".md", ".json", ".bib", ".tex", ".txt", ".py", ".yml", ".yaml", ".diff"}:
            yield path


def _scan_file(path: Path, findings: list[dict[str, Any]]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return
    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule_id, pattern, severity in PATTERNS:
            for match in pattern.finditer(line):
                findings.append(
                    {
                        "path": str(path.relative_to(ROOT)),
                        "line": line_number,
                        "rule_id": rule_id,
                        "severity": severity,
                        "snippet": _redact(line.strip(), match.group(0)),
                        "review_needed": True,
                    }
                )


def _redact(line: str, match: str) -> str:
    if len(match) <= 16:
        return line[:240]
    redacted = match[:6] + "...REDACTED..." + match[-4:]
    return line.replace(match, redacted)[:240]


def _update_final_gate_status(report: dict[str, Any]) -> None:
    status = _load_json_if_exists(FINAL_GATE_STATUS_PATH)
    if not status:
        status = {
            "target_venue": "escience2026",
            "manuscript_title": "A FAIR Evidence Object Layer for Auditable Agent Self-Improvement",
            "final_submission_ready": False,
        }
    license_decision = _load_json_if_exists(ROOT / "submission" / "escience2026" / "license_decision.json")
    license_template_exists = (ROOT / "submission" / "escience2026" / "license_decision.template.json").exists()
    status["license_status"] = {
        "support_path": "submission/escience2026/license_decision.md",
        "template_path": "submission/escience2026/license_decision.template.json",
        "template_present": license_template_exists,
        "final_path": "submission/escience2026/license_decision.json",
        "final_file_present": bool(license_decision),
        "final_ready": bool(license_decision) and license_decision.get("final_ready") is True,
        "status": "undecided" if not license_decision else "final_ready" if license_decision.get("final_ready") is True else "not_final_ready",
    }
    status["sensitive_content_scan_status"] = {
        "report_path": "submission/escience2026/sensitive_content_scan_report.json",
        "scan_completed": report["scan_completed"],
        "findings_count": len(report["findings"]),
        "requires_human_review": report["requires_human_review"],
        "final_ready": report["final_ready"],
        "status": "scan_completed_requires_human_review",
    }
    status["final_submission_ready"] = False
    blocking_items = list(status.get("blocking_items", []))
    for item in [
        "author final approval not signed",
        "live EasyChair/CFP deadline not manually verified",
        "repository/anonymization policy not finalized",
        "license not finalized",
        "sensitive content scan requires human review",
        "final gate files not created",
    ]:
        if item not in blocking_items:
            blocking_items.append(item)
    if "sensitive content scan not completed" in blocking_items:
        blocking_items.remove("sensitive content scan not completed")
    status["blocking_items"] = blocking_items
    remaining = list(status.get("remaining_human_actions", []))
    for action in [
        "Finalize license decision and create submission/escience2026/license_decision.json.",
        "Review submission/escience2026/sensitive_content_scan_report.json and resolve or accept findings before final approval.",
    ]:
        if action not in remaining:
            remaining.append(action)
    status["remaining_human_actions"] = remaining
    FINAL_GATE_STATUS_PATH.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "scan_completed": report["scan_completed"],
        "scanned_paths_count": len(report["scanned_paths"]),
        "findings_count": len(report["findings"]),
        "requires_human_review": report["requires_human_review"],
        "final_ready": report["final_ready"],
        "report_path": str(REPORT_PATH.relative_to(ROOT)),
    }


if __name__ == "__main__":
    raise SystemExit(main())
