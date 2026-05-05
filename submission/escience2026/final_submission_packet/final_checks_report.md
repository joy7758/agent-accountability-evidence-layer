# Final Checks Report

Final gate files were created earlier by `scripts/promote_recommended_gates.py` with explicit confirmation flags. A later editorial blocker invalidated that approval because visible table-caption placeholder text was found in the compiled PDF. The placeholder has been removed and the PDF has been rebuilt, but final author approval must be re-confirmed after this editorial fix.

```bash
PYTHONPATH=src python scripts/final_submission_check.py
PYTHONPATH=src python -m asiep_submission_linter --profile profiles/asiep/v0.1/profile.json --stage final --format json
PYTHONPATH=src python -m asiep_paper_linter --profile profiles/asiep/v0.1/profile.json --format json
PYTHONPATH=src python -m asiep_citation_linter --profile profiles/asiep/v0.1/profile.json --format json
PYTHONPATH=src python -m asiep_venue_linter --venue venues/escience2026/venue_policy.json --paper manuscript/paper_v0.4_escience_human_editable.md --format json
```

At the current editorial-fix state, `final_submission_check.py` is expected to fail until re-approval is completed. Passing these checks after re-approval means the repository package is submission-ready. It does not mean the paper has been submitted.
