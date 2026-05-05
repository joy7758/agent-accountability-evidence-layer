# Limitations Rewrite Packet

Purpose: preserve review-defensive limits and prevent overclaiming.

Target word budget: 250-300 words.

Claims to preserve: C10, C11, C12.

Citations to preserve: none required unless human authors add policy context.

Repository evidence refs:
- `manuscript/limitations.md`
- `docs/evaluation_method.md`
- `docs/fdo_rocrate_packaging.md`
- `submission/escience2026/final_human_checklist.md`

Local-only limitations that must remain:
- local fixtures only
- no real OTel collector
- no real LangSmith API
- no real FDO registry or PID registration
- no full RO-Crate certification
- privacy scanning is not DLP
- no large benchmark

Overclaim phrases to avoid:
- complete privacy protection
- legal compliance solution
- complete governance solution

Human rewrite checklist:
- [ ] Rewrite in human-authored prose.
- [ ] Do not weaken or remove limitations.
- [ ] Keep limitations tied to future work rather than apology language.
- [ ] Remove the section's `AUTHOR_VERIFY` marker only after verification.
