# Pull Request Ready and Self-Review Checklist

Use this before changing a Draft PR to Ready. A checked box is a factual claim backed by the PR diff, test output, evidence artifact, or linked source.

## Identity, scope, and traceability

- [ ] Searched for an existing open PR and reused it when it already owns this Jira unit.
- [ ] Correct base/head repository, branch, Jira key, and current head SHA are recorded.
- [ ] The PR delivers one coherent Jira implementation unit or justified reviewable vertical slice.
- [ ] Jira, parent, internal `EPIC/TASK`, `REQ`, direct `ADR`, applicable `AC`, and canonical source links are complete.
- [ ] Included and explicitly excluded scope are clear.
- [ ] No required acceptance work is disguised as an optional follow-up.
- [ ] No unrelated cleanup, generated junk, cache, environment, artifact, or other-agent work is included.

## Complete diff review

- [ ] Reviewed the full base-to-head diff, not only the latest commit.
- [ ] Reviewed every staged/committed path for ownership and intent.
- [ ] Reviewed edge cases, failure behavior, error handling, and compatibility.
- [ ] Reviewed public interfaces, schemas, migrations, callers, consumers, and rollback implications.
- [ ] Material implementation decisions and alternatives are explained; an ADR/change proposal exists when required.

## Security, data, and science

- [ ] No secrets, credentials, private Jira text, restricted raw data, or sensitive payloads are present.
- [ ] Source access, license, redistribution, retention, and provenance obligations are addressed.
- [ ] PIT/known-at, target-game exclusion, revision identity, joins, leakage, missingness, and canonical identity are addressed where applicable.
- [ ] Protected evaluation/judging/promotion rules are unchanged unless the correct protected authority approved the change.
- [ ] No fabricated performance, maturity, A&M lift, BAS/Aggie Excess effect, target-hardware threshold, or completion evidence appears.
- [ ] Dependency and supply-chain impact was reviewed when dependencies changed.

## Tests and evidence

- [ ] Narrow focused tests pass.
- [ ] Impacted integration/contract/replay/domain tests pass.
- [ ] Mapped validators and required PR-readiness gates pass for the current head SHA.
- [ ] Deterministic failures were diagnosed and corrected rather than blindly rerun.
- [ ] Evidence paths, commands, exact results, environment, and limitations are recorded.
- [ ] Applicable items in `policies/definition_of_done.json` are satisfied.

## Integration readiness

- [ ] Shared-contract and worktree ownership conflicts are resolved.
- [ ] Required CI/reviews are current for the final head SHA.
- [ ] Jira, branch, worktree, and PR state agree.
- [ ] Rollback/recovery is credible and documented proportionately.
- [ ] Honest maturity, null results, known limitations, and independently meaningful follow-ups are stated.
- [ ] Post-merge Jira update and branch/worktree cleanup plan is ready.
