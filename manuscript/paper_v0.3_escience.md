# A FAIR Evidence Object Layer for Auditable Agent Self-Improvement

Draft for human authoring and verification. This is a venue-targeted v0.3
draft for IEEE eScience 2026 planning, not a final submission.

## Abstract

Agent self-improvement claims are difficult to reproduce when traces,
feedback, score files, diffs, gate reports, and package metadata remain split
across runtime systems. This draft presents ASIEP, the Agent Self-Improvement
Evidence Profile, as a FAIR evidence object layer for auditable
self-improvement events. ASIEP is not a new self-improvement algorithm. It is a
minimal implementation that turns local trace fixtures into evidence records,
local evidence bundles, resolver-checked artifacts, validator decisions,
repair plans, and local exchange packages. The repository provides an
agent-native toolchain: validator, repairer, resolver, importer, packager,
evaluator, paper linter, citation linter, and venue linter. A local fixture
evaluation reports eight metrics, including local tamper detection recall,
false positive rate over known valid fixtures, packaging closure, and
agent-readability. The results should be read as reproducible local
infrastructure checks, not external certification, not a production deployment,
and not a general benchmark. The contribution for eScience is a trace-to-
evidence-to-package pipeline that makes agent self-improvement evidence
reusable, inspectable, and challengeable by other agents and human reviewers.

## Introduction

Scientific computing increasingly depends on workflow-like AI systems,
instrumented applications, and agentic tools that can revise their own
behavior. When an agent claims that a revision improved a task, a reviewer
needs more than a conversation transcript or a dashboard trace. The reviewer
needs a FAIR evidence object that can be found, parsed, validated, checked for
artifact closure, and reused in later review.

ASIEP addresses this infrastructure gap. It treats agent self-improvement as
an evidence package problem rather than as another self-improvement algorithm.
The target artifact is a reproducible agent evidence pipeline that can be
rerun locally before later external integrations.
Self-Refine, Reflexion, Voyager, and AgentDevel motivate the broader space of
agent improvement and self-evolving systems [@self_refine_2023;
@reflexion_2023; @voyager_2023; @agentdevel_2026]. ASIEP instead asks how one
claimed improvement can be recorded as a local, minimal implementation that
another agent can validate, repair, resolve, package, evaluate, and cite.

This framing fits eScience because the contribution is computational research
infrastructure: a reusable validator and corpus, a reproducible agent evidence
pipeline, a local evidence package path, local provenance and package metadata,
and explicit links to FAIR, PROV, RO-Crate-like, FDO-like, and trace-source
concepts.

## Problem and Scope

Agent self-improvement events combine several evidence types: runtime traces,
feedback, scores, diagnoses, candidate diffs, gate reports, approvals,
monitoring records, and rollback evidence. These artifacts are often stored in
separate tools. A receiving reviewer must reconstruct what changed, which
artifact supports the change, whether a gate decision follows the evidence,
and whether an artifact changed after the claim was made.

ASIEP v0.1 scopes this problem narrowly. It covers local, auditable
self-improvement evidence for one improvement cycle. It does not claim real
OpenTelemetry collector integration, real LangSmith API integration, a real
FDO registry, a global PID, full RO-Crate certification, production-ready
governance, complete privacy protection, or benchmark SOTA. It is a local
fixture and minimal implementation for testing the evidence object layer.

## Requirements for Agent Self-Improvement Evidence

A useful self-improvement evidence object should satisfy five infrastructure
requirements.

First, it should be agent-readable. Another agent should be able to discover
the profile manifest, schemas, policies, tools, examples, and reports from a
single entrypoint.

Second, it should preserve evidence. A repair loop should not forge gate
reports, approvals, external references, or digests. Unsafe promotion should
be repaired toward reject or real reevaluation, not toward falsifying safety
evidence.

Third, it should bind references to artifacts. A URI and digest string are not
enough unless a local evidence bundle can resolve the path, recompute the
hash, and reject path escape.

Fourth, it should support reproducibility. The same corpus should drive
validator, repairer, resolver, importer, packager, evaluator, paper linter,
citation linter, and venue linter checks.

Fifth, it should remain honest about mappings. PROV, OpenTelemetry GenAI,
LangSmith, FDO, and RO-Crate provide useful surrounding structures, but ASIEP
must record lossiness instead of claiming complete conformance
[@otel_genai_semconv; @otel_genai_agent_spans; @langsmith_observability_concepts;
@w3c_prov_dm; @w3c_prov_o; @fdo_architecture_spec; @workflow_run_rocrate;
@process_run_crate].

## ASIEP Profile and Lifecycle

ASIEP records the profile identity, self-improvement cycle, lineage,
trigger, actors, runtime metadata, evidence references, evaluation results,
gate decisions, integrity metadata, and compliance fields. Its lifecycle moves
from draft to candidate, evaluated, gated, promoted or rejected, and optionally
rolled back.

The validator checks JSON Schema conformance, lifecycle state order, evidence
reference closure, gate report presence, safety-regression constraints,
flip-count thresholds, rollback evidence, and digest format. M3 adds optional
bundle-root digest verification through the local resolver. M8 and M9 extend
the same accountability idea to paper and venue claims: a claim must be linked
to repository evidence, a metric, a citation source, or a limitation.

## Agent-native Toolchain

The ASIEP repository is designed so another agent can start at
`profiles/asiep/v0.1/profile.json` and discover each interface. The validator
returns stable error codes and agent-readable JSON. The repairer converts those
errors into evidence-preserving repair plans. The resolver checks local bundle
closure and SHA-256 digests. The importer maps local OTel-like and
LangSmith-like fixtures into ASIEP bundles without embedding raw prompt,
input, or output by default. The packager emits a package manifest, local
FDO-like record, RO-Crate-like metadata, and PROV JSON-LD. The evaluator
reruns the local M0-M5 chain and emits paper-ready metrics.

M7 and M8 add claim accountability. The paper linter checks that claims in the
draft map to repository evidence. The citation linter checks that external
claims map to a source registry, citation claim map, and BibTeX. M9 adds the
venue linter, which checks whether a venue-targeted draft preserves required
sections, local-only limitations, citation coverage, AI-use disclosure, and
page-budget risk.

## Evidence Bundle and Local Packaging

ASIEP follows a reference plus digest design. Evidence records refer to
artifacts in a local bundle rather than embedding all raw traces. The bundle
manifest declares artifact URIs, local paths, roles, media types, and expected
digests. The resolver rejects missing artifacts, digest mismatches, undeclared
references, unused declarations, and path escape attempts.

Packaging turns a resolver-valid and validator-valid bundle into a local
exchange package. The package contains `package_manifest.json`,
`fdo_record.json`, `ro-crate-metadata.json`, `prov.jsonld`, the evidence
record, the bundle manifest, and copied artifacts. The FDO output is FDO-like
and local. The RO-Crate output is RO-Crate-like metadata. The package is not
external certification and does not claim a registry PID.

## Evaluation

The M6 evaluator reads `evaluation/corpus/asiep_v0.1_corpus.json` and
`evaluation/crosswalk/asiep_v0.1_crosswalk.json`, then generates
`reports/asiep_v0.1_evaluation_report.json` and paper tables. The report
contains eight metrics: evidence completeness, cross-standard coverage, gate
reproducibility, tamper detection recall, false positive rate, privacy policy
compliance, packaging closure, and agent readability.

The local fixture result reports tamper detection recall of 1.0 for the known
attack corpus and false positive rate of 0.0 for known valid local fixtures.
These are local corpus results. They are useful for regression and
reproducibility, but they do not measure open-world security or deployment
performance. The privacy metric is also narrow: it checks local sentinel and
key patterns, not a production DLP system. OWASP guidance is used only as
security background for why adversarial evidence cases matter
[@owasp_llm_top10].

## Cross-standard Mapping

ASIEP uses a local crosswalk matrix to map core field groups to PROV,
OpenTelemetry GenAI-like trace concepts, LangSmith-like trace concepts,
FDO-like records, RO-Crate-like metadata, and AI governance logging. The
matrix records lossiness. The goal is not to replace PROV, OTel, LangSmith,
FDO, or RO-Crate. The goal is to locate ASIEP as an evidence object layer
between trace capture, provenance semantics, package exchange, and agent
review.

Governance sources also motivate the traceability problem. EU AI Act Article
12 links high-risk AI system logging to traceability and post-market
monitoring, while Article 72 addresses post-market monitoring
[@eu_ai_act_article_12; @eu_ai_act_article_72]. NIST's AI Agent Standards
Initiative is a timing signal for trustworthy and interoperable agents, not
evidence of ASIEP adoption [@nist_ai_agent_standards]. SLSA provenance
provides a software supply-chain analogy for artifact provenance
[@slsa_provenance_v1_1].

## Limitations

This draft preserves the main M0-M8 limits. The implementation is local
fixture only. It does not call real external APIs, real OTel collectors, real
LangSmith APIs, or real FDO registries. It does not register a real PID. It
does not provide full RO-Crate certification, legal compliance, production
privacy/DLP, cryptographic signature verification, a large benchmark, or a
human-subject evaluation. The FDO source in the M8 registry is partially
verified and should be rechecked by human authors before final submission.

The paper draft is also not final. IEEE eScience policy details, page limits,
templates, and AI-use rules must be verified by human authors against the
current CFP and author instructions before submission.

## Conclusion

ASIEP v0.1 demonstrates a local FAIR evidence object layer for auditable agent
self-improvement. It connects local trace fixtures, evidence bundles, digest
resolution, validator decisions, repair planning, package metadata, evaluation
reports, paper claims, external citations, and venue readiness checks. For
eScience, the contribution is not a stronger agent and not a governance
whitepaper. It is reusable scientific infrastructure for making agent
self-improvement evidence reproducible, inspectable, and challengeable.

## Acknowledgements and AI-use disclosure draft

Draft for human authoring and verification. Codex and other AI tools were used
for scaffolding, code generation, testing support, and draft preparation.
Human authors must verify and rewrite final prose, confirm all citations and
venue requirements, and remain responsible for all content. AI tools must not
be listed as authors.
