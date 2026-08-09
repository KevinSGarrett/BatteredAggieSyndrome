# Jira Local Schema

## Canonical issue record

Each `records/issues/**/*.json` contains:

- identity/hierarchy: schema version, Local ID, Jira key, import ID, issue type, parent, Epic, phase;
- state: workflow, historical/actionable classification, priority, critical path, maturity before/after, evidence state, READY/blocker data;
- provenance: owner/historical wave, source IDs, source-reference IDs, requirements, controls, ADRs, risks, gaps;
- executable specification: objective, why, scope, in/out, prerequisites, dependencies, blocks, expected files/protected files/outputs;
- completion contract: acceptance criteria, Definition of Done, tests, evidence, E2E validation, risks, stop conditions;
- search/operation: labels, component, execution lane, AI notes, canonical/derived paths.

## State separation

Workflow state, implementation maturity, and evidence state are independent. A record may be workflow `DONE` at maturity `FUNCTIONAL_STARTER` with verified evidence for that scoped starter while a separate post-wave issue remains open for empirical validation.

## IDs

Historical IDs (`EPIC-###`, `TASK-###`, `REQ-###`, `AC-###`, `ADR-###`, `RISK-###`, `GAP-###`, `HANDOFF-###`, `ISSUE-###`) are preserved. New Jira-local work uses `POST-EPIC-###`, `POST-STORY-###`, and `POST-SUBTASK-###`. Jira keys remain blank until the destination creates them.

## Dependencies

Hierarchy and execution dependency are separate. `parent_id`/`epic_id` define hierarchy. `dependencies` are hard prerequisites. `blocks` is the computed inverse. `related_to` records nonblocking provenance/reconciliation relationships.

## Sources

Source-reference IDs resolve through `sources/SOURCE_ANCHOR_INDEX.csv`; repository-relative path is canonical. Hash + heading/line + anchor support drift detection.

## Schema v2 second-pass fields


Canonical JSON remains the sole editable specification. Schema v2 adds:

- `files_to_inspect`: minimal read-only implementation/source context, distinct from modification authority.
- `components_expected_to_be_touched`: component-level scope when an exact file cannot safely be predicted.
- `governance_traceability_gate`, `traceability_inherited_from`, `traceability_resolution`, and effective counts.
- `completion_evidence_contract`: machine-readable minimum evidence and claim limit.
- `validation_class` on validation entries, while retaining the original `classification` field.
- `allowed_modification_paths` versus `read_only_context_paths`: explicit mutation authority separate from source context.
- `primary_source_refs` and `supporting_source_refs`: token-efficient source ordering without duplicating content.
- `evidence_manifest_path`, `work_packet_path`, `validation_classes`, `record_revision`, `last_content_audit`, and `specificity_fingerprint`: deterministic navigation/audit derivatives.
- `execution_mode`: `ATOMIC_EXECUTION` for directly executable post-wave Subtasks, `AGGREGATE_GATE` for non-executable Epic/Story integration gates, and `HISTORICAL_REFERENCE` for provenance-only records.
- Every actionable post-wave record has a compact packet. Aggregate packets explicitly prohibit atomic implementation and authorize only aggregate evidence/Jira-state closure actions.

All Markdown issue views, work packets, source manifests, indexes, import CSVs, and REST payloads are generated derivatives. After any canonical or operational change, run `python -B jira/tools/rebuild_all_derivatives.py`; strict validation rejects derivative drift.
