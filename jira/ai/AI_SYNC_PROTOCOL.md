# AI Sync Protocol

1. Treat canonical JSON as authoritative for specification, scope, hierarchy intent, technical dependencies, source/governance references, acceptance criteria, Definition of Done, tests, protected constraints, and expected artifacts.
2. Treat Jira as authoritative for assigned key/ID and raw live operational values such as status, assignee, sprint, board order, comments, and execution ownership.
3. Export `Local Issue ID`, `Issue key`, optional numeric `Issue ID`, status, assignee, sprint, and update timestamp. Run `python -B jira/tools/reconcile_jira_export.py <export.csv> --dry-run` first.
4. Resolve key/status conflicts rather than using last-write-wins. A Jira `Done` state cannot become local `DONE` until local evidence is `COMPLETE` or `VERIFIED`; dependency/evidence gates may safety-normalize an unsafe Jira state.
5. Run live reconciliation only after reviewing dry-run output. It writes actual mappings to `import/POST_IMPORT_KEY_MAP.csv`, preserves `import/POST_IMPORT_KEY_MAP_TEMPLATE.csv` as blank, records conflicts in `reconciliation/SYNC_CONFLICTS.csv`, and rolls back on strict-validation failure.
6. After any local specification or operational update, rebuild all derivatives, validate the Jira pack/source refs/dependencies/import artifacts, review READY/BLOCKED changes, append only material history events, and snapshot before/after major transitions.
