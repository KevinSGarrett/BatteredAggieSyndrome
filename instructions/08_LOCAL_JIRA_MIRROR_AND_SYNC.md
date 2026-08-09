# Local Jira Mirror, Index, and Synchronization Contract

`C:\BatteredAggieSyndrome\jira` is an AI-readable synchronization and traceability layer. It is not a second Jira database and must never silently override live BAT state.

## Authority model

- **Live Jira BAT:** mutable issue/workflow truth.
- **Repository governance/plans:** technical requirements, architecture, acceptance, protected rules.
- **Local `jira/`:** verified project/workflow metadata, stable issue-to-technical-source mappings, sync state, schemas, and optional local-only cache.

## Canonical structure

| Path | Role | Commit policy |
|---|---|---|
| `jira/README.md` | local mirror contract and operator entrypoint | committed |
| `jira/project.json` | verified project/site/board metadata | committed after read-only verification |
| `jira/field_catalog.json` | verified fields and their intended traceability use | committed after verification; no speculative custom fields |
| `jira/workflow_snapshot.json` | verified issue types/statuses/transitions | committed after verification |
| `jira/status_map.json` | conceptual-to-live BAT mapping | committed only when exact names/IDs/transitions verified |
| `jira/issue_source_map.json` | stable `BAT → EPIC/TASK/REQ/ADR/AC/docs/dependencies/PR` map | committed; reviewed with technical changes |
| `jira/sync_state.json` | last synchronization metadata and access state | committed only if intentionally used as project audit metadata |
| `jira/schemas/` | JSON schemas/contracts | committed |
| `jira/cache/` or `jira/snapshots/` payloads | optional full local issue snapshots | local-only by default; exclude secrets/churn |
| `jira/exports/` | temporary exports/reports | local-only by default |

Full issue text, comments, attachments, user data, or restricted content should not be committed merely because the AI benefits from a cache.

## First hydration procedure

1. Verify the exact Atlassian site and BAT project.
2. Fetch project/board metadata read-only.
3. Fetch issue types, fields, workflows/statuses/transitions.
4. Fetch a bounded representative set of issues to understand actual field conventions.
5. Populate metadata files with source IDs, names, timestamps, and verification flags.
6. Map conceptual states only where exact live transitions are confirmed.
7. Build stable technical mappings from explicit Jira links/fields and canonical repository sources.
8. Redact or omit secrets, private user data, comments not needed for execution, and attachment content.
9. Validate with `tools/validate_jira_control_plane.py`.
10. Review the diff before commit; do not commit routine status churn unless the repository explicitly adopts that model.

## Synchronization algorithm

For each read/update cycle:

1. Read `jira/sync_state.json` and determine cache age.
2. Fetch live Jira for any mutable field needed for the current decision.
3. Compare project/workflow IDs and detect schema/workflow drift.
4. Update stable metadata/map fields only from live verified values.
5. Never overwrite a curated technical mapping solely because a Jira description omits it; instead flag the mismatch.
6. Never overwrite live Jira status from the local mirror.
7. Record retrieval time and source identifiers.
8. Validate and report conflicts.

## Drift classes

### Workflow drift

A status, transition, field, issue type, or board filter changed. Block status writes until `status_map.json` is reverified.

### Execution-state drift

Local cached status/assignee differs from live Jira. Live Jira wins; update or ignore the stale cache.

### Technical-source drift

Jira links/IDs differ from `issue_source_map.json` or repository traceability. Apply source precedence, inspect the active task, and correct the erroneous side. Do not silently choose.

### Integration drift

Jira says Done but PR is open/failed/unmerged, or GitHub is merged but Jira remains In Progress. Determine real state, update Jira meaningfully, and record any DoD gap.

## Issue source-map contract

A populated mapping should contain, as applicable:

```json
{
  "BAT-123": {
    "internal_epic_ids": ["EPIC-008"],
    "internal_task_ids": ["TASK-041"],
    "requirement_ids": ["REQ-184"],
    "adr_ids": ["ADR-123"],
    "acceptance_control_ids": ["AC-012"],
    "source_documents": ["docs/..."],
    "dependencies": ["BAT-100"],
    "pull_requests": ["https://github.com/.../pull/1"]
  }
}
```

Only real verified IDs belong here. Empty arrays are better than invented mappings.

## Write safety

No Jira status transition until:

- `project.json.live_access_verified` is true;
- `status_map.json.live_workflow_verified` is true;
- the current issue source status is live-read;
- the target transition ID is available for that issue;
- required transition fields are known;
- the resulting state matches the task state machine.

Do not create custom fields automatically. Prefer existing Jira fields plus a standardized source-reference block unless a real repeated need justifies an administrative change.

## Offline behavior

When Jira is unavailable:

- do not assume cached mutable status is current;
- do not queue blind status transitions;
- continue only work already safely claimed and nonconflicting;
- record local progress in Git/PR/task packet;
- synchronize Jira once access returns;
- if ownership/dependency ambiguity is material, block or select unrelated work.

## Retention and privacy

Keep only the minimum cache needed for deterministic execution. Define retention if full issue snapshots are enabled. Do not package or commit Atlassian credentials, cookies, tokens, personal data, attachment binaries, or irrelevant private comments.

## Validation

Run:

```powershell
python -B tools/validate_jira_control_plane.py --repo-root . --strict
```

Validation must fail if workflow mappings claim verification without project access, if issue keys/IDs are malformed, if mapped repository paths do not exist, or if status writes would rely on empty/unverified transitions.
