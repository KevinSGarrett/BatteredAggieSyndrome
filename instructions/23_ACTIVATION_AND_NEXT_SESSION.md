# First Activation and Next Autonomous Session

This runbook is the exact bridge from the delivered instruction pack to the first real Codex implementation session on the user’s Windows machine. It separates safe read-only activation from operations that require explicit approval.

## 1. Install without destroying local state

Use the complete updated repository artifact only as an incoming comparison/staging source. Do not unzip it over `C:\BatteredAggieSyndrome` until the existing local Git and working-tree state are understood.

On the actual machine:

```powershell
Set-Location C:\BatteredAggieSyndrome
python -B tools\audit_control_plane.py --repo-root . --output artifacts\control-plane-audit.json
git status --short --branch
git remote -v
git branch --all --verbose --no-abbrev
git worktree list --porcelain
git log --graph --decorate --oneline --all -n 100
```

Compare incoming files with the canonical checkout and preserve all unexplained local changes. Apply the instruction-system update on a controlled branch/worktree after repository identity is established.

## 2. Reconcile GitHub

The discovery-time remote was empty. Recheck it; that fact can change.

- If the remote remains empty and trusted local history exists, initial publication is `HUMAN_REQUIRED`.
- If both local and remote now have related history, fetch and compare before choosing integration.
- If histories are unrelated, preserve both and obtain an explicit reconciliation decision.
- Never force-push, reset, or recreate history merely to make one side match.

After reconciliation, verify `main`, upstream tracking, merge methods, required checks, branch protection, secret scanning, dependency review, and automatic deletion of merged branches. Apply [19_GITHUB_ENFORCEMENT_RECOMMENDATIONS.md](19_GITHUB_ENFORCEMENT_RECOMMENDATIONS.md) only after the actual settings are inspected.

## 3. Hydrate Jira BAT

The audit account did not expose the requested BAT site. Connect an authorized identity to `kevinsgarrett.atlassian.net`, then read the project/board before any write.

Hydrate:

- project/board metadata;
- issue type hierarchy;
- fields and required fields;
- exact statuses and allowed transitions;
- board filter and current issue population;
- representative issues in each relevant type/status;
- issue-to-internal-source mappings and dependency links.

Update `jira/project.json`, `field_map.json`, `issue_type_map.json`, `workflow_snapshot.json`, `status_map.json`, `issue_source_map.json`, and `sync_state.json`, then run:

```powershell
python -B tools\validate_jira_control_plane.py --repo-root . --strict
```

Do not copy secret values or restricted private Jira text into the repository mirror.

## 4. Establish the first implementation lane

1. Read `AGENTS.md`, `instructions\START_HERE.md`, current state/backlog, and the live Jira board.
2. Resume any valid unfinished branch/PR/Jira item before creating new work.
3. Map the highest-priority dependency-ready live BAT issue to the internal handoff/task/REQ/ADR/AC sources.
4. If no live issue exists for required work, apply the issue-creation gate; do not explode the backlog.
5. Create/claim one branch and worktree using `codex/BAT-<number>-<short-description>`.
6. Complete the task packet and shared-contract ownership check.
7. Implement, progressively test, self-review, and update one coherent Draft PR.
8. Move Jira states only using verified transitions and real evidence.
9. Merge under policy, record outcome, clean safely, and continue.

## 5. Current first-choice work boundary

Repository evidence indicates:

- `HANDOFF-001` target-hardware evidence remains blocked until the declared representative Windows/Ryzen/32GB/RTX5060/NVMe host is available;
- `HANDOFF-002` source credentials/access/rights review is the independent P0 lane, but it is Ready only after real access and rights conditions are verified and a live BAT issue is mapped;
- no historical data, model performance, A&M lift, Aggie Excess, BAS effect, or hardware thresholds may be fabricated to simulate progress.

## 6. Recommended Codex launch instruction

Use this as the first instruction to the implementation session after installing/reconciling the pack:

> Work only in the canonical `C:\BatteredAggieSyndrome` repository or an approved sibling Git worktree. Read `AGENTS.md` and `instructions\START_HERE.md` first. Perform the read-only control-plane audit, reconcile local Git/GitHub/Jira state without destructive actions, and resume valid unfinished work before selecting new work. Follow the W25 terminal handoff, source precedence, Jira/Git policies, progressive testing, Definition of Done, protected PIT/evaluation/provenance rules, and autonomy permission matrix. Do not create Wave 26, duplicate the repository, discard unknown work, invent Jira/data/model/hardware evidence, weaken protected rules, leak secrets, create ticket/branch/PR spam, or repeat unchanged failures. Continue autonomously through meaningful dependency-ready work until a genuine human-required or global blocker is reached.

## 7. Activation completion evidence

The instruction system is fully activated only when:

- the actual local Git state and trusted history are documented;
- GitHub relationship/settings are reconciled and enforcement decisions recorded;
- the correct BAT site/project/workflow is hydrated and validated;
- one live issue maps through internal task/requirements/ADRs/acceptance/source documents;
- the first branch/worktree/task packet/PR lifecycle completes successfully;
- validators and tests pass from the real local checkout;
- unresolved external constraints remain honestly marked rather than guessed.
