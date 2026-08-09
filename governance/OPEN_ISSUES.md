# Open Issues

No current issue blocks completion of Wave 01. These remain explicit implementation/research tasks rather than invitations to guess.

## ISSUE-001 — SportsDataverse (MEDIUM)
- **Issue:** Season roster schema column-count inconsistency
- **Resolution path:** Profile actual season roster asset and freeze contract
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-002 — SportsDataverse/CFBD (HIGH)
- **Issue:** Betting spread sign/provider semantics differ
- **Resolution path:** Implement canonical spread convention + provider/timestamp contract tests
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-003 — CFBD (MEDIUM)
- **Issue:** Authenticated live sample payloads not materialized in pack
- **Resolution path:** Run included acquisition tool locally with environment-variable key
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-004 — Open-Meteo (LOW)
- **Issue:** Direct dynamic API JSON not materialized
- **Resolution path:** Run included no-key acquisition tool locally
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-005 — EADA (MEDIUM)
- **Issue:** Raw annual federal data file not materialized
- **Resolution path:** Download official annual data and profile with included strategy before production resources
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-006 — All sources (HIGH)
- **Issue:** Full-population missingness/value distributions not measured
- **Resolution path:** Materialize production-era datasets and run full profiling pipeline
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-007 — All feature families (HIGH)
- **Issue:** Statistical correlations/duplication not measured on full training matrix
- **Resolution path:** Run correlation clustering/ablation after point-in-time feature matrix exists
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-008 — Entity resolution (HIGH)
- **Issue:** Cross-source team/game/player/coach mappings not fully validated at scale
- **Resolution path:** Build source_entity_map and contract-test sampled seasons
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-009 — Texas A&M (HIGH)
- **Issue:** Historical game-week depth/injury coverage is uneven
- **Resolution path:** Acquire official game notes/depth/flip cards and assign evidence confidence
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-010 — Resources (HIGH)
- **Issue:** First-known-public timestamps for annual reports not fully materialized
- **Resolution path:** Store report publication/availability timestamps; lag features appropriately
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-011 — Weather (MEDIUM)
- **Issue:** Historical forecast-run coverage must be verified for desired forecast snapshots
- **Resolution path:** Use archived forecast/previous-run products where available; observed reanalysis only for observed-condition features
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-012 — PFF (NONE)
- **Issue:** Optional charting enrichment intentionally deferred
- **Resolution path:** No action for v1; future add-on only if user chooses and legitimate export available
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-013 — Draft development (MEDIUM)
- **Issue:** Historical CFBD draft outcomes have not yet been fully materialized/profiled in the pack
- **Resolution path:** Acquire completed draft history and validate player/team identity joins
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-014 — Preseason honors (MEDIUM)
- **Issue:** No single normalized historical national archive yet spans all conference teams/selectors/watch lists
- **Resolution path:** Build dated honor ingestion across conference offices, NCFAA, and approved selectors
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-015 — Coach role effects (HIGH)
- **Issue:** Role-conditioned coach residuals are specified but not statistically estimated
- **Resolution path:** Build role episodes and hierarchical residual model after full historical data materialization
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-016 — Transfer translation (HIGH)
- **Issue:** Same-player pre/post-transfer translation model not yet trained
- **Resolution path:** Build historical transfer cohort and position-specific translation models
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-017 — Availability impact (HIGH)
- **Issue:** Historical replacement-value and pregame depth snapshots remain incomplete
- **Resolution path:** Materialize depth/injury snapshots and player-value models
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-018 — Home-field strength (MEDIUM)
- **Issue:** Partial-pooled venue/team home effect not yet estimated
- **Resolution path:** Estimate residual home effects after controlling team/opponent/context
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-019 — Possession/tempo (MEDIUM)
- **Issue:** Expected-possession model not yet statistically estimated
- **Resolution path:** Build from point-in-time PBP/drive pace after full data materialization
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-020 — Field position (MEDIUM)
- **Issue:** Hidden-yards/field-position model not yet estimated
- **Resolution path:** Derive drive-start, kick/punt and turnover field-position value
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-021 — Special teams (MEDIUM)
- **Issue:** Kicking/punting/return submodels not yet trained/calibrated
- **Resolution path:** Train component models including weather and player continuity
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-022 — Fourth down/clock (LOW)
- **Issue:** Coach decision-quality and clock-management residuals not yet estimated
- **Resolution path:** Derive historical state/action/outcome datasets
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-023 — Officiating (LOW)
- **Issue:** No comprehensive national historical crew-assignment dataset is materialized
- **Resolution path:** Extract from official gamebooks/box scores where feasible and validate pregame assignment availability
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-024 — Rule eras (MEDIUM)
- **Issue:** Full 2005-present effective-dated NCAA rule timeline not yet materialized
- **Resolution path:** Build official rule-era registry during implementation
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-025 — Market snapshots (HIGH)
- **Issue:** Historical opening/current/closing first-known timestamps are not fully verified across providers
- **Resolution path:** Preserve provider/timestamp observations and enforce forecast cutoffs
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-026 — Uncertainty/OOD (MEDIUM)
- **Issue:** OOD thresholds and calibrated predictive intervals not yet learned
- **Resolution path:** Fit after production feature space exists
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-027 — Live/BAS collapse (NONE)
- **Issue:** Live model and collapse threshold not yet fixed/trained
- **Resolution path:** Implement after mature pregame system
- **Planned wave:** W06-W19
- **Status:** OPEN

## ISSUE-028 — Future source publication review (MEDIUM)
- **Issue:** Per-source redistribution/license status has not been verified for every raw artifact; this does not constrain private local acquisition or training.
- **Resolution path:** Keep raw payloads outside Git and review terms only if bulk redistribution, public repository inclusion, or commercialization is actually proposed.
- **Planned wave:** EVENT_DRIVEN_FUTURE_REVIEW
- **Status:** DEFERRED_UNTIL_DISTRIBUTION_PROPOSED

## ISSUE-029 — Architecture (HIGH)
- **Issue:** Final football-domain/service/module boundaries were not yet frozen
- **Resolution path:** W03 compared alternatives and accepted the logical modular-monolith/component/interface architecture while deliberately deferring detailed entity/model/orchestrator implementations to their owning waves
- **Planned wave:** W03
- **Status:** RESOLVED_W03

## ISSUE-030 — Validation (HIGH)
- **Issue:** Exact protected test seasons and promotion thresholds are not yet frozen
- **Resolution path:** Wave17 define based on data coverage and statistical power; protect afterward
- **Planned wave:** W17
- **Status:** OPEN

## ISSUE-031 — BAS (HIGH)
- **Issue:** Exact cross-fitting/expected-margin estimator for historical BAS labels is not yet selected
- **Resolution path:** Wave15 compare leakage-safe alternatives and freeze methodology
- **Planned wave:** W15
- **Status:** OPEN

## ISSUE-032 — Modeling (MEDIUM)
- **Issue:** Exact joint-score statistical family is not yet selected
- **Resolution path:** Wave16 compare coherent alternatives
- **Planned wave:** W16
- **Status:** OPEN

## ISSUE-033 — Orchestration (MEDIUM)
- **Issue:** Prefect remains a default, not an accepted mandatory orchestrator
- **Resolution path:** Wave21 benchmark operational fit before final selection
- **Planned wave:** W21
- **Status:** OPEN

## ISSUE-034 — Storage (MEDIUM)
- **Issue:** Exact physical storage implementation is not fully frozen
- **Resolution path:** W03 accepts native raw + Parquet + DuckDB as the early analytical default and makes PostgreSQL conditional behind a storage boundary; W07 must validate transactional/entity-resolution needs before finalizing canonical persistence
- **Planned wave:** W03-W07
- **Status:** PARTIALLY_RESOLVED_W03

## ISSUE-035 — A&M (HIGH)
- **Issue:** Historical A&M game-week availability/depth evidence coverage may constrain player availability training
- **Resolution path:** Wave06 research + Wave12 materialization confidence strategy
- **Planned wave:** W06/W12
- **Status:** OPEN

## ISSUE-036 — Research (MEDIUM)
- **Issue:** Wave06 may discover high-value sources/domains not present in reconnaissance pack
- **Resolution path:** Fresh multi-pass source research completed; W07-W24 plan revised through W06_REPLAN.
- **Planned wave:** W06
- **Status:** RESOLVED_W06


## ISSUE-037 — Dependency locking (LOW)
- **Issue:** No production ML/data dependency lock exists yet because Wave 02 intentionally installs no production data/model stack.
- **Resolution path:** Select and lock concrete production dependencies when architecture/source implementation requires them; do not manufacture a lock for packages not yet selected.
- **Planned wave:** W03/W19 as required
- **Status:** OPEN

## ISSUE-038 — PowerShell runtime validation (LOW)
- **Issue:** W02 generated Windows PowerShell wrappers, but the current execution environment has no PowerShell runtime for direct execution testing.
- **Resolution path:** Run `scripts/validate_repo.ps1` and related wrappers on the target Windows workstation; Python commands they invoke are already tested directly.
- **Planned wave:** W02 local handoff / W23
- **Status:** OPEN


## ISSUE-039 — Canonical relational persistence (MEDIUM)
- **Issue:** Whether entity-resolution/review workflows need PostgreSQL or another transactional relational backend is not yet proven.
- **Resolution path:** W07 define canonical entity workflows and benchmark DuckDB/Parquet versus a relational adapter under real mutation/concurrency requirements.
- **Planned wave:** W07
- **Status:** OPEN

## ISSUE-040 — Forecast snapshot product schema (MEDIUM)
- **Issue:** W03 defines snapshot semantics but not the final API/dashboard payload schema.
- **Resolution path:** W16/W22 finalize coherent output objects, lineage metadata and serving contract after model targets/product needs are concrete.
- **Planned wave:** W16/W22
- **Status:** OPEN

## ISSUE-041 — A&M statistical specialization form (HIGH)
- **Issue:** The national→A&M interface is accepted but residual adapter vs hierarchical multi-task vs other statistical implementation is intentionally unfrozen.
- **Resolution path:** W14/W16 compare with PIT-safe data and A&M-specific evaluation.
- **Planned wave:** W14/W16
- **Status:** OPEN

## ISSUE-042 — Architecture-to-code conformance (MEDIUM)
- **Issue:** Most W03 package boundaries are semantic and will materialize in later waves.
- **Resolution path:** Each owning wave must update the architecture registry/ADRs when creating packages and run `tools/validate_architecture.py`.
- **Planned wave:** W04-W25
- **Status:** OPEN

## ISSUE-043 — Snapshot freshness operations (MEDIUM)
- **Issue:** Immutable serving is accepted, but exact refresh/freshness SLA and stale-snapshot presentation are not yet defined.
- **Resolution path:** W21-W23 define orchestration/monitoring and W22 exposes snapshot timestamp/freshness in the product.
- **Planned wave:** W21-W23
- **Status:** OPEN

## W04 acceptance evidence items
- **ISSUE-046 — Statistical promotion thresholds pending:** Brier/log-loss/calibration/score/A&M/BAS promotion values are intentionally TBD until W17/protected evaluation evidence. Non-blocking for W04/W05.
- **ISSUE-047 — Data/entity quality thresholds pending:** domain completeness, quarantine and entity auto-accept thresholds await W06-W09 materialized data/review evidence.
- **ISSUE-048 — Local performance budgets pending:** peak RAM/runtime/storage limits await W19-W23 benchmarks on target hardware.
- **ISSUE-049 — Forecast freshness SLA pending:** exact stale/current operational threshold awaits W21-W22 orchestration/product cadence.


## W05 implementation-planning items
- **ISSUE-050 — W06 source-dependent backlog revalidation (HIGH):** W06 research/replan completed; source-dependent tasks were revalidated and new TASK-190..201 added. **Status:** RESOLVED_W06.
- **ISSUE-051 — Autonomous concurrency tuning (MEDIUM):** Exact safe parallel-worktree concurrency is intentionally not hard-coded; future waves should adapt to dependency independence and measured local resource pressure. **Owner:** W06-W23.
- **ISSUE-052 — Task duration/throughput evidence (LOW):** W05 does not estimate implementation hours/days. If future scheduling is needed, use measured throughput after real Codex implementation rather than retrospective guesses. **Owner:** future program operations.


## W06 research gap items
- **ISSUE-053 — Historical availability before official-report eras (HIGH):** Recent conference reports materially improve coverage, but older seasons/nonconference games remain incomplete. **Owner:** W12. **Status:** OPEN.
- **ISSUE-054 — National historical depth charts (HIGH):** No scalable open national historical depth-chart source was verified. Use official game notes/media guides where feasible and explicit uncertainty. **Owner:** W07/W12. **Status:** OPEN.
- **ISSUE-055 — Pregame officiating assignment history (MEDIUM):** No stable national public pregame-assignment feed with robust publication timestamps was verified. **Owner:** W13/W24. **Status:** OPEN/EXPERIMENTAL.
- **ISSUE-056 — Open route/coverage/formation/tracking history (MEDIUM):** Deep charting/tracking exists commercially but no open national source closes the gap. **Owner:** W18+. **Status:** OPTIONAL_RESEARCH.
- **ISSUE-057 — Older timestamped market history (MEDIUM):** High-quality modern historical snapshots exist, often paid; deeper older PIT history remains incomplete. **Owner:** W16-W17. **Status:** OPEN_OPTIONAL_LANE.
- **ISSUE-058 — Shared upstream provenance (HIGH):** Derived public repositories may share ESPN/247/other upstreams and must not be counted as independent corroboration. Licensing/redistribution status is nonblocking metadata for private use. **Owner:** W09+. **Status:** PROVENANCE_CONTROL_REQUIRED_RIGHTS_GATE_SUPERSEDED.
- **ISSUE-059 — Weather forecast era coverage (MEDIUM):** Issued forecast-run archives vary by model/variable/year; pre-archive eras require explicit fallback/uncertainty and may not support identical forecast snapshots. **Owner:** W08/W13. **Status:** OPEN.


## W07 carry-forward
- **ISSUE-064 — Entity resolver threshold evidence:** `THR-008` remains unset. W19 must build labeled entity-resolution/review fixtures before any fuzzy/ambiguous auto-accept threshold can be considered. **Status:** OPEN.
- **ISSUE-065 — Conditional PostgreSQL reopen:** PostgreSQL is not required under the current single-writer workflow. Reopen in W19/W22 if concurrent reviewers/services or atomic cross-process correction become real requirements. **Status:** OPEN_CONDITIONAL.
- **ISSUE-066 — W07 temporal field semantics:** W08 must define exact `published_at` / `first_known_at` / `effective_at` / `prediction_eligible_at` semantics for the W07 publication/capture identity hierarchy. **Status:** RESOLVED_W08 by `configs/temporal_registry.json`.
- **ISSUE-067 — Historical official identity evidence:** Historical official identity remains source-limited; W13 must keep officiating experimental unless stronger assignment/identity evidence is obtained. **Status:** OPEN.


## W08 carry-forward
- **ISSUE-060 — Historical first-known reconstruction (HIGH):** many mutable historical sources lack perfect publication/version archives. W19/W24 must measure coverage and use conservative retrieval/lag or suppress affected features. **Status:** OPEN.
- **ISSUE-061 — Weather run archive coverage (MEDIUM):** W08 freezes run/init/available/valid semantics; actual model/year/variable/horizon coverage remains W19/W24 materialization evidence. **Status:** OPEN.
- **ISSUE-062 — Availability noncoverage/materialization (HIGH):** policy-scope semantics are frozen, but historical game-by-game official report coverage must be materialized in W12/W19. **Status:** OPEN.
- **ISSUE-063 — Real historical leakage replay (CRITICAL):** W08 synthetic battery passes by contract; materialized historical matrices still require protected chronological leakage replay in W19/W24. **Status:** OPEN.


## W10 carry-forward
- **ISSUE-068 — Real feature promotion evidence (HIGH):** W10 has no materialized national training matrix/protected walk-forward results; all candidate seeds remain EXPERIMENTAL. **Owner:** W17/W19. **Status:** OPEN.
- **ISSUE-069 — Feature-family promotion threshold (HIGH):** `THR-007` remains blank/TBD; W17 must define only after evaluation design/data coverage is fixed. **Owner:** W17. **Status:** OPEN.
- **ISSUE-070 — Population feature data quality (HIGH):** W09/W10 cannot infer true coverage/missingness from representative samples. **Owner:** W19. **Status:** OPEN.
- **ISSUE-071 — Candidate interaction search control (MEDIUM):** exact interaction hypotheses should emerge from W11-W18 domain/model evidence rather than brute-force pair generation. **Owner:** W11-W18. **Status:** OPEN.

## W11 carry-forward
- **ISSUE-072 — Team-state empirical winner (HIGH):** W11 freezes candidate representations but has no real chronological national matrix to rank them. **Owner:** W17/W19. **Status:** OPEN.
- **ISSUE-073 — Early-season prior component weights (HIGH):** No Week-1 prior component or blend weight is frozen. **Owner:** W17/W19. **Status:** OPEN.
- **ISSUE-074 — Change-point threshold/calibration (MEDIUM):** Change-point methods and response strength remain uncalibrated. **Owner:** W17/W19. **Status:** OPEN.
- **ISSUE-075 — FCS/lower-division translation parameters (HIGH):** Hierarchy is frozen, but empirical translation functions and uncertainty require materialized cross-division history. **Owner:** W19. **Status:** OPEN.
- **ISSUE-076 — Available-strength player adjustment (HIGH):** W11 defines the interface only; detailed player availability/effectiveness/usage/replacement logic belongs to W12. **Owner:** W12. **Status:** OPEN.


## Wave 12 carry-forward

## ISSUE-077 — Historical depth state coverage (HIGH)
- **Issue:** National historical pregame depth/rotation evidence remains incomplete.
- **Resolution path:** W19 materialize official game notes/depth artifacts; preserve inferred/unknown states and coverage metrics.
- **Status:** OPEN

## ISSUE-078 — Historical availability before official-report eras (HIGH)
- **Issue:** Older injury/availability reconstruction remains sparse and source-dependent.
- **Resolution path:** W19 PIT reconstruction with confidence/noncoverage; do not manufacture healthy states.
- **Status:** OPEN

## ISSUE-079 — Player-value target/calibration (HIGH)
- **Issue:** W12 defines evidence/interfaces but no empirically calibrated player-value target or point impact.
- **Resolution path:** W17/W19 protected chronological training/evaluation.
- **Status:** OPEN

## ISSUE-080 — Same-player transfer training coverage (HIGH)
- **Issue:** Historical transfer cohort completeness/position sample sizes are not yet measured.
- **Resolution path:** W19 materialization then W17/W19 translation benchmark.
- **Status:** OPEN

## ISSUE-081 — Recruiting/transfer history and provenance (MEDIUM)
- **Issue:** Historical snapshots and upstream provenance vary; private acquisition/training is authorized, while raw publication remains disabled.
- **Resolution path:** Preserve W12 provenance metadata, acquire the maximum quality-supported public history, and apply a separate review only to a future distribution proposal.
- **Status:** OPEN_DATA_COVERAGE_RIGHTS_GATE_SUPERSEDED

## ISSUE-082 — Official availability report archive materialization (MEDIUM)
- **Issue:** W12 freezes source lane but has not downloaded/versioned every historical report.
- **Resolution path:** W19 acquisition with A&M/SEC priority.
- **Status:** OPEN

## ISSUE-083 — Availability source-confidence calibration (MEDIUM)
- **Issue:** W12 uses categorical authority tiers but no empirically calibrated numeric reliability weights.
- **Resolution path:** Evaluate only after labeled historical outcomes/coverage exist.
- **Status:** OPEN

## ISSUE-084 — Preseason honor historical completeness (LOW)
- **Issue:** Selector/watch-list history and announcement timestamps are not fully materialized.
- **Resolution path:** Materialize sources with reproducible history and provenance; quarantine or keep sparse only where technical access, schema, quality, PIT, or coverage evidence is inadequate.
- **Status:** OPEN

## W13 carry-forward issues
- **ISSUE-085:** National historical assistant-coach responsibility/play-caller coverage remains unmaterialized.
- **ISSUE-086:** Scheme/style taxonomy coverage and stability remain unmeasured.
- **ISSUE-087:** Coach-development residuals lack trained/control-adjusted empirical estimates.
- **ISSUE-088:** Home-field hierarchy has no protected empirical magnitude yet.
- **ISSUE-089:** Private-school detailed resource coverage remains structurally incomplete.
- **ISSUE-090:** Historical issued-weather-run coverage varies by era/model.
- **ISSUE-091:** Actual travel itinerary data are sparse; great-circle/origin proxies require later validation.
- **ISSUE-092:** Garbage-time/leverage policy has no protected winner.
- **ISSUE-093:** Opponent-adjustment and style-similarity methods have no protected winner.
- **ISSUE-094:** Pregame officiating assignment coverage remains unresolved nationally.
- **ISSUE-095:** Historical regulatory-environment materialization is incomplete.
- **ISSUE-096:** W14 specialization has not yet been designed or tested.
## W14 additions
- ISSUE-097 — Historical A&M depth/rotation coverage remains incomplete before modern official-report eras.
- ISSUE-098 — Historical OL-combination and receiver-role continuity coverage remains unmeasured.
- ISSUE-099 — Exact A&M snapshot cadence/clock times remain unselected.
- ISSUE-100 — Peer-cohort definition has no empirical winner.
- ISSUE-101 — Historical-analog retrieval/similarity method has no empirical winner.
- ISSUE-102 — A&M specialization architecture has no empirical winner.
- ISSUE-103 — `THR-005` A&M specialization incremental-value threshold remains blank/TBD.
- ISSUE-104 — Numeric A&M evaluation weighting remains unselected.
- ISSUE-105 — W15 BAS scientific specification has not yet been executed.

## W15 carry-forward issues
### ISSUE-106 — Exact BAS-independent expected-margin model family not selected
Owner: W16-W17. Status: OPEN. W15 freezes eligibility/provenance only.

### ISSUE-107 — Historical cross-fitted BAS labels not materialized
Owner: W19-W20. Status: OPEN. Requires real data/model artifacts.

### ISSUE-108 — Aggie Excess effect size/significance unknown
Owner: W17. Status: OPEN. No W15 claim.

### ISSUE-109 — THR-006 scientific criterion unset
Owner: W17. Status: OPEN. Must be precommitted before protected BAS results.

### ISSUE-110 — BAS component identifiability/stability unknown
Owner: W17-W18. Status: OPEN. Components remain candidates.

### ISSUE-111 — Live Collapse BAS definition/replay threshold unresolved
Owner: W18+. Status: OPEN. Isolated from pregame BAS.

### ISSUE-112 — Calibration of nested BAS probability severities unmeasured
Owner: W16-W17. Status: OPEN. W15 freezes only monotonicity/evaluation contract.


## W16 open items
- Select joint-score/model family only after protected protocol and real historical evidence.
- Select calibration method and populate THR-001..004 under W17 protocol.
- Select OOD/disagreement methods and populate THR-014/015 only from evidence.
- Quantify market augmentation value without contaminating the pure-football lane.
- Determine whether scenario mixture improves calibrated uncertainty once W19/W20 materialized artifacts exist.


## W18 carry-forward
- Real MLflow/Optuna adapters and version locks are not installed/validated against materialized models yet.
- W17 numeric promotion/OOD/disagreement thresholds remain blank pending development-only evidence.
- Advanced neural/sequence/graph empirical execution remains blocked pending conventional baseline evidence.
- Real experiment artifact/replay behavior must be exercised during W19-W20 materialized implementation.


## ISSUE-113 — W23 target-hardware benchmark gate
- **Status:** OPEN / RELEASE BLOCKER
- **Owner wave:** W23
- **Problem:** AC-038 requires representative benchmark evidence on the declared Windows/Ryzen 7 HX/32GB/RTX 5060-class target; the current build host does not match.
- **Required resolution:** Run the representative W23 benchmark on target hardware, review the evidence, freeze THR-011/THR-012 if justified, then re-run strict W23 validation.
- **Do not:** infer target budgets from `W23_NON_TARGET_BENCHMARK_SMOKE.json`.

## ISSUE-114 — W23 target benchmark carried into W25
- **Status:** OPEN / FINAL-READINESS CONDITION
- **Owner wave:** W25 carry-forward from W23
- **Context:** User explicitly instructed W24 execution before AC-038 could be cleared on the target machine.
- **Required final handling:** If representative target evidence is still absent during W25, keep THR-011/THR-012 blank/TBD and list local-production performance readiness as awaiting target-hardware validation.
- **Do not:** reinterpret W24 scope completion as target-hardware evidence.

## W25 final handoff issues
- AC-038 target-hardware benchmark remains unresolved; THR-011/THR-012 remain TBD.
- Real national historical materialization and empirical protected replay remain implementation work.
- No production feature set, trained champion, A&M specialization lift, BAS/Aggie Excess effect or live model is claimed.
- See `docs/final/FINAL_KNOWN_GAPS.md`.
