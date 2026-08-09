# Blockers, Loop Detection, Anti-Overengineering, and Recovery

Autonomous agents fail when they repeat, manufacture progress, or add complexity instead of resolving the current requirement. This policy makes those failure modes explicit.

Machine companions: `policies/loop_and_retry_policy.json` and `policies/blocker_taxonomy.json`.

## What constitutes a loop

A loop exists when one or more occur:

- the same command with the same inputs produces the same result twice;
- a deterministic test/CI failure is rerun without diagnosis/change;
- the same edit is applied, reverted, and reapplied;
- dependency installation is repeated without a changed hypothesis/environment;
- Git status/cleanup/reconciliation is repeatedly checked without new evidence/action;
- the same documents are reread without a new question/decision;
- multiple plans/checklists are generated instead of implementing the accepted plan;
- three genuinely different approaches fail without new evidence toward the outcome.

## Retry limits

- Credible transient failure: retry the unchanged action once.
- Deterministic failure: no unchanged retry; diagnose first.
- Distinct diagnosed approaches: after three without progress, classify a blocker unless new evidence justifies another.

These are defaults, not permission to retry unsafe/destructive operations.

## Loop recovery algorithm

1. Stop the repeated action.
2. Capture exact command/input/result/environment/SHA.
3. State the current hypothesis and why it failed.
4. Inspect logs, diffs, source contracts, dependency/version/platform state.
5. Choose one materially different diagnostic or approach.
6. Define what result would confirm/refute it.
7. If still blocked after the limit, create/update the blocker record.
8. Move to independent Ready work when safe.
9. If no Ready work exists, produce a concise global blocker summary.

Do not “escape” by refactoring unrelated code, creating another repository, weakening a test, or opening a new ticket/PR for the same failure.

## Blocker categories

- `DEPENDENCY`
- `DATA_SOURCE`
- `CREDENTIAL_ACCESS`
- `SOURCE_RIGHTS`
- `SHARED_CONTRACT`
- `PROTECTED_GOVERNANCE`
- `CI_ENVIRONMENT`
- `AMBIGUITY`
- `EXTERNAL_SERVICE`
- `HUMAN_APPROVAL`
- `RESOURCE_CAPACITY`

A blocker is a specific condition, not a mood. Use `templates/BLOCKER_RECORD.md`.

## Required blocker content

- exact blocked outcome and condition;
- objective evidence/error identifiers;
- attempts and how each hypothesis changed;
- exact action/input/decision that unblocks;
- owner/authority and affected dependents;
- safe fallback, if any;
- independent Ready work selected;
- next review trigger.

Never mark completion, fabricate data, or substitute a weaker outcome without authorized scope change.

## Anti-overengineering gate

Before introducing significant complexity, answer:

1. What current requirement needs this now?
2. Which existing simpler approach fails, and what evidence proves it?
3. What measurable benefit is expected?
4. What new maintenance/security/cost/failure/migration burden appears?
5. Can the requirement be met with fewer moving parts?
6. How is the complexity tested, observed, rolled back, and eventually removed?

Do not introduce without a concrete need:

- new framework/service/database/queue/cache;
- microservices/Kubernetes/distributed orchestration;
- vector database or LLM dependency in deterministic forecasts;
- extra agents/control layers;
- complex schemas/abstractions/factories;
- elaborate test harnesses;
- neural/graph/live modeling;
- broad refactor unrelated to the Jira item.

Preserve reasonable extension points, but do not build speculative futures.

## Meaningful housekeeping

Housekeeping is valid only when it directly unblocks or safely integrates work, such as:

- resolving a real dirty-worktree ownership issue;
- repairing a broken required validator;
- pruning a verified merged branch/worktree;
- updating stale canonical pointers that cause wrong task selection;
- regenerating required manifests after intentional changes.

Housekeeping must not become the primary output of repeated cycles.

## Scientific anti-overengineering

- Use simple baselines and protected evaluation before complex candidates.
- Do not run massive hyperparameter sweeps without data sufficiency, budget, pruning, and baseline evidence.
- Do not build live/in-game before the pregame system is empirically stable and replayable.
- Do not add infrastructure that exceeds target hardware or operating needs.
- Null results and rejected complexity are valid progress when evidence is retained.

## Ambiguity handling

Resolve from canonical sources whenever possible. Block only material ambiguity that could violate security/rights/data/PIT/evaluation/identity/integration. For low-risk reversible details, make a labeled inference, validate, and continue.

Do not use clarification requests to avoid a best-effort implementation when the repository already contains the answer.
