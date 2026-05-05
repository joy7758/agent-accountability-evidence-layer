# Manuscript Assets

This directory contains Paper v0.1 and the claim accountability layer for ASIEP
v0.1. The draft is intentionally evidence-bounded: claims are registered in
`claims_registry.json`, mapped to sections and paper assets in
`evidence_map.json`, and linted by `asiep_paper_linter`.

Run:

```bash
PYTHONPATH=src python -m asiep_paper_linter --profile profiles/asiep/v0.1/profile.json --format json
PYTHONPATH=src python scripts/paper_demo.py
```

M7 does not add new ASIEP runtime modules. It prepares the first paper draft and
keeps every core claim tied to local repository evidence.
