# Worktree, Concurrency & Resource Governance

## Isolation
Code-changing experiments use a dedicated Git worktree when Git metadata is available or an immutable verified source snapshot when operating from packaged ZIP handoffs.

## Protected paths
Experiment workers cannot mutate W17 protected split/metric/threshold/promotion files, ground truth, BAS definitions, cumulative historical results, or protected acceptance criteria.

## Shared contracts
Concurrent writes to an unfrozen shared contract are serialized. Read-only access may proceed concurrently.

## Resource declaration
Each experiment declares CPU, RAM, GPU/VRAM, disk/artifact estimate, trial count, concurrency class, and whether paid compute is required.

Paid compute is disabled unless explicitly authorized by the user.

## Local-first
W18 does not make Kubernetes, Redis, distributed schedulers, remote MLflow, or multi-node HPO mandatory.

## Cleanup
A worktree/source snapshot cannot be discarded before the result packet, artifact manifest, and replay/adoption state are captured. `.git`, caches, large model binaries, and large raw outputs never enter cumulative ZIPs.
