# IEEE eScience 2026 Submission Checklist

This checklist is for human authors preparing a venue-specific draft. It does
not certify that the paper satisfies final venue requirements.

| item | status | notes |
| --- | --- | --- |
| Paper length | draft check | Full paper target is 8 pages, references excluded per M9 brief. Run venue linter and final template count. |
| References | draft check | `references/asiep_references.bib` exists and citation linter is valid. |
| Anonymization status if needed | human check required | Confirm review mode and anonymization policy from current CFP. |
| AI-use disclosure | draft exists | See `author_ai_use_disclosure_draft.md`. Human authors must adapt it to official policy. |
| Local-only limitation | present | Draft states local fixture, minimal implementation, and not external certification boundaries. |
| Citation check | pass in M9 | Run `PYTHONPATH=src python -m asiep_citation_linter --profile profiles/asiep/v0.1/profile.json --format json`. |
| Claim/evidence check | pass in M9 | Run `PYTHONPATH=src python -m asiep_paper_linter --profile profiles/asiep/v0.1/profile.json --format json`. |
| Artifacts availability | local | Repo contains schemas, examples, bundles, generated reports, paper assets, source registry, and venue assets. |
| Repository link policy | human check required | Confirm whether the submission may include a repository URL during review. |
| Camera-ready risks | open | Recheck OTel status, FDO source status, eScience policy, template, and final page budget. |
