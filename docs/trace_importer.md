# Trace Importer

M4 adds a local trace-to-ASIEP importer. OTel-like and LangSmith-like fixtures are
trace sources; they are not substitutes for ASIEP. The importer maps local trace
runs, role markers, feedback, score, candidate diff, and gate report evidence
into an ASIEP evidence bundle that can be resolved and validated.

The machine-readable entrypoints are:

- `profiles/asiep/v0.1/profile.json`
- `profiles/asiep/v0.1/import_policy.json`
- `interfaces/asiep_import_request.schema.json`
- `interfaces/asiep_import_result.schema.json`
- `interfaces/otel_genai_trace_fixture.schema.json`
- `interfaces/langsmith_trace_fixture.schema.json`

Run an import:

```bash
PYTHONPATH=src python -m asiep_importer examples/import_requests/otel_chatbot_request.json --format json
```

Run the demo:

```bash
PYTHONPATH=src python scripts/import_trace_demo.py
```

## Import Boundaries

The importer is local-only. It does not call the LangSmith API, does not connect
to an OpenTelemetry collector, does not use a model, and does not fetch remote
URIs. It reads a fixture, writes a bundle, then reuses the local resolver and
validator.

The default content mode is `ref_only`. Raw prompts, raw user inputs, raw model
outputs, message bodies, and completions are blocked by default when
`fail_on_sensitive_content` is true. Evidence records contain artifact URIs and
digests, not raw sensitive conversation content.

The importer does not fabricate evidence. If a request requires a gate report,
candidate diff, feedback, or score and the source fixture does not contain the
corresponding role, import fails with `IMPORT_REQUIRED_ROLE_MISSING`. If a source
contains blocked raw content, import fails with
`IMPORT_SENSITIVE_CONTENT_BLOCKED`.

## Revalidation

A successful import writes:

- `evidence.json`
- `bundle.json`
- `artifacts/trace.json`
- `artifacts/feedback.json`
- `artifacts/score.json`
- `artifacts/candidate.diff`
- `artifacts/gate_report.json`
- optional `artifacts/diagnosis.md`

Each artifact is a real local file, and each digest is computed from the bytes
that were written. After generation, the importer runs the same checks another
agent should run:

```bash
PYTHONPATH=src python -m asiep_resolver examples/generated_bundles/otel_chatbot_bundle/bundle.json --format json
PYTHONPATH=src python -m asiep_validator examples/generated_bundles/otel_chatbot_bundle/evidence.json --bundle-root examples/generated_bundles/otel_chatbot_bundle --format json
```

## Current Limits

M4 intentionally covers only local fixtures. It does not implement real OTel
semantic conventions end to end, LangSmith API reads, external storage, FDO
packaging, RO-Crate export, or complex agent demos.
