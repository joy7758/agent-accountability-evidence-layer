# Artifacts and Reproducibility Rewrite Packet

Purpose: tell reviewers how the local artifact package can be found and rerun
after human authors decide repository/anonymization policy.

Target word budget: 180-220 words.

Claims to preserve: C3, C4, C5.

Citations to preserve: none required.

Repository evidence refs:
- `submission/escience2026/artifact_availability_statement.md`
- `scripts/selftest.py`
- `scripts/submission_demo.py`
- `README.md`

Local-only limitations that must remain:
- artifacts reproduce local results only
- no archive DOI unless actually created
- repository link policy requires human review

Overclaim phrases to avoid:
- permanently archived
- certified artifact
- official benchmark

Human rewrite checklist:
- [ ] Rewrite in human-authored prose.
- [ ] Decide repository URL and anonymization language.
- [ ] Do not claim an archive that does not exist.
- [ ] Remove the section's `AUTHOR_VERIFY` marker only after verification.
