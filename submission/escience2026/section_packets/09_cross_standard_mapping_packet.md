# Cross-standard Mapping Rewrite Packet

Purpose: position ASIEP relative to trace sources, provenance models, package
metadata, and governance logging.

Target word budget: 330-380 words.

Claims to preserve: C8, C9, C12, C13.

Citations to preserve:
- `w3c_prov_dm`
- `w3c_prov_o`
- `otel_genai_semconv`
- `otel_genai_agent_spans`
- `langsmith_observability_concepts`
- `fdo_architecture_spec`
- `workflow_run_rocrate`
- `process_run_crate`

Repository evidence refs:
- `evaluation/crosswalk/asiep_v0.1_crosswalk.json`
- `mappings/prov_mapping.md`
- `mappings/otel_mapping.md`
- `mappings/fdo_mapping.md`
- `mappings/ro_crate_mapping.md`

Local-only limitations that must remain:
- local minimal crosswalk
- explicit lossiness
- no compliance or certification claim

Overclaim phrases to avoid:
- standard adoption
- external validation
- full conformance
- complete interoperability

Human rewrite checklist:
- [ ] Rewrite in human-authored prose.
- [ ] Preserve all citation keys.
- [ ] Keep lossiness explicit.
- [ ] Remove the section's `AUTHOR_VERIFY` marker only after verification.
