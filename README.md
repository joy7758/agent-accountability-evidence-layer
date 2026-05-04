# Agent Accountability Evidence Layer

AAEL is an implementation-neutral evidence layer for agent accountability.

The first deliverable is ASIEP v0.1:

```text
ASIEP = Agent Self-Improvement Evidence Profile
```

ASIEP v0.1 is intentionally small. It does not build a stronger autonomous
agent, a customer-service system, or an agent framework. It defines the minimum
evidence profile needed for one agent or evaluator to verify a claimed
self-improvement:

- a JSON Schema
- a JSON-LD context
- a lifecycle state machine
- ten invariants
- a local validator
- attack samples
- initial mappings to PROV-O, OpenTelemetry, FDO, and RO-Crate

The design assumption is agent-to-agent accountability: future agents should be
able to inspect, reject, replay, and improve evidence about their own changes
without depending on one vendor runtime.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

PYTHONPATH=src python scripts/selftest.py
PYTHONPATH=src python -m asiep_validator examples/valid_chatbot_improvement.json
PYTHONPATH=src python -m asiep_validator examples/valid_chatbot_improvement.json --format json
```

Expected CLI result for the valid example:

```text
PASS
```

## Validation Layers

The agent-native profile entrypoint is
`profiles/asiep/v0.1/profile.json`. Agents should start there, then load the
schema, JSON-LD context, conformance matrix, examples, and validator entrypoint
listed in the manifest.

The v0.1 validator checks:

- JSON Schema conformance
- lifecycle state transitions
- evidence reference closure
- gate decision consistency with safety checks
- gate decision consistency with flip-count thresholds
- rollback evidence presence
- evidence and reference digest basics

Validator error codes are stable enough for v0.1 tests, but the profile is not
yet a finalized standard.

## Development Boundary

For v0.1, keep changes focused on the evidence profile. Do not add model calls,
deployment automation, commercial demo systems, or a complex multi-agent
runtime. The project should help future agents verify and improve evidence, not
hide accountability inside a larger agent product.
