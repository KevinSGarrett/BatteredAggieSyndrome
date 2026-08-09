# W23 Backup, Restore and Retention Runbook

Use `python tools/backup_state.py --source <state-dir> --output <backup.zip>` at a checkpoint/transaction boundary. The backup is content-manifested with SHA-256 per payload file. Verify/restore with `python tools/restore_state.py --backup <backup.zip> --destination <empty-dir>`; restore rejects unsafe archive paths, coverage mismatch and hash mismatch.

Protected retention classes (`GOVERNANCE`, `PUBLISHED_FORECAST`, `CHAMPION_HISTORY`) are not eligible for automatic deletion. `TRANSIENT_CACHE` may be pruned only after its minimum retention interval and only by a later explicit operator/pruning implementation. Experiment evidence remains review-controlled.

A restore drill must compare the restored file set and hashes with the backup manifest before the restored state is considered usable. Backups do not legalize redistribution of restricted source data; storage location and access controls remain source-policy dependent.
