from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from asiep_citation_linter import lint_citations
from asiep_paper_linter import lint_paper
from asiep_submission_linter import lint_submission
from asiep_validator.error_codes import get_error_code
from asiep_venue_linter import lint_venue


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "profiles" / "asiep" / "v0.1" / "profile.json"
LATEX_ROOT = ROOT / "submission" / "escience2026" / "latex"
MAIN_TEX = LATEX_ROOT / "main.tex"
PDF_PATH = LATEX_ROOT / "main.pdf"
LOG_PATH = LATEX_ROOT / "main.log"
REPORT_PATH = ROOT / "submission" / "escience2026" / "latex_compile_report.json"
INTEGRATION_REPORT_PATH = ROOT / "submission" / "escience2026" / "full_paper_integration_report.json"
PAPER_PATH = ROOT / "manuscript" / "paper_v0.4_escience_human_editable.md"
PAGE_LIMIT = 8


def main() -> int:
    profile = _load_json(PROFILE_PATH)
    paper_result = lint_paper(PROFILE_PATH)
    citation_result = lint_citations(PROFILE_PATH)
    venue_result = lint_venue(ROOT / "venues" / "escience2026" / "venue_policy.json", PAPER_PATH)
    submission_result = lint_submission(profile_path=PROFILE_PATH, stage="rewrite")

    compile_report = _generate_compile_report()
    _assert_schema_valid(compile_report, ROOT / profile["latex_compile_report_schema_path"])
    REPORT_PATH.write_text(json.dumps(compile_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _update_integration_report(compile_report)

    final_check = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "final_submission_check.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    try:
        final_payload = json.loads(final_check.stdout)
    except json.JSONDecodeError:
        final_payload = {
            "valid": False,
            "errors": [{"code": "SUBMISSION_LINTER_FAILED", "message": final_check.stdout or final_check.stderr}],
        }

    final_submission_ready = final_payload.get("valid") is True
    summary = {
        "paper_linter_valid": paper_result["valid"],
        "citation_linter_valid": citation_result["valid"],
        "venue_linter_valid": venue_result["valid"],
        "submission_linter_rewrite_valid": submission_result["valid"],
        "compile_attempted": compile_report["compile_attempted"],
        "compile_success": compile_report["compile_success"],
        "generated_pdf_path": compile_report["generated_pdf_path"],
        "page_count_checked": compile_report["page_count_checked"],
        "page_count_total": compile_report["page_count_total"],
        "within_page_limit": compile_report["within_page_limit"],
        "unresolved_citations": compile_report["unresolved_citations"],
        "unresolved_references": compile_report["unresolved_references"],
        "overfull_boxes": compile_report["overfull_boxes"],
        "final_submission_ready": final_submission_ready,
        "final_submission_check_valid": final_payload.get("valid", False),
        "required_human_actions": compile_report["required_human_actions"],
        "final_submission_check_errors": final_payload.get("errors", []),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _generate_compile_report() -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    required_human_actions: list[str] = []
    compiler: str | None = None
    compile_attempted = False
    compile_success = False

    if not LATEX_ROOT.exists():
        errors.append(_issue("LATEX_ROOT_MISSING", f"LaTeX root missing: {LATEX_ROOT.relative_to(ROOT)}."))
        required_human_actions.append("Restore submission/escience2026/latex before compiling.")
        return _report(None, False, False, errors, warnings, required_human_actions)
    if not MAIN_TEX.exists():
        errors.append(_issue("LATEX_MAIN_MISSING", f"LaTeX main file missing: {MAIN_TEX.relative_to(ROOT)}."))
        required_human_actions.append("Restore submission/escience2026/latex/main.tex before compiling.")
        return _report(None, False, False, errors, warnings, required_human_actions)

    if shutil.which("latexmk"):
        compiler = "latexmk"
        compile_attempted = True
        compile_success = _run(["latexmk", "-pdf", "-interaction=nonstopmode", "main.tex"]).returncode == 0 and PDF_PATH.exists()
    elif shutil.which("pdflatex") and shutil.which("bibtex"):
        compiler = "pdflatex+bibtex"
        compile_attempted = True
        sequence = [
            ["pdflatex", "-interaction=nonstopmode", "main.tex"],
            ["bibtex", "main"],
            ["pdflatex", "-interaction=nonstopmode", "main.tex"],
            ["pdflatex", "-interaction=nonstopmode", "main.tex"],
        ]
        compile_success = all(_run(command).returncode == 0 for command in sequence) and PDF_PATH.exists()
    elif shutil.which("xelatex"):
        compiler = "xelatex"
        compile_attempted = True
        compile_success = _run(["xelatex", "-interaction=nonstopmode", "main.tex"]).returncode == 0 and PDF_PATH.exists()
    else:
        warnings.append(_issue("LATEX_COMPILE_FAILED", "No local LaTeX compiler was found.", severity="warning"))
        required_human_actions.append("Install a LaTeX toolchain or compile externally, then rerun M12 checks.")
        return _report(None, False, False, errors, warnings, required_human_actions)

    log_findings = _inspect_log(LOG_PATH)
    warnings.extend(log_findings["warnings"])
    errors.extend(log_findings["errors"])
    if not compile_success:
        errors.append(_issue("LATEX_COMPILE_FAILED", "LaTeX compile did not produce a successful main.pdf."))
        required_human_actions.append("Inspect submission/escience2026/latex/main.log and fix LaTeX errors without changing claims.")

    page_info = _count_pages(PDF_PATH) if PDF_PATH.exists() else {"checked": False, "total": None}
    page_count_checked = bool(page_info["checked"])
    page_count_total = page_info["total"]
    references_excluded_page_count = None
    within_page_limit = False
    if compile_success and page_count_checked and page_count_total is not None:
        if page_count_total <= PAGE_LIMIT:
            references_excluded_page_count = page_count_total
            within_page_limit = True
        else:
            warnings.append(_issue("LATEX_REFERENCE_BOUNDARY_UNCHECKED", "PDF exceeds 8 total pages; automated checker cannot confirm references-excluded page count.", severity="warning"))
            required_human_actions.append("Inspect the PDF and record the first references page to verify the 8-page non-reference budget.")
    elif compile_success:
        errors.append(_issue("LATEX_PAGE_COUNT_FAILED", "PDF was generated but page count could not be checked."))
        required_human_actions.append("Check the PDF page count with pdfinfo or another local tool.")

    if compile_success and page_count_checked and page_count_total and page_count_total > PAGE_LIMIT:
        warnings.append(_issue("LATEX_PAGE_BUDGET_EXCEEDED", f"PDF has {page_count_total} total pages; human check is required for 8 pages excluding references.", severity="warning"))

    if log_findings["unresolved_citations"]:
        errors.append(_issue("LATEX_UNRESOLVED_CITATION", f"Undefined citations: {', '.join(log_findings['unresolved_citations'])}."))
    if log_findings["unresolved_references"]:
        errors.append(_issue("LATEX_UNRESOLVED_REFERENCE", f"Undefined references: {', '.join(log_findings['unresolved_references'])}."))
    if log_findings["bibtex_failed"]:
        errors.append(_issue("LATEX_BIBTEX_FAILED", "LaTeX/BibTeX log indicates a bibliography failure."))

    author_block = _check_author_block(PDF_PATH)
    if author_block["author_placeholders_present"]:
        warnings.append(_issue("LATEX_LAYOUT_CHECK_REQUIRED", "Compiled PDF still contains author identity or affiliation placeholders.", severity="warning"))
        required_human_actions.append("Replace author identity and affiliation placeholders before final submission.")
    if not author_block["author_block_verified"]:
        required_human_actions.append("Verify the author block in the compiled PDF before final approval.")

    if not within_page_limit:
        required_human_actions.append("Do not mark final_submission_ready until page count is checked against 8 pages excluding references.")
    if not _json_bool(ROOT / "submission" / "escience2026" / "repository_policy_decision.json", "final_ready"):
        required_human_actions.append("Create repository_policy_decision.json after human repository/anonymization review.")
    if not _json_bool(ROOT / "submission" / "escience2026" / "deadline_verification.json", "deadline_verified"):
        required_human_actions.append("Create deadline_verification.json after manually verifying the CFP/EasyChair deadline.")
    if not (ROOT / "submission" / "escience2026" / "author_final_approval.json").exists():
        required_human_actions.append("Create author_final_approval.json only after human approval of every final gate.")

    report = _report(compiler, compile_attempted, compile_success, errors, warnings, _dedupe_strings(required_human_actions))
    report["page_count_checked"] = page_count_checked
    report["page_count_total"] = page_count_total
    report["references_excluded_page_count"] = references_excluded_page_count
    report["within_page_limit"] = within_page_limit
    report["generated_pdf_path"] = str(PDF_PATH.relative_to(ROOT)) if PDF_PATH.exists() else None
    report["unresolved_citations"] = log_findings["unresolved_citations"]
    report["unresolved_references"] = log_findings["unresolved_references"]
    report["overfull_boxes"] = log_findings["overfull_boxes"]
    report.update(author_block)
    return report


def _report(
    compiler: str | None,
    compile_attempted: bool,
    compile_success: bool,
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    required_human_actions: list[str],
) -> dict[str, Any]:
    return {
        "report_id": "asiep-escience2026-latex-compile-m12",
        "paper_id": "asiep-paper-v0.4-escience-human-editable",
        "target_venue": "escience2026",
        "latex_root": str(LATEX_ROOT.relative_to(ROOT)),
        "main_tex_path": str(MAIN_TEX.relative_to(ROOT)),
        "compiler": compiler,
        "compile_attempted": compile_attempted,
        "compile_success": compile_success,
        "generated_pdf_path": str(PDF_PATH.relative_to(ROOT)) if PDF_PATH.exists() else None,
        "page_count_checked": False,
        "page_count_total": None,
        "references_excluded_page_count": None,
        "within_page_limit": False,
        "page_limit": PAGE_LIMIT,
        "references_excluded": True,
        "unresolved_citations": [],
        "unresolved_references": [],
        "overfull_boxes": [],
        "errors": _dedupe_issues(errors),
        "warnings": _dedupe_issues(warnings),
        "required_human_actions": _dedupe_strings(required_human_actions),
        "final_submission_ready": False,
    }


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=LATEX_ROOT, capture_output=True, text=True)


def _inspect_log(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "errors": [],
            "warnings": [],
            "unresolved_citations": [],
            "unresolved_references": [],
            "bibtex_failed": False,
        }
    text = path.read_text(encoding="utf-8", errors="replace")
    unresolved_citations = sorted(set(re.findall(r"Citation `([^']+)' undefined", text)))
    unresolved_references = sorted(set(re.findall(r"Reference `([^']+)' undefined", text)))
    overfull_boxes = [line.strip() for line in text.splitlines() if line.strip().startswith("Overfull \\hbox")]
    bibtex_failed = "I couldn't open database file" in text or "I found no \\bibdata command" in text
    warnings: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    if "Overfull \\hbox" in text or "AUTHOR_LAYOUT_CHECK_REQUIRED" in text:
        warnings.append(_issue("LATEX_LAYOUT_CHECK_REQUIRED", "LaTeX log contains overfull boxes or layout-check markers.", severity="warning"))
    if "There were undefined references" in text and not unresolved_references:
        unresolved_references.append("unknown")
    if "There were undefined citations" in text and not unresolved_citations:
        unresolved_citations.append("unknown")
    return {
        "errors": errors,
        "warnings": warnings,
        "unresolved_citations": unresolved_citations,
        "unresolved_references": unresolved_references,
        "overfull_boxes": overfull_boxes,
        "bibtex_failed": bibtex_failed,
    }


def _count_pages(path: Path) -> dict[str, Any]:
    if shutil.which("pdfinfo"):
        result = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True)
        if result.returncode == 0:
            match = re.search(r"^Pages:\s+(\d+)", result.stdout, re.MULTILINE)
            if match:
                return {"checked": True, "total": int(match.group(1))}
    try:
        from pypdf import PdfReader  # type: ignore

        return {"checked": True, "total": len(PdfReader(str(path)).pages)}
    except Exception:
        return {"checked": False, "total": None}


def _check_author_block(path: Path) -> dict[str, Any]:
    expected = [
        "Zhang Bin",
        "Independent Researcher",
        "joy7759@gmail.com",
        "0009-0002-8861-1481",
    ]
    placeholders = [
        "AUTHOR IDENTITY CHECK REQUIRED",
        "AUTHOR AFFILIATION CHECK REQUIRED",
    ]
    text = ""
    if path.exists() and shutil.which("pdftotext"):
        result = subprocess.run(["pdftotext", str(path), "-"], capture_output=True, text=True)
        if result.returncode == 0:
            text = result.stdout
    missing = [item for item in expected if item not in text]
    placeholders_present = any(item in text for item in placeholders)
    return {
        "author_placeholders_present": placeholders_present,
        "author_block_verified": bool(text) and not placeholders_present and not missing,
        "author_block_requires_final_human_review": True,
        "author_block_expected_strings": expected,
        "author_block_missing_strings": missing,
    }


def _update_integration_report(compile_report: dict[str, Any]) -> None:
    report = _load_json(INTEGRATION_REPORT_PATH)
    author_final_approval_exists = (ROOT / "submission" / "escience2026" / "author_final_approval.json").exists()
    repository_policy_decided = _json_bool(ROOT / "submission" / "escience2026" / "repository_policy_decision.json", "final_ready")
    deadline_verified = _json_bool(ROOT / "submission" / "escience2026" / "deadline_verification.json", "deadline_verified")
    license_decided = _json_bool(ROOT / "submission" / "escience2026" / "license_decision.json", "final_ready")
    sensitive_reviewed = _json_bool(ROOT / "submission" / "escience2026" / "sensitive_content_review.json", "final_ready")
    layout_reviewed = _json_bool(ROOT / "submission" / "escience2026" / "layout_review.json", "final_ready")
    final_ready = (
        compile_report["compile_success"]
        and compile_report["page_count_checked"]
        and compile_report["within_page_limit"]
        and author_final_approval_exists
        and repository_policy_decided
        and deadline_verified
        and license_decided
        and sensitive_reviewed
        and layout_reviewed
    )
    report.update(
        {
            "latex_compile_attempted": compile_report["compile_attempted"],
            "latex_compile_success": compile_report["compile_success"],
            "latex_pdf_path": compile_report["generated_pdf_path"],
            "latex_page_count_checked": compile_report["page_count_checked"],
            "latex_page_count_total": compile_report["page_count_total"],
            "latex_references_excluded_page_count": compile_report["references_excluded_page_count"],
            "latex_within_page_limit": compile_report["within_page_limit"],
            "latex_unresolved_citations": compile_report["unresolved_citations"],
            "latex_unresolved_references": compile_report["unresolved_references"],
            "latex_compile_report_path": str(REPORT_PATH.relative_to(ROOT)),
            "latex_compiled": compile_report["compile_success"],
            "page_count_checked": compile_report["page_count_checked"],
            "final_repository_policy_decided": repository_policy_decided,
            "final_deadline_verified": deadline_verified,
            "author_final_approval_exists": author_final_approval_exists,
            "final_submission_ready": final_ready,
        }
    )
    if "remaining_human_actions" in report:
        completed_when_compiled = {
            "Compile the IEEE LaTeX manuscript.",
        }
        completed_when_page_checked = {
            "Check page count against 8 pages excluding references.",
        }
        existing_actions = report["remaining_human_actions"]
        if compile_report["compile_success"]:
            existing_actions = [action for action in existing_actions if action not in completed_when_compiled]
        if compile_report["page_count_checked"] and compile_report["within_page_limit"]:
            existing_actions = [action for action in existing_actions if action not in completed_when_page_checked]
        report["remaining_human_actions"] = _dedupe_strings(
            existing_actions
            + [
                "Review submission/escience2026/latex_compile_report.json.",
            ]
        )
        if not repository_policy_decided:
            report["remaining_human_actions"].append("Create repository_policy_decision.json only after human repository/anonymization decision.")
        if not deadline_verified:
            report["remaining_human_actions"].append("Create deadline_verification.json only after human deadline verification.")
        if not author_final_approval_exists:
            report["remaining_human_actions"].append("Create author_final_approval.json only after human final approval.")
    INTEGRATION_REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _json_bool(path: Path, key: str) -> bool:
    payload = _load_json_if_exists(path)
    return bool(payload) and payload.get(key) is True


def _issue(code: str, message: str, *, severity: str | None = None) -> dict[str, str]:
    spec = get_error_code(code)
    return {
        "code": code,
        "severity": severity or spec.severity,
        "message": message,
        "remediation_hint": spec.remediation_hint,
        "repairability": spec.repairability,
    }


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _load_json(path)


def _assert_schema_valid(payload: dict[str, Any], schema_path: Path) -> None:
    schema_errors = sorted(Draft202012Validator(_load_json(schema_path)).iter_errors(payload), key=str)
    if schema_errors:
        messages = "; ".join(error.message for error in schema_errors)
        raise RuntimeError(f"Schema validation failed for {schema_path}: {messages}")


def _dedupe_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    unique = []
    for issue in issues:
        key = (issue.get("code"), issue.get("message"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(issue)
    return unique


def _dedupe_strings(items: list[str]) -> list[str]:
    seen = set()
    unique = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


if __name__ == "__main__":
    raise SystemExit(main())
