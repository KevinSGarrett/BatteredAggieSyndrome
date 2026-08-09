# Post-Import Validation Checklist

- [ ] Imported issue count equals the total in `validation/COVERAGE_REPORT.json`.
- [ ] Every Local Issue ID appears exactly once and maps to one real Jira key.
- [ ] `POST_IMPORT_KEY_MAP_TEMPLATE.csv` remains entirely blank for Jira keys/IDs.
- [ ] `POST_IMPORT_KEY_MAP.csv` contains only keys/IDs returned by the destination Jira site and agrees with canonical records.
- [ ] Reconciliation was first run with `--dry-run`; `reconciliation/SYNC_CONFLICTS.csv` was reviewed and every conflict was resolved or deliberately retained.
- [ ] No Jira `Done` state bypassed local complete/verified evidence, protected completion controls, or dependency gates.
- [ ] All 50 Epics exist; historical and post-wave Epics remain distinguishable.
- [ ] Stories/Tasks have the intended Epic parent and every Sub-task has the intended Story/Task parent; no orphan or impossible relationship exists.
- [ ] Descriptions preserve scope, acceptance criteria, Definition of Done, tests, evidence, stop conditions, and source references.
- [ ] Logical workflow, implementation maturity, evidence state, and execution mode survived as separate concepts.
- [ ] Controlled labels/components imported without uncontrolled variants; the default active board excludes historical planning items.
- [ ] Every dependency/related link in `JIRA_LINKS.csv` exists with the correct direction/type after real link types were discovered.
- [ ] READY items have no unresolved hard dependency; blocked items expose their unblock condition; deferred/conditional work is not pulled into the core release board.
- [ ] Requirement, acceptance-control, ADR, risk, gap, test, artifact, and source traceability remains resolvable by Local Issue ID.
- [ ] A sample of source references resolves to the same repository path/hash/anchor.
- [ ] `python -B jira/tools/validate_jira_pack.py`, `validate_source_refs.py`, `validate_dependencies.py`, `validate_import_files.py`, and `run_second_pass_audit.py` all pass after reconciliation.
