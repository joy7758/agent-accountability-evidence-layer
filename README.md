# Agent Accountability Evidence Layer

AAEL is an implementation-neutral evidence layer for agent accountability.

The first deliverable is ASIEP v0.1:

```text
ASIEP = Agent Self-Improvement Evidence Profile
```

ASIEP v0.1 is intentionally small. It does not build a stronger autonomous
agent, a customer-service system, or an agent framework. It defines the minimum
evidence profile needed for one agent or evaluator to verify a claimed
self-improvement:

- a JSON Schema
- a JSON-LD context
- a lifecycle state machine
- ten invariants
- a local validator
- attack samples
- initial mappings to PROV-O, OpenTelemetry, FDO, and RO-Crate

The design assumption is agent-to-agent accountability: future agents should be
able to inspect, reject, replay, and improve evidence about their own changes
without depending on one vendor runtime.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

PYTHONPATH=src python scripts/selftest.py
PYTHONPATH=src python -m asiep_validator examples/valid_chatbot_improvement.json
PYTHONPATH=src python -m asiep_validator examples/valid_chatbot_improvement.json --format json
PYTHONPATH=src python -m asiep_repairer examples/invalid_promote_with_regression.json --format json
PYTHONPATH=src python scripts/repair_loop_demo.py
PYTHONPATH=src python -m asiep_resolver examples/bundles/valid_chatbot_bundle/bundle.json --format json
PYTHONPATH=src python -m asiep_validator examples/bundles/valid_chatbot_bundle/evidence.json --bundle-root examples/bundles/valid_chatbot_bundle --format json
PYTHONPATH=src python scripts/resolve_bundle_demo.py
PYTHONPATH=src python -m asiep_importer examples/import_requests/otel_chatbot_request.json --format json
PYTHONPATH=src python scripts/import_trace_demo.py
PYTHONPATH=src python -m asiep_packager examples/package_requests/otel_chatbot_package_request.json --format json
PYTHONPATH=src python scripts/package_demo.py
PYTHONPATH=src python -m asiep_evaluator --profile profiles/asiep/v0.1/profile.json --format json
PYTHONPATH=src python scripts/evaluate_profile_demo.py
```

Expected CLI result for the valid example:

```text
PASS
```

## Validation Layers

The agent-native profile entrypoint is
`profiles/index.json`. Agents can discover ASIEP from that registry, then load
`profiles/asiep/v0.1/profile.json` to find the schema, JSON-LD context,
conformance matrix, examples, validator, repair policy, and repairer.

The v0.1 validator checks:

- JSON Schema conformance
- lifecycle state transitions
- evidence reference closure
- gate decision consistency with safety checks
- gate decision consistency with flip-count thresholds
- rollback evidence presence
- evidence and reference digest basics

## M2 Repair Loop

M2 adds an agent-readable, evidence-preserving repair loop. The validator JSON
output is constrained by `interfaces/asiep_validator_output.schema.json`; repair
plans are constrained by `interfaces/asiep_repair_plan.schema.json`; and repair
boundaries live in `profiles/asiep/v0.1/repair_policy.json`.

The repairer does not edit input files. It generates JSON Patch skeletons,
blocked actions, evidence requirements, and a revalidation command:

```bash
PYTHONPATH=src python -m asiep_repairer examples/invalid_promote_with_regression.json --format json
```

Current limits:

- no automatic evidence mutation
- no generated gate reports, approvals, refs, or digests
- no remote fetching or importer/exporter work
- unsafe `promote` decisions are planned toward `reject` or real reevaluation,
  not toward falsifying safety evidence

## M3 Evidence Bundles

M3 adds a local evidence bundle resolver. Bundles are described by
`interfaces/asiep_evidence_bundle.schema.json`; resolver output is constrained
by `interfaces/asiep_bundle_resolution.schema.json`; and the ASIEP manifest
links the resolver entrypoint.

Run the local resolver:

```bash
PYTHONPATH=src python -m asiep_resolver examples/bundles/valid_chatbot_bundle/bundle.json --format json
```

Run validator with local digest verification:

```bash
PYTHONPATH=src python -m asiep_validator examples/bundles/valid_chatbot_bundle/evidence.json --bundle-root examples/bundles/valid_chatbot_bundle --format json
```

Run all bundle fixtures:

```bash
PYTHONPATH=src python scripts/resolve_bundle_demo.py
```

Current M3 limits:

- local bundle resolution only
- no remote URI fetching
- no importer/exporter work
- no automatic digest repair
- no reading paths outside `bundle_root`

## M4 Trace Importer

M4 adds a local trace fixture importer. It converts OTel-like and LangSmith-like
JSON fixtures into ASIEP evidence bundles, then runs resolver and validator
checks over the generated bundle.

Run an OTel-like fixture import:

```bash
PYTHONPATH=src python -m asiep_importer examples/import_requests/otel_chatbot_request.json --format json
```

Run a LangSmith-like fixture import:

```bash
PYTHONPATH=src python -m asiep_importer examples/import_requests/langsmith_chatbot_request.json --format json
```

Run all import fixtures:

```bash
PYTHONPATH=src python scripts/import_trace_demo.py
```

Generated bundles are written under `examples/generated_bundles/` and can be
checked with:

```bash
PYTHONPATH=src python -m asiep_resolver examples/generated_bundles/otel_chatbot_bundle/bundle.json --format json
PYTHONPATH=src python -m asiep_validator examples/generated_bundles/otel_chatbot_bundle/evidence.json --bundle-root examples/generated_bundles/otel_chatbot_bundle --format json
```

Current M4 limits:

- local fixtures only
- no LangSmith API calls
- no OpenTelemetry collector
- no remote URI fetching
- default `ref_only`; raw prompt, input, output, messages, and completions are
  blocked when requested by policy
- missing gate reports or candidate diffs are not fabricated

## M5 FAIR/FDO and RO-Crate Packaging

M5 adds a local package layer for resolver-valid and validator-valid ASIEP
bundles. It creates a package manifest, a local FDO-like record, RO-Crate-like
metadata, PROV JSON-LD, and package-local copies of evidence, bundle, and
artifacts.

Prepare generated bundles:

```bash
PYTHONPATH=src python scripts/import_trace_demo.py
```

Package an OTel-generated bundle:

```bash
PYTHONPATH=src python -m asiep_packager examples/package_requests/otel_chatbot_package_request.json --format json
```

Run all package fixtures:

```bash
PYTHONPATH=src python scripts/package_demo.py
```

Package output structure:

```text
examples/generated_packages/otel_chatbot_package/
|-- package_manifest.json
|-- fdo_record.json
|-- ro-crate-metadata.json
|-- prov.jsonld
|-- evidence/
|-- bundle/
`-- artifacts/
```

Current M5 limits:

- local FDO-like record only
- no real FDO registry call
- no real PID application or global PID claim
- RO-Crate-like JSON-LD only; no full community certification
- no remote artifact fetch
- no raw prompt, input, output, messages, or completions in package metadata

## M6 Crosswalk Evaluation

M6 turns the local M0-M5 toolchain into reproducible evaluation evidence and
paper-ready assets. The evaluator reads `profile.json`, the evaluation policy,
the corpus manifest, and the crosswalk matrix, then reruns the local validator,
repairer, resolver, importer, and packager paths.

Run the evaluator:

```bash
PYTHONPATH=src python -m asiep_evaluator --profile profiles/asiep/v0.1/profile.json --format json
```

Run the summary demo:

```bash
PYTHONPATH=src python scripts/evaluate_profile_demo.py
```

Generated reports:

```text
reports/
|-- asiep_v0.1_evaluation_report.json
`-- asiep_v0.1_evaluation_summary.md
```

Generated paper assets:

```text
paper_assets/
|-- abstract_draft.md
|-- paper_outline.md
|-- tables/
`-- figures/
```

Current M6 limits:

- local fixtures only
- no real LangSmith API or OpenTelemetry collector
- no FDO registry, PID application, or global PID claim
- crosswalk coverage is a local minimal matrix, not external standard
  certification
- generated paper assets are tables, figures, an outline, and an abstract draft,
  not a full paper

Validator error codes are stable enough for v0.1 tests, but the profile is not
yet a finalized standard.

## Development Boundary

For v0.1, keep changes focused on the evidence profile. Do not add model calls,
deployment automation, commercial demo systems, or a complex multi-agent
runtime. The project should help future agents verify and improve evidence, not
hide accountability inside a larger agent product.
