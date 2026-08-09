# Local ↔ Jira Sync Contract

## Local authority

The repository owns stable Local ID, issue specification/scope, hierarchy intent, source references, requirements/ADRs/acceptance controls, technical dependencies, acceptance criteria, Definition of Done, required tests/evidence, protected constraints, and expected artifacts.

## Jira authority

Jira owns the assigned Jira key/ID, current operational workflow status, assignee, sprint, board rank, comments, and current execution ownership.

## Conflict policy

- Never silently overwrite an authoritative field from the other side.
- Specification changes originate locally through version control and are then pushed to Jira.
- Operational changes originate in Jira and are mirrored locally through export/API reconciliation.
- If both sides changed the same authority-owned field, emit a conflict and require review.
- Preserve historical evidence and prior accepted states; do not rewrite them in place.

## Reconciliation safety and key-map contract

- Always run `python -B jira/tools/reconcile_jira_export.py <jira-export.csv> --dry-run` before a live reconciliation. Dry-run must not mutate canonical records or generated derivatives.
- `POST_IMPORT_KEY_MAP_TEMPLATE.csv` is an intentionally blank reusable import template. Assigned Jira keys/IDs belong in `POST_IMPORT_KEY_MAP.csv` and canonical operational fields.
- Raw Jira status, assignee, sprint, numeric ID, and update timestamp are preserved under `operational_jira`; the logical local state remains safety-normalized against dependency, evidence, deferment, and protected-completion gates.
- Jira `Done` cannot overwrite local state unless evidence is already `COMPLETE` or `VERIFIED`. Unsafe status requests and key mismatches are written to `reconciliation/SYNC_CONFLICTS.csv`.
- Live reconciliation is transactional: it restores canonical records and derivatives if strict validation fails.

## Required update sequence

1. For Jira-originated changes, export `Local Issue ID` plus operational fields and run the reconciliation tool in `--dry-run` mode; resolve conflicts before committing. For local specification changes, edit only canonical JSON through version control.
2. Apply the authority-appropriate change. Live reconciliation writes a material event only after strict validation; manual local changes must append their own material event without rewriting accepted historical evidence.
3. Run `python -B jira/tools/rebuild_all_derivatives.py` so Markdown, packets, source manifests, traceability, queues, imports, and payloads are rebuilt together.
4. Recompute and inspect READY/BLOCKED state; aggregate gates never enter the atomic execution queue.
5. Run `python -B jira/tools/validate_second_pass.py` and `python -B jira/tools/run_second_pass_audit.py`.
6. Resolve conflicts instead of silently overwriting authority-owned fields.
7. Snapshot Jira-local operational state before/after major imports, reconciliations, or release transitions.
