# Wave 08 Adaptive Review

## Review
1. Planned objective remains correct: W08 owns PIT/known-at semantics and protected leakage fixtures.
2. W07 identity hierarchy is a sufficient prerequisite; no entity redesign is needed.
3. W06 availability/weather/regulatory findings materially refine domain temporal rules.
4. Highest-value improvement: separate knowledge time from target validity rather than forcing one generic as-of timestamp.
5. `prediction_eligible_at` is retained only as policy-derived/cache metadata, not raw truth.
6. No need to begin W09 feature registry or W19 materialization.
7. No architecture reason to add an online feature store/database/service.
8. Synthetic tests should be executable now, but maturity must remain explicit that real-data replay is pending.

## Result
Proceed with a bitemporal fail-closed PIT gateway, domain-specific snapshot contracts, immutable cutoff lineage and protected synthetic leakage battery. No 25-wave reallocation required.
