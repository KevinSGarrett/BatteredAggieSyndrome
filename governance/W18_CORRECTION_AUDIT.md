# Wave 18 Full-Rebuild Correction Audit

## Executive finding

Two earlier Wave 18 artifact pairs are rejected.

The first draft was structurally cumulative but materially underbuilt.

The first corrected draft improved Wave 18 substantially, but a second audit found it still failed the depth/ownership standard of the 25-wave program. The decisive defects were:

1. several central Wave 18 subsystems still existed mostly as thin contracts/reference snippets rather than a robust reference implementation;
2. `TASK-164 — Define advanced challenger admission criteria` is **owned by W18** but remained `PLANNED`;
3. completion checks focused too heavily on file counts, hashes and top-level master coverage instead of all W18-owned tasks, subsystem depth and executable integration;
4. result/store/queue/resource/tournament/replay/worktree/promotion boundaries were not integrated deeply enough for W19/Codex handoff.

This audit therefore rejects both earlier W18 pairs and rebuilds Wave 18 again against the exact authoritative W17 parent.

## Authoritative W17 parent

W17 cumulative SHA-256:

`f718edac011ed711f7bee6edee871832619aaf8b68398af6265117ead3b56a7b`

W17 hydration SHA-256:

`d24a09b4efdcf104638425d113b601493c6d51515ab0ebf71dce94618b9ac34f`

Parent canonical members: **521**

Full-rebuild invariant: every one of those 521 members must remain present in the final W18 cumulative tree.

## Rejected W18 artifacts

### Rejected thin draft
Cumulative:

`c9c690c20aa40bfe7e952b0b94a3eb0fabe27f080afc13354d66d02d2b2b7bc9`

Hydration:

`5c3c8581af7a0cfe0ca0938579f00ef09ffb8e05e3b6474d13fd8e72dbd87033`

### Rejected first corrected draft
Cumulative:

`40e04b5da6a7a1c760453bfc6c8769430bbdff304ad53964cc7abcf02bae9dfb`

Hydration:

`fb64510c594a8f21b52e7e277b16c535d5899f3c0b72a60d7ba89bf108ac064f`

Neither rejected pair may be used as the W19 parent.

## Full-rebuild acceptance standard

The replacement Wave 18 must satisfy all of the following simultaneously.

### Cumulative integrity
- exact W17 parent verified;
- zero W17 member deletions;
- canonical root remains `Aggie_Analytics_Engine/`;
- cumulative ZIP is built deterministically twice;
- hydration pack binds to the accepted cumulative SHA;
- W18→W19 verifier passes.

### Complete W18 owner-task coverage
Every task with `owner_wave == W18` must be DONE at appropriate reference/governance maturity, including:
- TASK-134
- TASK-135
- TASK-136
- TASK-137
- TASK-138
- TASK-139
- **TASK-164**

### Master Wave 18 coverage
The following are first-class systems, not label-only sections:
- experiment tracking;
- hyperparameter optimization;
- feature tournament;
- model tournament;
- experiment queue;
- research hypotheses;
- branches/worktrees;
- automatic replay;
- promotion gates;
- rejection;
- experiment lineage;
- immutable judging rules;
- Phase-5 challenger framework.

### Executable subsystem coverage
The repository must contain executable reference surfaces for:
- canonical experiment identity;
- transactional local metadata/evidence store;
- append-only queue/hash chain;
- bounded resource scheduler;
- result semantic compatibility;
- feature tournament;
- model tournament;
- development-only HPO reference;
- artifact-class/manifest policy;
- replay engine;
- worktree/shared-contract locks;
- one-way promotion-review bridge;
- advanced challenger admission.

### Negative governance tests
Tests must prove that:
- protected metrics cannot enter HPO/research packets;
- research plane cannot emit `PROMOTE`;
- A&M specialization tournaments require `TAMU-SP-00`;
- incompatible lanes/splits/data semantics cannot be directly ranked;
- blocked temporal fields cannot enter feature tournaments;
- W17 seal mutation is detected;
- paid compute cannot start without approval;
- large/restricted artifact classes cannot be committed as allowed research artifacts;
- advanced challengers remain blocked without conventional baseline evidence.

## Completion maturity

Wave 18 full rebuild is still **reference implementation/governance maturity**.

It does not claim:
- trained feature/model winners;
- protected benchmark values;
- calibrated OOD/disagreement thresholds;
- BAS/Aggie Excess significance;
- nonzero A&M specialization value;
- production champion promotion.

Those remain future empirical/operational work.

## Final artifact identity

The final accepted W18 v0.18.2 cumulative/hydration SHA values are written only after deterministic double-build and external pair verification. Until that final packaging gate passes, this repository remains a working full-rebuild candidate rather than an authoritative W19 parent.
