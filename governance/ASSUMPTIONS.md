# Assumptions

## ASSUMPTION-001 — SportsDataverse remains a strong public historical/PBP source through implementation
- **Status:** SUPPORTED_W06_CURRENT_SOURCE
- **Constraint class:** B
- **Notes:** W06 confirms the current SportsDataverse/cfbfastR repository remains a strong bulk historical source, but upstream publisher provenance/rights and schema versioning remain required.

## ASSUMPTION-002 — CFBD remains a strong supplemental source and API access is obtainable
- **Status:** SUPPORTED_W06_CURRENT_SOURCE_PENDING_MATERIALIZATION
- **Constraint class:** B
- **Notes:** W06 confirms CFBD remains active with current API/tier documentation and broad endpoint coverage; authenticated full materialization is still future implementation work.

## ASSUMPTION-003 — Local 32GB/RTX5060 environment can support Phases 1–4 with careful engineering
- **Status:** SUPPORTED
- **Constraint class:** B
- **Notes:** Source log 018; real benchmarks still to be measured.

## ASSUMPTION-004 — A&M official archives can support deeper historical roster/depth/injury reconstruction
- **Status:** PARTIALLY_SUPPORTED_W06
- **Constraint class:** B
- **Notes:** Official recent conference availability reporting substantially strengthens A&M/recent-season reconstruction, but national historical depth/injury coverage remains incomplete.

## ASSUMPTION-005 — A single canonical entity layer can reconcile major source identities with acceptable unresolved rate
- **Status:** PENDING
- **Constraint class:** A
- **Notes:** Large-scale entity-resolution validation not yet performed.

## ASSUMPTION-006 — PIT-safe weather forecast history exists for desired forecast snapshots
- **Status:** SUPPORTED_W06_WITH_ERA_LIMITS
- **Constraint class:** A
- **Notes:** NOAA model archives and Open-Meteo previous/single-run capabilities provide PIT-reconstructable issued forecasts for meaningful modern eras; coverage differs by model/variable/year.

## ASSUMPTION-007 — Historical market timestamps can be reconstructed sufficiently for market-augmented evaluation
- **Status:** PARTIALLY_SUPPORTED_W06_OPTIONAL_PAID
- **Constraint class:** A
- **Notes:** Timestamped historical market snapshots are obtainable from paid sources for modern eras, but older/deeper history and cost/rights remain constraints; pure-football lane remains independent.

## ASSUMPTION-008 — EADA can provide broad public/private baseline after materialization
- **Status:** SUPPORTED_PENDING_MATERIALIZATION
- **Constraint class:** B
- **Notes:** Recon identifies official federal path but raw annual file not in pack.

## ASSUMPTION-009 — Current five-phase framework remains useful after Wave06/implementation evidence
- **Status:** SUPPORTED_W06
- **Constraint class:** B
- **Notes:** W06 source research did not justify replacing the five-phase organizational framework; later evidence may still refine boundaries.

## ASSUMPTION-010 — The v1.2 reconnaissance pack covers all currently known architecture domains needed to begin planning
- **Status:** SUPERSEDED_BY_W06_EXPANSION
- **Constraint class:** B
- **Notes:** The v1.2 reconnaissance pack was sufficient to begin planning but W06 found important new/expanded source classes, especially official availability archives, issued forecast-run weather and regulatory-environment evidence.

## ASSUMPTION-011 — A modular monolith is sufficient for Phases 1-4 under the current local/snapshot-serving product scope
- **Status:** SUPPORTED_AS_DEFAULT
- **Constraint class:** B
- **Notes:** Revisit only if measured scaling/security/reliability needs justify service separation.

## ASSUMPTION-012 — Parquet plus DuckDB can satisfy the early local analytical workload
- **Status:** PENDING_IMPLEMENTATION_BENCHMARK
- **Constraint class:** B
- **Notes:** W07-W19 must benchmark data volume, entity workflows and memory behavior before treating this as final physical storage.

## ASSUMPTION-013 — Pregame product needs are compatible with immutable snapshot serving rather than synchronous online model execution
- **Status:** SUPPORTED_BY_CURRENT_SCOPE
- **Constraint class:** B
- **Notes:** W22 product requirements may challenge this if interactive latency semantics materially change.

## ASSUMPTION-014 — A network online feature store is unnecessary for the pregame system
- **Status:** SUPPORTED_BY_CURRENT_SCOPE
- **Constraint class:** B
- **Notes:** Future live/in-game work may require a different serving architecture without changing pregame PIT history.

## ASSUMPTION-015 — Official conference availability reporting can serve as a high-confidence recent availability lane only within each policy season/game/report scope
- **Status:** SUPPORTED_W06
- **Constraint class:** A
- **Notes:** Coverage varies by conference/start year and often applies only to conference games; noncoverage must remain UNKNOWN rather than healthy.

## ASSUMPTION-016 — Regulatory changes materially affect roster/experience feature semantics and require explicit effective dating
- **Status:** SUPPORTED_W06
- **Constraint class:** A
- **Notes:** W06 confirms recent roster-limit and eligibility changes make season-only implicit encoding inadequate for some roster/player features.

## ASSUMPTION-017 — Commercial advanced charting/tracking may add marginal predictive value but is not required for a strong core system
- **Status:** PENDING_EXPERIMENT
- **Constraint class:** C
- **Notes:** Current commercial sources exist; W18+ may evaluate only after strong open/public baselines and rights/cost review.

## ASSUMPTION-018 — A single authoritative writer plus append-only resolution events is sufficient for the current local entity workflow
- **Status:** SUPPORTED_BY_CURRENT_SCOPE_REOPEN_W19_W22
- **Constraint class:** B
- **Notes:** PostgreSQL remains optional; reopen if concurrent writers/transactional correction requirements appear.

## ASSUMPTION-019 — Type-prefixed UUID4 is a practical dependency-free surrogate ID representation before real entity materialization
- **Status:** SUPPORTED_AS_DEFAULT_NOT_YET_MATERIALIZED
- **Constraint class:** B
- **Notes:** Opacity/stability/no-source-coupling are protected; representation may change before assigned production IDs exist.

## ASSUMPTION-020 — A labeled resolver benchmark can eventually support some automatic candidate classes beyond verified direct/crosswalk mappings
- **Status:** PENDING_W19_LABELED_EVIDENCE
- **Constraint class:** C
- **Notes:** No fuzzy auto-accept is enabled in W07; THR-008 remains blank.


## Wave 08 additions
- **ASSUMPTION-021 — SUPPORTED_W08_CONTRACT:** A two-axis knowledge/validity temporal model is sufficient for the pregame PIT system before specialized live-event ordering Evidence: W08 source-domain contracts and synthetic cases cover current pregame requirements; future live lane may require richer event-time mechanics.
- **ASSUMPTION-022 — SUPPORTED_CONSERVATIVE_POLICY:** retrieved_at is a safe conservative fallback when earlier first-known time cannot be defended Evidence: Using retrieval can lose usable historical evidence but does not create future-information leakage; later source-specific archival evidence may recover earlier knowability.
- **ASSUMPTION-023 — PENDING_MATERIALIZATION:** Exact issued weather-run archives will support all desired forecast horizons/eras Evidence: W06 found strong modern archives but coverage varies by model/year/variable; W19/W24 must measure actual coverage.

## Wave 11 additions
- **ASSUMPTION-024 — PENDING_W17_W19:** Composite early-season priors can outperform single-source/static priors when component weights are learned chronologically. Constraint class: C.
- **ASSUMPTION-025 — PENDING_W17_W19:** Recency and regime similarity can improve current-team state relative to uniform historical weighting without destabilizing national performance. Constraint class: C.
- **ASSUMPTION-026 — PENDING_W19:** Historical FCS internal and FCS-vs-FBS evidence is sufficient to estimate useful cross-division translation with calibrated uncertainty. Constraint class: B.
- **ASSUMPTION-027 — SUPPORTED_AS_SCOPE_DEFAULT:** Progressively coarse D-II/D-III/NAIA/JUCO priors are sufficient boundary support for the A&M/FBS objective unless later evidence shows material value from deeper modeling. Constraint class: B.


## Wave 12 additions
- **ASSUMPTION-028 — PENDING_W17_W19:** Position-aware player-value and replacement evidence can outperform coarse starter/injury counts. Constraint class: C.
- **ASSUMPTION-029 — PENDING_W17_W19:** Historical same-player transfer cohorts provide enough coverage to learn useful position-aware translation with calibrated uncertainty. Constraint class: C.
- **ASSUMPTION-030 — SUPPORTED_AS_CONSERVATIVE_POLICY:** Missing/noncovered availability evidence must remain UNKNOWN rather than default healthy. Constraint class: A.
- **ASSUMPTION-031 — PENDING_W19:** Official conference availability archives can be materialized with sufficient version/timestamp coverage for recent A&M/SEC games. Constraint class: B.


## W13 additions
- **ASSUMPTION-024 — PENDING_MATERIALIZATION:** Historical scheme/play-caller evidence can be reconstructed with useful national coverage.
- **ASSUMPTION-025 — PENDING_RESEARCH:** Official or reliable pregame officiating assignments will have enough coverage to justify a crew-specific experiment.
- **ASSUMPTION-026 — PENDING_MATERIALIZATION:** Venue/travel metadata can be reconstructed accurately enough for DST-aware historical context.
- **ASSUMPTION-027 — PENDING_MATERIALIZATION:** Resource semantic crosswalks can support valid universal/public-enriched comparisons.
- **ASSUMPTION-028 — PENDING_MATERIALIZATION:** Rule/eligibility/transfer histories can be versioned sufficiently for affected historical features.
- **ASSUMPTION-029 — PENDING_MATERIALIZATION:** Score-state and style proxies have enough historical coverage to support later experiments.
## W14 additions
- ASSUMPTION-030: A&M/SEC evidence can support deeper current-state resolution — pending materialization.
- ASSUMPTION-031: nonzero A&M specialization may add protected value — pending; null is acceptable.
- ASSUMPTION-032: reproducible PIT-safe peer cohorts can be built — pending.
- ASSUMPTION-033: strict-prior analogs may add stable value/explanation — pending.
- ASSUMPTION-034: frequent A&M snapshots may justify their operating cost — pending.

## W15 additions
- **ASSUMPTION-035 — PENDING_W16_W17:** At least one BAS-independent national pregame expectation family will be accurate/stable enough to serve as the primary BAS label anchor.
- **ASSUMPTION-036 — PENDING_W17:** A&M has enough chronologically valid games across regimes for meaningful excess-underperformance stability analysis; if not, uncertainty/null reporting dominates.
- **ASSUMPTION-037 — PENDING_W17:** Frozen W14 peer cohorts can support sensitivity analysis without outcome-conditioned selection.
- **ASSUMPTION-038 — PENDING_W17_W18:** Candidate BAS components may be identifiable with sufficient data/control; no component is assumed useful.


## W16 assumptions
- A coherent joint score distribution is a strong default parent representation, not a guaranteed empirical winner.
- Count/structured/boosted/neural/ensemble families remain candidates until protected chronological evidence exists.
- OOD and disagreement signals are useful warning candidates, but exact methods and thresholds remain unresolved.
- Exact simulation mixtures are preferred for deterministic summaries when practical; Monte Carlo remains a candidate for complex scenarios.
