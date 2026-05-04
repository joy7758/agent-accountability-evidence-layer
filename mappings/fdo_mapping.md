# FDO Mapping

ASIEP evidence can be packaged as a digital object.

| ASIEP field | FDO-oriented role |
| --- | --- |
| `profile_id` | persistent object identifier candidate |
| `evidence[]` | typed object components |
| `digest` | integrity metadata |
| `references[]` | external object links |
| `profile_version` | profile metadata |

v0.1 does not generate an FDO package. It only defines the minimum fields that a
future package generator would need.
