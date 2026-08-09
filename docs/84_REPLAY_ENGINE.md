# Automatic Replay and Reproducibility Engine

> **Wave 18 full-rebuild status:** reference implementation + governance contract. No protected model result or production promotion is claimed.

## Replay prerequisite

A candidate cannot be adopted as a challenger until required replay evidence resolves the exact experiment spec, immutable inputs, code/environment, artifact manifest, and W17 judging-rule seal.

## Checks

Replay validates experiment ID, data snapshot hash, feature/version hash, model configuration, code tree/commit, environment lock, seed/stochastic policy, judging-rule seal, artifact hashes, output schema, and development metrics within declared tolerance.

Each mismatch has a distinct status such as INPUT_MISMATCH, CODE_MISMATCH, ENVIRONMENT_MISMATCH, JUDGING_RULE_MISMATCH, ARTIFACT_MISSING, or OUTPUT_MISMATCH.

## Deterministic versus stochastic

Deterministic stages require exact replay unless an implementation-specific deterministic serialization difference is explicitly normalized. Stochastic models declare seeds, runtime/library versions, and a predeclared numerical/statistical tolerance. Tolerance cannot be chosen after observing the replay difference.

## Automatic replay

The queue can automatically create a REPLAY_PENDING event after successful development execution. Replay runs in a fresh worktree/source snapshot and should not reuse mutable output directories. Replay success is stored independently of the source attempt.

## Failure policy

Replay failure blocks challenger adoption. It does not automatically prove the scientific idea is false; the failure may indicate infrastructure, environment, or nondeterminism problems requiring a corrected child experiment.
