| Target | Layer | Detected | Error codes | Purpose |
| --- | --- | --- | --- | --- |
| `examples/invalid_missing_gate_report.json` | evidence_example | True | `SCHEMA` | Attack sample for missing gate report evidence. |
| `examples/invalid_promote_with_regression.json` | evidence_example | True | `INV_SAFETY_REGRESSION` | Attack sample for unsafe promote decision with safety regression. |
| `examples/invalid_hash_chain_break.json` | evidence_example | True | `REF_UNRESOLVED` | Attack sample for broken evidence reference closure. |
| `examples/invalid_promote_with_p2f_threshold_violation.json` | evidence_example | True | `INV_FLIP_THRESHOLD` | Attack sample for threshold-violating promote decision. |
| `examples/invalid_transition_order.json` | evidence_example | True | `STATE_TRANSITION` | Attack sample for invalid state transition order. |
| `examples/bundles/invalid_missing_artifact_bundle/bundle.json` | bundle | True | `BUNDLE_ARTIFACT_MISSING` | Attack sample for missing local artifact. |
| `examples/bundles/invalid_digest_mismatch_bundle/bundle.json` | bundle | True | `BUNDLE_DIGEST_MISMATCH` | Attack sample for artifact digest tampering. |
| `examples/bundles/invalid_path_escape_bundle/bundle.json` | bundle | True | `BUNDLE_PATH_ESCAPE` | Attack sample for unsafe path escape. |
| `examples/import_requests/invalid_missing_gate_report_request.json` | import_request | True | `IMPORT_REQUIRED_ROLE_MISSING` | Import attack sample for missing gate report marker. |
| `examples/import_requests/invalid_sensitive_content_request.json` | import_request | True | `IMPORT_SENSITIVE_CONTENT_BLOCKED` | Import attack sample for blocked raw prompt content. |
| `examples/package_requests/invalid_unvalidated_bundle_package_request.json` | package_request | True | `PACKAGE_RESOLVER_FAILED` | Packaging attack sample for unvalidated source bundle. |
