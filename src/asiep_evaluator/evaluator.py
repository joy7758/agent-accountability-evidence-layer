from __future__ import annotations

import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from asiep_importer import import_trace
from asiep_packager import package_bundle
from asiep_repairer import generate_repair_plan
from asiep_resolver import resolve_bundle
from asiep_validator import validate_file


ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "reports" / "asiep_v0.1_evaluation_report.json"
SUMMARY_PATH = ROOT / "reports" / "asiep_v0.1_evaluation_summary.md"
PAPER_ASSETS = ROOT / "paper_assets"
CREATED_AT = "2026-05-05T07:00:00Z"


def evaluate_profile(profile_path: str | Path) -> dict[str, Any]:
    profile_file = _resolve_path(profile_path)
    profile = _load_json(profile_file)
    policy = _load_json(ROOT / profile["evaluation_policy_path"])
    corpus = _load_json(ROOT / policy["corpus_manifest_path"])
    crosswalk = _load_json(ROOT / policy["crosswalk_matrix_path"])

    _assert_schema(corpus, ROOT / profile["corpus_manifest_schema_path"])
    _assert_schema(crosswalk, ROOT / profile["crosswalk_matrix_schema_path"])
    _assert_crosswalk_complete(crosswalk)

    _prepare_generated_dirs()
    pipeline_results = [_evaluate_expected_result(item) for item in corpus["expected_results"]]
    crosswalk_coverage = _crosswalk_coverage(crosswalk)
    metric_results = _metric_results(profile, corpus, crosswalk, pipeline_results, crosswalk_coverage)
    attack_results = [result for result in pipeline_results if not result["expected_valid"]]
    attack_corpus_results = {
        "total_attack_samples": len(attack_results),
        "detected_attack_samples": sum(1 for result in attack_results if not result["actual_valid"]),
        "results": attack_results,
    }

    report = {
        "profile": "ASIEP",
        "profile_version": "0.1.0",
        "evaluation_id": "evaluation:asiep-v0.1-m6",
        "evaluation_version": "0.1.0",
        "created_at": CREATED_AT,
        "repository": {
            "name": "agent-accountability-evidence-layer",
            "root": ".",
            "commit": _git_commit(),
        },
        "evaluated_components": _evaluated_components(profile),
        "corpus_summary": _corpus_summary(corpus),
        "pipeline_results": pipeline_results,
        "metric_results": metric_results,
        "attack_corpus_results": attack_corpus_results,
        "crosswalk_coverage": crosswalk_coverage,
        "generated_artifacts": _generated_artifact_list(),
        "limitations": [
            "M6 uses local fixtures only and does not call OTel collectors, LangSmith APIs, FDO registries, or remote artifact stores.",
            "Crosswalk coverage is a local minimal mapping and does not claim external standard certification.",
            "Metrics are computed over the repository corpus, not over production agent traces.",
            "Privacy compliance checks search for blocked raw-content keys and synthetic sentinel strings; they are not a full DLP scanner."
        ],
        "revalidation_commands": [
            "PYTHONPATH=src python -m asiep_evaluator --profile profiles/asiep/v0.1/profile.json --format json",
            "PYTHONPATH=src python scripts/evaluate_profile_demo.py",
            "PYTHONPATH=src python -m pytest tests/test_evaluator.py"
        ],
    }

    _write_outputs(report, crosswalk)
    _assert_schema(report, ROOT / profile["evaluation_report_schema_path"])
    return report


def _evaluate_expected_result(item: dict[str, Any]) -> dict[str, Any]:
    target = ROOT / item["target_path"]
    target_type = item["target_type"]
    actual_valid = False
    actual_codes: list[str] = []
    try:
        if target_type == "evidence_example":
            report = validate_file(target)
            actual_valid = report.valid
            actual_codes = [] if report.valid else report.codes
        elif target_type == "repair_case":
            plan = generate_repair_plan(target)
            actual_valid = bool(plan["repair_actions"] or plan["blocked_actions"]) and not plan["valid_before"]
            actual_codes = []
        elif target_type == "bundle":
            result = resolve_bundle(target)
            actual_valid = bool(result["valid"])
            actual_codes = [error["code"] for error in result["errors"]]
        elif target_type == "import_request":
            result = import_trace(target)
            actual_valid = bool(result["valid"])
            actual_codes = [error["code"] for error in result["errors"]]
        elif target_type == "package_request":
            result = package_bundle(target)
            actual_valid = bool(result["valid"])
            actual_codes = [error["code"] for error in result["errors"]]
        elif target_type == "generated_package":
            actual_valid, actual_codes = _check_generated_package(target)
        else:
            actual_valid = False
            actual_codes = ["EVAL_PIPELINE_STEP_FAILED"]
    except Exception:
        actual_valid = False
        actual_codes = ["EVAL_PIPELINE_STEP_FAILED"]

    passed = actual_valid == item["expected_valid"] and actual_codes == item["expected_error_codes"]
    if not passed and not actual_codes:
        actual_codes = ["EVAL_EXPECTED_RESULT_MISMATCH"]
    return {
        "target_path": item["target_path"],
        "target_type": target_type,
        "command": item["command"],
        "expected_valid": item["expected_valid"],
        "actual_valid": actual_valid,
        "expected_error_codes": item["expected_error_codes"],
        "actual_error_codes": actual_codes,
        "passed": passed,
        "purpose": item["purpose"],
        "related_invariant_ids": item["related_invariant_ids"],
        "related_metric_ids": item["related_metric_ids"],
    }


def _check_generated_package(package_dir: Path) -> tuple[bool, list[str]]:
    required = [
        "package_manifest.json",
        "fdo_record.json",
        "ro-crate-metadata.json",
        "prov.jsonld",
        "evidence/evidence.json",
        "bundle/bundle.json",
        "artifacts/trace.json",
        "artifacts/feedback.json",
        "artifacts/score.json",
        "artifacts/candidate.diff",
        "artifacts/gate_report.json",
    ]
    missing = [path for path in required if not (package_dir / path).exists()]
    if missing:
        return False, ["PACKAGE_MANIFEST_INVALID"]
    schema_checks = [
        ("package_manifest.json", "interfaces/asiep_package_manifest.schema.json", "PACKAGE_MANIFEST_INVALID"),
        ("fdo_record.json", "interfaces/asiep_fdo_record.schema.json", "PACKAGE_FDO_RECORD_INVALID"),
        ("ro-crate-metadata.json", "interfaces/asiep_rocrate_metadata.schema.json", "PACKAGE_ROCRATE_INVALID"),
        ("prov.jsonld", "interfaces/asiep_prov_jsonld.schema.json", "PACKAGE_PROV_INVALID"),
    ]
    for file_name, schema_path, code in schema_checks:
        errors = _schema_errors(_load_json(package_dir / file_name), ROOT / schema_path)
        if errors:
            return False, [code]
    resolver_result = resolve_bundle(package_dir / "bundle" / "bundle.json")
    if not resolver_result["valid"]:
        return False, [error["code"] for error in resolver_result["errors"]]
    validator_report = validate_file(package_dir / "evidence" / "evidence.json", bundle_root=package_dir / "bundle")
    if not validator_report.valid:
        return False, validator_report.codes
    return True, []


def _metric_results(
    profile: dict[str, Any],
    corpus: dict[str, Any],
    crosswalk: dict[str, Any],
    pipeline_results: list[dict[str, Any]],
    crosswalk_coverage: dict[str, Any],
) -> list[dict[str, Any]]:
    metrics = [
        _evidence_completeness_metric(),
        _cross_standard_coverage_metric(crosswalk_coverage),
        _gate_reproducibility_metric(),
        _tamper_detection_metric(pipeline_results),
        _false_positive_metric(pipeline_results),
        _privacy_policy_metric(),
        _packaging_closure_metric(pipeline_results),
        _agent_readability_metric(profile),
    ]
    expected = set(_load_json(ROOT / "profiles/asiep/v0.1/evaluation_policy.json")["metrics"])
    seen = {metric["metric_id"] for metric in metrics}
    if seen != expected:
        raise ValueError(f"metric set mismatch: {seen ^ expected}")
    return metrics


def _evidence_completeness_metric() -> dict[str, Any]:
    package_dirs = [ROOT / "examples/generated_packages/otel_chatbot_package", ROOT / "examples/generated_packages/langsmith_chatbot_package"]
    required_roles = {"trace", "feedback", "score", "candidate_diff", "gate_report"}
    numerator = 0
    denominator = 0
    for package_dir in package_dirs:
        manifest = _load_json(package_dir / "package_manifest.json")
        roles = {artifact["role"] for artifact in manifest["artifacts"]}
        denominator += len(required_roles)
        numerator += len(required_roles & roles)
        required_files = ["evidence/evidence.json", "bundle/bundle.json", "fdo_record.json", "ro-crate-metadata.json", "prov.jsonld"]
        denominator += len(required_files)
        numerator += sum(1 for path in required_files if (package_dir / path).exists())
    return _metric(
        "evidence_completeness",
        "Evidence completeness",
        numerator,
        denominator,
        "Count required evidence roles and package files in generated valid packages.",
        "Generated valid packages carry required ASIEP evidence roles and package files.",
        ["Computed over two generated local fixture packages only."],
    )


def _cross_standard_coverage_metric(crosswalk_coverage: dict[str, Any]) -> dict[str, Any]:
    return _metric(
        "cross_standard_coverage",
        "Cross-standard coverage",
        crosswalk_coverage["mapped_cells"],
        crosswalk_coverage["total_cells"],
        "Count non-empty and non-not_applicable mappings across PROV, OTel, LangSmith-like, FDO-like, RO-Crate-like, and governance columns.",
        "The local crosswalk covers most field groups but honestly marks non-applicable mappings.",
        ["Coverage is for local minimal mappings, not external standard certification."],
    )


def _gate_reproducibility_metric() -> dict[str, Any]:
    paths = [
        ROOT / "examples/valid_chatbot_improvement.json",
        ROOT / "examples/generated_bundles/otel_chatbot_bundle/evidence.json",
        ROOT / "examples/generated_bundles/langsmith_chatbot_bundle/evidence.json",
    ]
    numerator = 0
    denominator = 0
    for path in paths:
        evidence = _load_json(path)
        denominator += 1
        gate = evidence["gates"][0]
        checks_pass = all(not check["regression"] and check["passed"] for check in evidence["safety_checks"])
        flips_pass = all(item["count"] <= item["threshold"] for item in evidence["flip_counts"].values())
        has_gate_report = any(item["id"] == gate["gate_report_ref"] and item["type"] == "gate_report" for item in evidence["evidence"])
        if gate["decision"] in {"promote", "reject"} and checks_pass and flips_pass and has_gate_report:
            numerator += 1
    return _metric(
        "gate_reproducibility",
        "Gate reproducibility",
        numerator,
        denominator,
        "Check whether gate decision can be reviewed from gate_report_ref, safety checks, flip counts, and thresholds.",
        "Valid local examples expose the evidence needed to review promote decisions.",
        ["Does not replay model behavior or external evaluator logic."],
    )


def _tamper_detection_metric(pipeline_results: list[dict[str, Any]]) -> dict[str, Any]:
    attacks = [result for result in pipeline_results if not result["expected_valid"]]
    numerator = sum(1 for result in attacks if not result["actual_valid"])
    return _metric(
        "tamper_detection_recall",
        "Tamper detection recall",
        numerator,
        len(attacks),
        "Count known invalid or attack samples that are rejected by validator, resolver, importer, or packager.",
        "Known local attack samples are detected by the appropriate M0-M5 layer.",
        ["The corpus is small and synthetic."],
    )


def _false_positive_metric(pipeline_results: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [result for result in pipeline_results if result["expected_valid"] and result["target_type"] != "repair_case"]
    numerator = sum(1 for result in valid if not result["actual_valid"])
    denominator = len(valid)
    return {
        "metric_id": "false_positive_rate",
        "name": "False positive rate",
        "value": 0.0 if denominator == 0 else numerator / denominator,
        "numerator": numerator,
        "denominator": denominator,
        "method": "Count known valid local fixtures incorrectly rejected by the pipeline.",
        "interpretation": "Lower is better; zero means no known valid local fixture was rejected.",
        "limitations": ["Only covers repository fixtures, not external traces."],
    }


def _privacy_policy_metric() -> dict[str, Any]:
    packages = [ROOT / "examples/generated_packages/otel_chatbot_package", ROOT / "examples/generated_packages/langsmith_chatbot_package"]
    blocked = ["raw_prompt", "raw_user_input", "raw_model_output", "messages", "completion", "SYNTHETIC_SECRET_PROMPT_DO_NOT_IMPORT"]
    numerator = 0
    for package in packages:
        text = "".join((package / name).read_text(encoding="utf-8") for name in ["package_manifest.json", "fdo_record.json", "ro-crate-metadata.json", "prov.jsonld"])
        if not any(item in text for item in blocked):
            numerator += 1
    return _metric(
        "privacy_policy_compliance",
        "Privacy policy compliance",
        numerator,
        len(packages),
        "Search generated package metadata for blocked raw-content keys and the synthetic sensitive sentinel.",
        "Generated package metadata keeps raw prompt/input/output content out by default.",
        ["String search is not a full privacy classifier."],
    )


def _packaging_closure_metric(pipeline_results: list[dict[str, Any]]) -> dict[str, Any]:
    packages = [result for result in pipeline_results if result["target_type"] == "generated_package"]
    numerator = sum(1 for result in packages if result["actual_valid"])
    return _metric(
        "packaging_closure",
        "Packaging closure",
        numerator,
        len(packages),
        "Validate generated package closure: manifest, evidence, bundle, artifacts, FDO-like record, RO-Crate-like metadata, and PROV JSON-LD.",
        "Generated packages are closed over the local evidence bundle and metadata files.",
        ["Package closure is local-only and does not test remote resolvability."],
    )


def _agent_readability_metric(profile: dict[str, Any]) -> dict[str, Any]:
    required_paths = [
        "validator_output_schema_path",
        "repair_plan_schema_path",
        "bundle_resolution_schema_path",
        "import_result_schema_path",
        "package_result_schema_path",
        "evaluation_report_schema_path",
        "crosswalk_matrix_schema_path",
        "corpus_manifest_schema_path",
    ]
    numerator = sum(1 for key in required_paths if key in profile and (ROOT / profile[key]).exists())
    denominator = len(required_paths)
    return _metric(
        "agent_readability",
        "Agent readability",
        numerator,
        denominator,
        "Count machine-readable schemas exposed by profile.json for validator, repair, resolver, import, package, and evaluation outputs.",
        "The profile manifest indexes the agent-readable interface surfaces needed for automated review.",
        ["Does not measure downstream agent performance."],
    )


def _metric(
    metric_id: str,
    name: str,
    numerator: float,
    denominator: float,
    method: str,
    interpretation: str,
    limitations: list[str],
) -> dict[str, Any]:
    return {
        "metric_id": metric_id,
        "name": name,
        "value": 0.0 if denominator == 0 else numerator / denominator,
        "numerator": numerator,
        "denominator": denominator,
        "method": method,
        "interpretation": interpretation,
        "limitations": limitations,
    }


def _crosswalk_coverage(crosswalk: dict[str, Any]) -> dict[str, Any]:
    columns = ["prov_mapping", "otel_mapping", "langsmith_mapping", "fdo_mapping", "rocrate_mapping", "governance_mapping"]
    mapped = 0
    total = len(crosswalk["mappings"]) * len(columns)
    for mapping in crosswalk["mappings"]:
        mapped += sum(1 for column in columns if mapping[column] and mapping[column] != "not_applicable")
    invariant_coverage = {f"I{index}": False for index in range(1, 11)}
    for mapping in crosswalk["mappings"]:
        for invariant_id in mapping["invariant_ids"]:
            if invariant_id in invariant_coverage:
                invariant_coverage[invariant_id] = True
    return {
        "field_group_count": len({mapping["field_group"] for mapping in crosswalk["mappings"]}),
        "standards_count": len(crosswalk["standards"]),
        "mapped_cells": mapped,
        "total_cells": total,
        "coverage": 0.0 if total == 0 else mapped / total,
        "invariant_coverage": invariant_coverage,
    }


def _assert_crosswalk_complete(crosswalk: dict[str, Any]) -> None:
    required_groups = {"profile", "record", "lineage", "trigger", "actors", "runtime", "evidence", "evaluation", "gate", "integrity", "compliance", "bundle", "import", "package", "repair"}
    groups = {mapping["field_group"] for mapping in crosswalk["mappings"]}
    if not required_groups <= groups:
        missing = sorted(required_groups - groups)
        raise ValueError(f"crosswalk missing field groups: {missing}")
    coverage = _crosswalk_coverage(crosswalk)["invariant_coverage"]
    if not all(coverage.values()):
        missing = [key for key, value in coverage.items() if not value]
        raise ValueError(f"crosswalk missing invariants: {missing}")


def _corpus_summary(corpus: dict[str, Any]) -> dict[str, Any]:
    counter = Counter(item["target_type"] for item in corpus["expected_results"])
    valid = sum(1 for item in corpus["expected_results"] if item["expected_valid"])
    invalid = len(corpus["expected_results"]) - valid
    return {
        "total_expected_results": len(corpus["expected_results"]),
        "valid_targets": valid,
        "invalid_targets": invalid,
        "target_types": dict(sorted(counter.items())),
    }


def _evaluated_components(profile: dict[str, Any]) -> list[dict[str, str]]:
    components = {
        "profile_manifest": "profiles/asiep/v0.1/profile.json",
        "schema": profile["schema_path"],
        "jsonld_context": profile["jsonld_context_path"],
        "conformance_matrix": profile["conformance_matrix_path"],
        "validator": "src/asiep_validator/validator.py",
        "repairer": "src/asiep_repairer/repairer.py",
        "resolver": "src/asiep_resolver/resolver.py",
        "importer": "src/asiep_importer/importer.py",
        "packager": "src/asiep_packager/packager.py",
        "examples": "examples",
        "attack_corpus": "attack_corpus",
        "generated_packages": "examples/generated_packages",
    }
    return [
        {
            "component_id": component_id,
            "path": path,
            "status": "present" if (ROOT / path).exists() else "generated" if component_id == "generated_packages" else "missing",
        }
        for component_id, path in components.items()
    ]


def _generated_artifact_list() -> list[dict[str, str]]:
    return [
        {"path": "reports/asiep_v0.1_evaluation_report.json", "artifact_type": "evaluation_report"},
        {"path": "reports/asiep_v0.1_evaluation_summary.md", "artifact_type": "evaluation_summary"},
        {"path": "paper_assets/tables/crosswalk_matrix.md", "artifact_type": "paper_table"},
        {"path": "paper_assets/tables/evaluation_metrics.md", "artifact_type": "paper_table"},
        {"path": "paper_assets/tables/attack_corpus_results.md", "artifact_type": "paper_table"},
        {"path": "paper_assets/figures/pipeline_flow.mmd", "artifact_type": "paper_figure"},
        {"path": "paper_assets/figures/state_machine.mmd", "artifact_type": "paper_figure"},
        {"path": "paper_assets/paper_outline.md", "artifact_type": "paper_asset"},
        {"path": "paper_assets/abstract_draft.md", "artifact_type": "paper_asset"},
    ]


def _write_outputs(report: dict[str, Any], crosswalk: dict[str, Any]) -> None:
    (ROOT / "reports").mkdir(exist_ok=True)
    (PAPER_ASSETS / "tables").mkdir(parents=True, exist_ok=True)
    (PAPER_ASSETS / "figures").mkdir(parents=True, exist_ok=True)
    _write_json(REPORT_PATH, report)
    SUMMARY_PATH.write_text(_summary_markdown(report), encoding="utf-8")
    (PAPER_ASSETS / "README.md").write_text(_paper_readme(), encoding="utf-8")
    (PAPER_ASSETS / "tables" / "crosswalk_matrix.md").write_text(_crosswalk_table(crosswalk), encoding="utf-8")
    (PAPER_ASSETS / "tables" / "evaluation_metrics.md").write_text(_metrics_table(report["metric_results"]), encoding="utf-8")
    (PAPER_ASSETS / "tables" / "attack_corpus_results.md").write_text(_attack_table(report["attack_corpus_results"]["results"]), encoding="utf-8")
    (PAPER_ASSETS / "figures" / "pipeline_flow.mmd").write_text(_pipeline_mermaid(), encoding="utf-8")
    (PAPER_ASSETS / "figures" / "state_machine.mmd").write_text(_state_machine_mermaid(), encoding="utf-8")
    (PAPER_ASSETS / "paper_outline.md").write_text(_paper_outline(), encoding="utf-8")
    (PAPER_ASSETS / "abstract_draft.md").write_text(_abstract_draft(), encoding="utf-8")


def _summary_markdown(report: dict[str, Any]) -> str:
    metrics = {metric["metric_id"]: metric for metric in report["metric_results"]}
    return (
        "# ASIEP v0.1 Evaluation Summary\n\n"
        f"- evaluation_id: `{report['evaluation_id']}`\n"
        f"- pipeline_results: {len(report['pipeline_results'])}\n"
        f"- tamper_detection_recall: {metrics['tamper_detection_recall']['value']:.3f}\n"
        f"- false_positive_rate: {metrics['false_positive_rate']['value']:.3f}\n"
        f"- privacy_policy_compliance: {metrics['privacy_policy_compliance']['value']:.3f}\n"
        f"- cross_standard_coverage: {metrics['cross_standard_coverage']['value']:.3f}\n\n"
        "This summary is generated from local fixtures only and does not claim external standard certification.\n"
    )


def _paper_readme() -> str:
    return (
        "# Paper Assets\n\n"
        "These assets are generated by `asiep_evaluator` from local M0-M6 fixtures. "
        "They are paper-ready inputs, not a full paper and not external standard certification.\n"
    )


def _crosswalk_table(crosswalk: dict[str, Any]) -> str:
    rows = ["| Field group | ASIEP field | PROV | OTel | LangSmith-like | FDO-like | RO-Crate-like | Governance | Lossiness |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for mapping in crosswalk["mappings"]:
        rows.append(
            "| {field_group} | `{asiep_field}` | {prov_mapping} | {otel_mapping} | {langsmith_mapping} | {fdo_mapping} | {rocrate_mapping} | {governance_mapping} | {lossiness} |".format(
                **{key: _escape_md(str(value)) for key, value in mapping.items()}
            )
        )
    return "\n".join(rows) + "\n"


def _metrics_table(metrics: list[dict[str, Any]]) -> str:
    rows = ["| Metric | Value | Numerator | Denominator | Method |", "| --- | ---: | ---: | ---: | --- |"]
    for metric in metrics:
        rows.append(f"| `{metric['metric_id']}` | {metric['value']:.3f} | {metric['numerator']} | {metric['denominator']} | {_escape_md(metric['method'])} |")
    return "\n".join(rows) + "\n"


def _attack_table(results: list[dict[str, Any]]) -> str:
    rows = ["| Target | Layer | Detected | Error codes | Purpose |", "| --- | --- | --- | --- | --- |"]
    for result in results:
        rows.append(f"| `{result['target_path']}` | {result['target_type']} | {not result['actual_valid']} | `{', '.join(result['actual_error_codes'])}` | {_escape_md(result['purpose'])} |")
    return "\n".join(rows) + "\n"


def _pipeline_mermaid() -> str:
    return """flowchart TD
  A["local trace fixture"] --> B["asiep_importer"]
  B --> C["ASIEP evidence bundle"]
  C --> D["asiep_resolver"]
  D --> E["asiep_validator --bundle-root"]
  E --> F["asiep_repairer"]
  E --> G["asiep_packager"]
  G --> H["FDO-like / RO-Crate-like / PROV package"]
  H --> I["asiep_evaluator"]
  I --> J["reports and paper assets"]
"""


def _state_machine_mermaid() -> str:
    return """stateDiagram-v2
  [*] --> DRAFT
  DRAFT --> CANDIDATE
  CANDIDATE --> EVALUATED
  EVALUATED --> GATED
  GATED --> PROMOTED
  GATED --> REJECTED
  PROMOTED --> ROLLED_BACK
"""


def _paper_outline() -> str:
    return (
        "# Paper Outline\n\n"
        "1. Problem framing: agent accountability evidence in agent-to-agent workflows.\n"
        "2. Related work positioning: PROV, OpenTelemetry GenAI, LangSmith-like traces, FDO, RO-Crate, governance logs.\n"
        "3. ASIEP profile: schema, JSON-LD context, state machine, invariants.\n"
        "4. Toolchain: validator, repairer, resolver, importer, packager.\n"
        "5. Evaluation: corpus, crosswalk, metrics, attack detection.\n"
        "6. Limitations: local fixtures, no external registry, no full standard certification.\n"
        "7. Standardization path: profile stabilization and interop tests.\n"
    )


def _abstract_draft() -> str:
    return (
        "# Abstract Draft\n\n"
        "We present ASIEP v0.1, a minimal Agent Self-Improvement Evidence Profile for "
        "agent-to-agent accountability. Rather than implementing a self-improving agent, "
        "ASIEP defines a machine-readable evidence object, validator, repair planning "
        "interface, local bundle resolver, trace-fixture importer, and local FAIR/FDO-like "
        "and RO-Crate-like package layer. A local evaluation corpus exercises valid and "
        "adversarial examples across schema, state, reference, digest, gate, import, and "
        "package checks. The M6 evaluation report provides reproducible metrics and a "
        "cross-standard matrix without claiming external registry integration or full "
        "standards certification.\n"
    )


def _escape_md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _prepare_generated_dirs() -> None:
    for path in (ROOT / "examples/generated_bundles", ROOT / "examples/generated_packages"):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)


def _assert_schema(payload: dict[str, Any], schema_path: Path) -> None:
    errors = _schema_errors(payload, schema_path)
    if errors:
        raise ValueError(f"{schema_path} validation failed: {errors[0].message}")


def _schema_errors(payload: dict[str, Any], schema_path: Path) -> list[Any]:
    schema = _load_json(schema_path)
    return sorted(Draft202012Validator(schema).iter_errors(payload), key=str)


def _resolve_path(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _git_commit() -> str:
    return "local-reproducible-run"
