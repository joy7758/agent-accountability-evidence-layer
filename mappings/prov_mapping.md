# PROV-O Mapping

ASIEP can be read as a compact PROV evidence graph.

| ASIEP field | PROV-O concept |
| --- | --- |
| `profile_id` | `prov:Bundle` |
| `subject_agent` | `prov:Agent` |
| `improvement` | `prov:Entity` |
| `lifecycle[].actor` | `prov:wasAssociatedWith` |
| `lifecycle[].at` | `prov:generatedAtTime` |
| `evidence[]` | `prov:Entity` |
| `evidence[].refs` | `prov:wasDerivedFrom` |
| `gates[]` | `prov:Activity` |

v0.1 only documents the mapping. It does not emit RDF.
