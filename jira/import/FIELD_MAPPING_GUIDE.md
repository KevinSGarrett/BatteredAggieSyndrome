# Field Mapping Guide

| CSV column | Destination | Required handling |
|---|---|---|
| Issue type | Jira issue/work type | Map Epic, Story, Task, and Sub-task to existing destination types. |
| Issue ID | External import identity | Preserve unique numeric values during the hierarchy import. |
| Parent | Parent | Map to Parent; values are parent Issue IDs in the ordered single-file import. |
| Summary | Summary | Required. |
| Description | Description | Multiline Markdown-like text; verify rendering after test import. |
| Status | Status | Map portable defaults to existing workflow statuses. |
| Priority | Priority | Map to existing target priorities. |
| Labels | Labels | Multi-value mapping; keep controlled vocabulary. |
| Component | Component/s | Pre-create or map controlled components. |
| Local Issue ID | Custom field | Required stable reconciliation key. |
| Source IDs | Custom field | Searchable compact list of historical/governance IDs. |
| Phase | Custom field/label | Portable grouping; no unsupported initiative level is assumed. |
| Logical Workflow State | Custom field | Preserves READY/BLOCKED/etc. separately from target workflow. |
| Implementation Maturity | Custom field | Mandatory semantic separation from status. |
| Evidence State | Custom field | Mandatory semantic separation from status/maturity. |
| Owner Historical Wave | Custom field | Historical wave or POST_W25 provenance. |
| Critical Path | custom boolean/label | Dependency criticality, not schedule duration. |
| Execution Lane | custom select/label | Safe parallelism and gate routing. |

Detailed requirement, ADR, acceptance, risk, test, artifact, and source-reference lists stay canonical in the local records/indexes to avoid custom-field bloat.
