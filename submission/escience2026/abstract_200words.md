# 200-word Abstract Draft

Agent self-improvement claims are difficult to reproduce when traces,
feedback, scores, diffs, gate reports, and package metadata remain split
across runtime systems. This draft presents ASIEP, the Agent Self-Improvement
Evidence Profile, as a FAIR evidence object layer for auditable
self-improvement events. ASIEP is not a new self-improvement algorithm. It is a
minimal implementation that turns local trace fixtures into evidence records,
local evidence bundles, resolver-checked artifacts, validator decisions,
repair plans, and local exchange packages. The repository provides an
agent-native toolchain: validator, repairer, resolver, importer, packager,
evaluator, paper linter, citation linter, and venue linter. A local fixture
evaluation reports eight metrics, including local tamper detection recall,
false positive rate over known valid fixtures, packaging closure, and
agent-readability. Results are reproducible local infrastructure checks, not
external certification, production deployment, or general benchmark evidence.
The contribution for eScience is a trace-to-evidence-to-package pipeline that
makes agent self-improvement evidence reusable, inspectable, and challengeable
by other agents and human reviewers.
