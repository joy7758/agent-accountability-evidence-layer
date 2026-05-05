# FAIR/FDO and RO-Crate Packaging

M5 packages a resolver-valid and validator-valid ASIEP evidence bundle into a
local, agent-readable exchange package. The package is meant for other agents to
discover, inspect, revalidate, and map across standards.

An ASIEP bundle binds evidence refs to local artifacts and digests. An ASIEP
package wraps that verified bundle with:

- `package_manifest.json`
- `fdo_record.json`
- `ro-crate-metadata.json`
- `prov.jsonld`
- `evidence/evidence.json`
- `bundle/bundle.json`
- `artifacts/*`

## FDO-like Boundary

`fdo_record.json` is a local FDO-like record for M5. It uses `local_pid` values
such as `urn:asiep:fdo:package:otel-chatbot-001`. It is not a global PID, is not
registered, and is not claimed to be globally resolvable.

## RO-Crate-like Boundary

`ro-crate-metadata.json` is a small JSON-LD-like graph that links the package
dataset, evidence record, bundle manifest, artifacts, profile conformance, and
packaging action. It does not claim full RO-Crate certification.

## PROV JSON-LD

`prov.jsonld` expresses the ASIEP self-improvement cycle, subject agent, base and
candidate blueprint entities, evidence entities, and package generation activity
using a minimal PROV JSON-LD shape.

## Validation Order

The packager must run local resolver checks before validator checks:

```bash
PYTHONPATH=src python -m asiep_resolver <bundle.json> --format json
PYTHONPATH=src python -m asiep_validator <evidence.json> --bundle-root <bundle-root> --format json
```

Packaging stops if either precondition fails. The packager does not modify the
input evidence object or rewrite digests to force a pass.

## Usage

Prepare generated bundles from local fixtures:

```bash
PYTHONPATH=src python scripts/import_trace_demo.py
```

Package a generated bundle:

```bash
PYTHONPATH=src python -m asiep_packager examples/package_requests/otel_chatbot_package_request.json --format json
```

Run the package demo:

```bash
PYTHONPATH=src python scripts/package_demo.py
```

## Current Limits

M5 is local-only. It does not call a real FDO registry, request a real PID,
perform remote artifact fetch, validate against the full RO-Crate community
profile, call LangSmith, call an OTel collector, or use a model.
