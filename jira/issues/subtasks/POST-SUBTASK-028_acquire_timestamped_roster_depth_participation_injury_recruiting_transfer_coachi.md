<!-- GENERATED VIEW. Canonical record: jira/records/issues/subtasks/POST-SUBTASK-028_acquire_timestamped_roster_depth_participation_injury_recruiting_transfer_coachi.json -->
# POST-SUBTASK-028 — [POST-SUBTASK-028] Expand immutable national core and supporting-domain history to the maximum quality-supported seasons

## Canonical metadata

```json
{
  "acceptance_control_ids": [],
  "acceptance_criteria": [
    "The bounded 2022-2025 population remains identified as the first validated contemporary tranche and is not represented as terminal history, the complete lake, or GAP-002 resolution.",
    "The acquisition targets at least approximately 2010-2025, extends earlier where source/domain quality supports it, and records every attempted source/endpoint/season/type/domain outcome without discarding an otherwise useful season because another domain is incomplete.",
    "Every capture or failed attempt records source and endpoint, request identity, season and season type, team/game scope where applicable, domain and grain, schema/version, retrieval and known-at state, content hash and immutable external path, pagination, rights class, and provider limitation.",
    "The declared output `artifacts/data_lake/historical_expansion_acquisition_manifest.json` is deterministic, provenance-complete, stored without bulk raw data in Git, and consumable by POST-SUBTASK-029.",
    "No source availability, completeness threshold, empirical result, model readiness, A&M lift, BAS, Aggie Excess, or GAP-002 closure is fabricated or implied."
  ],
  "adr_ids": [],
  "ai_context_notes": [
    "Canonical parent Story: POST-STORY-010. Governance traceability gate: POST-SUBTASK-033. Inherited traceability is resolved through `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.",
    "Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-028.json`; inspect only the listed implementation files and prerequisite outputs.",
    "May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.",
    "Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient."
  ],
  "allowed_modification_paths": [
    "artifacts/data_lake/historical_expansion_acquisition_manifest.json",
    "artifacts/jira_evidence/POST-SUBTASK-028.json"
  ],
  "blocked_reason": "",
  "blocks": [
    "POST-SUBTASK-029",
    "POST-SUBTASK-030"
  ],
  "canonical_record": "jira/records/issues/subtasks/POST-SUBTASK-028_acquire_timestamped_roster_depth_participation_injury_recruiting_transfer_coachi.json",
  "canonical_source_role": "AUTHORITATIVE_LOCAL_SPECIFICATION",
  "completion_evidence_contract": {
    "acceptance_matrix_required": true,
    "artifact_hashes_required": true,
    "completion_claim_limit": "IMPLEMENTED",
    "downstream_consumer": "POST-SUBTASK-029",
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
    "The atomic scope in POST-SUBTASK-028 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.",
    "Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.",
    "Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.",
    "Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.",
    "No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.",
    "The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.",
    "The output set `artifacts/data_lake/historical_expansion_acquisition_manifest.json` is demonstrably consumable by POST-SUBTASK-029 without manual reconstruction or undocumented state."
  ],
  "dependencies": [
    "POST-SUBTASK-027"
  ],
  "effective_traceability_counts": {
    "acceptance_control_ids": 4,
    "adr_ids": 6,
    "gap_ids": 1,
    "requirement_ids": 8,
    "risk_ids": 5
  },
  "effective_traceability_total": 24,
  "end_to_end_validation": "Validate that the expanded acquisition manifest independently enumerates source/endpoint, season/type, team/game, domain/grain, schema/version, missing/failure, immutable provenance, and historical known-at/PIT state, and that POST-SUBTASK-029 rejects missing, stale, hash-invalid, rights-blocked, or silently terminal-2022-2025 inputs.",
  "epic_id": "POST-EPIC-003",
  "evidence_manifest_path": "artifacts/jira_evidence/POST-SUBTASK-028.json",
  "evidence_state": "PLANNED",
  "execution_lane": "DATA_MATERIALIZATION",
  "execution_mode": "ATOMIC_EXECUTION",
  "expected_maturity_after_completion": "IMPLEMENTED",
  "expected_outputs": [
    "artifacts/data_lake/historical_expansion_acquisition_manifest.json"
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
  "generated_markdown": "jira/issues/subtasks/POST-SUBTASK-028_acquire_timestamped_roster_depth_participation_injury_recruiting_transfer_coachi.md",
  "governance_review_required": false,
  "governance_traceability_gate": "POST-SUBTASK-033",
  "historical_classification": "ACTIONABLE_POST_WAVE",
  "import_id": 100332,
  "in_scope": [
    "Preserve the validated 2022-2025 tranche unchanged as a bounded input and expand beyond it.",
    "Acquire every useful approved domain available per season: teams, schedules, games, official outcomes, drives, plays, team/player box scores, rosters, rankings, venues, advanced game statistics, structured gamebook equivalents, and useful approved supporting context.",
    "Use approved direct APIs/downloads and permitted Scrapfly, ScraperAPI, browser, Docker, or equivalent routes autonomously; substitute sources when a preferred route fails.",
    "Write bulk raw and normalized payloads only below AGGIE_ANALYTICS_DATA_ROOT as immutable content-addressed captures.",
    "Record partial seasons, missing domains, schema drift, failed endpoints, reconciliation candidates, and historical known-at/PIT limitations as evidence.",
    "Produce and validate `artifacts/data_lake/historical_expansion_acquisition_manifest.json` and hand it to POST-SUBTASK-029."
  ],
  "issue_type": "Subtask",
  "jira_key": "BAT-378",
  "labels": [
    "actionable",
    "core-release",
    "data-materialization",
    "post-wave",
    "raw-data",
    "subtask",
    "historical-expansion"
  ],
  "last_content_audit": "2026-08-09",
  "local_id": "POST-SUBTASK-028",
  "maturity_before": "SCAFFOLD",
  "objective": "Acquire immutable expanded national core and supporting-domain history, targeting approximately 2010-2025 and earlier quality-supported seasons",
  "operational_jira": {
    "assignee": "",
    "jira_issue_id": "24518",
    "jira_updated_at": "2026-08-09T00:03:29.806-0500",
    "last_synced_at": "2026-08-09T05:44:21.584799+00:00",
    "source_export": "C:\\BatteredAggieSyndrome\\jira\\reconciliation\\BAT_JIRA_EXPORT.csv",
    "sprint": "",
    "status_raw": "To Do"
  },
  "out_of_scope": [
    "Claiming that the bounded 2022-2025 tranche is terminal national history or the default final training population.",
    "Discarding an otherwise useful season solely because player, roster, play-by-play, gamebook, box-score, or advanced-stat coverage is incomplete.",
    "Promoting incomplete evidence into an unsupported domain, fabricating completeness thresholds, or weakening protected PIT/target-game rules.",
    "Committing bulk raw/normalized source data, credentials, or restricted payloads to Git, Jira, logs, screenshots, or model prompts.",
    "Claiming production model readiness, champion performance, A&M lift, BAS, Aggie Excess, or GAP-002 resolution."
  ],
  "owner_wave": "POST_W25",
  "parent_id": "POST-STORY-010",
  "phase": "PHASE-1",
  "prerequisites": [
    "Dependency POST-SUBTASK-027 complete at required maturity"
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
  "ready": true,
  "record_revision": "2.0",
  "related_to": [],
  "required_evidence": [
    "`artifacts/data_lake/historical_expansion_acquisition_manifest.json` with SHA-256, producer command/version, source/endpoint request identities, season/type and domain/grain coverage, schema versions, immutable external paths/hashes, known-at/PIT state, provider failures, and negative findings.",
    "An acceptance matrix proving the bounded 2022-2025 tranche is nonterminal and every attempted acquisition has a PASS, FAIL, PARTIAL, UNAVAILABLE, or BLOCKED disposition without fabricated completeness.",
    "Disk/cleanup evidence showing bulk data remained under AGGIE_ANALYTICS_DATA_ROOT and reconstructible temporary or abandoned payloads were removed after validation.",
    "Exact commands/tool versions, exit codes, redacted credential checks, and downstream POST-SUBTASK-029 consumer validation."
  ],
  "required_tests": [
    {
      "classification": "EXISTING_AUTOMATED_TEST",
      "expectation": "Run as a regression check after completing POST-SUBTASK-028; retain command, exit code, and relevant output.",
      "path": "tests/test_w19_foundation.py",
      "validation_class": "REGRESSION"
    },
    {
      "classification": "CHRONOLOGICAL_REPLAY",
      "expectation": "Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.",
      "path": "artifacts/data_lake/historical_expansion_acquisition_manifest.json",
      "validation_class": "CHRONOLOGICAL_REPLAY"
    },
    {
      "classification": "SCIENTIFIC",
      "expectation": "Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.",
      "path": "artifacts/data_lake/historical_expansion_acquisition_manifest.json",
      "validation_class": "SCIENTIFIC"
    },
    {
      "classification": "INTEGRATION",
      "expectation": "Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.",
      "path": "artifacts/data_lake/historical_expansion_acquisition_manifest.json",
      "validation_class": "INTEGRATION"
    },
    {
      "classification": "REPRODUCIBILITY",
      "expectation": "Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.",
      "path": "ISSUE_COMPLETION_MANIFEST",
      "validation_class": "REPRODUCIBILITY"
    },
    {
      "classification": "NEW_AUTOMATED_TEST_REQUIRED",
      "expectation": "Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test.",
      "path": "NEW_TEST_REQUIRED::POST-SUBTASK-028",
      "validation_class": "NEW_AUTOMATED_TEST_REQUIRED"
    }
  ],
  "requirement_ids": [],
  "risk_failure_conditions": [
    "The 2022-2025 tranche is silently treated as terminal history or a convenience window replaces the approximately 2010-2025 expansion target.",
    "A weak domain causes an otherwise useful season to be globally discarded or incomplete evidence is promoted into an unsupported domain.",
    "An attempted source/endpoint/season/domain, provider limitation, partial response, schema version, or negative finding is omitted from the manifest.",
    "Bulk data escapes the external root, immutable identity is missing, credentials are exposed, or reconstructible temporary artifacts are retained after validation.",
    "The manifest cannot be deterministically consumed and fail-closed validated by POST-SUBTASK-029."
  ],
  "risk_ids": [],
  "schema_version": 2,
  "scope": "Execute the critical-path historical-expansion acquisition entrypoint after the validated bounded 2022-2025 tranche. Inventory and acquire the maximum quality-supported national history, targeting approximately 2010-2025 and extending earlier where supported, across teams, schedules, games, official outcomes, drives, plays, team/player box scores, rosters, rankings, venues, advanced game statistics, structured gamebook-equivalent data, and useful supporting context. Preserve source/endpoint, request, season/type, team/game, domain/grain, schema/version, immutable hash/path, retrieval/known-at, provider-failure, and rights identities; hand the deterministic manifest to POST-SUBTASK-029.",
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
  "specificity_fingerprint": "a3c1d54fce4be726396a79aaf5305e07c026355305d357424e0984ca18518f2a",
  "stop_conditions": [
    "Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.",
    "Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.",
    "Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence."
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
  "title": "[POST-SUBTASK-028] Expand immutable national core and supporting-domain history to the maximum quality-supported seasons",
  "traceability_inherited_from": [
    "POST-SUBTASK-033"
  ],
  "traceability_resolution": "INHERITED_DOMAIN_GATE",
  "unblock_condition": "",
  "validation_classes": [
    "CHRONOLOGICAL_REPLAY",
    "INTEGRATION",
    "NEW_AUTOMATED_TEST_REQUIRED",
    "REGRESSION",
    "REPRODUCIBILITY",
    "SCIENTIFIC"
  ],
  "why_this_exists": "This is an independently executable and verifiable work unit required by Story POST-STORY-010: Player, roster, recruiting, market, weather, and contextual raw domains.",
  "work_packet_path": "jira/ai/work_packets/POST-SUBTASK-028.md",
  "workflow_state": "READY"
}
```

## Objective

Acquire immutable expanded national core and supporting-domain history, targeting approximately 2010-2025 and earlier quality-supported seasons

## Why This Exists

This is an independently executable and verifiable work unit required by Story POST-STORY-010: Player, roster, recruiting, market, weather, and contextual raw domains.

## Scope

Execute the critical-path historical-expansion acquisition entrypoint after the validated bounded 2022-2025 tranche. Inventory and acquire the maximum quality-supported national history, targeting approximately 2010-2025 and extending earlier where supported, across teams, schedules, games, official outcomes, drives, plays, team/player box scores, rosters, rankings, venues, advanced game statistics, structured gamebook-equivalent data, and useful supporting context. Preserve source/endpoint, request, season/type, team/game, domain/grain, schema/version, immutable hash/path, retrieval/known-at, provider-failure, and rights identities; hand the deterministic manifest to POST-SUBTASK-029.

### Explicit In Scope

- Preserve the validated 2022-2025 tranche unchanged as a bounded input and expand beyond it.
- Acquire every useful approved domain available per season: teams, schedules, games, official outcomes, drives, plays, team/player box scores, rosters, rankings, venues, advanced game statistics, structured gamebook equivalents, and useful approved supporting context.
- Use approved direct APIs/downloads and permitted Scrapfly, ScraperAPI, browser, Docker, or equivalent routes autonomously; substitute sources when a preferred route fails.
- Write bulk raw and normalized payloads only below AGGIE_ANALYTICS_DATA_ROOT as immutable content-addressed captures.
- Record partial seasons, missing domains, schema drift, failed endpoints, reconciliation candidates, and historical known-at/PIT limitations as evidence.
- Produce and validate `artifacts/data_lake/historical_expansion_acquisition_manifest.json` and hand it to POST-SUBTASK-029.

### Explicit Out of Scope

- Claiming that the bounded 2022-2025 tranche is terminal national history or the default final training population.
- Discarding an otherwise useful season solely because player, roster, play-by-play, gamebook, box-score, or advanced-stat coverage is incomplete.
- Promoting incomplete evidence into an unsupported domain, fabricating completeness thresholds, or weakening protected PIT/target-game rules.
- Committing bulk raw/normalized source data, credentials, or restricted payloads to Git, Jira, logs, screenshots, or model prompts.
- Claiming production model readiness, champion performance, A&M lift, BAS, Aggie Excess, or GAP-002 resolution.

## Prerequisites

- Dependency POST-SUBTASK-027 complete at required maturity

## Hard Dependencies

- POST-SUBTASK-027

## Blocks

- POST-SUBTASK-029
- POST-SUBTASK-030

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

- artifacts/data_lake/historical_expansion_acquisition_manifest.json

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

1. The bounded 2022-2025 population remains identified as the first validated contemporary tranche and is not represented as terminal history, the complete lake, or GAP-002 resolution.
2. The acquisition targets at least approximately 2010-2025, extends earlier where source/domain quality supports it, and records every attempted source/endpoint/season/type/domain outcome without discarding an otherwise useful season because another domain is incomplete.
3. Every capture or failed attempt records source and endpoint, request identity, season and season type, team/game scope where applicable, domain and grain, schema/version, retrieval and known-at state, content hash and immutable external path, pagination, rights class, and provider limitation.
4. The declared output `artifacts/data_lake/historical_expansion_acquisition_manifest.json` is deterministic, provenance-complete, stored without bulk raw data in Git, and consumable by POST-SUBTASK-029.
5. No source availability, completeness threshold, empirical result, model readiness, A&M lift, BAS, Aggie Excess, or GAP-002 closure is fabricated or implied.

## Definition of Done

1. The atomic scope in POST-SUBTASK-028 is completed without absorbing sibling work or weakening any protected requirement, control, split, judging rule, rights decision, or security boundary.
2. Every acceptance criterion has a PASS, FAIL, or BLOCKED evidence row; only all applicable PASS results permit completion, and negative results remain preserved.
3. Every declared output exists at its documented location with content hash, schema/version, provenance, input identities, and an explicit production/experimental/conditional/rejected eligibility state where applicable.
4. Every required validation entry is executed or explicitly blocked with reason; NEW_AUTOMATED_TEST_REQUIRED entries are implemented and run before completion.
5. No secrets, restricted raw payloads, fabricated data, fabricated metrics, fabricated rights approvals, or unsupported maturity claims are committed or imported into Jira.
6. The canonical record, generated Markdown, AI work packet, source manifest, indexes, import derivatives, change log, live Jira operational fields when connected, and READY/BLOCKED queues are synchronized and pass strict validation.
7. The output set `artifacts/data_lake/historical_expansion_acquisition_manifest.json` is demonstrably consumable by POST-SUBTASK-029 without manual reconstruction or undocumented state.

## Required Tests / Validation

- **EXISTING_AUTOMATED_TEST** / `REGRESSION` — `tests/test_w19_foundation.py` — Run as a regression check after completing POST-SUBTASK-028; retain command, exit code, and relevant output.
- **CHRONOLOGICAL_REPLAY** / `CHRONOLOGICAL_REPLAY` — `artifacts/data_lake/historical_expansion_acquisition_manifest.json` — Demonstrate cutoff eligibility and negative leakage behavior using pinned chronology; future/same-game/postgame contamination must fail closed.
- **SCIENTIFIC** / `SCIENTIFIC` — `artifacts/data_lake/historical_expansion_acquisition_manifest.json` — Evaluate the precommitted hypothesis/metric against pinned data and splits; preserve null, negative, unstable, and failed results.
- **INTEGRATION** / `INTEGRATION` — `artifacts/data_lake/historical_expansion_acquisition_manifest.json` — Prove the produced artifact can be parsed and consumed by the next declared task without manual reconstruction or hidden state.
- **REPRODUCIBILITY** / `REPRODUCIBILITY` — `ISSUE_COMPLETION_MANIFEST` — Record exact source/data/code/config/tool/runtime identities and content hashes needed to reproduce or audit the result.
- **NEW_AUTOMATED_TEST_REQUIRED** / `NEW_AUTOMATED_TEST_REQUIRED` — `NEW_TEST_REQUIRED::POST-SUBTASK-028` — Add the smallest deterministic unit/integration/E2E test that directly proves at least one issue-specific acceptance condition not already covered by an existing test.

## Required Evidence

- `artifacts/data_lake/historical_expansion_acquisition_manifest.json` with SHA-256, producer command/version, source/endpoint request identities, season/type and domain/grain coverage, schema versions, immutable external paths/hashes, known-at/PIT state, provider failures, and negative findings.
- An acceptance matrix proving the bounded 2022-2025 tranche is nonterminal and every attempted acquisition has a PASS, FAIL, PARTIAL, UNAVAILABLE, or BLOCKED disposition without fabricated completeness.
- Disk/cleanup evidence showing bulk data remained under AGGIE_ANALYTICS_DATA_ROOT and reconstructible temporary or abandoned payloads were removed after validation.
- Exact commands/tool versions, exit codes, redacted credential checks, and downstream POST-SUBTASK-029 consumer validation.

## Completion Evidence Contract

```json
{
  "acceptance_matrix_required": true,
  "artifact_hashes_required": true,
  "completion_claim_limit": "IMPLEMENTED",
  "downstream_consumer": "POST-SUBTASK-029",
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

Validate that the expanded acquisition manifest independently enumerates source/endpoint, season/type, team/game, domain/grain, schema/version, missing/failure, immutable provenance, and historical known-at/PIT state, and that POST-SUBTASK-029 rejects missing, stale, hash-invalid, rights-blocked, or silently terminal-2022-2025 inputs.

## Expected Maturity After Completion

`IMPLEMENTED`

## Risk / Failure Conditions

- The 2022-2025 tranche is silently treated as terminal history or a convenience window replaces the approximately 2010-2025 expansion target.
- A weak domain causes an otherwise useful season to be globally discarded or incomplete evidence is promoted into an unsupported domain.
- An attempted source/endpoint/season/domain, provider limitation, partial response, schema version, or negative finding is omitted from the manifest.
- Bulk data escapes the external root, immutable identity is missing, credentials are exposed, or reconstructible temporary artifacts are retained after validation.
- The manifest cannot be deterministically consumed and fail-closed validated by POST-SUBTASK-029.

## Stop Conditions

- Stop rather than improvise if a required source, credential, rights decision, schema, authoritative target host, protected split, or upstream artifact is unavailable.
- Stop if the work would require weakening an acceptance control, changing a sealed judging rule, using future/same-game information, committing a secret, or bypassing provider controls.
- Stop and create/update a blocker if the observable acceptance criteria cannot be evaluated from saved evidence.

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
- Read the exact source sections in `jira/sources/issue_source_manifests/POST-SUBTASK-028.json`; inspect only the listed implementation files and prerequisite outputs.
- May modify only the files explicitly listed in `files_expected_to_be_touched`, declared new outputs, and the Jira/evidence records required by the completion protocol. An empty file list does not authorize arbitrary repository edits.
- Return exact commands, exit codes, artifacts, hashes, input identities, acceptance-matrix results, negative findings, and remaining blockers; narrative completion is insufficient.
