# Evidence Bundle Resolver

ASIEP uses references, summaries, and digests instead of embedding all raw
evidence inside the profile. The profile should stay compact enough for agents
to validate, repair, and review, while the local bundle carries concrete
artifacts such as traces, feedback, scores, diagnosis notes, diffs, and gate
reports.

## Purpose

The bundle resolver binds an ASIEP evidence record to a local evidence package:

- read `bundle.json`
- validate it against `interfaces/asiep_evidence_bundle.schema.json`
- load the ASIEP evidence record declared by `evidence_record_path`
- match `evidence[].uri` values to `artifacts[].uri`
- keep all artifact paths inside `bundle_root`
- check that artifact files exist
- recompute SHA-256 digests
- compare expected and actual digests
- emit `interfaces/asiep_bundle_resolution.schema.json`

The resolver is local only. It does not fetch remote URIs, call models, or
modify evidence records.

## Resolver And Validator

The resolver answers whether a local bundle binds correctly to a record. The
validator answers whether the ASIEP record conforms to the profile. M3 connects
them with `--bundle-root`:

```bash
PYTHONPATH=src python -m asiep_resolver examples/bundles/valid_chatbot_bundle/bundle.json --format json
PYTHONPATH=src python -m asiep_validator examples/bundles/valid_chatbot_bundle/evidence.json --bundle-root examples/bundles/valid_chatbot_bundle --format json
```

Without `--bundle-root`, validator behavior remains the M2 behavior.

## Digest Mismatch

Digest mismatch means the artifact bytes do not match the expected digest in
the evidence record and bundle manifest. Do not automatically replace the
expected digest with the actual digest. First decide which source is
authoritative:

- the artifact may be the wrong version
- the evidence record may point to stale evidence
- the bundle manifest may have been edited incorrectly

Only update digest metadata after an agent or human verifies the artifact
version.

## Path Escape

Artifact paths are bundle-relative. The resolver rejects paths that escape
`bundle_root`, such as `../secret.txt`, and does not read the external file.
This prevents a bundle from smuggling unrelated local files into the evidence
set.

## Current Limits

- no network resolution
- no remote URI fetching
- no OTel, LangSmith, FDO, or RO-Crate import/export
- no automatic evidence mutation
- no automatic digest repair
- no access-control enforcement beyond local policy metadata
