# Final Human Checklist

M10 creates a human rewrite package. It is not a submission-ready paper.

## CFP And Policy

- [ ] Verify the current IEEE eScience 2026 CFP page.
- [ ] Resolve the deadline ambiguity: Monday, May 18, 2026 / Tuesday, May 19,
      2026 11:59 PM AoE as shown on CFP.
- [ ] Confirm full paper page limit: 8 pages excluding references.
- [ ] Confirm IEEE 8.5x11 double-column, single-spaced 10-point format.
- [ ] Confirm review mode and repository-link policy for single-blind review.
- [ ] Confirm accepted full paper proceedings policy.

## Human Rewrite

- [ ] Rewrite every section in human-authored prose.
- [ ] Remove every `AUTHOR_VERIFY` marker.
- [ ] Verify all metrics against `reports/asiep_v0.1_evaluation_report.json`.
- [ ] Verify all citations against `references/source_registry.json` and
      `references/asiep_references.bib`.
- [ ] Preserve local fixture, minimal implementation, and no-external-
      certification boundaries.
- [ ] Confirm no unsupported standard adoption, registry, or deployment claim
      remains.

## IEEE AI-use Disclosure

- [ ] Put AI-use disclosure in acknowledgements if AI-generated content remains
      in submitted content.
- [ ] Identify the AI system used.
- [ ] Identify the sections where AI-generated content was used.
- [ ] Briefly describe the level of use.
- [ ] State that human authors are responsible for all submitted content.
- [ ] Do not list AI tools as authors.

## Formatting And Submission

- [ ] Move the human-rewritten text into the IEEE LaTeX scaffold.
- [ ] Compile the LaTeX manuscript locally.
- [ ] Confirm the main text fits within 8 pages excluding references.
- [ ] Decide artifact availability and anonymization wording.
- [ ] Run paper, citation, venue, and submission linters.
- [ ] Manually inspect all generated checklists and readiness reports.

## M11 Final Gates

- [ ] All `AUTHOR_VERIFY` markers removed by human author.
- [ ] All citation keys checked against `references/asiep_references.bib`.
- [ ] All local-only limitations preserved.
- [ ] All evaluation numbers verified against
      `reports/asiep_v0.1_evaluation_report.json`.
- [ ] AI-use disclosure reviewed against IEEE policy.
- [ ] eScience deadline ambiguity manually checked.
- [ ] LaTeX compiled.
- [ ] Page count checked against 8-page limit excluding references.
- [ ] Repository/anonymization decision made.
- [ ] Final lint passed.

## M11-C Full-paper Integration Gates

- [ ] Full manuscript integrated.
- [ ] Citation keys checked.
- [ ] Evaluation numbers checked against
      `reports/asiep_v0.1_evaluation_report.json`.
- [ ] Local-only boundaries preserved.
- [ ] AI-use disclosure checked against IEEE/eScience policy.
- [ ] LaTeX synced.
- [ ] LaTeX compiled.
- [ ] Page count checked against 8 pages excluding references.
- [ ] Deadline ambiguity manually checked.
- [ ] Repository/anonymization decision made.
- [ ] Final author approval completed.
- [ ] `author_final_approval.json` created only after human approval.
- [ ] `final_submission_check.py` passed.

## M12 LaTeX And Final Submission Gates

- [x] LaTeX compiled successfully.
- [x] PDF generated.
- [x] Page count checked.
- [x] Confirmed <= 8 pages excluding references.
- [x] Unresolved citations = 0.
- [x] Unresolved references = 0.
- [ ] Overfull boxes reviewed.
- [ ] License finalized.
- [ ] Sensitive content scan completed and reviewed.
- [ ] Repository/anonymization policy decided.
- [ ] Deadline ambiguity manually resolved.
- [ ] AI-use disclosure reviewed.
- [ ] `author_final_approval.json` created after human approval.
- [ ] `final_submission_check.py` passed.

## M12-G1 Governance Draft Gates

- [x] Deadline verification draft prepared.
- [x] Repository policy draft prepared.
- [x] Author final approval draft prepared.
- [ ] Live EasyChair/CFP deadline verified.
- [ ] Repository/anonymization policy finalized.
- [ ] License finalized.
- [ ] Sensitive content scan completed.
- [ ] Final PDF reviewed.
- [ ] Author final approval signed.
- [ ] `submission/escience2026/deadline_verification.json` created.
- [ ] `submission/escience2026/repository_policy_decision.json` created.
- [ ] `submission/escience2026/author_final_approval.json` created.
- [ ] `final_submission_ready=true`.

## M12-L2R Recommended Final Gate Decisions

- [x] Recommended license decision prepared.
- [x] Recommended repository policy prepared.
- [x] Recommended conservative deadline planning prepared.
- [x] Recommended layout review prepared.
- [x] Recommended sensitive scan classification prepared.
- [x] Recommended AI-use disclosure review prepared.
- [x] Recommended author approval plan prepared.
- [ ] Human reviewed recommended decisions.
- [ ] Human promoted recommended decisions to final gate files.
- [ ] `deadline_verification.json` created.
- [ ] `repository_policy_decision.json` created.
- [ ] `license_decision.json` created.
- [ ] `sensitive_content_review.json` created.
- [ ] `layout_review.json` created.
- [ ] `author_final_approval.json` created.
- [ ] `final_submission_ready=true`.
