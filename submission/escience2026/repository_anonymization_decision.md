# Repository And Anonymization Decision Support

Current venue policy records IEEE eScience 2026 as single-blind review. This
file does not make the repository decision; it preserves the options that a
human author must choose before final submission.

## Options

1. Include a public GitHub link in the paper.
2. Include an anonymized artifact package if current author instructions
   require anonymization.
3. Omit the repository link during review and add it later if allowed.

## Risks

- Single-blind review usually permits author identity visibility, but the
  current author instructions still need human verification.
- A repository URL may reveal author identity, commit history, and project
  metadata.
- Omitting the repository may reduce artifact inspectability during review.

## Required Human Decision

Set one of these values in `repository_policy_decision.json` only after human
review:

- `public_repo_allowed`
- `anonymized_required`
- `omit_until_camera_ready`
- `undecided`

Current state: `repository_policy = undecided`.

## Governance Draft Status

`submission/escience2026/governance_drafts/repository_policy_decision.draft.json`
is a prepared policy draft. It is not the final repository decision and must not
be used to pass final submission gates.

The final gate file
`submission/escience2026/repository_policy_decision.json` must be created only
after human review. Until then, `final_submission_ready` remains false.
