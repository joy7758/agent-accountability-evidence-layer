# ASIEP Profile and Lifecycle Rewrite Packet

Purpose: explain ASIEP fields, state machine, invariants, and validator
coverage.

Target word budget: 400-450 words.

Claims to preserve: C1, C3, C4.

Citations to preserve: none required.

Repository evidence refs:
- `schemas/asiep.schema.json`
- `docs/state_machine.md`
- `docs/invariants.md`
- `conformance/asiep_v0.1_matrix.yaml`
- `src/asiep_validator/validator.py`

Local-only limitations that must remain:
- lifecycle is ASIEP v0.1 profile scope
- validator coverage is local implementation coverage

Overclaim phrases to avoid:
- complete formal verification
- externally certified schema
- standard compliance

Human rewrite checklist:
- [ ] Rewrite in human-authored prose.
- [ ] Verify lifecycle terms against `docs/state_machine.md`.
- [ ] Verify invariant claims against `docs/invariants.md`.
- [ ] Remove the section's `AUTHOR_VERIFY` marker only after verification.
