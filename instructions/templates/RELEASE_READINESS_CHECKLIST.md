# Release Readiness Checklist

## Identity and scope

- Release/tag/candidate:
- Included PRs and Jira issues:
- Requirements/ADRs/acceptance controls:
- Code, config, schema, data, model, and forecast artifacts:
- Explicit exclusions:

## Validation

- [ ] Every included task satisfies the Definition of Done.
- [ ] Required CI and full applicable repository/domain suites pass at the intended head SHA.
- [ ] Repository, instruction, Jira-control, W25, security, and dependency validators pass.
- [ ] PIT/leakage/replay/provenance/evaluation gates pass where applicable.
- [ ] Migration/compatibility and rollback/restore were exercised where applicable.
- [ ] Source rights, privacy, retention, and redistribution boundaries are satisfied.
- [ ] Resource/runtime/freshness evidence is measured rather than guessed.
- [ ] No secret, restricted raw payload, cache, worktree, or unrelated artifact is included.

## Operations

- [ ] Known-good rollback or forward-fix target identified.
- [ ] Backup/restore and immutable artifact references recorded.
- [ ] Observability, alerts, ownership, and incident path are ready.
- [ ] Documentation/runbooks and release notes reflect actual behavior.
- [ ] Known limitations, null results, and unproven claims are explicit.

## Authorization and result

- Permission class:
- Required human approval, if any:
- Release decision: `READY | NOT_READY | BLOCKED`
- Evidence location:
- Re-entry condition if blocked:
