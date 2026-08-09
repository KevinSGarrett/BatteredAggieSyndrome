# Hypothesis & Experiment Queue

## Hypothesis record
Each hypothesis includes a stable ID, falsifiable statement, mechanism/rationale, target, comparator, allowed inputs, proposed experiment family, disconfirming evidence, owner, priority, and lifecycle state.

## Hypothesis lifecycle
`PROPOSED → TRIAGED → APPROVED_FOR_EXPERIMENT → TESTING → SUPPORTED_CANDIDATE | REJECTED | INCONCLUSIVE | DEFERRED`

Reopening a rejected hypothesis requires a materially new basis and creates a new version/record while preserving the earlier rejection.

## Experiment queue
An approved hypothesis becomes an immutable experiment specification before entering the queue. Queue transitions are append-only and hash chained.

## Queue priority
Priority depends on:
- dependency readiness;
- expected information value;
- risk reduction;
- A&M/national product value;
- compute/resource cost;
- implementation readiness;
- wave ownership.

Idle hardware is not a priority signal.

## Deduplication
Before admission:
- exact experiment identity duplicates are rejected;
- materially equivalent open experiments are linked;
- known failed children are surfaced;
- retries declare whether identity-bearing configuration changed.

## Failure semantics
Infrastructure failure is not scientific rejection. Scientific rejection is not infrastructure failure. Governance failures block until corrected.

## Fairness
A&M specialization may receive disproportionate research attention, but may not starve required national baselines, PIT correctness, data-quality work, or protected governance.
