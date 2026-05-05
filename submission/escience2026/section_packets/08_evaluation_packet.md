# Evaluation Rewrite Packet

Purpose: report M6 local fixture metrics without generalizing beyond the local
corpus.

Target word budget: 450-500 words.

Claims to preserve: C5, C6, C7, C8, C11.

Citations to preserve: none required for repository-local metrics.

Repository evidence refs:
- `reports/asiep_v0.1_evaluation_report.json`
- `paper_assets/tables/evaluation_metrics.md`
- `paper_assets/tables/attack_corpus_results.md`
- `evaluation/corpus/asiep_v0.1_corpus.json`

Local-only limitations that must remain:
- local fixture evaluation
- known valid/invalid corpus
- not external benchmark
- privacy metric is not DLP

Overclaim phrases to avoid:
- open-world security
- benchmark SOTA
- production privacy
- complete attack coverage

Human rewrite checklist:
- [ ] Rewrite in human-authored prose.
- [ ] Verify all numeric values against the regenerated evaluation report.
- [ ] Keep metric interpretation scoped to local fixtures.
- [ ] Remove the section's `AUTHOR_VERIFY` marker only after verification.
