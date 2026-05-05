# Evidence Bundle and Local Packaging Rewrite Packet

Purpose: describe local artifact binding, digest verification, and local
exchange package outputs.

Target word budget: 380-420 words.

Claims to preserve: C2, C3, C12.

Citations to preserve: none required unless human authors cite FDO/RO-Crate
background in this section.

Repository evidence refs:
- `src/asiep_resolver/resolver.py`
- `src/asiep_packager/packager.py`
- `docs/evidence_bundle_resolver.md`
- `docs/fdo_rocrate_packaging.md`
- `interfaces/asiep_package_manifest.schema.json`

Local-only limitations that must remain:
- FDO-like local record
- RO-Crate-like local metadata
- no registry PID
- no full external certification

Overclaim phrases to avoid:
- globally resolvable PID
- full RO-Crate certification
- registered FDO object
- complete tamper-proofing

Human rewrite checklist:
- [ ] Rewrite in human-authored prose.
- [ ] Explain digest verification without overstating cryptographic guarantees.
- [ ] Preserve local-like package boundary.
- [ ] Remove the section's `AUTHOR_VERIFY` marker only after verification.
