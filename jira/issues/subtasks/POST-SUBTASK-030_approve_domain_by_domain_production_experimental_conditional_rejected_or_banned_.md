<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-030_approve_domain_by_domain_production_experimental_conditional_rejected_or_banned_.json -->
# POST-SUBTASK-030 — [POST-SUBTASK-030] Gate domain-by-domain production, experimental, conditional, rejected, or unavailable eligibility

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "Preserve 2022-2025 as a bounded nonterminal tranche; target approximately 2010-2025 and earlier quality-supported seasons across teams, schedules, games, outcomes, drives, plays, team/player box scores, rosters, rankings, venues, advanced statistics, structured gamebook equivalents, and useful context. Record source/endpoint, season/type, team/game, domain/grain, schema/version, immutable identity, missingness, provider failures, and historical known-at/PIT state without discarding a useful season because another domain is incomplete.",
    "Coverage and timestamp quality are measured by season/team/source/domain, with A&M detail reported separately and upstream-equivalent feeds not miscounted as independent corroboration.",
    "Closing market, realized weather, final participation, restricted, thin, or unsupported domains cannot enter earlier production cutoffs or block the core v1 without explicit evidence.",
    "All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-010. Governance traceability gate: POST-SUBTASK-033. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-030.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/data_lake/historical_expansion_eligibility_gate.json",
    "artifacts/jira_evidence/POST-SUBTASK-030.json"
  ],
  "blocked_reason": "",
  "blocks": [
    "POST-EPIC-007",
    "POST-STORY-011",
    "POST-STORY-021",
    "POST-STORY-023",
    "POST-SUBTASK-031",
    "POST-SUBTASK-032",
    "POST-SUBTASK-033",
    "POST-SUBTASK-061",
    "POST-SUBTASK-062",
    "POST-SUBTASK-063",
    "POST-SUBTASK-067",
    "POST-SUBTASK-068",
    "POST-SUBTASK-069"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-030_approve_domain_by_domain_production_experimental_conditional_rejected_or_banned_.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "PRODUCTION_READY",
    "downstream_consumer": "POST-STORY-010",
    "governance_traceability_gate": "POST-SUBTASK-033",
    "negative_results_preserved": true,
    "provenance_dimensions": [
      "source",
      "data",
      "code",
      "config",
      "tool",
      "runtime",
      "split/cutoff when applicable"
    ]
  },
  "component": "raw-snapshots",
  "components_expected_to_be_touched": [
    "raw-snapshots",
    "raw-data"
  ],
  "content_contract_version": "2.0",
  "critical_path": true,
  "definition_of_done": [
    "The atomic scope in POST-SUBTASK-030 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-010."
  ],
  "dependencies": [
    "POST-SUBTASK-027",
    "POST-SUBTASK-028",
    "POST-SUBTASK-029"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 4,
    "adr_ids": 6,
    "gap_ids": 1,
    "requirement_ids": 8,
    "risk_ids": 5
  },
  "effective_traceability_total": 24,
  "end_to_end_validation": "The expanded manifest is deterministic and consumable by the profiling step, preserves partial seasons and missing domains, and never treats rights metadata or the 2022-2025 tranche as a terminal-history gate. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-007, POST-STORY-011, POST-STORY-021, POST-STORY-023, POST-SUBTASK-031, POST-SUBTASK-032, POST-SUBTASK-033, POST-SUBTASK-061, POST-SUBTASK-062, POST-SUBTASK-063, POST-SUBTASK-067, POST-SUBTASK-068….",
  "epic_id": "POST-EPIC-003",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-030.json",
  "evidence_state": "VERIFIED",
  "execution_lane": "PROTECTED_GATE",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "PRODUCTION_READY",
  "expected_outputs": [
    "artifacts/data_lake/historical_expansion_eligibility_gate.json"
  ],
  "files_expected_to_be_read": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_w19_foundation.py",
    "src/aggie_analytics/data/adapters.py",
    "src/aggie_analytics/data/contracts.py",
    "src/aggie_analytics/data/snapshots.py",
    "docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md"
  ],
  "files_expected_to_be_touched": [],
  "files_to_inspect": [
    "governance/DO_NOT_DRIFT.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_w19_foundation.py",
    "src/aggie_analytics/data/adapters.py",
    "src/aggie_analytics/data/contracts.py",
    "src/aggie_analytics/data/snapshots.py",
    "docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md"
  ],
  "gap_ids": [],
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-030_approve_domain_by_domain_production_experimental_conditional_rejected_or_banned_.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-033",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100334,
  "in_scope": [
    "Perform the exact action: Gate domain-by-domain production, experimental, conditional, rejected, or unavailable eligibility.",
    "Consume only verified prerequisite outputs from `POST-SUBTASK-027`, `POST-SUBTASK-028`, `POST-SUBTASK-029`.",
    "Demonstrate with saved evidence: Preserve 2022-2025 as a bounded nonterminal tranche; target approximately 2010-2025 and earlier quality-supported seasons across teams, schedules, games, outcomes, drives, plays, team/player box scores, rosters, rankings, venues, advanced statistics, structured gamebook equivalents, and useful context. Record source/endpoint, season/type, team/game, domain/grain, schema/version, immutable identity, missingness, provider failures, and historical known-at/PIT state without discarding a useful season because another domain is incomplete.",
    "Demonstrate with saved evidence: Coverage and timestamp quality are measured by season/team/source/domain, with A&M detail reported separately and upstream-equivalent feeds not miscounted as independent corroboration.",
    "Demonstrate with saved evidence: Closing market, realized weather, final participation, restricted, thin, or unsupported domains cannot enter earlier production cutoffs or block the core v1 without explicit evidence.",
    "Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.",
    "Produce, validate, content-hash, and register `artifacts/data_lake/context_eligibility_gate.json`.",
    "Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-380",
  "labels": [
    "actionable",
    "core-release",
    "post-wave",
    "protected-gate",
    "raw-data",
    "subtask",
    "historical-expansion"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-030",
  "maturity_before": "SCAFFOLD",
  "objective": "Gate domain-by-domain production, experimental, conditional, rejected, or unavailable eligibility",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24520",
    "jira_updated_at": "2026-08-09T23:24:02.046-0500",
    "last_synced_at": "2026-08-10T04:24:34.496382+00:00",
    "source_export": "C:\\BatteredAggieSyndrome.data\\worktrees\\BAT-516-openai-foundation-complete\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "Done"
  },
  "out_of_scope": [
    "Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.",
    "Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.",
    "Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.",
    "Work assigned to sibling subtasks: Expand immutable national core and supporting-domain history to the maximum quality-supported seasons; Profile supporting-domain schema, historical coverage, timestamp quality, upstream lineage, and nonblocking source-policy metadata.",
    "Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-010",
  "phase": "PHASE-1",
  "prerequisites": [
    "Dependency POST-SUBTASK-027 complete at required maturity",
    "Dependency POST-SUBTASK-028 complete at required maturity",
    "Dependency POST-SUBTASK-029 complete at required maturity"
  ],
  "primary_source_refs": [
    "SRCREF-02013",
    "SRCREF-02014",
    "SRCREF-02015",
    "SRCREF-02016"
  ],
  "priority": "P0",
  "protected_change_required": false,
  "protected_files_and_interfaces": [
    "AGENTS.md",
    "governance/DO_NOT_DRIFT.md",
    "governance/PROTECTED_ACCEPTANCE_RULES.md",
    "governance/PROTECTED_JUDGING_RULE_SEAL.csv",
    "governance/PROTECTED_SPLIT_REGISTRY.csv",
    "governance/THRESHOLD_PRECOMMITMENT_REGISTRY.csv",
    "configs/judging_rule_seal.json",
    "docs/45_SCIENTIFIC_BAS_SPECIFICATION.md"
  ],
  "read_only_context_paths": [
    "AGENTS.md",
    "governance/DO_NOT_DRIFT.md",
    "governance/PROTECTED_ACCEPTANCE_RULES.md",
    "governance/PROTECTED_JUDGING_RULE_SEAL.csv",
    "governance/PROTECTED_SPLIT_REGISTRY.csv",
    "governance/THRESHOLD_PRECOMMITMENT_REGISTRY.csv",
    "configs/judging_rule_seal.json",
    "docs/45_SCIENTIFIC_BAS_SPECIFICATION.md",
    "docs/final/CODEX_HANDOFF.md",
    "docs/final/FINAL_BACKLOG.csv",
    "docs/final/FINAL_COMPONENT_MATURITY.csv",
    "docs/final/FINAL_IMPLEMENTATION_PRIORITY.md",
    "docs/final/FINAL_KNOWN_GAPS.csv",
    "tests/test_w19_foundation.py",
    "src/aggie_analytics/data/adapters.py",
    "src/aggie_analytics/data/contracts.py",
    "src/aggie_analytics/data/snapshots.py",
    "docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md"
  ],
  "ready": false,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/data_lake/context_eligibility_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.",
    "An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.",
    "Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.",
    "An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.",
    "PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-030; retain command, exit code, and relevant output.",
      "path": "tests/test_w19_foundation.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "CHRONOLOGICAL_REPLAY",
      "expectation": "Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.",
      "path": "artifacts/data_lake/context_eligibility_gate.json",
      "validation_class": "CHRONOLOGICAL_REPLAY"
    },
    {
      "classification": "SECURITY",
      "expectation": "Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.",
      "path": "artifacts/data_lake/context_eligibility_gate.json",
      "validation_class": "SECURITY"
    },
    {
      "classification": "END_TO_END",
      "expectation": "Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.",
      "path": "artifacts/data_lake/context_eligibility_gate.json",
      "validation_class": "END_TO_END"
    },
    {
      "classification": "REPRODUCIBILITY",
      "expectation": "Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.",
      "path": "ISSUE_COMPLETION_MANIFEST",
      "validation_class": "REPRODUCIBILITY"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-030.",
    "A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.",
    "Acceptance failure: the evidence cannot demonstrate that preserve 2022-2025 as a bounded nonterminal tranche; target approximately 2010-2025 and earlier quality-supported seasons across teams, schedules, games, outcomes, drives, plays, team/player box scores, rosters, rankings, venues, advanced statistics, structured gamebook equivalents, and useful context. Record source/endpoint, season/type, team/game, domain/grain, schema/version, immutable identity, missingness, provider failures, and historical known-at/PIT state without discarding a useful season because another domain is incomplete.",
    "Acceptance failure: the evidence cannot demonstrate that coverage and timestamp quality are measured by season/team/source/domain, with A&M detail reported separately and upstream-equivalent feeds not miscounted as independent corroboration.",
    "Acceptance failure: the evidence cannot demonstrate that closing market, realized weather, final participation, restricted, thin, or unsupported domains cannot enter earlier production cutoffs or block the core v1 without explicit evidence.",
    "Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the atomic 3 of 3 step in Story POST-STORY-010 (Historical expansion across core and supporting domains): Gate domain-by-domain production, experimental, conditional, rejected, or unavailable eligibility. Consume only verified prerequisite outputs from `POST-SUBTASK-027`, `POST-SUBTASK-028`, `POST-SUBTASK-029`. Produce `artifacts/data_lake/context_eligibility_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.",
  "source_ids": [
    "GAP-002",
    "GAP-006",
    "GAP-010",
    "GAP-011",
    "HANDOFF-003",
    "HANDOFF-008"
  ],
  "source_refs": [
    "SRCREF-02013",
    "SRCREF-02014",
    "SRCREF-02015",
    "SRCREF-02016",
    "SRCREF-02017",
    "SRCREF-02018",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01889",
    "SRCREF-01564",
    "SRCREF-01894",
    "SRCREF-01568",
    "SRCREF-01572",
    "SRCREF-01573"
  ],
  "specificity_fingerprint": "93ccbcdefbb617916bee9d492011915f0ea93a36dc6f133c7d3bc439a9ac236e",
  "stop_conditions": [
    "Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.",
    "Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.",
    "Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity."
  ],
  "supporting_source_refs": [
    "SRCREF-02017",
    "SRCREF-02018",
    "SRCREF-02001",
    "SRCREF-02002",
    "SRCREF-02003",
    "SRCREF-02004",
    "SRCREF-02005",
    "SRCREF-02006",
    "SRCREF-01889",
    "SRCREF-01564",
    "SRCREF-01894",
    "SRCREF-01568",
    "SRCREF-01572",
    "SRCREF-01573"
  ],
  "title": "[POST-SUBTASK-030] Gate domain-by-domain production, experimental, conditional, rejected, or unavailable eligibility",
  "traceability_inherited_from": [
    "POST-SUBTASK-033"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "",
  "validation_classes": [
    "CHRONOLOGICAL_REPLAY",
    "END_TO_END",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SECURITY"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-010: Player, roster, recruiting, market, weather, and contextual raw domains.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-030.md",
  "workflow_state": "DONE"
}
```

## Objective

Gate domain-by-domain production, experimental, conditional, rejected, or unavailable eligibility

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-010: Player, roster, recruiting, market, weather, and contextual raw domains.

## Scope

Execute the atomic 3 of 3 step in Story POST-STORY-010 (Historical expansion across core and supporting domains): Gate domain-by-domain production, experimental, conditional, rejected, or unavailable eligibility. Consume only verified prerequisite outputs from `POST-SUBTASK-027`, `POST-SUBTASK-028`, `POST-SUBTASK-029`. Produce `artifacts/data_lake/context_eligibility_gate.json`; evaluate every issue-specific acceptance condition; preserve negative results; and hand the pinned output to the Story gate/downstream dependency graph.

### Explicit In Scope

- Perform the exact action: Gate domain-by-domain production, experimental, conditional, rejected, or unavailable eligibility.
- Consume only verified prerequisite outputs from `POST-SUBTASK-027`, `POST-SUBTASK-028`, `POST-SUBTASK-029`.
- Demonstrate with saved evidence: Preserve 2022-2025 as a bounded nonterminal tranche; target approximately 2010-2025 and earlier quality-supported seasons across teams, schedules, games, outcomes, drives, plays, team/player box scores, rosters, rankings, venues, advanced statistics, structured gamebook equivalents, and useful context. Record source/endpoint, season/type, team/game, domain/grain, schema/version, immutable identity, missingness, provider failures, and historical known-at/PIT state without discarding a useful season because another domain is incomplete.
- Demonstrate with saved evidence: Coverage and timestamp quality are measured by season/team/source/domain, with A&M detail reported separately and upstream-equivalent feeds not miscounted as independent corroboration.
- Demonstrate with saved evidence: Closing market, realized weather, final participation, restricted, thin, or unsupported domains cannot enter earlier production cutoffs or block the core v1 without explicit evidence.
- Demonstrate with saved evidence: All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.
- Produce, validate, content-hash, and register `artifacts/data_lake/context_eligibility_gate.json`.
- Record explicit PASS/FAIL/BLOCKED dispositions and update downstream readiness only from verified evidence.

### Explicit Out of Scope

- Unrelated refactors, dependency upgrades, or architecture changes outside this atomic work unit.
- Changing protected requirements, judging rules, split seals, PIT cutoffs, or accepted ADRs merely to obtain a passing result.
- Treating synthetic fixtures, file existence, or a successful command as proof of real-data, empirical, target-hardware, technical-source, or operating readiness.
- Work assigned to sibling subtasks: Expand immutable national core and supporting-domain history to the maximum quality-supported seasons; Profile supporting-domain schema, historical coverage, timestamp quality, upstream lineage, and nonblocking source-policy metadata.
- Using same-game, future, postgame, closing-line, realized-weather, corrected-late, or globally fitted information in a pregame path.

## Prerequisites

- Dependency POST-SUBTASK-027 complete at required maturity
- Dependency POST-SUBTASK-028 complete at required maturity
- Dependency POST-SUBTASK-029 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-027
- POST-SUBTASK-028
- POST-SUBTASK-029

## Blocks

- POST-EPIC-007
- POST-STORY-011
- POST-STORY-021
- POST-STORY-023
- POST-SUBTASK-031
- POST-SUBTASK-032
- POST-SUBTASK-033
- POST-SUBTASK-061
- POST-SUBTASK-062
- POST-SUBTASK-063
- POST-SUBTASK-067
- POST-SUBTASK-068
- POST-SUBTASK-069

## Read / Inspect First

- governance/DO_NOT_DRIFT.md
- docs/final/CODEX_HANDOFF.md
- docs/final/FINAL_BACKLOG.csv
- docs/final/FINAL_COMPONENT_MATURITY.csv
- docs/final/FINAL_IMPLEMENTATION_PRIORITY.md
- docs/final/FINAL_KNOWN_GAPS.csv
- tests/test_w19_foundation.py
- src/aggie_analytics/data/adapters.py
- src/aggie_analytics/data/contracts.py
- src/aggie_analytics/data/snapshots.py
- docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md

## Files Expected To Be Modified

- None.

## Components Expected To Be Touched

- raw-snapshots
- raw-data

## Protected Files / Interfaces

- AGENTS.md
- governance/DO_NOT_DRIFT.md
- governance/PROTECTED_ACCEPTANCE_RULES.md
- governance/PROTECTED_JUDGING_RULE_SEAL.csv
- governance/PROTECTED_SPLIT_REGISTRY.csv
- governance/THRESHOLD_PRECOMMITMENT_REGISTRY.csv
- configs/judging_rule_seal.json
- docs/45_SCIENTIFIC_BAS_SPECIFICATION.md

## Expected Outputs / Artifacts

- artifacts/data_lake/historical_expansion_eligibility_gate.json

## Direct Requirements

- None.

## Direct Acceptance Controls

- None.

## Governance Traceability Inheritance

- Gate: `POST-SUBTASK-033`
- Inherited from: POST-SUBTASK-033
- Resolution: `INHERITED_DOMAIN_GATE`
- Effective counts: `{"acceptance_control_ids": 4, "adr_ids": 6, "gap_ids": 1, "requirement_ids": 8, "risk_ids": 5}`

## Acceptance Criteria

1. Preserve 2022-2025 as a bounded nonterminal tranche; target approximately 2010-2025 and earlier quality-supported seasons across teams, schedules, games, outcomes, drives, plays, team/player box scores, rosters, rankings, venues, advanced statistics, structured gamebook equivalents, and useful context. Record source/endpoint, season/type, team/game, domain/grain, schema/version, immutable identity, missingness, provider failures, and historical known-at/PIT state without discarding a useful season because another domain is incomplete.
2. Coverage and timestamp quality are measured by season/team/source/domain, with A&M detail reported separately and upstream-equivalent feeds not miscounted as independent corroboration.
3. Closing market, realized weather, final participation, restricted, thin, or unsupported domains cannot enter earlier production cutoffs or block the core v1 without explicit evidence.
4. All prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Definition of Done

1. The atomic scope in POST-SUBTASK-030 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, private-research publication boundary, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, genuinely private personal information, raw third-party publication payloads, fabricated data, fabricated metrics, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The Story gate consumes the complete prerequisite evidence set and issues an explicit downstream approval/block/reject/defer decision for POST-STORY-010.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_w19_foundation.py` — Run as a regression check after completing POST-SUBTASK-030; retain command, exit code, and relevant output.
- **CHRONOLOGICAL_REPLAY** / `CHRONOLOGICAL_REPLAY` — `artifacts/data_lake/context_eligibility_gate.json` — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- **SECURITY** / `SECURITY` — `artifacts/data_lake/context_eligibility_gate.json` — Verify no secret/restricted payload leakage, least-privilege handling, redaction, and fail-closed behavior.
- **END_TO_END** / `END_TO_END` — `artifacts/data_lake/context_eligibility_gate.json` — Evaluate the complete Story contract from prerequisite evidence through downstream-consumable gate output; unresolved blockers remain blocking.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.

## Required Evidence

- `artifacts/data_lake/context_eligibility_gate.json` plus SHA-256/content identity, producer command/version, prerequisite artifact identities, creation time, and validation disposition.
- An acceptance-evidence matrix with one row per criterion, observable result, evidence location/hash, verifier, timestamp, and PASS/FAIL/BLOCKED disposition.
- Exact commands/tool versions, exit codes, stdout/stderr locations, and negative/failure results; narrative completion alone is not evidence.
- An issue completion manifest recording achieved maturity, evidence state, remaining blockers, downstream issues reevaluated, and Jira/local synchronization result.
- PIT evidence showing prediction cutoff, known-at fields, rejected future/same-game/postgame records, fold/split identity, and leakage-test results.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "completion_claim_limit": "PRODUCTION_READY",
  "downstream_consumer": "POST-STORY-010",
  "governance_traceability_gate": "POST-SUBTASK-033",
  "negative_results_preserved": true,
  "provenance_dimensions": [
    "source",
    "data",
    "code",
    "config",
    "tool",
    "runtime",
    "split/cutoff when applicable"
  ]
}
```

## End-to-End Validation Requirement

The expanded manifest is deterministic and consumable by the profiling step, preserves partial seasons and missing domains, and never treats rights metadata or the 2022-2025 tranche as a terminal-history gate. The gate decision must explicitly reevaluate downstream issues: POST-EPIC-007, POST-STORY-011, POST-STORY-021, POST-STORY-023, POST-SUBTASK-031, POST-SUBTASK-032, POST-SUBTASK-033, POST-SUBTASK-061, POST-SUBTASK-062, POST-SUBTASK-063, POST-SUBTASK-067, POST-SUBTASK-068….

## Expected Maturity After Completion

`PRODUCTION_READY`

## Risk / Failure Conditions

- The work would be invalid if any prerequisite artifact, source/data/code/config identity, or declared maturity differs from the pinned issue contract for POST-SUBTASK-030.
- A command may exit successfully while producing stale, partial, synthetic-only, leakage-contaminated, non-reproducible, or legally unusable evidence.
- Acceptance failure: the evidence cannot demonstrate that preserve 2022-2025 as a bounded nonterminal tranche; target approximately 2010-2025 and earlier quality-supported seasons across teams, schedules, games, outcomes, drives, plays, team/player box scores, rosters, rankings, venues, advanced statistics, structured gamebook equivalents, and useful context. Record source/endpoint, season/type, team/game, domain/grain, schema/version, immutable identity, missingness, provider failures, and historical known-at/PIT state without discarding a useful season because another domain is incomplete.
- Acceptance failure: the evidence cannot demonstrate that coverage and timestamp quality are measured by season/team/source/domain, with A&M detail reported separately and upstream-equivalent feeds not miscounted as independent corroboration.
- Acceptance failure: the evidence cannot demonstrate that closing market, realized weather, final participation, restricted, thin, or unsupported domains cannot enter earlier production cutoffs or block the core v1 without explicit evidence.
- Acceptance failure: the evidence cannot demonstrate that all prerequisite evidence is linked and unresolved blockers remain explicit; file creation alone cannot pass this gate.

## Stop Conditions

- Stop only the affected route or domain if a required resource is technically inaccessible and no equivalent public route is found after documented attempts, or if a required schema, PIT/provenance artifact, target host, or protected split is unavailable.
- Quarantine affected records or domains on corruption, fabrication, incompatible schema, PIT or target leakage, malware, exposed credentials, or genuinely private personal information; do not globally block unrelated acquisition or analysis.
- Stop and preserve evidence if an observable acceptance criterion cannot be evaluated without fabricating data, metrics, provenance, availability, or maturity.

## Source References

- SRCREF-02013
- SRCREF-02014
- SRCREF-02015
- SRCREF-02016
- SRCREF-02017
- SRCREF-02018
- SRCREF-02001
- SRCREF-02002
- SRCREF-02003
- SRCREF-02004
- SRCREF-02005
- SRCREF-02006
- SRCREF-01889
- SRCREF-01564
- SRCREF-01894
- SRCREF-01568
- SRCREF-01572
- SRCREF-01573

## AI Context Notes

- Canonical parent Story: POST-STORY-010. Governance traceability gate: POST-SUBTASK-033. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-030.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.
