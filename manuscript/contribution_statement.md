# Contribution Statement

## Contribution 1

Defines ASIEP as a minimal evidence profile for agent self-improvement events.

- claim_ids: C1, C2
- supporting artifacts: `schemas/asiep.schema.json`, `profiles/asiep/v0.1/profile.json`, `docs/invariants.md`
- limitations: focused on self-improvement evidence events, not all agent governance events

## Contribution 2

Implements an agent-native conformance toolchain: validator, repairer,
resolver, importer, packager, evaluator.

- claim_ids: C3, C4, C5
- supporting artifacts: `src/asiep_validator/`, `src/asiep_repairer/`, `src/asiep_resolver/`, `src/asiep_importer/`, `src/asiep_packager/`, `src/asiep_evaluator/`
- limitations: local examples and fixtures only

## Contribution 3

Provides cross-standard mappings to PROV, OTel-like traces, LangSmith-like
traces, FDO-like records, and RO-Crate-like metadata.

- claim_ids: C8, C9
- supporting artifacts: `evaluation/crosswalk/asiep_v0.1_crosswalk.json`, `mappings/`, `paper_assets/tables/crosswalk_matrix.md`
- limitations: local minimal mapping, not external conformance testing

## Contribution 4

Evaluates ASIEP using local valid fixtures, adversarial evidence cases,
bundle/package verification, and paper-ready metrics.

- claim_ids: C5, C6, C7
- supporting artifacts: `evaluation/corpus/asiep_v0.1_corpus.json`, `reports/asiep_v0.1_evaluation_report.json`, `paper_assets/tables/evaluation_metrics.md`, `paper_assets/tables/attack_corpus_results.md`
- limitations: small synthetic corpus and no broad benchmark
