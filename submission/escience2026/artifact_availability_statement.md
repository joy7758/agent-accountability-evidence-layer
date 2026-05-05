# Artifact Availability Statement Draft

AUTHOR_VERIFY: Replace repository URL, archive DOI if any, and anonymization
language before submission.

The ASIEP v0.1 artifacts are planned to be made available as a public
repository containing the profile manifest, schema, JSON-LD context,
validator, repairer, resolver, importer, packager, evaluator, examples,
attack corpus, generated reports, paper assets, and submission-support
metadata.

The artifact supports the local fixture pipeline described in the paper:

```text
trace fixture -> importer -> evidence bundle -> resolver -> validator ->
repairer -> packager -> evaluator -> paper assets
```

The current package is local-only. It does not require network access, does
not call real external APIs, does not apply for external identifiers, and does
not claim external certification. Human authors must decide whether the
repository URL can be included during single-blind review.

Suggested final wording after human verification:

```text
Artifacts for this work are available at <REPOSITORY_OR_ARCHIVE_URL>. The
repository includes the ASIEP profile, local fixtures, validator, repairer,
resolver, importer, packager, evaluator, attack corpus, and generated
evaluation reports. The artifacts are intended to reproduce the local results
reported in this paper and do not constitute external standard certification.
```
