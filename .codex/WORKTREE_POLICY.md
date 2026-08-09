# Codex Worktree Policy

Default isolated branch naming: `codex/<epic>-<task>`.

## Use a worktree when
- implementation can be isolated behind a stable interface;
- a change is experimental or may be rejected;
- parallel work would otherwise create unrelated file churn.

## Do not parallelize
- simultaneous edits to unfrozen canonical schemas;
- requirements/ADR renumbering;
- shared PIT/leakage contracts;
- promotion rules or protected validation state;
- the same migration or manifest file.

Before merge, rebase/update against the authoritative branch, run repository validation, resolve shared-contract changes explicitly, and preserve REQ/ADR traceability.
