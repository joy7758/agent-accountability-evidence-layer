# OpenTelemetry Mapping

ASIEP can be projected into trace-like records without requiring an OTel
runtime.

| ASIEP field | OTel concept |
| --- | --- |
| `profile_id` | trace or resource attribute |
| `lifecycle[]` | ordered span events |
| `lifecycle[].state` | span event name |
| `evidence[].id` | event attribute |
| `gates[].decision` | span status or attribute |
| validator code | event attribute `asiep.validation.code` |

v0.1 avoids an importer or exporter. The mapping exists so future agents can
add one without changing the profile semantics.
