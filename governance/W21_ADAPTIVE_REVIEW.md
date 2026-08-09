# W21 Adaptive Review

## Decision
The W21 mission remains correct. No new wave is needed and no future-wave mission is reallocated.

## Material adaptation
The master prompt listed Prefect as a strong default, not an invariant. The inherited repository still has zero runtime dependencies and already contains bounded local research scheduling. Adding Prefect solely for W21 would increase installation/operational surface before a demonstrated need for distributed scheduling, UI-backed orchestration or remote agents.

W21 therefore implements a **durable local standard-library orchestration kernel behind explicit step contracts**. This is a functional starter, not a claim that Prefect is inferior. W23 may revisit the backend when target-hardware/runtime/observability evidence exists.

## Protected boundaries retained
- W17 judging-rule seal remains promotion authority.
- W18 research cannot self-promote.
- W19 PIT/lineage is mandatory.
- W20 registry remains non-authoritative for champion selection.
- Failed/quarantined runs fail closed and do not silently mutate checkpoint history.
