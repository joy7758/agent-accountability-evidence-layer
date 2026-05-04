# ASIEP Repair Loop

The ASIEP repair loop is an agent-readable diagnosis and planning interface. It
does not modify evidence objects and it does not bypass audit.

## Roles

- The validator is the machine referee. It reports profile, schema, state,
  reference, gate, rollback, and digest failures.
- The error code registry is the agent repair interface. Stable codes give
  another agent a predictable way to classify errors.
- The repair policy is the repair boundary. It says which actions are allowed,
  which actions are forbidden, and which errors require real external evidence.
- The repair plan is the agent-executable plan. It contains JSON Patch
  skeletons, blocked actions, evidence requirements, and revalidation commands.

## Evidence Preservation

The repairer must preserve evidence integrity:

- It must not forge gate reports, approvals, external references, or evidence
  digests.
- It must not change `safety_checks[].regression` from `true` to `false` to
  force a profile to pass.
- It must not raise thresholds or lower flip counts without new evidence.
- It must not generate random hashes.
- It must not modify deployment or production state.

When evidence is missing, the plan can include a TODO placeholder only if the
action is marked `requires_external_evidence=true`. That placeholder is a
request for a real agent or human to provide evidence, not a valid final value.

## Flow

```text
validator --format json
  -> agent-readable error
repairer --format json
  -> evidence-preserving repair plan
agent supplies real evidence or changes unsafe decision to reject
validator --format json
  -> revalidation
review agent checks the resulting evidence object
```

For unsafe promotion, the safe repair path is to change the gate decision to
`reject`, or to require a new evaluation and real gate report before any future
promotion. The repairer never edits the safety result to make promotion pass.

## Commands

```bash
PYTHONPATH=src python -m asiep_validator examples/invalid_promote_with_regression.json --format json
PYTHONPATH=src python -m asiep_repairer examples/invalid_promote_with_regression.json --format json
PYTHONPATH=src python scripts/repair_loop_demo.py
```

After applying any repair plan outside this tool, rerun the validator. A repair
plan is a plan, not proof of conformance.
