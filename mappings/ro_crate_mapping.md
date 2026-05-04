# RO-Crate Mapping

ASIEP can be represented as a research object crate for reproducibility.

| ASIEP field | RO-Crate role |
| --- | --- |
| `profile_id` | crate identifier |
| `evidence[]` | file or contextual entity |
| `references[]` | contextual entity |
| `digest` | integrity metadata |
| `improvement.summary` | description |

v0.1 does not produce `ro-crate-metadata.json`; it records the intended mapping
for later work.
