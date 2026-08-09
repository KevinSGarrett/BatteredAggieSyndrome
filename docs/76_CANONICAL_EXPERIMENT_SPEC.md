# Canonical Experiment Specification and Identity

> **Wave 18 full-rebuild status:** reference implementation + governance contract. No protected model result or production promotion is claimed.

## Purpose

Every research execution must have a result-independent canonical identity before the first metric is produced. The identity exists so that repeated executions, failed trials, child experiments, replays, and external tracking tools can all point at one immutable definition rather than a mutable notebook or UI run.

The canonical experiment specification binds the scientific question, target, model/feature configuration, point-in-time data snapshot, feature registry version, code state, environment, development split, metric registry, W17 judging-rule seal, stochastic configuration, resource budget, and parent lineage. Result values, rank, promotion decisions, protected metrics, and elapsed time are prohibited from identity material.

## Identity fields

Required identity fields are organized into six groups.

**Scientific intent:** hypothesis ID, experiment class, target, lane, comparator/baseline, expected mechanism, disconfirming criterion.

**Data identity:** canonical dataset snapshot ID, point-in-time cutoff policy version, entity map version, temporal registry version, materialization manifest hash, training cutoff.

**Feature identity:** raw-field registry version, feature lifecycle registry version, transformation version, feature-set ID, explicit exclusions and lane restrictions.

**Model identity:** model family, architecture/configuration, objective, target schema version, BAS anchor version when relevant, A&M specialization ID when relevant.

**Execution identity:** code commit/tree fingerprint, package/environment lock, random seed policy, deterministic/nondeterministic declaration, hardware class when materially relevant.

**Governance identity:** development split, metric registry version, threshold-method version, W17 judging-rule seal hash, owner wave, required acceptance controls.

## Canonicalization

Identity serialization uses deterministic canonical JSON: mapping keys are sorted, paths are normalized, volatile runtime values are excluded, set-like values are ordered, and floating-point values are serialized deterministically. The resulting SHA-256-derived `EXP-*` ID is stable across tracking backends.

An experiment specification cannot be edited after execution begins. A material change creates a child experiment with `parent_experiment_id` and a reason such as `HYPERPARAMETER_CHANGE`, `FEATURE_CHANGE`, `DATA_REFRESH`, `CODE_CHANGE`, `BUG_FIX`, `REPLAY`, or `RESOURCE_ONLY_RETRY`.

## Collision and duplication rules

If an `experiment_id` already exists with the identical canonical payload, the system treats a new request as a duplicate/retry request rather than a new experiment. If the same ID maps to different canonical JSON, execution stops because this represents an identity collision or corrupted store.

A failed attempt is not replaced. Attempts are numbered under the same experiment only when scientific identity is unchanged and the retry reason is operational rather than scientific.

## External tools

MLflow run IDs, Optuna study/trial numbers, worktree paths, process IDs, host names, timestamps, and artifact-cache paths are external references. They are never the canonical identity and may change without changing the experiment definition.

## Acceptance

The reference implementation in `aggie_analytics.experimentation.lineage` and `store` must demonstrate stable IDs, duplicate detection, result-field rejection, transactional storage, and append-only attempt/result evidence. W19+ may extend storage without changing these semantics.
