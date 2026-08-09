# Runbook — Migration and Data Recovery

## Trigger

Schema/data migration fails, is interrupted, corrupts state, or requires rollback.

## Before mutation

- identify source/target schema and version;
- establish single migration owner;
- verify backup/snapshot identity;
- test migration and rollback on representative non-production data;
- define idempotency/resume behavior;
- obtain Human Required authority for destructive/production migration.

## Failure response

1. stop further writes;
2. preserve logs/checkpoints and affected state;
3. determine partial application boundaries;
4. prevent readers from treating partial state as valid;
5. choose resume, rollback, restore, or forward-fix based on evidence;
6. verify data counts, hashes, constraints, lineage, and application compatibility;
7. update incident/migration record.

Do not delete or overwrite the only copy of valuable data.

## Exit criteria

State is restored or migrated consistently, validation passes, lineage is intact, and operational readers use an explicitly valid version.
