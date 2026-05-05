# A FAIR Evidence Object Layer for Auditable Agent Self-Improvement

Draft for human rewrite and verification. This v0.4 file is a human-editable
IEEE eScience 2026 working draft, not a final submission. Every
`AUTHOR_VERIFY` marker must be resolved by human authors before M11.

## Abstract

AUTHOR_VERIFY: Rewrite this abstract in the authors' own prose after checking
the final report in `reports/asiep_v0.1_evaluation_report.json`.

Agent self-improvement claims are hard to reproduce when traces, feedback,
scores, diffs, gate reports, repair decisions, and package metadata are split
across tools. We present ASIEP, the Agent Self-Improvement Evidence Profile,
as a local minimal implementation of a FAIR evidence object layer for
auditable self-improvement events. ASIEP is not a new self-improvement
algorithm; it records a claimed improvement as a machine-readable evidence
object with references, digests, lifecycle states, invariants, validation
errors, repair plans, bundle resolution, and local packaging. The repository
implements a trace-to-evidence-to-package pipeline and evaluates it with local
fixtures, adversarial evidence cases, a cross-standard matrix, and generated
packages. The results are local fixture infrastructure checks, not external
certification, not a deployment claim, and not a general benchmark.

## Introduction

AUTHOR_VERIFY: Rewrite for narrative flow and verify all citations.

Scientific workflows increasingly include LLM agents, trace sources, and
agentic tools that can revise their behavior. When such a system claims that a
revision improved performance, the useful scientific artifact is not only a
conversation log or a dashboard trace. Reviewers need a findable, reusable,
machine-readable evidence object that another agent or human reviewer can
validate, resolve, package, and challenge.

Self-Refine, Reflexion, Voyager, and AgentDevel motivate the broader space of
agent improvement and release-oriented self-evolving systems
[@self_refine_2023; @reflexion_2023; @voyager_2023; @agentdevel_2026]. ASIEP
occupies a different layer. It treats a self-improvement event as evidence to
be inspected, not as an algorithm to produce the improvement. This framing
matches eScience because the main contribution is computational research
infrastructure: a FAIR evidence object, reproducible local pipeline, local
evidence package, reusable validator, and explicit crosswalk to provenance and
package structures.

## Problem and Scope

AUTHOR_VERIFY: Keep the scope narrow. Do not broaden this into general AI
governance.

An agent self-improvement event can involve runtime traces, feedback, scores,
diagnoses, candidate diffs, gate reports, approvals, monitoring records, and
rollback evidence. These artifacts are usually stored in different systems.
That fragmentation makes it hard to reproduce whether a claimed change was
evaluated, whether the gate decision follows the evidence, whether referenced
artifacts still exist, and whether artifact digests still match.

ASIEP v0.1 addresses this as a local fixture and minimal implementation. It
does not call real OpenTelemetry collectors, real LangSmith APIs, or real FDO
registries. It does not register real persistent identifiers. Its RO-Crate and
FDO outputs are local-like exchange metadata. Its privacy checks are local
sentinel checks, not production DLP. It is not external certification.

## Requirements for Agent Self-Improvement Evidence

AUTHOR_VERIFY: Convert these into concise eScience requirements.

The profile is designed around six requirements:

1. Agent-readable discovery through `profiles/asiep/v0.1/profile.json`.
2. Stable schema, invariant, and error-code surfaces for automated review.
3. Evidence-preserving repair plans that do not invent gate reports,
   approvals, external references, or digests.
4. Local evidence bundle resolution that recomputes SHA-256 digests and blocks
   path escape.
5. Trace-to-evidence import from local OTel-like and LangSmith-like fixtures
   without embedding raw prompt, input, or output by default.
6. Local package closure through manifest, FDO-like record, RO-Crate-like
   metadata, and PROV JSON-LD.

## ASIEP Profile and Lifecycle

AUTHOR_VERIFY: Check field names against `schemas/asiep.schema.json` and
`docs/state_machine.md`.

ASIEP records profile identity, cycle metadata, lineage, triggers, actors,
runtime metadata, evidence references, evaluation results, gate decisions,
integrity metadata, compliance fields, and optional rollback evidence. Its
lifecycle moves from draft to candidate, evaluated, gated, promoted or
rejected, and optionally rolled back.

The validator checks JSON Schema conformance, lifecycle ordering, evidence
reference closure, gate report presence, safety regression constraints, flip
threshold constraints, rollback evidence, digest format, and optional local
bundle verification. The invariant and conformance matrix surfaces are
designed so another agent can map a failure to a field, rule, example, test,
and remediation hint.

## Agent-native Toolchain

AUTHOR_VERIFY: Verify every module path and keep the list short enough for an
8-page IEEE paper.

The current repository implements the following local toolchain:

- `asiep_validator`: validates evidence objects and emits agent-readable JSON.
- `asiep_repairer`: converts validator errors into evidence-preserving repair
  plans.
- `asiep_resolver`: resolves local bundle references and verifies digests.
- `asiep_importer`: converts local OTel-like and LangSmith-like fixtures into
  ASIEP bundles.
- `asiep_packager`: emits local exchange packages with package manifest,
  FDO-like record, RO-Crate-like metadata, and PROV JSON-LD.
- `asiep_evaluator`: reruns the local corpus and emits metrics and
  paper-ready tables.
- `asiep_paper_linter`, `asiep_citation_linter`, and venue/submission linters:
  check claim evidence, source mappings, venue fit, and human rewrite gates.

## Evidence Bundle and Local Packaging

AUTHOR_VERIFY: Make clear that local package metadata is a bridge, not a
formal certification claim.

ASIEP uses reference plus digest rather than embedding all raw evidence in the
record. The bundle manifest declares artifact URIs, paths, roles, media types,
and expected digests. The resolver loads the local bundle, checks that paths
remain inside the bundle root, recomputes digests, and reports missing files,
undeclared references, unused declarations, or digest mismatches.

The packager runs resolver and validator first, then emits a local package
containing `package_manifest.json`, `fdo_record.json`,
`ro-crate-metadata.json`, `prov.jsonld`, the evidence record, the bundle
manifest, and copied artifacts. The package is intended for exchange and
revalidation by another agent.

## Evaluation

AUTHOR_VERIFY: Replace any stale metric values with the exact values from the
latest regenerated report before submission.

The M6 evaluator generates `reports/asiep_v0.1_evaluation_report.json`. The
report includes eight metrics: evidence completeness, cross-standard coverage,
gate reproducibility, tamper detection recall, false positive rate, privacy
policy compliance, packaging closure, and agent readability.

The local fixture evaluation reports tamper detection recall of 1.0 for known
adversarial examples and false positive rate of 0.0 for known valid local
fixtures. These are regression-style local corpus measurements. They should
not be presented as open-world security results or benchmark comparisons.

## Cross-standard Mapping

AUTHOR_VERIFY: Confirm all citation keys and lossiness statements.

The local crosswalk maps ASIEP field groups to PROV, OpenTelemetry GenAI-like
trace concepts, LangSmith-like trace concepts, FDO-like records,
RO-Crate-like metadata, and AI governance logging. PROV supplies a
domain-agnostic provenance vocabulary [@w3c_prov_dm; @w3c_prov_o]. OTel and
LangSmith represent trace-source context [@otel_genai_semconv;
@otel_genai_agent_spans; @langsmith_observability_concepts]. FDO and
RO-Crate motivate package and object exchange boundaries
[@fdo_architecture_spec; @workflow_run_rocrate; @process_run_crate].

The matrix records lossiness explicitly. ASIEP does not replace these
standards or tools. It defines the evidence object that sits between trace
capture, provenance semantics, local package exchange, and agent-readable
review.

## Artifacts and Reproducibility

AUTHOR_VERIFY: Replace the repository URL placeholder before submission and
check anonymization requirements.

The repository contains the ASIEP schema, JSON-LD context, invariant docs,
validator, repairer, resolver, importer, packager, evaluator, local examples,
attack corpus, source registry, citation map, and paper assets. The
submission package includes a human authoring protocol, submission manifest,
IEEE-style LaTeX scaffold, artifact availability statement, final human
checklist, and AI-use disclosure draft. Human authors must decide whether the
repository link should be included during single-blind review.

## Limitations

AUTHOR_VERIFY: Preserve all limitations. Do not compress this section below
what reviewers need to assess the evidence.

The implementation is local-fixture only. It does not use real external
services, does not apply for a registry identifier, does not provide
cryptographic signature verification beyond local digests, and does not
include a large-scale benchmark or human-subject evaluation. The privacy check
is intentionally narrow. The package metadata is local-like. The current
paper is a human-editable draft and must be rewritten, checked against the CFP
deadline ambiguity, formatted, compiled, and reviewed before submission.

## Conclusion

AUTHOR_VERIFY: Rewrite with the final contribution framing after page-budget
work.

ASIEP v0.1 demonstrates a local FAIR evidence object layer for auditable agent
self-improvement. Its contribution is not another agent-improvement algorithm.
It is a reproducible evidence pipeline that turns local trace fixtures into
evidence objects, verifies local artifact binding, validates gate decisions,
generates repair plans, packages evidence for exchange, and produces
paper-ready evaluation assets.

## Acknowledgements and AI-use disclosure draft

AUTHOR_VERIFY: This disclosure must appear in the acknowledgements in the
final IEEE-style manuscript if AI-generated content remains in submitted
content.

Codex / OpenAI language-model tools were used for project scaffolding, code
generation assistance, testing support, evidence-map drafting, citation
infrastructure drafting, and preparation of this human-editable manuscript
draft. AI-generated content was used in draft sections including the abstract,
introduction, toolchain summary, evaluation summary, limitation wording, and
submission-support files. The level of use was structural drafting,
summarization of repository artifacts, code scaffolding, and editorial
organization; final claims, citations, formatting, and prose must be verified
and rewritten by human authors. Human authors are responsible for all
submitted content, and AI systems are not authors.
