# Agent-Native Design

AAEL is designed for agent-to-agent accountability. Human documentation is
useful, but it is not the only source of truth. The first consumer should be an
agent that needs to validate, repair, review, or package an evidence object.

## Machine-First Sources

- `profiles/index.json` is the package-level discovery registry. Agents should
  start there when they do not already know the exact profile path.
- `profiles/asiep/v0.1/profile.json` is the agent entrypoint. It tells an agent
  where the schema, context, state machine, invariants, examples, validator,
  repairer, resolver, importer, and conformance matrix live.
- `schemas/asiep.schema.json` is the structural constraint layer.
- `contexts/asiep.context.jsonld` is the semantic term layer.
- `conformance/asiep_v0.1_matrix.yaml` is the rule index that maps invariants to
  schema fields, validator rules, examples, and cross-standard mappings.
- `src/asiep_validator/validator.py` is the machine referee for the profile.
- `src/asiep_resolver/resolver.py` is the local evidence binding layer. It
  resolves bundle artifacts and recomputes digests without network access.
- `src/asiep_importer/importer.py` is the local trace-to-evidence bridge. It
  imports OTel-like and LangSmith-like fixtures into evidence bundles, then
  reuses the resolver and validator.
- `src/asiep_packager/packager.py` is the local exchange packaging layer. It
  wraps validated bundles as package manifests, FDO-like records,
  RO-Crate-like metadata, and PROV JSON-LD without claiming registry submission.
- `src/asiep_validator/error_codes.py` is the agent repair interface. Stable
  codes and remediation hints let another agent patch an evidence object.
- `profiles/asiep/v0.1/import_policy.json` is the importer boundary. It keeps
  default imports in `ref_only` mode and blocks raw sensitive content.
- `profiles/asiep/v0.1/package_policy.json` is the packaging boundary. It keeps
  M5 local-only and forbids remote fetches, global PID claims, and sensitive
  inline metadata.
- `examples/` is the conformance corpus for positive and adversarial evidence.
- `mappings/` is the cross-standard alignment layer for PROV, OpenTelemetry,
  FDO, and RO-Crate.

## Validator Contract

The text validator output remains compatible with M0 scripts. Agent workflows
should use:

```bash
PYTHONPATH=src python -m asiep_validator <evidence.json> --format json
```

JSON output is the repair contract. Every error includes:

- stable `code`
- `severity`
- human-readable but machine-passable `message`
- `json_path`
- best-effort `invariant_id`
- `remediation_hint`

An agent can use this output to edit the evidence object, rerun the validator,
and hand the result to another review agent.

## Human Docs

Human docs explain the profile. They do not replace the manifest, schema,
JSON-LD context, conformance matrix, validator, examples, or error registry.
When a document disagrees with a machine-readable source, fix the
machine-readable source first and then update the explanation.
