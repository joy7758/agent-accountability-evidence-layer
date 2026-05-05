# Limitations

Each limitation is part of the claim accountability layer. It should be cited
when the paper makes a nearby positive claim.

## Local fixtures only

Why acceptable for v0.1: the first goal is a reproducible evidence chain that
can be run in the repository.

Future work: add verified trace exports from real systems after M8 reference
hardening.

## No real external API integration

Why acceptable for v0.1: M4 intentionally uses local OTel-like and
LangSmith-like fixtures to avoid hidden service dependencies.

Future work: add adapters for real exports without changing ASIEP semantics.

## No external FDO registry

Why acceptable for v0.1: M5 tests local package records without making false
registry claims.

Future work: define a policy-gated registry submission path.

## No real PID registration

Why acceptable for v0.1: package records use local identifiers to avoid
pretending that a global registry exists.

Future work: test real identifier workflows with explicit registry metadata.

## No full RO-Crate certification

Why acceptable for v0.1: the package metadata is JSON-LD-like and local, which
is enough to test agent-readable closure.

Future work: validate against community tooling and record which checks pass.

## No production privacy/DLP system

Why acceptable for v0.1: importer and evaluator tests only prove local policy
sentinel behavior.

Future work: integrate redaction policy, DLP scanning, and review logs.

## No cryptographic signature verification beyond current local digest mechanisms

Why acceptable for v0.1: local SHA-256 recomputation is sufficient to catch
missing and tampered bundle artifacts in the fixture corpus.

Future work: add signature verification and key management.

## No large-scale benchmark

Why acceptable for v0.1: metrics are intended as reproducible regression checks,
not broad performance claims.

Future work: build a larger benchmark with external trace exports and harder
attack samples.

## No human-subject evaluation

Why acceptable for v0.1: the contribution is a technical evidence layer, not a
study of user behavior.

Future work: evaluate whether auditors and agent developers can use ASIEP
outputs effectively.

## No proof that ASIEP is complete for all agent systems

Why acceptable for v0.1: ASIEP deliberately focuses on self-improvement
evidence events.

Future work: define additional AAEL profiles or extensions for other agent
accountability surfaces.
