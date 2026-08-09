# Research Queue, Scheduler, and Bounded Resource Admission

> **Wave 18 full-rebuild status:** reference implementation + governance contract. No protected model result or production promotion is claimed.

## Queue philosophy

Research automation is not permission to consume every available resource or jump ahead in the wave plan. The queue is an ordered set of approved research work whose dependencies, owner wave, judging-rule seal, shared-contract mutation scope, and resource budget have been checked.

## States and actors

The canonical lifecycle is `PROPOSED → APPROVED → QUEUED → RUNNING → SUCCEEDED/FAILED → REPLAY_PENDING → REPLAY_VERIFIED → ADOPTED_AS_CHALLENGER/PROMOTION_REVIEW_REQUIRED/REJECTED/ARCHIVED`.

Research agents may propose. Research governors approve/reject and make challenger-adoption decisions. Schedulers enqueue admitted work. Experiment workers execute. Replay verifiers verify. No research-plane role has a `PROMOTE` capability.

## Priority

Priority is derived from MUST/SHOULD/RESEARCH/COULD classification, dependency readiness, active owner wave, queue age, failure/retry state, and shared-contract conflicts. Priority does not override protected gates.

Idle GPU/CPU is never sufficient justification to run a future-wave task. A blocked task remains blocked even when compute would otherwise sit idle.

## Resource admission

Every experiment declares CPU threads, RAM, optional GPU slots/VRAM, disk/artifact budget, trial budget, and whether paid compute is requested. Admission compares that request with the current resource pool and returns explicit rejection reasons.

Remote paid compute is disabled unless the user has explicitly approved it. This is a gate, not a cost-estimation hint.

## Shared-contract locks

Work that mutates canonical schemas, W08 temporal contracts, W10 feature lifecycle, W15 BAS labels, W16 target schemas, or W17 protected rules is serialized and normally prohibited from autonomous research worktrees. Ordinary isolated experiments may run in parallel when their inputs are frozen and output paths are experiment-local.

## Retries

Operational retries are distinguished from scientific child experiments. A transient I/O failure can create another attempt under the same experiment identity. Changing parameters/features/model/data creates a child experiment. Retry budgets and stop conditions are explicit so automation cannot enter infinite loops.
