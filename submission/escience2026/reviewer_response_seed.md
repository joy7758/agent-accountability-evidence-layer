# Reviewer Response Seed

## Is this just a JSON schema?

No. The schema is one layer of a repository-local evidence pipeline that
includes validation, repair planning, bundle resolution, digest verification,
trace fixture import, local packaging, evaluation, claim linting, citation
linting, and venue readiness checks.

## Why not just use OpenTelemetry?

OpenTelemetry is a trace source. ASIEP uses OTel-like local fixtures as input
and adds self-improvement evidence semantics: gate decisions, safety checks,
bundle closure, repairability, local packages, and paper evidence.

## Why not just use PROV?

PROV gives provenance entities, activities, and agents. ASIEP maps to PROV but
adds self-improvement-specific invariants, error codes, repair plans, evidence
roles, and local bundle/package validation.

## How is this different from AgentDevel?

AgentDevel is related release-engineering work for self-evolving agents. ASIEP
is complementary: it defines the evidence object and validation layer around a
claimed improvement, not the method that produces the improvement.

## Why only local fixtures?

The v0.1 goal is a reproducible minimal profile and toolchain. Local fixtures
make the pipeline rerunnable and inspectable before adding real external
exports.

## Are the metrics over-optimistic?

They would be if framed as a benchmark. The draft frames them as local
fixture-based regression and reproducibility checks with numerator,
denominator, method, and limitations.

## What does FDO-like mean?

It means ASIEP emits a local machine-readable record inspired by FDO
architecture. It does not claim registry submission, a global PID, or FDO
certification.

## What is the contribution to eScience?

The contribution is reusable scientific infrastructure: a FAIR evidence object
and trace-to-evidence-to-package pipeline for auditable agent
self-improvement.
