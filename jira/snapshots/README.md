# Jira-local Snapshots

Run `python jira/tools/snapshot_jira_state.py` after a major import, release gate, evidence acceptance, or bulk status reconciliation. Snapshots contain only Jira-local issue operational metadata, key maps, queue state, and hashes—not duplicated project source/data files. Restore by comparing a snapshot to canonical records and applying a reviewed reconciliation; never blindly overwrite specifications.
