# ASIEP v0.1 State Machine

ASIEP v0.1 models the lifecycle of a self-improvement claim as evidence, not as
agent runtime behavior.

```text
DRAFT -> CANDIDATE -> EVALUATED -> GATED -> PROMOTED
                                      \-> REJECTED
PROMOTED -> ROLLED_BACK
```

## States

- `DRAFT`: the improvement claim exists but is not yet ready for evaluation.
- `CANDIDATE`: the candidate change and required inputs have been identified.
- `EVALUATED`: evaluation evidence has been produced.
- `GATED`: a gate report has compared evidence against policy.
- `PROMOTED`: the change is accepted for use by the target agent or system.
- `REJECTED`: the gate rejected the change.
- `ROLLED_BACK`: a previously promoted change was rolled back.

## Rules

- The lifecycle must start at `DRAFT`.
- States must move through the allowed transition graph.
- Promotion must pass through `EVALUATED` and `GATED`.
- Rollback is only valid after promotion and requires rollback evidence.
- The state machine describes accountability evidence only; it does not automate
  deployment or agent self-modification.
