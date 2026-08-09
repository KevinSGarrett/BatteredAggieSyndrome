# Adaptive Change Log

## CHANGE-001
- **Wave:** W01
- **Original:** ZIP entry order implicitly used for chat chronology
- **Revised:** Explicit numerical 001→020 source-log ordering
- **Reason:** Archive lists 020 first; chronology errors could resurrect superseded ideas
- **Requirements:** REQ-131
- **ADRs:** ADR-022
- **Future impact:** No 25-wave scope change

## CHANGE-002
- **Wave:** W01
- **Original:** Exact host filename could be mistaken for artifact identity
- **Revised:** Content/internal edition/required structure/SHA identity
- **Reason:** Uploaded recon copy has suffixes while internal edition is authoritative
- **Requirements:** REQ-020
- **ADRs:** ADR-023
- **Future impact:** Applies to future pack validation

## CHANGE-003
- **Wave:** W01
- **Original:** Root PACK_MANIFEST might be treated as authoritative
- **Revised:** Use final/manifests/FINAL_FILE_MANIFEST.csv and FINAL_FILE_HASHES.sha256; document root self-entry mismatch
- **Reason:** Final manifest validates 216/216; root manifest only mismatches self-referential entry
- **Requirements:** REQ-008
- **ADRs:** ADR-024
- **Future impact:** Wave02 packaging should formalize non-self-referential manifest policy

## CHANGE-004
- **Wave:** W01
- **Original:** Historical source proposals could be flattened into current requirements
- **Revised:** Explicit supersession ledger and source precedence
- **Reason:** Source chat contains corrected pretrained/PFF/data-scope ideas
- **Requirements:** REQ-009
- **ADRs:** ADR-026
- **Future impact:** Prevents drift in later waves

## CHANGE-005
- **Wave:** W01
- **Original:** Wave plan could be treated as fixed task checklist
- **Revised:** Operationalize Level A/B/C classification, hypotheses ledger and opportunity backlog
- **Reason:** Master v2.1 explicitly requires adaptive evidence-driven evolution
- **Requirements:** REQ-010/012/015
- **ADRs:** ADR-021
- **Future impact:** No future wave renumbering; scopes remain revisable

## CHANGE-006
- **Wave:** W02
- **Original:** Pre-create the anticipated full future package tree
- **Revised:** Keep W02 src package minimal and defer domain/service packages to W03
- **Reason:** Avoid premature architecture lock-in and redundant file growth
- **Requirements:** REQ-133;REQ-144
- **ADRs:** ADR-031;ADR-038
- **Future impact:** W03 explicitly evaluates/finalizes logical boundaries

## CHANGE-007
- **Wave:** W02
- **Original:** Pack verification/manifest rules remain mostly prose
- **Revised:** Make prior-pair verification, safe extraction, deterministic manifests and pair validation executable
- **Reason:** W01 revealed real filename/manifest integrity edge cases
- **Requirements:** REQ-136;REQ-137;REQ-138;REQ-147;REQ-148
- **ADRs:** ADR-034;ADR-039
- **Future impact:** Future waves gain deterministic start/end validation

## CHANGE-008
- **Wave:** W02
- **Original:** Hydration contents assembled manually
- **Revised:** Use machine-readable hydration allowlist plus generated binding/recovery/hashes
- **Reason:** Reduces omission/drift risk across 23 remaining waves
- **Requirements:** REQ-139
- **ADRs:** ADR-035
- **Future impact:** Future hydration packs generated consistently

## CHANGE-009
- **Wave:** W02
- **Original:** GitHub/Codex operating structure could overcommit to future CI/tool schemas
- **Revised:** Create minimal cross-platform CI and repository-local Codex contracts only
- **Reason:** Preserves verified current value while deferring unneeded complexity
- **Requirements:** REQ-140;REQ-149;REQ-150
- **ADRs:** ADR-036;ADR-037
- **Future impact:** W23 expands CI; Codex config added only if verified/useful

## CHANGE-010
- **Wave:** W03
- **Original:** A service-oriented/microservice decomposition remained a plausible architecture interpretation
- **Revised:** Adopt offline-first modular monolith with logical boundaries and defer network-service splits
- **Reason:** Local target, snapshot product and reproducibility do not create a current independent-scaling need
- **Requirements:** REQ-151;REQ-170
- **ADRs:** ADR-040;ADR-053
- **Future impact:** W23 may revisit deployment splits only on evidence


## CHANGE-011
- **Wave:** W03
- **Original:** Forecast serving could imply synchronous feature/model execution
- **Revised:** Serve immutable precomputed forecast snapshots
- **Reason:** Improves reproducibility, local reliability and temporal lineage
- **Requirements:** REQ-152;REQ-171
- **ADRs:** ADR-041;ADR-050
- **Future impact:** W22 builds product surfaces against snapshot contract


## CHANGE-012
- **Wave:** W03
- **Original:** DuckDB/Polars/PostgreSQL were undifferentiated strong defaults
- **Revised:** Prefer native raw + Parquet + DuckDB early; keep PostgreSQL conditional behind storage boundary
- **Reason:** Avoid mandatory server before transactional/concurrent need is demonstrated
- **Requirements:** REQ-167;REQ-168
- **ADRs:** ADR-042;ADR-043
- **Future impact:** W07 validates canonical relational needs


## CHANGE-013
- **Wave:** W03
- **Original:** Research, LLM and future-live responsibilities were conceptually present but not isolated as architecture planes
- **Revised:** Make research/LLM/live boundaries explicit and protect deterministic pregame path
- **Reason:** Prevents governance bypass, unreproducible runtime dependencies and same-game leakage
- **Requirements:** REQ-153;REQ-154;REQ-166;REQ-172
- **ADRs:** ADR-048;ADR-049;ADR-051
- **Future impact:** W18/W21/Phase5 inherit explicit isolation


## CHANGE-014
- **Wave:** W03
- **Original:** Architecture existed only in prose/ADRs
- **Revised:** Add machine-readable component/interface/data-zone registry plus executable validator
- **Reason:** Reduces future drift as packages materialize
- **Requirements:** REQ-173;REQ-174
- **ADRs:** ADR-054
- **Future impact:** Every later architecture-changing wave must update/validate registry


## CHANGE-015
- **Wave:** W03
- **Original:** W02 opportunity backlog accidentally reused OPP-009/010/011 IDs
- **Revised:** Renumber W02-added duplicates to OPP-013/014/015 while preserving the original opportunities
- **Reason:** Unique identifiers are required for reliable future backlog references
- **Requirements:** REQ-173
- **ADRs:** ADR-054
- **Future impact:** No wave mission change

## CHANGE-010 — W04 requirement classification hardening
Several W01-W03 entries mixed invariants with strong modeling defaults or historical wave-scoped completion. W04 preserved every stable requirement ID but corrected the class/status semantics in the classification audit.

## CHANGE-011 — W04 acceptance evidence dimension
Requirement lifecycle/class and acceptance evidence are now separate. Future mandatory requirements remain `CONTRACT_DEFINED_OWNER_PENDING` until their owning wave provides evidence; they are not falsely marked PASS.

## CHANGE-012 — W04 threshold deferral by evidence owner
No model/data/performance threshold was fabricated. `ACCEPTANCE_THRESHOLD_REGISTRY.csv` assigns each unresolved quantitative threshold to the wave that can actually justify it.

## CHANGE-013 — W04 executable acceptance governance
Acceptance controls, threshold references and REQ/ADR/RISK mappings are machine-readable and validated by repository tooling.


## Wave 05
- CHANGE-014: dependency DAG/gate spine replaces fake calendar critical path.
- CHANGE-015: W06 is mandatory replan gate; source-dependent W07+ tasks remain provisional.
- CHANGE-016: bounded adaptive parallelism; unfrozen shared-contract mutations serialized.
- CHANGE-017: coherent work packets replace one-requirement-per-prompt micro-handoffs while exact traceability remains.


## Wave 06

### CHANGE-018
- **Original:** Availability reconstruction depended mainly on fragmented team/media evidence
- **Revised:** Use versioned official conference/CFP availability reports as primary evidence wherever policy coverage applies, with explicit noncoverage elsewhere
- **Reason:** Fresh research found materially broader official recent football availability-report systems
- **Requirements:** REQ-247;REQ-248;REQ-259
- **ADRs:** ADR-077;ADR-086
- **Future impact:** W07-W08;W12-W14

### CHANGE-019
- **Original:** Historical weather sources emphasized generic forecast/history and observed weather
- **Revised:** Preserve issued forecast model runs with model/version/run-init/lead/valid-time semantics; keep observed/reanalysis separate
- **Reason:** NOAA model-run archives and Open-Meteo previous/single-run interfaces materially improve what-was-knowable reconstruction
- **Requirements:** REQ-245;REQ-246
- **ADRs:** ADR-078;ADR-086
- **Future impact:** W08;W13

### CHANGE-020
- **Original:** Rule era focused mainly on on-field football rule changes
- **Revised:** Expand to effective-dated regulatory environment covering playing rules, roster limits, eligibility and transfer rules
- **Reason:** Recent NCAA roster/eligibility changes materially alter player/roster feature semantics
- **Requirements:** REQ-250
- **ADRs:** ADR-081
- **Future impact:** W08;W12-W13

### CHANGE-021
- **Original:** Lower divisions were represented by coarse priors without a refreshed official-source hierarchy
- **Revised:** Use bounded NCAA/NAIA/NJCAA official statistics/rankings as the preferred lower-division evidence lane
- **Reason:** Fresh research confirmed viable official source classes without requiring FBS-equivalent recursive modeling
- **Requirements:** REQ-249
- **ADRs:** ADR-080
- **Future impact:** W11-W12

### CHANGE-022
- **Original:** W07+ source-dependent WBS tasks were provisional pending research
- **Revised:** Clear W06_REPLAN, convert revalidated tasks to PLANNED/READY and add TASK-190 through TASK-201 for newly discovered temporal/source/governance work
- **Reason:** Fresh research materially changed future source semantics but not the 25-wave mission structure
- **Requirements:** REQ-258
- **ADRs:** ADR-087
- **Future impact:** W07-W24

### CHANGE-023
- **Original:** W03 modular-monolith architecture remained subject to source-universe challenge
- **Revised:** Retain modular monolith and immutable snapshot serving; refine data contracts instead of introducing distributed infrastructure
- **Reason:** Source diversity creates adapter/temporal/provenance requirements, not independent scaling or online-serving requirements
- **Requirements:** REQ-253
- **ADRs:** ADR-085
- **Future impact:** W07-W23


## CHANGE-024
- **Wave:** W07
- **Original:** W07 source identity could be modeled as provider/resource plus normalized records
- **Revised:** Freeze five-layer source evidence identity: source system → resource → publication version → raw capture → source observation
- **Reason:** W06 found mutable availability/ranking/report pages where publication edits and retrieval events must remain distinguishable
- **Requirements:** REQ-275;REQ-276
- **ADRs:** ADR-096
- **Future impact:** W08-W09;W12;W24


## CHANGE-025
- **Wave:** W07
- **Original:** Entity resolver could choose a numeric confidence threshold during W07
- **Revised:** Disable fuzzy auto-accept; only verified mapping/direct/crosswalk classes auto-accept until W19 labeled evidence exists
- **Reason:** No labeled resolver benchmark exists and inventing THR-008 would create false precision and silent identity risk
- **Requirements:** REQ-266;REQ-278;REQ-282
- **ADRs:** ADR-092
- **Future impact:** W19


## CHANGE-026
- **Wave:** W07
- **Original:** PostgreSQL could become canonical-state default because manual entity review is relational
- **Revised:** Keep append-only Parquet/DuckDB single-writer default behind storage ports; defer PostgreSQL until concurrent transactional need is demonstrated
- **Reason:** Current local batch/review workflow derives current state from immutable events and has no multi-writer requirement
- **Requirements:** REQ-168;REQ-281
- **ADRs:** ADR-097;ADR-098
- **Future impact:** W19;W22


## CHANGE-027
- **Wave:** W07
- **Original:** Prior-wave verifier expected only current_wave in CURRENT_STATE even though W06 emitted wave
- **Revised:** Normalize W07 CURRENT_STATE to current_wave and make verifier backward-compatible with legacy wave key
- **Reason:** The W06 pack binding was valid but its own verifier could fail on a state-key naming mismatch
- **Requirements:** REQ-001;REQ-002
- **ADRs:** ADR-100
- **Future impact:** W08-W25


## CHANGE-028
- **Wave:** W07
- **Original:** Identity correction might mutate canonical rows in place
- **Revised:** Use append-only resolution decisions plus merge redirects/split supersessions and rebuild later derivatives under new versions
- **Reason:** Destructive correction would break forecast replay and provenance
- **Requirements:** REQ-262;REQ-277;REQ-279
- **ADRs:** ADR-094
- **Future impact:** W08;W19

## Wave 08
- **CHANGE-029:** Treat effective/known-at timestamps as one generic as-of time → Separate knowledge/system time from real-world validity/event time — Future-effective known rules and late-published older reports prove one-axis semantics can leak or wrongly exclude data
- **CHANGE-030:** Treat prediction_eligible_at as a universal stored timestamp → Define it as policy-versioned derived/cache metadata plus mandatory validity/domain/revision checks — Eligibility is context- and target-dependent; one raw timestamp cannot encode all semantics
- **CHANGE-031:** Use weather date/observation as generic historical environment → Require exact issued model-run availability + valid-time lineage for pregame replay — W06/Recon distinguish historical forecast evidence from realized weather
- **CHANGE-032:** Treat missing official availability report as weak negative signal → Explicitly encode report policy/game scope; noncoverage remains UNKNOWN — W06 conference policies do not cover every game/era
- **CHANGE-033:** Allow current corrections to backfill canonical history → Replay source revisions as-known-at-cutoff and preserve older versions — Reproducibility requires historical snapshots to reflect information actually available then
- **CHANGE-034:** PIT tests remain prose-only until materialization → Add executable synthetic bitemporal/leakage battery now while clearly deferring real-data proof — Protected semantics benefit from early executable tests without overstating production evidence
- **CHANGE-035:** Repaired inherited duplicate W07 carry-forward issue IDs by preserving their content as ISSUE-064..067.

## W09
- **CHANGE-036** — Preserve 1,197 verified recon temporal field classifications instead of rescoring them during W09 — Avoid scanner/LLM drift from evidence-backed temporal registry.
- **CHANGE-037** — Represent unknown W06 endpoint schemas as SCHEMA_PENDING_MATERIALIZATION — Prevents invented field coverage.
- **CHANGE-038** — Separate sample missingness evidence from population completeness — Prevents representative samples from becoming fake dataset statistics.
- **CHANGE-039** — Treat exact-name field overlap as review clusters, not semantic duplicates — Prevents destructive source consolidation.
- **CHANGE-040** — Freeze raw-field → W10 candidate-input handoff without feature promotion — Keeps empirical adoption authority in W10+.


## CHANGE-041
- **Wave:** W10
- **Original:** Rolling/EWMA/trend candidates could be interpreted as fixed transformations.
- **Revised:** Parameters are explicit experiment candidates; no universal window/decay is frozen.
- **Reason:** Avoid intuitive/historical overfitting.

## CHANGE-042
- **Wave:** W10
- **Original:** Feature screening methods listed independently.
- **Revised:** Multi-stage evidence pipeline; no single importance/association statistic promotes.
- **Reason:** Correlation, MI, regularization and model importance each have known failure modes.

## CHANGE-043
- **Wave:** W10
- **Original:** Feature lifecycle existed as named states.
- **Revised:** State transitions are target-specific, append-only and evidence-gated; BANNED is structural.
- **Reason:** Prevent silent resurrection and target leakage of feature decisions.

## CHANGE-044
- **Wave:** W10
- **Original:** W10 might be read as the empirical selection wave.
- **Revised:** W10 implements contracts/reference code and zero promotions; W17/W19 own real-data evidence.
- **Reason:** Required historical materialization/protected evaluation does not yet exist.

## CHANGE-041
- **Wave:** W11
- **Revised:** Treat national historical utility and current-team relevance as separate roles
- **Reason:** Avoid discarding old national data merely because current-team regime changed
- **Requirements:** REQ-372
- **ADRs:** ADR-143
- **Future impact:** W12/W13 populate richer state inputs; W17/W19 select parameters empirically.

## CHANGE-042
- **Wave:** W11
- **Revised:** Freeze a four-part team-state semantic interface rather than one static rating
- **Reason:** Preserves underlying-vs-available distinction and W12 ownership
- **Requirements:** REQ-364;REQ-366
- **ADRs:** ADR-139;ADR-149
- **Future impact:** W12/W13 populate richer state inputs; W17/W19 select parameters empirically.

## CHANGE-043
- **Wave:** W11
- **Revised:** Replace illustrative recency/Week-1 weights with explicit experiment candidates
- **Reason:** Source-chat numbers were examples; hard-coding would create unsupported model assumptions
- **Requirements:** REQ-369;REQ-370;REQ-373
- **ADRs:** ADR-141;ADR-142;ADR-144
- **Future impact:** W12/W13 populate richer state inputs; W17/W19 select parameters empirically.

## CHANGE-044
- **Wave:** W11
- **Revised:** Make change-point response shrinkage/uncertainty-first instead of automatic reset
- **Reason:** Reduces false regime breaks and preserves useful history
- **Requirements:** REQ-375;REQ-376
- **ADRs:** ADR-145
- **Future impact:** W12/W13 populate richer state inputs; W17/W19 select parameters empirically.

## CHANGE-045
- **Wave:** W11
- **Revised:** Freeze a bounded lower-division hierarchy with continuous strength + uncertainty
- **Reason:** Prevents infinite recursion while preserving FCS/FBS calibration value
- **Requirements:** REQ-378;REQ-379;REQ-382;REQ-383
- **ADRs:** ADR-146;ADR-147
- **Future impact:** W12/W13 populate richer state inputs; W17/W19 select parameters empirically.


## CHANGE-046
- **Wave:** W12
- **Original:** Player state could be interpreted as one mutable roster/depth/availability status.
- **Revised:** Separate effective-dated roster membership, depth/rotation expectation, availability and postgame participation.
- **Reason:** Recon policies and PIT safety require distinct evidence semantics.
- **Requirements:** REQ-389..REQ-393
- **ADRs:** ADR-152;ADR-157
- **Future impact:** W19 materializes these states separately.

## CHANGE-047
- **Wave:** W12
- **Original:** Availability could collapse to starter-out counts or active/out labels.
- **Revised:** Probability + effectiveness + expected usage + replacement scenario + uncertainty.
- **Reason:** Source/recon explicitly require player/replacement-specific impact and limited/questionable scenarios.
- **Requirements:** REQ-396..REQ-404
- **ADRs:** ADR-154..ADR-156
- **Future impact:** W16/W17 calibrate forecast impact.

## CHANGE-048
- **Wave:** W12
- **Original:** Transfer context might be approximated by conference movement.
- **Revised:** Same-player position-aware translation design using continuous competition/context; no fixed conference penalty.
- **Reason:** Recon transfer policy.
- **Requirements:** REQ-407..REQ-412
- **ADRs:** ADR-158;ADR-159
- **Future impact:** W17/W19 train/evaluate from real historical transfers.

## CHANGE-049
- **Wave:** W12
- **Original:** TASK-200 was blocked by stale planned TASK-197.
- **Revised:** Complete TASK-197 as explicit W12 catch-up by augmenting dataset source/access/license provenance, then complete TASK-200 audit.
- **Reason:** Avoid waiving a real dependency and preserve W06 rights/provenance findings.
- **Requirements:** REQ-419
- **ADRs:** ADR-164;ADR-165
- **Future impact:** W19 acquisition/publication decisions inherit richer provenance.

## CHANGE-050
- **Wave:** W12
- **Original:** Official availability lane could be mistaken for already materialized history.
- **Revised:** Freeze priority/adapter/materialization plan only; mark actual report acquisition as pending W19.
- **Reason:** Honest implementation status.
- **Requirements:** REQ-417;REQ-418
- **ADRs:** ADR-163
- **Future impact:** A&M/SEC recent history gets first materialization priority.

## CHANGE-051
- **Wave:** W12
- **Original:** Preseason honors/draft signals could become intuition-based bonuses.
- **Revised:** Timestamped experimental candidate lanes with future draft leakage explicitly banned.
- **Reason:** Recon honors/draft policies.
- **Requirements:** REQ-413..REQ-416
- **ADRs:** ADR-161;ADR-162
- **Future impact:** W17 ablation decides incremental value.

## CHANGE-052
- **Wave:** W12
- **Original:** Available-strength/player contracts might be interpreted as calibrated forecast effects.
- **Revised:** W12 freezes abstract interfaces only; no empirical player/transfer/availability winner or point mapping.
- **Reason:** Protected empirical promotion and honest maturity.
- **Requirements:** REQ-420;REQ-421
- **ADRs:** ADR-166;ADR-167
- **Future impact:** W16-W19 own calibration/selection/materialization.


## CHANGE-053
- **Wave:** W13
- **Original:** Coach identity could collapse to one generic rating
- **Revised:** Effective-dated role/responsibility episodes plus residual/hierarchical candidate profiles
- **Reason:** Preserves role-specific career evidence and avoids raw-output attribution
- **Requirements:** REQ-422;REQ-423;REQ-424;REQ-425;REQ-426
- **ADRs:** ADR-168;ADR-169;ADR-170
- **Future impact:** W14;W17;W19


## CHANGE-054
- **Wave:** W13
- **Original:** Home/resources could be intuition-based team bonuses
- **Revised:** Learned home residual plus explicit R0/R1/R2/R3 resource lanes
- **Reason:** Controls confounding and public/private asymmetry
- **Requirements:** REQ-435;REQ-436;REQ-437;REQ-438;REQ-459
- **ADRs:** ADR-175;ADR-176
- **Future impact:** W14;W17;W19


## CHANGE-055
- **Wave:** W13
- **Original:** Rule era could remain a season label
- **Revised:** Effective-dated regulatory environment with definition versioning
- **Reason:** Rules/roster/eligibility/transfer semantics change within training history
- **Requirements:** REQ-440;REQ-441
- **ADRs:** ADR-178
- **Future impact:** W14;W19


## CHANGE-056
- **Wave:** W13
- **Original:** Game mechanics could collapse to aggregate rankings
- **Revised:** Componentize possession, field position, special teams and score-state policies
- **Reason:** Avoid double counting and preserve interpretable experimental lanes
- **Requirements:** REQ-442;REQ-443;REQ-444;REQ-445;REQ-447;REQ-448
- **ADRs:** ADR-179;ADR-180;ADR-181
- **Future impact:** W16;W17;W20


## CHANGE-057
- **Wave:** W13
- **Original:** Officiating could be treated as causal team/referee narrative
- **Revised:** Fail-closed experimental crew lane with pregame-public assignment requirement
- **Reason:** Recon evidence says retrospective crew identity exists but upcoming assignment availability is uncertain/confounded
- **Requirements:** REQ-454;REQ-455
- **ADRs:** ADR-184
- **Future impact:** W17;W24


## CHANGE-058
- **Wave:** W13
- **Original:** TASK-088 W14 architecture depended on future W20 TASK-087 implementation gate
- **Revised:** TASK-088 now depends on frozen W12/W13 contract gates
- **Reason:** Restores executable numbered wave order without bypassing implementation evidence
- **Requirements:** REQ-461
- **ADRs:** ADR-186
- **Future impact:** W14


## CHANGE-059
- **Wave:** W13
- **Original:** Adaptive-change CSV lagged W11/W12 Markdown log
- **Revised:** Backfill CHANGE-041 through CHANGE-052 into CSV ledger
- **Reason:** Keep structured recovery state consistent with narrative history
- **Requirements:** REQ-457
- **ADRs:** ADR-185
- **Future impact:** W14-W25
## W14
- CHANGE-060 repaired 14 W13 requirement CSV rows whose fields were column-shifted; stable IDs and meanings were preserved.
- CHANGE-061 made A&M higher resolution an overlay on national canonical/PIT truth rather than a separate truth system.
- CHANGE-062 made the no-adjustment national forecast a mandatory specialization baseline and valid final outcome.
- CHANGE-063 separated peer cohorts from historical analog retrieval.
- CHANGE-064 retained frequent immutable snapshot cadences as candidates rather than freezing exact times.
- CHANGE-065 froze multiple specialization challengers without choosing a winner.

## W15 changes
- CHANGE-066: chronological/canonical-game cross-fit rather than row-only holdout.
- CHANGE-067: BAS-independent primary expectation anchor with separate sensitivity anchors.
- CHANGE-068: explicit null/no-excess scientific outcome.
- CHANGE-069: component additivity not assumed.
- CHANGE-070: Collapse BAS isolated to live replay.
- CHANGE-071/072: repaired future-wave TASK-040 dependency inversions for W15/W16.
- CHANGE-073: refreshed stale operating/navigation state.


## W16 additions
- **CHANGE-074:** Reframed W16 baseline tasks as contract/reference work; W20 remains trained starter implementation.
- **CHANGE-075:** Repaired W17 protected-evaluation sequencing semantics so split/metrics/protocols are frozen before any protected evidence and no pre-materialization empirical values are implied.
- **CHANGE-076:** Made the joint score distribution the coherence parent for score/margin/win outputs.
- **CHANGE-077:** Froze pure-football, market-augmented and benchmark-only lane isolation.
- **CHANGE-078:** Kept OOD/model-disagreement thresholds blank until W17.
- **CHANGE-079:** Bound scenario simulation to immutable PIT snapshots, explicit weights/lineage and reproducible seeds.

- **CHANGE-080:** Removed stale W17 `TASK-040` dependency from W14 `TASK-094`; specialization semantics precede empirical baseline-bar science.


## W17 additions
- **CHANGE-081** — Seal 2024-2025 as governance-protected holdout and 2026+ as forward forecast-first shadow lane Reason: Prevents later test-period cherry-picking while preserving a future operational holdout
- **CHANGE-082** — Explicitly distinguish governance protection from real-world/public outcome knowledge Reason: 2024-2025 outcomes are historical by W17; honest protection is a no-tuning rule, not a claim of blindness
- **CHANGE-083** — Freeze threshold derivation methods now; keep THR-001..007/014/015 numeric values blank until development-only materialized evidence exists Reason: No real trained development evidence exists yet and protected results may not create thresholds
- **CHANGE-084** — Add explicit BLOCKED_PROTOCOL_UNSEALED/BLOCKED_THRESHOLD_UNSET/BLOCKED_ARTIFACT_MISSING states Reason: Missing evidence must fail closed rather than silently waive governance
- **CHANGE-085** — Predeclare metric hierarchy plus national/A&M/context scorecards before protected result review Reason: Prevents metric switching and subgroup fishing
- **CHANGE-086** — Make W17 judging rules immutable inputs to W18; research agents may propose but cannot mutate splits/metrics/threshold methods/promotion rules Reason: Experimenter cannot rewrite its own scoring rules
- **CHANGE-087** — Refresh cumulative navigation to W17 complete / W18 next Reason: Prevent fresh-session wrong-wave execution from stale presentation state

- **CHANGE-088** — Keep MLflow Tracking and Optuna as selected replaceable adapters after current official-doc validation; core remains tool-neutral Reason: Current local SQLite/Journal capabilities fit local-first requirements without server/cloud dependency

- **CHANGE-089** — Hash-seal W17 judging-rule files and verify before execution/adoption Reason: Experimenter cannot rewrite judging rules after seeing results

- **CHANGE-090** — Remove PROMOTE from research queue and require external promotion governor Reason: Prevents self-promotion and protected feedback loops

- **CHANGE-091** — Block expensive neural/sequence/graph execution until materialized baseline evidence and resource rationale exist Reason: Complexity must earn its place; W17 has no trained baseline metrics yet

- **CHANGE-092** — Add explicit TASK-139 -> TASK-041 program-sequence dependency and make TASK-041 READY only after W18 clears Reason: Preserves exact wave sequencing in machine-readable DAG
- **CHANGE-093** — Reconstruct the Codex work-packet queue to cover all 33 canonical epics from the authoritative WBS/DAG Reason: W18 final backlog validation exposed an inherited seven-packet truncation; validation is preserved rather than suppressed

## Corrected W18 additions
- **CHANGE-094** — Reject thin W18 draft and rebuild corrected W18 with full tournament/HPO/replay/worktree subsystems Reason: Audit found master-scope omissions and several 7–20 line core docs
- **CHANGE-095** — Create explicit target-specific feature tournament with eligibility, ablation, stability, cost and replay stages Reason: Master W18 explicitly requires a feature tournament and W10 lifecycle needs a governed research path
- **CHANGE-096** — Create explicit model tournament with mandatory simple baselines, A&M no-adjustment baseline and market-lane isolation Reason: Master W18 explicitly requires a model tournament and complexity must earn its place
- **CHANGE-097** — Version HPO search spaces/studies and enforce development-only objectives, bounded budgets and safe storage Reason: Prevents result-dependent search changes and protected-feedback leakage
- **CHANGE-098** — Add explicit hypothesis lifecycle, experiment deduplication and semantic comparison compatibility Reason: Autonomous research needs falsifiable state/history and incompatible candidates must not be ranked
- **CHANGE-099** — Add artifact manifests, typed replay failures, protected worktree scopes and explicit resource/paid-compute policy Reason: Makes reference execution reproducible and fail-closed
- **CHANGE-100** — Preserve MLflow/Optuna as replaceable adapters and document canonical mapping, local persistence and non-authority boundaries Reason: Current official documentation supports local-first use without making tools governance truth
- **CHANGE-101** — Add machine-readable W18 master-requirement coverage matrix and dedicated tournament/HPO/replay tests Reason: Prevents future scope omissions from being hidden by a passing generic validator

## W18 full-rebuild corrections
- **CHANGE-102** — Audit all W18-owned tasks and close TASK-164 advanced challenger admission. Reason: TASK-164 is owned by W18 and was still PLANNED. Affects REQ-631;REQ-632; ADR-314; future W19-W25.
- **CHANGE-103** — Add transactional local SQLite reference store with integrity checks. Reason: W19/W20 need executable local experiment lineage before real runs. Affects REQ-681;REQ-691; ADR-297;ADR-307; future W19-W23.
- **CHANGE-104** — Add resource admission, owner-wave/seal/lock/paid-compute gates. Reason: Local autonomous research needs enforceable resource boundaries. Affects REQ-682;REQ-684;REQ-685; ADR-298;ADR-300;ADR-301; future W19-W23.
- **CHANGE-105** — Add semantic compatibility and Pareto/multi-metric evidence preservation. Reason: Prevents false rankings across different splits/data/lanes and arbitrary scalarization. Affects REQ-686;REQ-687; ADR-302;ADR-303; future W20-W23.
- **CHANGE-106** — Add artifact class policy, precommitted replay tolerance and store linkage. Reason: Reproducibility requires executable artifact/replay boundaries. Affects REQ-688;REQ-690;REQ-698; ADR-304;ADR-306;ADR-313; future W19-W23.
- **CHANGE-107** — Add local JSONL tracker and explicit MLflow non-authority boundary. Reason: Research governance must survive optional tool absence. Affects REQ-692;REQ-693; ADR-307;ADR-308; future W19-W23.
- **CHANGE-108** — Retain outer/inner search counts and canonical Optuna evidence export. Reason: Improves later interpretation of development selection bias. Affects REQ-694;REQ-695; ADR-309;ADR-310; future W20-W24.
- **CHANGE-109** — Separate operational failure from scientific rejection and query negative history before repeat. Reason: Autonomous agents must not erase/repeat dead ends. Affects REQ-683;REQ-696;REQ-697; ADR-299;ADR-311;ADR-312; future W19-W23.
- **CHANGE-110** — Require 170-test full-rebuild subsystem gate, full requirement→artifact matrix and all W18 owner tasks DONE. Reason: Direct response to repeated underbuilt W18 artifact failure. Affects REQ-699;REQ-700; ADR-315;ADR-316; future W19-W25.

- **CHANGE-111** — W19 converts W07-W10 contracts into a dependency-free content-addressed source→entity→PIT→feature starter with lineage; no future-wave reallocation required.


## CHANGE-W21-001
- **Wave:** W21
- **Original:** Prefect remained the current strong-default orchestration candidate.
- **Revised:** Implement a dependency-free durable local orchestration kernel behind replaceable contracts; keep Prefect optional.
- **Reason:** Current single-machine/local-first requirements do not yet demonstrate enough benefit to justify a mandatory orchestration dependency.
- **Requirements:** REQ-714;REQ-716
- **ADRs:** ADR-326
- **Future impact:** W23 may re-evaluate using operational evidence; W22 consumes immutable published snapshots regardless of backend.


## CHANGE-W22-001
- **Wave:** W22
- **Original:** Source conversation favored FastAPI + Streamlit initially, React later.
- **Revised:** Dependency-free serving core + optional FastAPI adapter + build-free static dashboard on the same API contract.
- **Reason:** Avoid duplicate local app runtimes and hidden UI computation while keeping the product replaceable and local-first.
- **Requirements:** REQ-722;REQ-728
- **ADRs:** ADR-332;ADR-335
- **Future impact:** W23 hardens this boundary; React/Streamlit remain optional future adapters.

## CHANGE-W22-002
- **Wave:** W22
- **Original:** THR-010 freshness SLA remained TBD.
- **Revised:** Keep it TBD, but make the product fail-honest: exact age is always visible and CURRENT is impossible without a configured threshold.
- **Reason:** Meets stale-visibility requirements without inventing an unsupported operational SLA.
- **Requirements:** REQ-724
- **ADRs:** ADR-333
- **Future impact:** W23 may populate THR-010 only from operational evidence.


## CHANGE-W23-001
- **Wave:** W23
- **Revised:** Keep service-light local operations; do not add infrastructure without measured need.
- **ADRs:** ADR-336..339

## CHANGE-W23-002
- **Wave:** W23
- **Revised:** Implement benchmark harness but preserve AC-038/TASK-163 blocker until the actual target hardware runs the representative profile.
- **Reason:** Current execution host is not the declared Windows/Ryzen/32GB/RTX5060 environment.
- **Requirements:** REQ-733;REQ-736
- **ADR:** ADR-340

## CHANGE-W24-001
- **Wave:** W24
- **Original:** W24 could not start until TASK-163 cleared AC-038 on the actual target machine.
- **Revised:** Execute W24 under the user's explicit sequencing instruction from completed TASK-162 while preserving TASK-161/TASK-163/AC-038/THR-011/THR-012 as unresolved.
- **Reason:** Latest explicit user instruction has highest source-of-truth precedence; no-fabricated-evidence rules still apply.
- **Requirements:** REQ-737;REQ-745
- **ADRs:** ADR-341;ADR-346
- **Future impact:** W25 must carry the target-hardware gap if still unresolved.

## CHANGE-W24-002
- **Wave:** W24
- **Original:** Historical-game outputs relied on completion-time eligibility.
- **Revised:** Explicitly reject the target game's own HISTORICAL_GAME_OUTPUT by game identity.
- **Reason:** W24 leakage challenge found a defense-in-depth gap under malformed metadata.
- **Requirements:** REQ-740
- **ADR:** ADR-343

## CHANGE-W24-003
- **Wave:** W24
- **Original:** W06 source descriptions were adequate for SportsDataverse/Open-Meteo implementation.
- **Revised:** Add explicit cfbfastR raw→derived provenance and precise weather access/ensemble-history semantics.
- **Reason:** Current source-owner documentation materially clarifies these contracts.
- **Requirements:** REQ-741;REQ-742;REQ-743
- **ADRs:** ADR-344;ADR-345

## W25 final changes
- **CHANGE-120:** W25 is terminal; no Wave 26. Optional advanced/live work moves to the implementation/research backlog.
- **CHANGE-121:** Final handoff freezes an explicit maturity/known-gap taxonomy so packaging cannot be mistaken for production-model validation.
