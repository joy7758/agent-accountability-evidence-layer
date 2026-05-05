# Agent-native Toolchain Rewrite Packet

Purpose: summarize the implemented validator, repairer, resolver, importer,
packager, evaluator, and linting tools.

Target word budget: 450-500 words.

Claims to preserve: C3, C4.

Citations to preserve: none required.

Repository evidence refs:
- `src/asiep_validator`
- `src/asiep_repairer`
- `src/asiep_resolver`
- `src/asiep_importer`
- `src/asiep_packager`
- `src/asiep_evaluator`
- `src/asiep_submission_linter`

Local-only limitations that must remain:
- tools operate on local fixtures and local packages
- no external API, collector, registry, or auto-submission

Overclaim phrases to avoid:
- autonomous deployment
- complete agent framework
- production governance runtime

Human rewrite checklist:
- [ ] Rewrite in human-authored prose.
- [ ] Verify every module path exists.
- [ ] Keep the section compact for page budget.
- [ ] Remove the section's `AUTHOR_VERIFY` marker only after verification.
