# Deadline Verification

The current eScience CFP deadline row contains an ambiguity that must be
resolved manually before final submission.

Raw CFP line recorded for M12:

> Paper Submissions Due: Monday, May 18, 2026, Tuesday, May 19, 2026 (11:59 PM, anywhere on earth)

The row contains both Monday May 18 and Tuesday May 19 in the same deadline
statement. Human authors must verify the final EasyChair and CFP deadline before
submission.

Current state: `deadline_verified = false`.

## Governance Draft Status

`submission/escience2026/governance_drafts/deadline_verification.draft.json`
records conservative planning and a source-based draft. Conservative deadline
planning is not final deadline verification.

The final gate file `submission/escience2026/deadline_verification.json` must be
created only after a human verifies the live EasyChair/CFP deadline. Until then,
`final_submission_ready` remains false.
