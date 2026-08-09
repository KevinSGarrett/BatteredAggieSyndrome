# Wave 18 — Experimentation & Autonomous Research Architecture

## Purpose
Wave 18 converts the research plane into a governed, replayable experimentation system. It may propose and execute development experiments, compare candidates, preserve negative evidence, and prepare challengers for external W17 promotion review. It may never redefine the rules used to judge itself.

Wave 18 is **reference/contract maturity**. It does not claim trained model winners, protected scores, feature promotions, BAS significance, or champion changes.

## Protected inputs
The research plane treats these as externally governed inputs:
- W07 canonical identity;
- W08 PIT/leakage rules;
- W09 raw-field lineage;
- W10 feature lifecycle;
- W14 A&M no-adjustment baseline;
- W15 BAS definitions;
- W16 coherent model/output contracts;
- W17 protected splits, metrics, scorecards, threshold methods, and promotion states.

`JRS-W17-001` hash-seals the W17 judging-rule files. A mismatch blocks execution or adoption.

## Logical planes
### Hypothesis plane
Stores falsifiable research questions, expected mechanism, target, comparator, failure condition, allowed data/features, and owner.

### Experiment-definition plane
Creates immutable result-independent identities binding code, data, features, model config, development split, metric registry, threshold-method hash, environment, seeds, resource budget, and parent lineage.

### Execution plane
Runs only approved experiments in an isolated worktree or immutable source snapshot. Workers write experiment-local outputs and cannot mutate protected governance.

### Tracking plane
Canonical experiment/result/evidence records are tool-neutral. MLflow Tracking is the preferred replaceable adapter for search/UI/artifact logging, not governance truth.

### HPO/search plane
Optuna is the preferred replaceable adapter for development-only hyperparameter search. Protected holdout and forward-shadow metrics are prohibited search objectives.

### Tournament plane
Feature and model tournaments compare predeclared candidate sets under common development evidence. Tournament rank is research triage, not promotion.

### Replay plane
Candidates must resolve identity, data, code, environment, artifacts, and judging-rule seal before challenger adoption.

### Adoption plane
Research governance may reject, mark inconclusive, retain, or adopt as challenger. It cannot emit production `PROMOTE`.

## Lifecycle
`HYPOTHESIS → EXPERIMENT_SPEC → APPROVAL → QUEUED → ISOLATED_RUN → RESULT_PACKET → TOURNAMENT/COMPARISON → REPLAY → ADOPT/REJECT/INCONCLUSIVE → EXTERNAL_W17_PROMOTION_REVIEW`

Every transition is append-only and attributable.

## Negative results
Failed, rejected, dominated, pruned, and inconclusive experiments remain searchable. Configuration changes create child experiments rather than overwriting failed attempts.

## Feature tournament
A feature tournament must:
- admit PIT-safe candidates only;
- use a frozen baseline feature set;
- retain target-specific lifecycle semantics;
- include ablation/stability evidence;
- retain rejected candidates;
- never directly emit CORE, SUPPORTED, or PROMOTE.

## Model tournament
Every model tournament includes strong simple comparators. Complex models do not compete only against other complex models. A&M tournaments retain `TAMU-SP-00` no-adjustment baseline. Market-augmented candidates do not replace the pure-football lane.

## HPO
Search spaces, sampler/pruner, objectives, development split, budget, concurrency, and seed policy are versioned before trials. Protected metrics cannot influence search.

## Worktrees/resources
Parallelism is bounded by dependency readiness, shared-contract ownership, CPU/RAM/GPU/storage limits, artifact pressure, and merge risk. Idle compute does not authorize future-wave work. Paid remote compute requires explicit user approval.

## Artifact policy
Large datasets and model binaries remain outside cumulative ZIPs. Repository evidence stores manifests, hashes, URIs/paths, schema/version metadata, and reproducible instructions.

## Protected-result one-way rule
Protected results may reach promotion review. They may not flow back into HPO, feature selection, model selection, threshold creation, scorecard changes, or hypothesis rewriting.

## Completion
Wave 18 requires first-class experiment identity, queues, feature/model tournaments, HPO contracts, worktree/resource governance, replay/adoption, negative-result retention, judging-rule sealing, advanced-challenger admission, and W19 handoff. No trained winner is required or claimed.
