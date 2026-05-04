# ASIEP v0.1 Invariants

ASIEP v0.1 keeps ten invariants. They are designed for machine validation and
future agent-to-agent review.

| ID | Invariant | Primary enforcement |
| --- | --- | --- |
| INV-001 | A profile must conform to `schemas/asiep.schema.json`. | JSON Schema and validator `SCHEMA` |
| INV-002 | Lifecycle must start at `DRAFT`. | validator `STATE_TRANSITION` |
| INV-003 | Lifecycle transitions must follow `docs/state_machine.md`. | validator `STATE_TRANSITION` |
| INV-004 | Every evidence reference used by lifecycle events, evidence links, safety checks, flip counts, gates, or rollback must resolve to an item in `evidence`. | validator `REF_UNRESOLVED` |
| INV-005 | Every gate must include a `gate_report_ref`. | schema required field |
| INV-006 | `promote` is forbidden when any safety check records a regression. | validator `INV_SAFETY_REGRESSION` |
| INV-007 | `promote` is forbidden when any p2-or-higher safety check fails. | validator `INV_SAFETY_REGRESSION` |
| INV-008 | `promote` is forbidden when a flip-count metric exceeds its threshold. | validator `INV_FLIP_THRESHOLD` |
| INV-009 | Rollback state or rollback gate decision requires rollback evidence. | validator `ROLLBACK_EVIDENCE` |
| INV-010 | Evidence and external references must carry a basic SHA-256 digest. | schema-required digest fields and validator `DIGEST_BASIC` |

## Notes

- The validator returns the first failing invariant layer to keep negative
  examples stable and easy for agents to interpret.
- Digest checks in v0.1 are basic format checks. The schema requires digest
  fields; the validator checks `sha256` and 64-character hex values. It does not
  fetch remote content or recompute hashes.
- The profile is implementation-neutral. It should be usable by future agents
  reviewing evidence from many runtimes.
