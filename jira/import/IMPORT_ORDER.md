# Import Order

1. Discover/configure the destination Jira project or space and complete `project/JIRA_TARGET_PROFILE.yaml`.
2. Choose **one** hierarchy CSV shape: current (`JIRA_CLOUD_CURRENT_IMPORT.csv`) or legacy administrator (`JIRA_CLOUD_LEGACY_EXTERNAL_SYSTEM_IMPORT.csv`). Do not import both aliases.
3. Dry-run a representative subset in a disposable project and validate field mapping, rich descriptions, encoding, and parent behavior.
4. Import the full ordered hierarchy: Epics first, then Stories/Tasks, then Sub-tasks.
5. Export `Local Issue ID ↔ Jira key/Jira ID` and run `tools/reconcile_jira_export.py`.
6. Discover valid workflow transition IDs and apply the desired-state plan only where the target workflow permits it.
7. Validate counts, hierarchy, descriptions, statuses, priorities, components, labels, custom fields, and execution-mode separation.
8. Create hard-dependency and related links from `JIRA_LINKS.csv`/REST templates using real Jira keys and discovered link-type names.
9. Validate links, complete `POST_IMPORT_VALIDATION_CHECKLIST.md`, and run all local validators.
10. Create the active board/filter emphasizing `post-wave`, `actionable`, and logical READY/BLOCKED states while excluding historical planning work by default.
