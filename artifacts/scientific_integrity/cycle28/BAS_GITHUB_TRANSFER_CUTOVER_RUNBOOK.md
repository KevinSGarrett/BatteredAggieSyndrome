# BAS GitHub transfer cutover runbook

Disposition until separate exact authorization: `BAS_REPOSITORY_TRANSFER_PREPARED_NOT_AUTHORIZED`

Recommended action: transfer the existing public repository `KevinSGarrett/BatteredAggieSyndrome` to `GridironCortex/BatteredAggieSyndrome`. Do not create a disconnected target repository first.

Cycle #28 did not execute this transfer.

## Preconditions (all required)

1. Operator hold released or an exact cutover authorization names source, target, visibility, and window.
2. No live Week 1 capture owners.
3. Open PR dependencies (#678, #679, Cycle #28 successors, #654 untouched) are classified safe.
4. Integration branch `foundation/gridiron-cortex-contract-boundary` is preserved by verified Git bundle and independently restored.
5. All linked worktrees inventoried.
6. `GridironCortex/BatteredAggieSyndrome` does not already exist, or an exact conflict resolution is authorized.
7. Acting account has org permission to transfer into GridironCortex.
8. Settings inventory is complete with secret/variable **names only**.

## Cutover steps (only after authorization)

1. Confirm source `KevinSGarrett/BatteredAggieSyndrome` and target org/name/visibility.
2. Transfer the existing repository; do not copy.
3. Update `origin` explicitly in:
   - `C:\BatteredAggieSyndrome` (authoritative active checkout)
   - `C:\All-22\repos\BatteredAggieSyndrome` (integration clone)
   - every linked worktree
4. Verify Actions, secret/variable names, rulesets, apps, PRs, issues, releases, and external scripts.
5. Do not rely indefinitely on GitHub redirect behavior.

## Rollback

Restore remotes to `KevinSGarrett/BatteredAggieSyndrome` if the transfer is reversed. Re-verify worktrees and the integration bundle.

## Non-effects

Repository ownership transfer does not admit All-22 data, merge the integration branch, release the operator hold, recover scientific trust, or change frozen forecast identities.
