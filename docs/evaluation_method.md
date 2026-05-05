# M6 Evaluation Method

M6 stops adding runtime features and turns the implemented M0-M5 chain into a
machine-readable evidence layer for review and paper preparation. The goal is
not to claim external certification. The goal is to let another agent rerun the
local corpus, inspect cross-standard coverage, compare metrics, and cite the
generated paper assets.

## Agent Entry Points

`profiles/asiep/v0.1/profile.json` remains the primary agent entry point. It now
indexes:

- `profiles/asiep/v0.1/evaluation_policy.json`
- `interfaces/asiep_evaluation_report.schema.json`
- `interfaces/asiep_crosswalk_matrix.schema.json`
- `interfaces/asiep_corpus_manifest.schema.json`
- `evaluation/crosswalk/asiep_v0.1_crosswalk.json`
- `evaluation/corpus/asiep_v0.1_corpus.json`
- `paper_assets/`
- the `asiep_evaluator` CLI entrypoint

Human-readable documents explain the method, but the machine-readable policy,
schemas, corpus, matrix, and generated report are the review surface.

## Evaluation Report

`reports/asiep_v0.1_evaluation_report.json` is constrained by
`interfaces/asiep_evaluation_report.schema.json`. It records evaluated
components, corpus coverage, pipeline results, metrics, attack corpus results,
crosswalk coverage, generated paper assets, limitations, and revalidation
commands.

The report is generated with:

```bash
PYTHONPATH=src python -m asiep_evaluator --profile profiles/asiep/v0.1/profile.json --format json
```

The summary wrapper is:

```bash
PYTHONPATH=src python scripts/evaluate_profile_demo.py
```

## Crosswalk Matrix

`evaluation/crosswalk/asiep_v0.1_crosswalk.json` maps ASIEP field groups to:

- PROV
- OpenTelemetry GenAI
- LangSmith-like Trace
- FDO-like Record
- RO-Crate-like Metadata
- AI Governance Logging

Each row includes invariant IDs, validator rules, error codes, mapping columns,
lossiness, and notes. The matrix is intentionally honest about partial or
high-loss mappings. It does not claim complete OpenTelemetry, LangSmith, FDO, or
RO-Crate implementation.

## Corpus Manifest

`evaluation/corpus/asiep_v0.1_corpus.json` describes the local evaluation
corpus. It covers valid evidence examples, invalid evidence examples, bundle
attacks, import attacks, package attacks, repair cases, and generated package
closure checks.

Each expected result includes the target path, target type, command,
expected validity, expected error codes, purpose, related invariant IDs, and
related metric IDs.

## Metrics

The evaluator computes these minimum metrics:

- `evidence_completeness`: required evidence roles and package files present in
  generated valid packages.
- `cross_standard_coverage`: mapped cells across the local crosswalk matrix.
- `gate_reproducibility`: whether local promote decisions can be reviewed from
  gate report refs, safety checks, flip counts, and thresholds.
- `tamper_detection_recall`: known invalid or attack samples rejected by the
  correct M0-M5 layer.
- `false_positive_rate`: known valid local fixtures incorrectly rejected.
- `privacy_policy_compliance`: generated package metadata avoids blocked raw
  prompt/input/output keys and the synthetic sensitive sentinel.
- `packaging_closure`: generated packages include the package manifest, evidence,
  bundle, artifacts, FDO-like record, RO-Crate-like metadata, and PROV JSON-LD.
- `agent_readability`: profile manifest exposes schemas for validator, repair,
  resolver, import, package, and evaluation outputs.

Each metric reports numerator, denominator, value, method, interpretation, and
limitations so another agent can compare future runs.

## Paper Assets

The evaluator generates:

- `paper_assets/tables/crosswalk_matrix.md`
- `paper_assets/tables/evaluation_metrics.md`
- `paper_assets/tables/attack_corpus_results.md`
- `paper_assets/figures/pipeline_flow.mmd`
- `paper_assets/figures/state_machine.mmd`
- `paper_assets/paper_outline.md`
- `paper_assets/abstract_draft.md`

These are inputs for Paper v0.1, not a complete paper.

## Current Limits

- Local fixtures only.
- No network access, external APIs, collectors, registries, or real PID
  registration.
- No large-model calls.
- No complete external standards certification.
- Metrics are computed over the repository corpus rather than production traces.
- Privacy checks are policy sentinels and key scans, not a full DLP classifier.
