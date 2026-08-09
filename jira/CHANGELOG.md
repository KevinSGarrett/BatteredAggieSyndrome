# Jira System Changelog

## 2026-08-08 — v1 generated

- Completed full read-only repository reconnaissance.
- Reconciled historical WBS status against final maturity/gap/handoff evidence.
- Created 463 canonical issue records and generated views.
- Created source, requirement, acceptance, ADR, risk, gap, test, artifact, hierarchy, and dependency traceability.
- Created compact AI queues/work packets and Jira import/API templates.
- Created validation, rebuild, reconciliation, and snapshot tooling.

Future meaningful changes must be appended; do not log trivial generated formatting churn.

## 2026-08-09 — Historical Data Scope and Expansion Contract

- Preserved POST-SUBTASK-025 through POST-SUBTASK-027 and their verified 2022-2025 evidence as the first bounded contemporary tranche; those completions no longer admit a terminal-history or GAP-002-resolution interpretation.
- Strengthened POST-STORY-010 / POST-SUBTASK-028 through POST-SUBTASK-030 as the critical-path expanded acquisition, independent population profiling, and tiered season/domain/use-eligibility chain targeting approximately 2010-2025 and earlier quality-supported history.
- Strengthened POST-STORY-011 / POST-SUBTASK-031 through POST-SUBTASK-033 as the content-addressed external-storage, provenance, negative-evidence, and non-bypassable national historical-lake readiness chain.
- Bound POST-SUBTASK-072 and POST-SUBTASK-073 to the expanded quality-supported population; a narrower model window now requires explicit protected empirical justification.
- Required immutable bulk storage below `AGGIE_ANALYTICS_DATA_ROOT`, independent coverage dimensions, preservation of partial/negative findings, and cleanup of reconstructible stale artifacts.

## 2026-08-08 — v2 second-pass hardening

- Generic executable-subtask scope specifications: 159 → 0
- Actionable scopes that merely repeated the objective: 212 → 0
- Actionable items without end-to-end validation: 4 → 0
- Legal-review tasks incorrectly forced to add an automated test: 2 → 0
- All actionable records now declare explicit governance-traceability gates/inheritance, files to inspect versus files authorized for modification, task-appropriate validation classes, completion evidence contracts, and issue-specific risks/evidence/DoD.
- AI packet coverage: 229 / 229 actionable records (159 atomic execution; 70 non-executable aggregate gates).
- All issue Markdown, AI work packets, source manifests, indexes, import CSVs, and REST payloads are regenerated from canonical JSON and checked for derivative consistency.
- Source-reference validation now fails closed on any hash/range drift until exact anchor relocation is proven with `validate_source_refs.py --repair`; invalid stored anchor hashes are never auto-repaired.
- Jira reconciliation dry-run is now genuinely non-mutating; live reconciliation is transactional, rejects unsupported or evidence-unsafe workflow transitions, records conflicts, rolls back on strict-validation failure, and rebuilds every derivative only after a valid commit.
- The reusable `POST_IMPORT_KEY_MAP_TEMPLATE.csv` remains blank by contract, while assigned live keys/IDs are stored separately in `POST_IMPORT_KEY_MAP.csv` and validated against canonical records.
- Derivative rebuild entry points are import-safe and idempotent; importing reconciliation utilities no longer triggers an unintended rebuild.
- BAS scientific acceptance explicitly permits and preserves a valid null Aggie-specific excess result; no nonzero BAS effect is forced.
