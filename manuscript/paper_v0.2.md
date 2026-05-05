# A FAIR Evidence Layer for Agent-to-Agent Accountability: The Case of Auditable Self-Improvement

## Abstract

Agent-to-agent systems need evidence objects that go beyond traces and
conversational logs. ASIEP v0.1, the Agent Self-Improvement Evidence Profile,
is a minimal profile for self-improvement events. It records trigger, lineage,
evidence references, validation outcomes, gate decisions, integrity fields, and
compliance metadata while keeping raw trace content outside the evidence object
by default. The repository implements an agent-native validator, repairer,
resolver, local trace-fixture importer, local package generator, evaluator, and
paper linter. A local evaluation uses fixtures, adversarial examples, a
crosswalk matrix, generated bundles, and generated packages. The result is a
local, reproducible evidence chain. Its limits are explicit: fixtures are
local, external services are not contacted, persistent identifiers are local
names, and package validation is repository-local rather than external
certification.

## Introduction

Self-improving agent systems create a specific accountability problem. A new
agent version may claim that it improved a workflow, but reviewers need more
than a release note or a trace. They need a compact evidence object that another
agent can parse, check, repair, and package without depending on one agent
framework.

AAEL addresses that problem by separating the accountability evidence layer
from the agent that produced the change. ASIEP v0.1 is the first profile in
that layer. It does not propose a new self-improvement algorithm. It defines the
evidence shape and toolchain needed to review one self-improvement cycle. This
is complementary to work on self-refinement and self-evolving agents such as
Self-Refine, Reflexion, Voyager, and AgentDevel
[@self_refine_2023; @reflexion_2023; @voyager_2023; @agentdevel_2026].

## Problem Statement

Execution traces, feedback records, score files, diffs, gate reports, and
rollback notes are often stored in separate systems. That fragmentation makes
agent-to-agent review brittle. The receiving agent must infer what changed,
which evidence supports the change, whether a gate decision follows the
evidence, and whether artifacts have been tampered with.

The problem is therefore not only trace capture. The missing layer is a
profile-level contract that binds references, digest checks, lifecycle
transitions, repair planning, package metadata, evaluation results, and claim
accountability into one machine-readable review surface.

## Related Work

Self-improvement methods focus primarily on improving agent behavior. For
example, Self-Refine uses iterative self-feedback, Reflexion uses verbal
reinforcement signals, Voyager explores open-ended skill acquisition, and
AgentDevel reframes self-evolving LLM agents as release engineering
[@self_refine_2023; @reflexion_2023; @voyager_2023; @agentdevel_2026].
ASIEP targets a different layer: evidence for reviewing a claimed
self-improvement event.

Observability systems are also adjacent. OpenTelemetry documents GenAI semantic
conventions and agent or framework spans; at the time of access, the GenAI
semantic conventions and operation values such as `create_agent`,
`invoke_agent`, and `execute_tool` were marked Development
[@otel_genai_semconv; @otel_genai_agent_spans]. LangSmith documents trace,
run, and feedback concepts for LLM application observability, but it is product
documentation rather than an open standard
[@langsmith_observability_concepts; @langsmith_feedback_docs]. ASIEP M4 uses
local OTel-like and LangSmith-like fixtures and does not call either external
service.

Provenance and packaging work provide important structure. W3C PROV-DM is a
domain-agnostic provenance model centered on entities, activities, and agents,
while PROV-O maps PROV concepts into an ontology
[@w3c_prov_dm; @w3c_prov_o]. Workflow Run RO-Crate and Process Run Crate
describe run provenance using RO-Crate metadata and process execution
entities [@workflow_run_rocrate; @process_run_crate]. FDO architecture work
motivates machine-actionable digital objects [@fdo_architecture_spec]. ASIEP
uses local PROV JSON-LD, RO-Crate-like metadata, and FDO-like records, with
explicit lossiness and no claim of external registration.

Governance and security sources motivate traceability without making ASIEP a
legal or security solution. EU AI Act Article 12 links high-risk AI system
logging to traceability and post-market monitoring, while Article 72 addresses
post-market monitoring plans [@eu_ai_act_article_12; @eu_ai_act_article_72].
NIST's AI Agent Standards Initiative signals active work on trustworthy,
interoperable, and secure agent ecosystems [@nist_ai_agent_standards]. OWASP
GenAI security guidance and SLSA provenance provide threat and supply-chain
analogies [@owasp_llm_top10; @slsa_provenance_v1_1]. ASIEP uses these as
background, not as proof of legal compliance or security completeness.

## Design Goals

The design is agent-native. A reviewing agent should start from
`profiles/asiep/v0.1/profile.json` and discover the schema, context, state
machine, invariants, validator, repairer, resolver, importer, packager,
evaluator, paper assets, paper linter, source registry, citation map, and
citation linter.

ASIEP also prefers references plus digests over embedded raw content. Evidence
artifacts can remain in a local bundle, while the evidence object records
stable references, roles, and hashes. This keeps the profile smaller and makes
privacy and access-policy decisions explicit. The repository implementation
uses SHA-256 digest recomputation and local bundle closure; it does not provide
cryptographic signature verification or access-control enforcement.

## ASIEP Profile

The ASIEP evidence object records profile identity, cycle identity, lineage,
trigger metadata, actors, runtime metadata, evidence references, safety checks,
flip counts, gate decisions, integrity metadata, and compliance information.
The schema is intentionally narrow for v0.1. It covers auditable
self-improvement cycles rather than every possible agent governance event.

The profile manifest is the primary discovery surface. It points to the JSON
Schema, JSON-LD context, policies, interface schemas, command templates,
examples, mappings, paper claim layer, and citation layer. This makes the
repository usable by agents that need to validate, repair, import, package,
evaluate, lint paper claims, or inspect external citations.

## Lifecycle State Machine and Invariants

ASIEP models a cycle through lifecycle states: draft, candidate, evaluated,
gated, promoted or rejected, and optionally rolled back. The validator checks
that the state sequence, gate evidence, safety evidence, flip thresholds,
rollback evidence, and evidence references remain consistent.

The M1 conformance matrix maps invariants to schema fields, validator rules,
examples, tests, and cross-standard mappings. M6 extends that idea into a
crosswalk matrix and corpus manifest so that invariants can be traced into
evaluation and paper claims.

## Agent-native Toolchain

The validator checks schema, lifecycle, reference closure, gate consistency,
rollback evidence, digest format, and optional local bundle resolution.

The repairer converts validation errors into evidence-preserving repair plans.
It can propose structural patches or reject unsafe promotions, but it does not
forge gate reports, approvals, external references, or digests.

The resolver binds evidence references to local bundle artifacts and recomputes
SHA-256 digests. It detects missing artifacts, digest mismatches, undeclared
references, unused references, and unsafe path escape attempts.

The importer converts local OTel-like and LangSmith-like fixtures into ASIEP
evidence bundles. It uses a reference-only default and blocks sensitive raw
content in the provided attack fixture.

The packager turns resolver-valid and validator-valid bundles into local
exchange packages with a package manifest, local FDO-like record,
RO-Crate-like metadata, and PROV JSON-LD.

The evaluator reruns the local M0-M5 chain, computes metrics, generates a JSON
evaluation report, and emits paper-ready tables and figures.

The paper linter and citation linter extend the same agent-native discipline to
claims. The paper linter checks repository evidence binding. The citation
linter checks source registry consistency, claim-to-citation mapping, BibTeX
coverage, and high-risk overclaim phrases.

## Evaluation

The M6 evaluator uses `evaluation/corpus/asiep_v0.1_corpus.json` and
`evaluation/crosswalk/asiep_v0.1_crosswalk.json`. It generates
`reports/asiep_v0.1_evaluation_report.json` and the tables under
`paper_assets/tables/`.

The current local report contains eight metrics: evidence completeness,
cross-standard coverage, gate reproducibility, tamper detection recall, false
positive rate, privacy policy compliance, packaging closure, and agent
readability. The evaluation is local and fixture-based, so metric values should
be read as reproducible v0.1 checks rather than deployment evidence or a
general benchmark.

## Attack Corpus and Robustness

The local corpus includes missing gate report evidence, unsafe promotion with a
safety regression, unresolved references, threshold-violating promotion,
invalid state order, missing bundle artifacts, digest mismatch, path escape,
missing import roles, blocked sensitive content, and unvalidated package input.

The evaluator reports that the known local attack corpus is detected by the
appropriate layer. This result is useful for regression testing the profile,
but it does not measure robustness against open-ended adversaries. Security
guidance such as OWASP is used here to motivate the need for adversarial
thinking, not to certify ASIEP as a complete defense [@owasp_llm_top10].

## Cross-standard Mapping

The crosswalk matrix maps ASIEP field groups to PROV, OpenTelemetry GenAI-like
trace fields, LangSmith-like trace fields, local FDO-like records,
RO-Crate-like metadata, and AI governance logging concepts. Each row records
lossiness. Some mappings are partial because ASIEP focuses on accountability
evidence across lifecycle, gate, artifact, repair, package, evaluation, and
citation surfaces.

This crosswalk is a local minimal mapping. It is meant to make
interoperability claims inspectable, not to assert conformance to every
external ecosystem. The most important M8 hardening is the boundary language:
OTel and LangSmith are trace sources, PROV is provenance structure, FDO and
RO-Crate are packaging inspirations, and ASIEP is the evidence profile between
them [@otel_genai_semconv; @w3c_prov_dm; @fdo_architecture_spec;
@workflow_run_rocrate].

## Discussion

ASIEP's main design choice is to keep self-improvement accountability outside
the self-improvement algorithm. That makes the profile compatible with multiple
agent runtimes and trace sources. The cost is that ASIEP v0.1 depends on local
fixtures and controlled examples rather than large external corpora.

The claim registry, evidence map, source registry, and citation claim map
extend this accountability discipline to the paper itself. A paper claim is
not accepted just because it is plausible; it must point to repository
evidence, a metric, a paper asset, an external citation, or a limitation. When
a source is only background or partially verified, the claim map records that
status.

## Limitations

The current implementation uses local fixtures only. It does not call external
trace services, registries, or collectors. Its package identifiers are local
names. The privacy check is a policy sentinel and key scan, not a deployment
DLP system. Digest checking is local SHA-256 recomputation, not signature
verification. The corpus is small and synthetic. The profile is not proven
complete for every agent system.

M8 adds citation hardening, but it is still not a final literature review.
Some sources are evolving, including OpenTelemetry GenAI conventions and FDO
architecture documentation. Product documentation such as LangSmith may change.
The source registry records access dates and caveats so future agents can
repeat the verification work.

## Standardization Path

The next research step is to test ASIEP against real trace exports and broader
attack corpora, then stabilize the profile through independent implementation
and interop tests. A standards path should proceed through profile
stabilization, external source rechecking, real import adapters, independent
package review, and clearer mappings to provenance and packaging communities.

NIST's AI Agent Standards Initiative is relevant as a timing signal for
trusted and interoperable agent ecosystems, but the repository does not claim
that ASIEP has been adopted by NIST [@nist_ai_agent_standards].

## Conclusion

ASIEP v0.1 demonstrates a local, agent-readable evidence layer for auditable
self-improvement. The repository links trace fixtures, evidence bundles,
resolver checks, validator decisions, repair plans, package metadata,
evaluation reports, paper claims, and external citation records. The result is
not a new self-improving agent. It is a reviewable evidence contract that
future agents can inspect, recompute, challenge, and cite with explicit
limitations.
