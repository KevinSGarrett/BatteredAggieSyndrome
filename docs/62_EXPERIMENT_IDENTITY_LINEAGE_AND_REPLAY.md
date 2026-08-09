# Experiment Identity, Lineage & Replay

## Result-independent identity
Experiment identity is computed before execution. Metrics, completion time, recommendation, and result quality are excluded.

Identity-bearing inputs include:
- hypothesis ID and parent experiment;
- task/candidate family;
- source revision;
- data snapshot;
- feature registry/version;
- model configuration;
- development split;
- metric registry hash;
- threshold-method hash;
- environment fingerprint;
- seed policy;
- resource budget.

Changing an identity-bearing input creates a new experiment ID.

## Attempts vs child experiments
An attempt may repeat the same immutable experiment spec after infrastructure interruption. If configuration, code, data, features, seed policy, split, or search space changes, it becomes a child experiment.

## Artifact manifest
Each attempt records artifact logical name, SHA-256, byte size, artifact type, storage location, producer, sensitivity/redistribution class, and retention class. Large binaries remain external.

## Replay levels
1. **Structural replay** — all exact identities and sealed inputs resolve.
2. **Deterministic replay** — deterministic outputs hash-match.
3. **Statistical replay** — seeded stochastic outputs satisfy predeclared replay tolerances.
4. **Environment replay** — runtime/package fingerprint is reconstructable.

## Replay outcomes
- PENDING
- STRUCTURAL_VERIFIED
- VERIFIED
- MISMATCH
- BLOCKED_INPUT_MISSING
- BLOCKED_ENVIRONMENT_UNAVAILABLE
- NOT_REQUIRED

Replay mismatches are evidence, never silently waived.

## Challenger adoption
A candidate may be adopted as a challenger only after the required replay level succeeds. Challenger adoption is not W17 production promotion.

## Protected result isolation
Research result packets contain development evidence only. Protected W17 metrics remain outside the research/HPO feedback loop.
