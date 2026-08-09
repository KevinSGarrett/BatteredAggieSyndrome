# Assumption Challenge Log

## ASSUMPTION-CHALLENGE-001
- **Assumption:** PFF is necessary for sophisticated v1
- **Result:** REJECTED
- **Evidence:** Free/public SportsDataverse/CFBD plus derived features support core; PFF deferred.

## ASSUMPTION-CHALLENGE-002
- **Assumption:** A currently downloadable pretrained CFB model can be foundational
- **Result:** REJECTED
- **Evidence:** Later source log could not verify referenced artifact; no dependency allowed.

## ASSUMPTION-CHALLENGE-003
- **Assumption:** Raw 900+ fields should be fed directly to XGBoost
- **Result:** REJECTED
- **Evidence:** Fields span grains/IDs/leakage/postgame values; feature registry and PIT transforms required.

## ASSUMPTION-CHALLENGE-004
- **Assumption:** Home winning percentage measures stadium strength
- **Result:** REJECTED
- **Evidence:** Confounded by team quality; use residual/partial pooling.

## ASSUMPTION-CHALLENGE-005
- **Assumption:** Static coach rating is adequate
- **Result:** REJECTED
- **Evidence:** Role history and shared-context confounding require role-conditioned residuals.

## ASSUMPTION-CHALLENGE-006
- **Assumption:** Resources can be a simple money bonus
- **Result:** REJECTED
- **Evidence:** Likely double counts roster/coaching/talent; use conditional upstream/resource-efficiency representations.

## ASSUMPTION-CHALLENGE-007
- **Assumption:** Observed weather can stand in for earlier forecast
- **Result:** REJECTED
- **Evidence:** Temporal leakage; preserve forecast-vs-observed distinction.

## ASSUMPTION-CHALLENGE-008
- **Assumption:** Closing line is valid for all historical forecast times
- **Result:** REJECTED
- **Evidence:** Later market observations cannot enter earlier forecasts.

## ASSUMPTION-CHALLENGE-009
- **Assumption:** All FCS opponents can share one generic rating
- **Result:** REVISED
- **Evidence:** FCS needs meaningful team-specific secondary model with cross-division calibration.

## ASSUMPTION-CHALLENGE-010
- **Assumption:** Large LLM or cloud GPU is required for high accuracy
- **Result:** REJECTED
- **Evidence:** Core is structured ML/data engineering; local-first is sufficient for baseline system.

## ASSUMPTION-CHALLENGE-011
- **Assumption:** Recon pack is the complete historical data lake
- **Result:** REJECTED
- **Evidence:** It is evidence/schema/policy reconnaissance; bulk materialization remains future work.

## ASSUMPTION-CHALLENGE-012
- **Assumption:** Recon sample profiles are population statistics
- **Result:** REJECTED
- **Evidence:** Pack explicitly prohibits that interpretation.

## ASSUMPTION-CHALLENGE-013
- **Assumption:** Wave 02 should create every future football-domain package/folder now.
- **Result:** REJECTED
- **Evidence:** Wave 03 owns logical/system architecture; premature folders would create false commitment and duplicate work.

## ASSUMPTION-CHALLENGE-014
- **Assumption:** Docker is required for Wave 02 reproducibility.
- **Result:** REJECTED FOR CURRENT WAVE
- **Evidence:** Local Python tooling and Windows/Linux CI satisfy current repository-operating needs; Docker remains available later where it earns operational value.

## ASSUMPTION-CHALLENGE-015
- **Assumption:** A third-party Python environment manager must be mandatory.
- **Result:** REJECTED
- **Evidence:** Standard venv/pip provides the portability floor; other managers may remain optional accelerators.

## ASSUMPTION-CHALLENGE-016
- **Assumption:** Repository manifest/hash files can safely include their own final hashes.
- **Result:** REJECTED
- **Evidence:** Self-reference is not stable; W02 makes the W01 non-self-referential policy executable.


## ASSUMPTION-CHALLENGE-017
- **Assumption:** The forecasting platform should be split into microservices now.
- **Result:** REJECTED FOR CURRENT ARCHITECTURE
- **Evidence:** No demonstrated independent scaling/security/latency requirement; local-first snapshot-serving modular monolith is simpler and more reproducible.


## ASSUMPTION-CHALLENGE-018
- **Assumption:** Pregame forecasts require an online feature store.
- **Result:** REJECTED FOR CURRENT ARCHITECTURE
- **Evidence:** Forecasts are generated as immutable scheduled/as-needed snapshots; shared PIT feature contracts provide train/inference consistency without a network serving layer.


## ASSUMPTION-CHALLENGE-019
- **Assumption:** PostgreSQL must be the canonical-state database from the beginning.
- **Result:** REVISED
- **Evidence:** Parquet + DuckDB is the early default; a PostgreSQL adapter remains available if W07/W22 finds transactional/concurrent needs.


## ASSUMPTION-CHALLENGE-020
- **Assumption:** LLM agents should orchestrate or perform deterministic core forecast computations.
- **Result:** REJECTED
- **Evidence:** Normal Python/data/model components are more reproducible; LLM use is assistive for unstructured evidence/research/explanation.


## ASSUMPTION-CHALLENGE-021
- **Assumption:** Texas A&M should have a separate canonical data pipeline/source of truth.
- **Result:** REJECTED
- **Evidence:** A&M gets higher-resolution evidence and field-specific precedence but maps into the same canonical/PIT identity system.


## ASSUMPTION-CHALLENGE-022
- **Assumption:** Live/in-game and pregame systems can share one mutable feature path without special isolation.
- **Result:** REJECTED
- **Evidence:** Live same-game information is future information relative to pregame; future live lane is isolated and one-way from pregame prior.

## ASSUMPTION-CHALLENGE-023
- **Assumption:** Every requirement must have an executable unit test in Wave 04.
- **Result:** REVISED
- **Evidence:** Acceptance mode must fit the requirement: static, integration, replay, science, benchmark or manual review. Future implementation evidence cannot be manufactured now.

## ASSUMPTION-CHALLENGE-024
- **Assumption:** Wave 04 should choose numeric model/data/performance thresholds now.
- **Result:** REJECTED
- **Evidence:** Protected-model, full-data and target-hardware evidence does not yet exist. The threshold registry assigns owners instead of inventing values.

## ASSUMPTION-CHALLENGE-025
- **Assumption:** Level-A/B/C class can double as acceptance PASS/FAIL state.
- **Result:** REJECTED
- **Evidence:** Constraint authority/revisability and evidence maturity are independent dimensions.

## ASSUMPTION-CHALLENGE-026
- **Assumption:** Passing repository tests means future football data/model/product requirements are accepted.
- **Result:** REJECTED
- **Evidence:** W04 validates the acceptance framework itself; owner-wave implementation/scientific evidence remains explicitly pending.


## Wave 05 challenges
- 027 REJECTED: no invented task duration schedule.
- 028 REJECTED: indiscriminate maximum Codex concurrency is not optimal.
- 029 REJECTED: W07+ source-dependent details cannot be frozen before W06 research.
- 030 REVISED: coherent tasks + exact mapping outperform one-task-per-requirement decomposition.

## Wave 07 challenges

### ASSUMPTION-CHALLENGE-031
- **Assumption:** Manual entity review requires PostgreSQL immediately
- **Result:** REJECTED FOR CURRENT SCOPE
- **Evidence:** Current local workflow has one authoritative writer and append-only decision events; no concurrent transactional requirement is demonstrated.

### ASSUMPTION-CHALLENGE-032
- **Assumption:** An exact normalized name match is sufficient durable player/coach identity
- **Result:** REJECTED
- **Evidence:** Transfers, duplicate names, suffix/spelling variants and role changes make name-only durable joins unsafe; exact names generate candidates only.

### ASSUMPTION-CHALLENGE-033
- **Assumption:** Identical raw SHA-256 means two retrieval events are the same evidence event
- **Result:** REJECTED
- **Evidence:** Retrieval time itself is evidence for what was checked/known; identical bytes can legitimately have distinct raw_capture identities.

## W08
- **ASSUMPTION-021 — CONFIRMED_AS_PREGAME_DEFAULT:** Two-axis knowledge/validity semantics cover the protected pregame PIT system; live event ordering remains separate.
- **ASSUMPTION-022 — CONFIRMED_CONSERVATIVE:** Retrieval time is safe as a fallback when earlier public timing cannot be defended, though it may reduce usable coverage.


## ASSUMPTION-CHALLENGE-024
- **Assumption:** One rolling window/decay should be selected now.
- **Result:** REJECTED.
- **Evidence:** W10 has no protected real-data comparison; window is an experiment parameter.

## ASSUMPTION-CHALLENGE-025
- **Assumption:** A high mutual-information or importance score is sufficient feature evidence.
- **Result:** REJECTED.
- **Evidence:** W10 screening contract requires conditional, ablation and temporal evidence.

## ASSUMPTION-CHALLENGE-026
- **Assumption:** A single universal feature set should serve all forecast targets.
- **Result:** REJECTED.
- **Evidence:** Existing REQ-066 plus W10 target-specific lifecycle architecture.

## ASSUMPTION-CHALLENGE-027
- **Assumption:** W10 synthetic tests can justify production promotion.
- **Result:** REJECTED.
- **Evidence:** Synthetic tests prove semantics only; materialized walk-forward evidence is absent.

## Wave 11 challenges

### ASSUMPTION-CHALLENGE-W11-01
- **Assumption:** One fixed recency decay should define current team state.
- **Result:** REJECTED.
- **Evidence:** Source examples were explicitly illustrative; W11 registers multiple chronological candidates and freezes no decay parameter.

### ASSUMPTION-CHALLENGE-W11-02
- **Assumption:** A new coach/QB/scheme should automatically reset all historical team evidence.
- **Result:** REJECTED.
- **Evidence:** Change points can justify shrinkage and wider uncertainty; hard resets require later protected evidence.

### ASSUMPTION-CHALLENGE-W11-03
- **Assumption:** FCS/lower-division opponents can be represented by one fixed point penalty.
- **Result:** REJECTED.
- **Evidence:** The source design requires internal FCS strength, cross-division translation and explicit uncertainty.

### ASSUMPTION-CHALLENGE-W11-04
- **Assumption:** W11 synthetic/reference comparisons can select a production team-state representation.
- **Result:** REJECTED.
- **Evidence:** Real chronological matrices and protected downstream metrics are not yet materialized.


## Wave 12 challenges

### ASSUMPTION-CHALLENGE-W12-01
- **Assumption:** Roster membership and listed starter/depth status are interchangeable.
- **Result:** REJECTED.
- **Evidence:** Recon roster/depth policies explicitly separate membership, depth, expected role and outcome participation.

### ASSUMPTION-CHALLENGE-W12-02
- **Assumption:** Every QB injury should receive a fixed larger point penalty than other positions.
- **Result:** REJECTED.
- **Evidence:** W12 represents value, usage, replacement and uncertainty; the learned gap may often be larger for QB but is not hard-coded.

### ASSUMPTION-CHALLENGE-W12-03
- **Assumption:** Missing injury/availability reports imply the player is healthy.
- **Result:** REJECTED.
- **Evidence:** W06/W08 official-report scope and W12 evidence policy require UNKNOWN under noncoverage/missing evidence.

### ASSUMPTION-CHALLENGE-W12-04
- **Assumption:** Conference labels alone are sufficient transfer translation.
- **Result:** REJECTED.
- **Evidence:** Recon transfer policy requires continuous opponent/team strength, same-player history, supporting cast, scheme, role and uncertainty.

### ASSUMPTION-CHALLENGE-W12-05
- **Assumption:** W12 synthetic/reference tests can select a production player-value or transfer model.
- **Result:** REJECTED.
- **Evidence:** Real historical matrices and protected chronological predictive evaluation remain W17/W19 evidence.
## W14 challenges
- CHALLENGE-030 — "A&M must always get a nonzero correction": **REJECTED**; no-adjustment is mandatory baseline and valid outcome.
- CHALLENGE-031 — "Higher-resolution A&M data deserves separate canonical truth": **REJECTED**; resolution increases, canonical authority does not fork.
- CHALLENGE-032 — "Freeze the weekly snapshot cadence now": **REVISED**; retain candidate cadences until evidence/operations selection.

## ASSUMPTION-CHALLENGE-034
- **Assumption:** BAS can be labeled from any model prediction as long as the target row is held out.
- **Result:** REJECTED
- **Evidence:** Historical expectation must also obey chronological training cutoffs and canonical-game exclusion.

## ASSUMPTION-CHALLENGE-035
- **Assumption:** A&M specialization should define the expected margin used to prove Aggie underperformance.
- **Result:** REJECTED FOR PRIMARY SCIENTIFIC LABEL
- **Evidence:** An A&M-underperformance adapter can absorb/circularly encode the effect being tested.

## ASSUMPTION-CHALLENGE-036
- **Assumption:** Because the product is named BAS, an A&M-specific excess effect must exist.
- **Result:** REJECTED
- **Evidence:** Null/no-excess is an explicitly protected scientific outcome.

## ASSUMPTION-CHALLENGE-037
- **Assumption:** W15 should choose the most significant BAS component/peer/regime now.
- **Result:** REJECTED
- **Evidence:** Protected results do not yet exist; post-hoc selection would create multiplicity and stability bias.


## Wave 22 challenges

### ASSUMPTION-CHALLENGE-W22-01
- **Assumption:** Streamlit should automatically be the initial production dashboard because it was an early default.
- **Result:** REVISED.
- **Evidence:** W22 has one immutable artifact-serving contract; a FastAPI/static UI reuses that contract in one runtime while keeping Streamlit available for analyst prototypes.

### ASSUMPTION-CHALLENGE-W22-02
- **Assumption:** A numeric freshness SLA must be chosen to complete the product wave.
- **Result:** REJECTED.
- **Evidence:** THR-010 explicitly requires operational evidence. W22 can prove timestamp visibility and stale classification semantics with a configurable threshold without fabricating the production value.

### ASSUMPTION-CHALLENGE-W22-03
- **Assumption:** User-facing explainability should compute SHAP/model explanations on each request.
- **Result:** REJECTED.
- **Evidence:** Request-time computation would bypass immutable snapshot reproducibility; W22 renders only precomputed published explanation evidence.

## Wave 24 challenges

### ASSUMPTION-CHALLENGE-W24-01
- **Assumption:** A user instruction to advance waves implies the blocked W23 benchmark may be treated as passed.
- **Result:** REJECTED.
- **Evidence:** User instruction changes sequencing; AC-038 still requires evidence from the declared target machine.

### ASSUMPTION-CHALLENGE-W24-02
- **Assumption:** Completion timestamps alone are sufficient to prevent the target game's outcome from entering its own pregame state.
- **Result:** REJECTED AS DEFENSE-IN-DEPTH.
- **Evidence:** Malformed/corrupted metadata could make a target output appear old; explicit target_game_id exclusion is safer and testable.

### ASSUMPTION-CHALLENGE-W24-03
- **Assumption:** `cfbfastR-cfb-data` and `cfbfastR-cfb-raw` can corroborate one another as separate data sources.
- **Result:** REJECTED.
- **Evidence:** Current SportsDataverse documentation states the analysis-ready repository is derived from enriched final JSON in the raw sibling.

### ASSUMPTION-CHALLENGE-W24-04
- **Assumption:** Newly available ensemble weather mean/spread should automatically become a production feature.
- **Result:** REJECTED.
- **Evidence:** Historical depth is recent and predictive value is untested; retain as optional research evidence.
