# Final Human Checklist

M10 creates a human rewrite package. It is not a submission-ready paper.

## CFP And Policy

- [x] Verify the current IEEE eScience 2026 CFP page.
- [x] Resolve the deadline ambiguity: Monday, May 18, 2026 / Tuesday, May 19,
      2026 11:59 PM AoE as shown on CFP.
- [x] Confirm full paper page limit: 8 pages excluding references.
- [x] Confirm IEEE 8.5x11 double-column, single-spaced 10-point format.
- [x] Confirm review mode and repository-link policy for single-blind review.
- [x] Confirm accepted full paper proceedings policy.

## Human Rewrite

- [x] Rewrite every section in human-authored prose.
- [x] Remove every `AUTHOR_VERIFY` marker.
- [x] Verify all metrics against `reports/asiep_v0.1_evaluation_report.json`.
- [x] Verify all citations against `references/source_registry.json` and
      `references/asiep_references.bib`.
- [x] Preserve local fixture, minimal implementation, and no-external-
      certification boundaries.
- [x] Confirm no unsupported standard adoption, registry, or deployment claim
      remains.

## IEEE AI-use Disclosure

- [x] Put AI-use disclosure in acknowledgements if AI-generated content remains
      in submitted content.
- [x] Identify the AI system used.
- [x] Identify the sections where AI-generated content was used.
- [x] Briefly describe the level of use.
- [x] State that human authors are responsible for all submitted content.
- [x] Do not list AI tools as authors.

## Formatting And Submission

- [x] Move the human-rewritten text into the IEEE LaTeX scaffold.
- [x] Compile the LaTeX manuscript locally.
- [x] Confirm the main text fits within 8 pages excluding references.
- [x] Decide artifact availability and anonymization wording.
- [x] Run paper, citation, venue, and submission linters.
- [x] Manually inspect all generated checklists and readiness reports.

## M11 Final Gates

- [x] All `AUTHOR_VERIFY` markers removed by human author.
- [x] All citation keys checked against `references/asiep_references.bib`.
- [x] All local-only limitations preserved.
- [x] All evaluation numbers verified against
      `reports/asiep_v0.1_evaluation_report.json`.
- [x] AI-use disclosure reviewed against IEEE policy.
- [x] eScience deadline ambiguity manually checked.
- [x] LaTeX compiled.
- [x] Page count checked against 8-page limit excluding references.
- [x] Repository/anonymization decision made.
- [x] Final lint passed.

## M11-C Full-paper Integration Gates

- [x] Full manuscript integrated.
- [x] Citation keys checked.
- [x] Evaluation numbers checked against
      `reports/asiep_v0.1_evaluation_report.json`.
- [x] Local-only boundaries preserved.
- [x] AI-use disclosure checked against IEEE/eScience policy.
- [x] LaTeX synced.
- [x] LaTeX compiled.
- [x] Page count checked against 8 pages excluding references.
- [x] Deadline ambiguity manually checked.
- [x] Repository/anonymization decision made.
- [x] Final author approval completed.
- [x] `author_final_approval.json` created only after human approval.
- [x] `final_submission_check.py` passed.

## M12 LaTeX And Final Submission Gates

- [x] LaTeX compiled successfully.
- [x] PDF generated.
- [x] Page count checked.
- [x] Confirmed <= 8 pages excluding references.
- [x] Unresolved citations = 0.
- [x] Unresolved references = 0.
- [x] Overfull boxes reviewed.
- [x] License finalized.
- [x] Sensitive content scan completed and reviewed.
- [x] Repository/anonymization policy decided.
- [x] Deadline ambiguity manually resolved.
- [x] AI-use disclosure reviewed.
- [x] `author_final_approval.json` created after human approval.
- [x] `final_submission_check.py` passed.

## M12-G1 Governance Draft Gates

- [x] Deadline verification draft prepared.
- [x] Repository policy draft prepared.
- [x] Author final approval draft prepared.
- [x] Live EasyChair/CFP deadline verified.
- [x] Repository/anonymization policy finalized.
- [x] License finalized.
- [x] Sensitive content scan completed.
- [x] Final PDF reviewed.
- [x] Author final approval signed.
- [x] `submission/escience2026/deadline_verification.json` created.
- [x] `submission/escience2026/repository_policy_decision.json` created.
- [x] `submission/escience2026/author_final_approval.json` created.
- [x] `final_submission_ready=true`.

## M12-L2R Recommended Final Gate Decisions

- [x] Recommended license decision prepared.
- [x] Recommended repository policy prepared.
- [x] Recommended conservative deadline planning prepared.
- [x] Recommended layout review prepared.
- [x] Recommended sensitive scan classification prepared.
- [x] Recommended AI-use disclosure review prepared.
- [x] Recommended author approval plan prepared.
- [x] Human reviewed recommended decisions.
- [x] Human promoted recommended decisions to final gate files.
- [x] `deadline_verification.json` created.
- [x] `repository_policy_decision.json` created.
- [x] `license_decision.json` created.
- [x] `sensitive_content_review.json` created.
- [x] `layout_review.json` created.
- [x] `author_final_approval.json` created.
- [x] `final_submission_ready=true`.

## M13 Final Review Packet And Promotion Dry Run

- [x] Final review packet prepared.
- [x] Promotion command preview prepared.
- [x] Promotion dry-run available.
- [x] Promotion command run by human author.
- [x] Final gate files created.
- [x] `final_submission_check.py` passed.
- [x] `final_submission_ready=true`.

## M14-AUTHOR Author Block Fix

- [x] Author identity placeholder removed.
- [x] Author affiliation placeholder removed.
- [x] Author block recompiled into PDF.
- [x] Author identity finally confirmed.
- [x] Institutional affiliation confirmed or Independent Researcher accepted.
- [x] `author_final_approval.json` created.
- [x] `final_submission_check.py` passed.
- [x] `final_submission_ready=true`.

## M14-FINAL Final Gate Promotion

- [x] Promotion script run with explicit confirmation flags.
- [x] Final gate files created by `scripts/promote_recommended_gates.py`.
- [x] Deadline verification final file present.
- [x] Repository policy final file present.
- [x] License decision final file present.
- [x] Sensitive content review final file present.
- [x] Layout review final file present.
- [x] Author final approval final file present.
- [x] `final_submission_check.py` passed.
- [x] Repository package marked `final_submission_ready=true`.
- [ ] EasyChair upload completed.
- [ ] EasyChair submission confirmation saved.
