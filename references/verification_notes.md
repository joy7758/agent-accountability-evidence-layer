# M8 Verification Notes

M8 verifies external citation infrastructure for `manuscript/paper_v0.2.md`.
It does not make the paper final and does not claim external certification.

## What Was Verified

- Primary arXiv pages for Self-Refine, Reflexion, Voyager, and AgentDevel.
- OpenTelemetry GenAI semantic conventions and GenAI agent/framework span pages,
  including Development status at access time.
- LangSmith product documentation for observability concepts and feedback.
- W3C PROV-DM and PROV-O W3C Recommendation pages.
- Workflow Run RO-Crate paper and Process Run Crate profile documentation.
- FDO architecture documentation as a local FDO-like comparison source.
- EU AI Act Service Desk pages for Article 12 and Article 72.
- NIST AI Agent Standards Initiative page.
- OWASP GenAI security guidance and SLSA provenance specification.

## Primary Sources

- `self_refine_2023`, `reflexion_2023`, `voyager_2023`, `agentdevel_2026`
- `w3c_prov_dm`, `w3c_prov_o`
- `workflow_run_rocrate`

## Canonical Or Official Sources

- `otel_genai_semconv`, `otel_genai_agent_spans`
- `langsmith_observability_concepts`, `langsmith_feedback_docs`
- `process_run_crate`, `fdo_architecture_spec`
- `nist_ai_agent_standards`
- `eu_ai_act_article_12`, `eu_ai_act_article_72`
- `owasp_llm_top10`, `slsa_provenance_v1_1`

## What Remains Unverified

No source used as a ready citation in `paper_v0.2.md` is marked
`unverified` in `references/source_registry.json`. Remaining gaps are
documented in `references/verification_gaps.md` because several sources are
evolving or require closer review before a venue-specific submission.

## Claims Downgraded

- OTel language is limited to "OTel-like local fixtures" and Development
  status is stated.
- LangSmith language is limited to "LangSmith-like local fixtures" and product
  documentation status is stated.
- FDO language is limited to local FDO-like records and local identifiers.
- RO-Crate language is limited to RO-Crate-like metadata, not external
  certification.
- Evaluation metrics are described as local fixture results, not benchmark
  claims.

## Citation Gaps

There are no known `citation_required` markers left in `paper_v0.2.md`.
Potential future citations are tracked as verification gaps rather than being
used as ready claims.

## Why No External Certification Is Claimed

The repository does not call a real FDO registry, does not request or resolve a
global PID, does not run a community RO-Crate validator, does not call a real
OpenTelemetry collector, and does not call the LangSmith API. M5 and M8 are
local, agent-readable hardening layers.

## How To Update Sources

1. Update `references/source_registry.json` with stable `source_id` and
   `citation_key` values.
2. Update `references/asiep_references.bib` with matching BibTeX keys.
3. Update `references/citation_claim_map.json` for affected claims.
4. Rerun:

```bash
PYTHONPATH=src python -m asiep_citation_linter --profile profiles/asiep/v0.1/profile.json --format json
PYTHONPATH=src python scripts/citation_demo.py
```
