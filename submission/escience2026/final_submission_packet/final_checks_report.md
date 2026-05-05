# Final Checks Report

Final gate files were created by `scripts/promote_recommended_gates.py` with explicit confirmation flags. The repository-side final checks should be rerun before manual EasyChair upload:

```bash
PYTHONPATH=src python scripts/final_submission_check.py
PYTHONPATH=src python -m asiep_submission_linter --profile profiles/asiep/v0.1/profile.json --stage final --format json
PYTHONPATH=src python -m asiep_paper_linter --profile profiles/asiep/v0.1/profile.json --format json
PYTHONPATH=src python -m asiep_citation_linter --profile profiles/asiep/v0.1/profile.json --format json
PYTHONPATH=src python -m asiep_venue_linter --venue venues/escience2026/venue_policy.json --paper manuscript/paper_v0.4_escience_human_editable.md --format json
```

Passing these checks means the repository package is submission-ready. It does not mean the paper has been submitted.
