# Current Jira Context

- Project state: W25 planning/design/handoff complete; **there is no Wave 26**.
- Jira pack: v2 second-pass hardened; 463 issues; strict audit `PASS`.
- Product state: implementation/real-data/empirical/production work remains governed by the post-wave graph; no missing evidence is fabricated.
- READY atomic issues: 3 — POST-SUBTASK-023, POST-SUBTASK-028, POST-SUBTASK-126.
- BLOCKED atomic/issues: 118.
- Start: read `jira/index/READY_QUEUE.csv`, then one selected canonical record, its source manifest, and `jira/index/ISSUE_GOVERNANCE_CONTEXT.csv`.
- Authority: `jira/reconciliation/SOURCE_AUTHORITY_MAP.md`.
- External boundaries: `jira/reconciliation/UNAVOIDABLE_EXTERNAL_ACTIONS.md`.
- Completion: rebuild all derivatives and run `python -B jira/tools/validate_second_pass.py`; code/file existence alone is not Done.
