| Metric | Value | Numerator | Denominator | Method |
| --- | ---: | ---: | ---: | --- |
| `evidence_completeness` | 1.000 | 20 | 20 | Count required evidence roles and package files in generated valid packages. |
| `cross_standard_coverage` | 0.933 | 84 | 90 | Count non-empty and non-not_applicable mappings across PROV, OTel, LangSmith-like, FDO-like, RO-Crate-like, and governance columns. |
| `gate_reproducibility` | 1.000 | 3 | 3 | Check whether gate decision can be reviewed from gate_report_ref, safety checks, flip counts, and thresholds. |
| `tamper_detection_recall` | 1.000 | 11 | 11 | Count known invalid or attack samples that are rejected by validator, resolver, importer, or packager. |
| `false_positive_rate` | 0.000 | 0 | 8 | Count known valid local fixtures incorrectly rejected by the pipeline. |
| `privacy_policy_compliance` | 1.000 | 2 | 2 | Search generated package metadata for blocked raw-content keys and the synthetic sensitive sentinel. |
| `packaging_closure` | 1.000 | 2 | 2 | Validate generated package closure: manifest, evidence, bundle, artifacts, FDO-like record, RO-Crate-like metadata, and PROV JSON-LD. |
| `agent_readability` | 1.000 | 8 | 8 | Count machine-readable schemas exposed by profile.json for validator, repair, resolver, import, package, and evaluation outputs. |
