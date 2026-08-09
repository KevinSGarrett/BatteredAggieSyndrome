# Risk Register — Wave 03

## RISK-001 — Temporal leakage from season/future/postgame fields
- **Severity:** CRITICAL
- **Likelihood:** HIGH
- **Mitigation:** W08 PIT contracts/tests; feature temporal classes; protected leakage battery
- **Status:** OPEN

## RISK-002 — Closing-line or realized-weather hindsight contaminates earlier snapshots
- **Severity:** CRITICAL
- **Likelihood:** HIGH
- **Mitigation:** Immutable timestamped market/weather evidence and cutoffs
- **Status:** OPEN

## RISK-003 — Cross-source entity-resolution errors merge/split wrong player/team/game
- **Severity:** HIGH
- **Likelihood:** HIGH
- **Mitigation:** Canonical IDs, source maps, confidence, contract tests and unresolved queue
- **Status:** OPEN

## RISK-004 — Historical injury/depth evidence sparse or retrospective
- **Severity:** HIGH
- **Likelihood:** HIGH
- **Mitigation:** Evidence confidence, snapshot acquisition, missingness/uncertainty; do not invent
- **Status:** OPEN

## RISK-005 — Feature selection overfits protected validation periods
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Nested/rolling evaluation, holdout protection, stability and family ablations
- **Status:** OPEN

## RISK-006 — BAS learns fan narrative/noise instead of persistent A&M effect
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** General underperformance baseline, Aggie Excess, cross-fit labels, significance/regime tests
- **Status:** OPEN

## RISK-007 — A&M specialization overfits small sample
- **Severity:** HIGH
- **Likelihood:** HIGH
- **Mitigation:** National foundation, shrinkage, peer cohorts, A&M weighting only when walk-forward improves
- **Status:** OPEN

## RISK-008 — Resource features double-count talent/coaching/roster advantages
- **Severity:** MEDIUM
- **Likelihood:** HIGH
- **Mitigation:** Ablations, residual/resource-efficiency designs, feature redundancy analysis
- **Status:** OPEN

## RISK-009 — Private-school financial missingness creates systematic bias
- **Severity:** MEDIUM
- **Likelihood:** HIGH
- **Mitigation:** Universal EADA baseline, enriched public lane, explicit missingness; no fabricated values
- **Status:** OPEN

## RISK-010 — PFF or commercial source dependency blocks reproducibility
- **Severity:** LOW
- **Likelihood:** HIGH
- **Mitigation:** PFF deferred/optional; core must operate without it
- **Status:** OPEN

## RISK-011 — Public API/schema/rate-limit changes break ingestion
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Wave06 source audit, versioned contracts, fallbacks, source risk register
- **Status:** OPEN

## RISK-012 — Licensing/redistribution uncertainty exposes public repo risk
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Source governance registry; local-only raw default when uncertain
- **Status:** OPEN

## RISK-013 — Root recon PACK_MANIFEST self-entry appears corrupt
- **Severity:** LOW
- **Likelihood:** LOW
- **Mitigation:** Use authoritative final manifests; document single self-reference mismatch; do not infer broader corruption
- **Status:** OPEN

## RISK-014 — Source-chat ZIP archive order causes chronology inversion
- **Severity:** MEDIUM
- **Likelihood:** HIGH
- **Mitigation:** Numeric 001→020 sorting is explicit Wave01/next-session rule
- **Status:** OPEN

## RISK-015 — Host filename suffix causes false pack mismatch
- **Severity:** LOW
- **Likelihood:** MEDIUM
- **Mitigation:** Validate content/internal edition/hash, not exact copy filename
- **Status:** OPEN

## RISK-016 — Complex model architecture adds cost without predictive gain
- **Severity:** MEDIUM
- **Likelihood:** MEDIUM
- **Mitigation:** Simple baselines/champion; complexity must win evidence-backed comparison
- **Status:** OPEN

## RISK-017 — FCS/lower-division recursion explodes scope
- **Severity:** MEDIUM
- **Likelihood:** MEDIUM
- **Mitigation:** FBS/FCS hierarchy and coarse lower-division priors with uncertainty
- **Status:** OPEN

## RISK-018 — Coach effects confounded by players/co-staff/scheme/opponents
- **Severity:** HIGH
- **Likelihood:** HIGH
- **Mitigation:** Residual/hierarchical role-conditioned models and uncertainty
- **Status:** OPEN

## RISK-019 — Home-field effect confounded by team quality
- **Severity:** MEDIUM
- **Likelihood:** HIGH
- **Mitigation:** Neutral-equivalent residual and shrinkage; no raw home win percentage
- **Status:** OPEN

## RISK-020 — Transfer translation uses simplistic conference stereotype
- **Severity:** MEDIUM
- **Likelihood:** MEDIUM
- **Mitigation:** Same-player cohorts + continuous opponent/context strength + uncertainty
- **Status:** OPEN

## RISK-021 — Model outputs contradict score/margin/win/BAS relationships
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Joint-score/simulation coherence contract and consistency tests
- **Status:** OPEN

## RISK-022 — Autonomous agent modifies judging rules or hides bad results
- **Severity:** CRITICAL
- **Likelihood:** MEDIUM
- **Mitigation:** Protected immutable validation/promotion/ground-truth governance
- **Status:** OPEN

## RISK-023 — RAM pressure from raw PBP/feature matrices destabilizes local pipeline
- **Severity:** MEDIUM
- **Likelihood:** MEDIUM
- **Mitigation:** Parquet partitioning, DuckDB/Polars lazy processing, caches, bounded concurrency
- **Status:** OPEN

## RISK-024 — Repository grows through duplication rather than refinement
- **Severity:** MEDIUM
- **Likelihood:** MEDIUM
- **Mitigation:** Active redundancy-removal mandate, change logs, file-purpose reviews
- **Status:** OPEN

## RISK-025 — Recon samples mistaken for full data coverage/performance
- **Severity:** HIGH
- **Likelihood:** HIGH
- **Mitigation:** Explicit sample-vs-population rule and full-data profiling contract
- **Status:** OPEN

## RISK-026 — Current source status becomes stale before implementation
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Wave06 fresh research and Wave24 refresh
- **Status:** OPEN

## RISK-027 — Rule changes alter feature semantics across eras
- **Severity:** MEDIUM
- **Likelihood:** MEDIUM
- **Mitigation:** Effective-dated rule registry and versioned definitions
- **Status:** OPEN

## RISK-028 — Mirrored game rows leak across folds
- **Severity:** CRITICAL
- **Likelihood:** MEDIUM
- **Mitigation:** Canonical game grouping and split-safety tests
- **Status:** OPEN

## RISK-029 — Unsafe ZIP member path escapes extraction directory
- **Severity:** HIGH
- **Likelihood:** LOW
- **Mitigation:** Verify archive paths before extraction and use safe_extract helper
- **Status:** MITIGATED_W02

## RISK-030 — Repository/pack manifests become self-referential or nondeterministic
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Exclude manifest/hash files; sorted hashing; fixed ZIP metadata; pair validation
- **Status:** MITIGATED_W02

## RISK-031 — Parallel Codex worktrees collide on shared unfrozen contracts
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Explicit worktree policy, protected/shared file ownership and focused task packets
- **Status:** OPEN

## RISK-032 — Wave02 prematurely freezes domain/service architecture
- **Severity:** MEDIUM
- **Likelihood:** MEDIUM
- **Mitigation:** Minimal src scaffold; defer football/service boundaries to W03
- **Status:** MITIGATED_W02

## RISK-033 — Local and CI validation behavior diverges
- **Severity:** MEDIUM
- **Likelihood:** MEDIUM
- **Mitigation:** CI calls same Python validation/tests used locally
- **Status:** MITIGATED_W02

## RISK-034 — Windows path or line-ending differences break tooling
- **Severity:** MEDIUM
- **Likelihood:** MEDIUM
- **Mitigation:** pathlib, gitattributes/editorconfig, Windows/Linux CI
- **Status:** OPEN

## RISK-035 — Credentials or large local artifacts enter cumulative ZIP
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Secret scan, forbidden-artifact scan, gitignore and strict packaging validation
- **Status:** OPEN

## RISK-036 — Required external environment manager becomes unnecessary dependency
- **Severity:** LOW
- **Likelihood:** MEDIUM
- **Mitigation:** Use venv/pip portability baseline; optional accelerators only
- **Status:** MITIGATED_W02

## RISK-037 — Modular monolith degrades into tightly coupled god modules
- **Severity:** MEDIUM
- **Likelihood:** MEDIUM
- **Mitigation:** Enforce logical ownership/import direction and architecture registry tests
- **Status:** OPEN


## RISK-038 — Parquet/DuckDB default cannot satisfy later transactional or concurrent entity workflows
- **Severity:** MEDIUM
- **Likelihood:** MEDIUM
- **Mitigation:** Keep storage contracts backend-neutral and evaluate PostgreSQL/relational adapter in W07/W22
- **Status:** OPEN


## RISK-039 — Snapshot serving exposes stale forecast if refresh orchestration fails
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Timestamp every forecast, show freshness, monitor refresh jobs and never label stale snapshot as current
- **Status:** OPEN


## RISK-040 — Research experiment or agent bypasses protected evaluation and changes production state
- **Severity:** CRITICAL
- **Likelihood:** MEDIUM
- **Mitigation:** Separate research plane; protected evaluation/promotion interface; immutable judging rules
- **Status:** OPEN


## RISK-041 — LLM-derived extraction enters canonical state without sufficient evidence validation
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Retain source evidence/extraction provenance/confidence and require deterministic validation/review
- **Status:** OPEN


## RISK-042 — W03 A&M specialization interface is misread as a frozen residual-model implementation
- **Severity:** MEDIUM
- **Likelihood:** MEDIUM
- **Mitigation:** Document semantic-only contract; W14/W16 retain statistical-family authority
- **Status:** OPEN


## RISK-043 — Serving layer bypasses forecast snapshots and creates unreproducible on-request outputs
- **Severity:** HIGH
- **Likelihood:** LOW
- **Mitigation:** Read-only serving boundary plus architecture dependency tests and snapshot lineage
- **Status:** OPEN


## RISK-044 — Future service split breaks shared contracts or creates duplicate sources of truth
- **Severity:** HIGH
- **Likelihood:** LOW
- **Mitigation:** Split only behind accepted interfaces and preserve canonical/PIT ownership
- **Status:** OPEN


## RISK-045 — Architecture registry drifts from later implementation
- **Severity:** MEDIUM
- **Likelihood:** MEDIUM
- **Mitigation:** Run architecture validator each wave and update registry via ADR when boundaries materially change
- **Status:** OPEN

## W04 acceptance/governance risks

## RISK-046 — Acceptance criteria remain too vague to verify
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Machine-readable control catalog with criterion, evidence mode, gate, owner and exact traceability
- **Status:** MITIGATED_W04

## RISK-047 — Arbitrary numeric thresholds create false rigor
- **Severity:** HIGH
- **Likelihood:** HIGH
- **Mitigation:** Threshold registry records unknown values as evidence-pending; no W04 placeholders
- **Status:** MITIGATED_W04

## RISK-048 — Future controls are marked PASS without evidence
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Requirement lifecycle and acceptance evidence state are separate; future controls remain DEFINED_PENDING_OWNER
- **Status:** MITIGATED_W04

## RISK-049 — Protected test becomes iterative tuning feedback
- **Severity:** CRITICAL
- **Likelihood:** MEDIUM
- **Mitigation:** Protected-test seal and promotion criteria fixed before inspection
- **Status:** OPEN

## RISK-050 — Ambiguous PIT evidence fails open
- **Severity:** CRITICAL
- **Likelihood:** MEDIUM
- **Mitigation:** Unknown known-at semantics are unsafe/review-required and release-blocking until resolved
- **Status:** OPEN

## RISK-051 — REQ/ADR/RISK/acceptance traceability drifts
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Exact coverage validator and machine-readable mapping files
- **Status:** MITIGATED_W04

## RISK-052 — Performance limits are guessed before real workloads
- **Severity:** MEDIUM
- **Likelihood:** HIGH
- **Mitigation:** Benchmark-first threshold ownership on target hardware in W19-W23
- **Status:** OPEN

## RISK-053 — Logs expose credentials/restricted data
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Redacted structured logging acceptance policy
- **Status:** OPEN

## RISK-054 — Manual rights/semantic review is skipped after automated PASS
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Explicit MANUAL_REVIEW evidence mode with recorded rationale/evidence/date
- **Status:** OPEN


# Wave 05 planning risks

## RISK-055 — W05 backlog becomes stale after W06 source discoveries
- **Severity:** HIGH
- **Likelihood:** HIGH
- **Mitigation:** Mandatory W06 replan gate; preserve task IDs and revise statuses/dependencies through change log
- **Status:** OPEN

## RISK-056 — Backlog over-decomposition creates micro-handoff overhead
- **Severity:** MEDIUM
- **Likelihood:** MEDIUM
- **Mitigation:** Codex packets group coherent task slices; tasks remain atomic enough to test but not prompt fragments
- **Status:** MITIGATED_W05

## RISK-057 — Backlog under-specification lets Codex infer unsafe scope
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Explicit outputs, mutation scope, dependencies, AC/REQ mapping and stop conditions
- **Status:** MITIGATED_W05

## RISK-058 — Parallel worktrees concurrently mutate shared contracts
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Shared-contract ownership table and serialized mutation lane
- **Status:** OPEN

## RISK-059 — Fake time estimates distort implementation decisions
- **Severity:** MEDIUM
- **Likelihood:** MEDIUM
- **Mitigation:** No duration estimates; dependency/complexity classes only until measured throughput exists
- **Status:** MITIGATED_W05

## RISK-060 — Blocked tasks execute before protected prerequisite gate
- **Severity:** CRITICAL
- **Likelihood:** MEDIUM
- **Mitigation:** Machine-readable dependency DAG/readiness validator; protected gates block downstream readiness
- **Status:** OPEN

## RISK-061 — Requirement/acceptance/task traceability drifts as backlog changes
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Exact-coverage task traceability tables and validate_backlog.py
- **Status:** OPEN

## RISK-062 — Critical-path label is mistaken for a promised delivery schedule
- **Severity:** MEDIUM
- **Likelihood:** MEDIUM
- **Mitigation:** Document dependency-critical semantics and prohibit duration interpretation
- **Status:** MITIGATED_W05

## RISK-063 — Autonomous Codex queue expands scope beyond current wave or protected contracts
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Packet wave ownership, stop conditions, protected-control boundary, integration steward rules
- **Status:** OPEN

## RISK-064 — Too many concurrent worktrees exceed local CPU/RAM/storage or increase merge risk
- **Severity:** MEDIUM
- **Likelihood:** MEDIUM
- **Mitigation:** Bounded adaptive concurrency based on independence/resource pressure; no fixed maximum required by W05
- **Status:** OPEN

## W06 source/data risks
See RISK-065..079 and `docs/data_research/w06/DATA_SOURCE_RISK_REGISTER.csv`. Highest risks are availability noncoverage/missingness semantics, weather model-era gaps, derived-source upstream provenance, changing regulatory semantics and unresolved historical depth/injury data.

## W07 canonical identity/entity-resolution risks

### RISK-080 — Name collisions/normalization conflate distinct players or coaches
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Prohibit name-only durable joins; review ambiguous candidates; labeled resolver tests in W19
- **Status:** OPEN

### RISK-081 — One real entity is fragmented into duplicate canonical IDs
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Verified source mappings, aliases, merge/redirect history and duplicate-detection review
- **Status:** OPEN

### RISK-082 — Source IDs are reused or change semantics across time/schema versions
- **Severity:** HIGH
- **Likelihood:** LOW_MEDIUM
- **Mitigation:** Scope source keys by source/type/context; validate direct-ID contracts; preserve source versions
- **Status:** OPEN

### RISK-083 — Transfers/role changes accidentally create new player/coach identities
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Separate human identity from membership/role episodes
- **Status:** MITIGATED_BY_CONTRACT

### RISK-084 — Rescheduled/canceled/relocated games are duplicated or conflated
- **Severity:** HIGH
- **Likelihood:** MEDIUM
- **Mitigation:** Explicit underlying-contest identity policy and review on opponent replacement/conflicts
- **Status:** OPEN

### RISK-085 — Mutable official reports overwrite earlier publication/capture evidence
- **Severity:** CRITICAL
- **Likelihood:** MEDIUM
- **Mitigation:** Layer publication version/raw capture/source observation identity; immutable raw hashes
- **Status:** MITIGATED_BY_CONTRACT

### RISK-086 — Uncalibrated fuzzy score silently auto-accepts wrong mapping
- **Severity:** CRITICAL
- **Likelihood:** MEDIUM
- **Mitigation:** Disable fuzzy auto-accept; THR-008 remains unset until labeled W19 evidence
- **Status:** MITIGATED_BY_CONTRACT

### RISK-087 — Entity merge/split correction rewrites history and breaks replay
- **Severity:** CRITICAL
- **Likelihood:** LOW_MEDIUM
- **Mitigation:** Append-only decisions, redirect/supersession and versioned downstream rebuilds
- **Status:** MITIGATED_BY_CONTRACT

### RISK-088 — Future multi-user review outgrows single-writer storage model
- **Severity:** MEDIUM
- **Likelihood:** LOW
- **Mitigation:** Storage port + explicit PostgreSQL reopen triggers; benchmark W19/W22
- **Status:** OPEN

### RISK-089 — Weak officiating identity creates false referee histories
- **Severity:** MEDIUM
- **Likelihood:** HIGH
- **Mitigation:** Keep unresolved/name-only official identities out of promoted features; W13 gap policy
- **Status:** OPEN

### RISK-090 — Stale wave-state fields cause wrong-wave execution despite valid pack binding
- **Severity:** HIGH
- **Likelihood:** LOW_MEDIUM
- **Mitigation:** Normalize CURRENT_STATE current_wave field; backward-compatible verifier; cross-file wave validator
- **Status:** MITIGATED_W07

## W08 temporal risks
- **RISK-091 (CRITICAL):** Knowledge time conflated with effective/valid time — Bitemporal W08 contract + AC-067
- **RISK-092 (CRITICAL):** Current mutable page incorrectly treated as historical publication — first-known evidence policy + retrospective quarantine
- **RISK-093 (CRITICAL):** Later source correction rewrites historical replay — append-only publication versions + AC-069
- **RISK-094 (CRITICAL):** No availability report inferred as healthy — policy-scope metadata + UNKNOWN noncoverage
- **RISK-095 (CRITICAL):** Observed weather contaminates earlier pregame forecasts — issued model-run contract + synthetic replay
- **RISK-096 (HIGH):** Weather model initialization mistaken for public availability — separate model_available_at/first_known_at
- **RISK-097 (HIGH):** Fiscal/reporting period mistaken for public availability date — resource dual-time contract
- **RISK-098 (HIGH):** Rule season/effective year used without publication/validity semantics — regulatory dual-time contract
- **RISK-099 (CRITICAL):** Same/future game outputs leak into pregame aggregates — game-completion gate + protected synthetic tests
- **RISK-100 (CRITICAL):** Historical model training uses labels from future games — separate model-training cutoff + AC-076
- **RISK-101 (HIGH):** Naive/local timezone timestamps shift eligibility boundary — timezone-aware UTC normalization + raw value preservation
- **RISK-102 (HIGH):** prediction_eligible_at treated as universal raw truth — derived-policy semantics + validator
- **RISK-103 (CRITICAL):** Feature code bypasses PIT gateway — protected architecture/gateway validation
- **RISK-104 (HIGH):** Historical archive lacks exact first-known evidence — conservative retrieval/lag, uncertainty, suppress feature where necessary
- **RISK-105 (HIGH):** Synthetic PIT tests create false confidence before real replay — explicit maturity state and integration/replay controls remain pending

## Wave 09 raw-feature registry
New risks cover schema drift, scanner type inference, sample-vs-population missingness, name-based false redundancy, semantic join compatibility, temporal-classification drift, accidental feature promotion, invented unknown schemas, nested-path drift, optional Parquet dependency creep, raw-field ID instability, rights/provenance loss and PIT-gateway bypass. Canonical statuses live in `RISK_REGISTER.csv`.


## W11 team-state risks
- **RISK-133 — Recent-game weighting overreacts to football randomness (HIGH):** Compare recency candidates chronologically; retain broader priors and uncertainty **Status:** OPEN. **Owner:** W11-W17.
- **RISK-134 — Early-season prior remains stale after genuine team change (HIGH):** Regime-aware/change-point candidates and faster evidence updating where validated **Status:** OPEN. **Owner:** W11-W17.
- **RISK-135 — Composite prior double-counts talent/returning production/resources (HIGH):** Redundancy/ablation and target-specific lifecycle evidence **Status:** OPEN. **Owner:** W11-W17.
- **RISK-136 — Program resources become an unjustified weekly points bonus (MEDIUM):** Upstream-prior-only default and later ablation **Status:** MITIGATED_W11_CONTRACT. **Owner:** W11-W17.
- **RISK-137 — Regime similarity uses future staff/QB/roster information (CRITICAL):** All continuity factors consume W08 PIT-effective evidence only **Status:** MITIGATED_W11_CONTRACT. **Owner:** W11+.
- **RISK-138 — Change-point detector produces false resets (HIGH):** No automatic hard reset; shrinkage/uncertainty response and protected comparison **Status:** MITIGATED_W11_CONTRACT. **Owner:** W11-W17.
- **RISK-139 — Source/schema coverage break is mistaken for performance regime shift (HIGH):** Track source/schema versions and include data-coverage-break candidate **Status:** MITIGATED_W11_CONTRACT. **Owner:** W11-W19.
- **RISK-140 — FCS strength translation is overconfident (HIGH):** Internal FCS network plus cross-division evidence and translation uncertainty **Status:** OPEN. **Owner:** W11-W19.
- **RISK-141 — Lower-division modeling expands without bound (MEDIUM):** Explicit bounded hierarchy terminating in class priors **Status:** MITIGATED_W11_CONTRACT. **Owner:** W11+.
- **RISK-142 — Hard-coded division penalty creates systematic bias (HIGH):** Fixed penalties prohibited; empirical translation required **Status:** MITIGATED_W11_CONTRACT. **Owner:** W11-W17.
- **RISK-143 — Uncertainty score is misused as directional team-strength correction (HIGH):** Contract separates uncertainty magnitude from strength direction **Status:** MITIGATED_W11_CONTRACT. **Owner:** W11-W16.
- **RISK-144 — National sample utility and current-team relevance are conflated (HIGH):** Separate weighting roles/contracts **Status:** MITIGATED_W11_CONTRACT. **Owner:** W11-W17.
- **RISK-145 — W11 implies injury-adjusted available strength before W12 evidence (HIGH):** Placeholder preserves underlying estimate and marks W12 ownership explicitly **Status:** MITIGATED_W11_CONTRACT. **Owner:** W11-W12.
- **RISK-146 — Early-season/team-state candidate selection overfits small subgroups (HIGH):** Protected chronological national evidence plus subgroup stability; selection deferred W17/W19 **Status:** OPEN. **Owner:** W17-W19.


## Wave 12 risk focus
W12 specifically hardens against roster/depth/availability conflation, postgame depth backfill, binary injury oversimplification, duplicate injury penalties, noncoverage-as-healthy inference, fixed transfer conference penalties, freshman misuse of transfer-production models, future NFL Draft leakage, upstream recruiting/transfer rights assumptions and synthetic-evidence overclaiming. See `RISK-147` through `RISK-161` in `RISK_REGISTER.csv`.


## Wave 13 risk focus
W13 hardens against coach-attribution confounding, title/responsibility ambiguity, weather hindsight, travel/timezone simplification, private-resource fabrication, home-field confounding, rule-era drift, hidden-yards double counting, garbage-time policy bias, opponent-adjustment circularity, schedule look-ahead leakage, officiating bias/coverage gaps and a repaired W14 dependency inversion. See `RISK-162` through `RISK-180` in `RISK_REGISTER.csv`.
## W14 additions
Key open risks are A&M overfitting, sparse high-resolution historical evidence, peer/analog cherry-picking, regime instability, complex-model tuning noise and national degradation hidden by A&M-only scoring. W14 mitigates these with no-adjustment baseline, shrinkage, strict-prior peers/analogs, dual scorecards and protected W16/W17 selection.

## W15 BAS scientific risk focus
W15 hardens against label leakage, future-trained cross-fit expectations, mirrored-game dependence, circular A&M-underperformance anchors, peer/regime cherry-picking, small-sample instability, multiple comparisons, component double counting, live-collapse leakage, pressure to force a nonzero BAS result and fabricated `THR-006`. See `RISK-195` through `RISK-211` in `RISK_REGISTER.csv`.


## W16 additions
RISK-212 through RISK-226 cover incoherent isolated outputs, overtime/tie handling, underdispersion, complexity overfit, market leakage, A&M/BAS circularity/overfit, scenario double counting, arbitrary OOD/disagreement thresholds, Monte Carlo noise, score-support truncation, calibration leakage and accidental presentation of synthetic contracts as trained performance.


## W17 protected-validation risks
- **RISK-227 (CRITICAL) — Protected 2024-2025 outcomes influence tuning or feature/model choices.** Mitigation: Seal split/metrics before protected access; log result access and prohibit tuning feedback. Status: OPEN_W17_PROTOCOL_MITIGATED.
- **RISK-228 (CRITICAL) — Protected holdout is moved after disappointing results.** Mitigation: Holdout movement prohibited except pre-result documented coverage ADR; otherwise UNEVALUABLE. Status: MITIGATED_W17_PROTOCOL.
- **RISK-229 (CRITICAL) — Thresholds are selected after seeing protected results.** Mitigation: Development-only threshold precommitment; protected results cannot set/relax values. Status: MITIGATED_W17_PROTOCOL.
- **RISK-230 (CRITICAL) — Blank thresholds are interpreted as zero or silently waived.** Mitigation: Fail-closed reference gate returns BLOCKED_THRESHOLD_UNSET. Status: MITIGATED_W17_REFERENCE.
- **RISK-231 (HIGH) — Subgroup fishing creates spurious A&M/context claims.** Mitigation: Predeclare scorecards; exploratory post-hoc groups cannot become promotion evidence without new sealed protocol. Status: MITIGATED_W17_PROTOCOL.
- **RISK-232 (CRITICAL) — A&M specialization overfits small protected sample.** Mitigation: Mandatory no-adjustment comparator, shrinkage/null path, dual national/A&M scorecards. Status: OPEN_REAL_EVIDENCE_PENDING.
- **RISK-233 (CRITICAL) — BAS multiple testing creates false Aggie Excess/component claims.** Mitigation: Null-first stability/multiplicity protocol; component family controls and no-effect outcome. Status: OPEN_REAL_EVIDENCE_PENDING.
- **RISK-234 (HIGH) — Metric hacking favors one model by switching primary metric.** Mitigation: Metric hierarchy frozen before protected results; Brier/MAE/proper distribution scores retain declared roles. Status: MITIGATED_W17_PROTOCOL.
- **RISK-235 (MEDIUM) — Calibration conclusion depends on arbitrary bins.** Mitigation: ECE diagnostic only; intercept/slope/reliability and proper scores required. Status: MITIGATED_W17_PROTOCOL.
- **RISK-236 (CRITICAL) — Market closing data leaks into earlier forecast evaluation.** Mitigation: Matched PIT cutoffs and separate benchmark lane; W08 market snapshot rules remain protected. Status: MITIGATED_BY_W08_W17.
- **RISK-237 (HIGH) — OOD score is misused as directional team-strength signal.** Mitigation: Evaluate as warning/error association only; directional use prohibited. Status: MITIGATED_W17_PROTOCOL.
- **RISK-238 (HIGH) — Model disagreement is mistaken for calibrated uncertainty.** Mitigation: Require incremental error/coverage evidence and THR-015 development-only thresholding. Status: OPEN_REAL_EVIDENCE_PENDING.
- **RISK-239 (HIGH) — Protected holdout lacks source coverage for a candidate feature.** Mitigation: Report candidate unevaluable or use pre-result coverage ADR; do not replace holdout after result review. Status: OPEN_MATERIALIZATION_PENDING.
- **RISK-240 (HIGH) — Rule/regime shift in 2024-2025 causes distribution shift.** Mitigation: Keep shift visible as protected robustness evidence; analyze predeclared regime scorecard, do not tune on it. Status: OPEN_REAL_EVIDENCE_PENDING.
- **RISK-241 (CRITICAL) — Repeated future use of same protected test turns it into training feedback.** Mitigation: One-way result access, immutable result records and 2026+ forward shadow evidence; future resets require governance. Status: OPEN_W21_PLUS.
- **RISK-242 (CRITICAL) — W17 protocol PASS is misreported as trained predictive performance.** Mitigation: Explicit protocol-only maturity, zero protected metric claims and W17 validation guard. Status: MITIGATED_W17.

## W18 experimentation/research risks
RISK-243 through RISK-260 cover result-dependent experiment identity, judging-rule mutation, protected-metric HPO leakage, tool lock-in, unsafe distributed SQLite HPO, canonical-repo worktree contamination, negative-result deletion, silent changed-config retries, replay mismatch, self-promotion, protected-feedback loops, premature advanced-model compute, unauthorized paid compute, concurrent shared-contract mutations, tool-version drift, oversized artifacts, sensitive research logs and false empirical-completion claims. Canonical status remains in `RISK_REGISTER.csv`.

## Corrected W18 risk additions
RISK-261 through RISK-280 cover tournament mispromotion, baseline omission, HPO leakage/search drift, resource/storage misuse, hypothesis/result rewriting, protected worktree mutation, replay/adoption bypass, incompatible ranking, negative-result deletion, thin-scope recurrence, draft-parent confusion, and W17 preservation failure. Canonical status remains in `RISK_REGISTER.csv`.

## W18 full-rebuild risk additions
RISK-281 through RISK-300 cover local experiment-store corruption, queue tampering, identity/retry drift, resource overcommit, unauthorized paid compute, shared-contract conflicts, incompatible rankings, hidden multi-metric regressions, artifact leakage, protected feedback leakage, replay-tolerance drift, adapter authority confusion, hidden search multiplicity, repeated dead ends, operational/scientific failure confusion, evidence-destroying worktree cleanup, premature advanced-model admission, shallow-wave recurrence, and wrong-parent reuse. Canonical details remain in `RISK_REGISTER.csv`.

## W24 additions
- **RISK-308 (HIGH):** W24 sequencing override could be mistaken for W23 target-hardware clearance. **Status:** OPEN_CARRIED_W25. AC-233 preserves the blocker explicitly.
- **RISK-309 (HIGH):** SportsDataverse sibling layers could be double-counted as independent evidence. **Status:** MITIGATED_REFERENCE_W24 via SRC-061 provenance semantics.
- **RISK-310 (MEDIUM):** Recent ensemble weather data could be over-promoted without long-history evidence. **Status:** MITIGATED_POLICY_W24; SRC-062 remains optional/research-only.

## W25 final risk posture
The full 310-row risk register is snapshotted in `docs/final/FINAL_RISK_REGISTER.csv`. Open empirical/data/source risks remain handoff risks rather than being cosmetically closed. The highest explicit deployment blocker remains AC-038 target-hardware evidence.
