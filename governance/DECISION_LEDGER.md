# Decision Ledger

Generated: 2026-08-08T14:25:01+00:00

Wave 01 records current accepted architectural/governance decisions without pretending later-wave implementation has occurred.

## ADR-001 — National foundation + A&M specialization
- **Status:** ACCEPTED
- **Constraint class:** A/B boundary
- **Decision:** Broad national learning with disproportionate A&M specialization; exact statistical decomposition remains revisable.
- **Evidence basis:** source logs 001/013/015; master §17
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-002 — Scientific BAS headline definition
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** BAS headline is P(A&M performs ≥7 points worse than strictly valid pregame expected margin), with ≥3/14/21 severity support.
- **Evidence basis:** source logs 006/010/011; master §18
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-003 — SportsDataverse + CFBD public foundation
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Use SportsDataverse as primary historical/PBP foundation and CFBD as primary supplemental source, subject to Wave06 current research.
- **Evidence basis:** source logs 007; recon source priority
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-004 — PFF deferred and non-blocking
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** PFF is optional future enrichment only; core plan operates without it.
- **Evidence basis:** source log 007; recon; master §42
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-005 — Point-in-time known-at architecture
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Every historical prediction is reconstructed from observations eligible before prediction timestamp.
- **Evidence basis:** source logs 001/009/012; recon; master §27
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-006 — Immutable raw + dated observations
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Raw evidence is immutable and mutable state is represented as effective-dated observations/snapshots.
- **Evidence basis:** recon canonical rules; master §28
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-007 — Canonical IDs separate from source IDs
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Internal canonical entities are stable; source IDs/aliases remain mapped evidence.
- **Evidence basis:** source log 005; recon canonical rules
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-008 — Empirical feature lifecycle
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** LLM/domain intuition may propose; PIT walk-forward experiments, ablation and stability decide production feature status.
- **Evidence basis:** source logs 009/012; master §26
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-009 — FBS/FCS/lower-division hierarchy
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** FBS full, FCS meaningful secondary, lower divisions increasingly coarse priors with uncertainty.
- **Evidence basis:** source log 014; master §17
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-010 — Separate national history from current-team evidence
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Old games teach general football; direct current-team state is driven by current roster/regime/continuity/recent evidence.
- **Evidence basis:** source log 013; master W11
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-011 — Player/replacement availability architecture
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Injury impact depends on player value, replacement, usage, availability/effectiveness, matchup and uncertainty.
- **Evidence basis:** source log 010; recon v1.1; master §33
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-012 — Role-conditioned hierarchical coaching
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Coach careers use effective-dated role episodes and residual/partial-pooled effects; no static generic coach rating.
- **Evidence basis:** source logs 003/004; recon v1.1; master §32
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-013 — Resources as conditional upstream capacity
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Resources inform priors/expectation and BAS efficiency; avoid direct dollar bonus/double counting and preserve public/private asymmetry.
- **Evidence basis:** source log 016; recon
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-014 — Pure-football + market-augmented lanes
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Keep market-free forecast separate from timestamp-safe market-augmented forecast.
- **Evidence basis:** source log 001; master §38
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-015 — Canonical game as split unit
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** All representations of a game remain in same train/validation/test fold.
- **Evidence basis:** recon v1.2; master §41
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-016 — Joint-score coherence requirement
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Win, score, margin, spread-cover and BAS residual distributions must be mathematically coherent.
- **Evidence basis:** source log 011; recon v1.2; master §39
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-017 — Governed autonomous research
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Research agents may propose/run approved experiments but cannot alter judging rules or directly promote themselves.
- **Evidence basis:** source log 017; master §56
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-018 — Local-first compute
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Phases 1–4 target local Ryzen/32GB/RTX5060; remote GPU optional later.
- **Evidence basis:** source logs 018/019; master §44
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-019 — Five-phase framework
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Foundation → advanced football intelligence → A&M specialization → production/autonomy → advanced research, refinable if dependencies justify.
- **Evidence basis:** source log 019; master §48
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-020 — No large raw data in repo packs
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Repository holds acquisition code/contracts/tiny fixtures/manifests/docs, not full raw lake/model binaries.
- **Evidence basis:** master §§43,49
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-021 — Adaptive 25-wave plan
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Wave missions are minimum centers of gravity; later scopes may be revised while retaining exactly 25 waves.
- **Evidence basis:** master §§2-7
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-022 — Numerical source-log chronology
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Wave 01 reads chat logs by numeric filename sequence 001→020, not ZIP member order.
- **Evidence basis:** W01 input-integrity hardening
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-023 — Content-based reconnaissance identity
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Internal pack edition/required structure/hashes define identity; host copy suffixes do not invalidate the artifact.
- **Evidence basis:** W01 input-integrity hardening
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-024 — Authoritative recon integrity manifest
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Use final/manifests/FINAL_FILE_MANIFEST.csv + FINAL_FILE_HASHES.sha256 as authoritative; root PACK_MANIFEST self-entry mismatch is documented non-blocking self-reference artifact.
- **Evidence basis:** W01 validation
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-025 — Deterministic services for deterministic work
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Prefer normal Python services for deterministic ingestion/validation/state jobs; use LLMs where language/research reasoning adds value.
- **Evidence basis:** source log 017
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-026 — No unverified pretrained-model dependency
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Train/evaluate our own models; external public models may be benchmarks/reference only when currently verified.
- **Evidence basis:** source logs 002→007 supersession
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-027 — Learned home-field effect
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Estimate partial-pooled residual home/venue effects; no hard-coded Kyle Field bonus.
- **Evidence basis:** recon v1.1; master §34
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-028 — Learned transfer translation
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** No fixed conference transfer penalty; learn destination translation from historical cohorts/context.
- **Evidence basis:** recon v1.1; master §29
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-029 — Effective-dated rule-era registry
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Version material NCAA rule changes and affected feature definitions; season alone is insufficient when explicit versioning is needed.
- **Evidence basis:** recon v1.2; master §37
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

## ADR-030 — Immutable market/prediction snapshots
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Preserve market and prediction observations at each forecast timestamp; never overwrite earlier state.
- **Evidence basis:** recon v1.2; master §§38,58
- **Revisability:** Baseline decision; Level-B portions remain revisable through evidence-backed ADR.

# Wave 02 decisions

## ADR-031 — Minimal src-layout until Wave03
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Use an installable src/aggie_analytics package scaffold but do not create speculative future domain/service packages before Wave03 architecture comparison.
- **Evidence basis:** W02 adaptive review; master W02/W03
- **Revisability/notes:** Operational structure accepted; domain boundaries remain explicitly open.

## ADR-032 — Python 3.12 preferred local baseline
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Prefer CPython 3.12 locally while allowing 3.11-3.13 in starter metadata until actual ML/data dependency compatibility is measured.
- **Evidence basis:** Local-first compatibility and simplicity
- **Revisability/notes:** Revisit when production dependency stack is selected.

## ADR-033 — Portable venv/pip baseline
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Python venv plus pip is the required portable bootstrap; optional faster environment managers may accelerate but are not mandatory.
- **Evidence basis:** No-cargo-cult/local portability rule
- **Revisability/notes:** Revisable if measured workflow benefit justifies another required manager.

## ADR-034 — Standard-library deterministic pack tooling
- **Status:** ACCEPTED
- **Constraint class:** A/B boundary
- **Decision:** Wave pack verification, manifesting, safe ZIP handling and packaging use Python standard library and normalized ZIP metadata.
- **Evidence basis:** W01 manifest issue; cumulative integrity requirements
- **Revisability/notes:** Core safety behavior is protected; implementation may evolve.

## ADR-035 — Machine-readable hydration allowlist
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Hydration content is generated from configs/hydration_manifest.json plus generated HYDRATE_FIRST/PACK_BINDING/hash evidence.
- **Evidence basis:** Master hydration rule; anti-drift
- **Revisability/notes:** Do not silently expand hydration with full repo.

## ADR-036 — Minimal cross-platform CI now; full CI Wave23
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Create Windows/Linux Python 3.12 repository-integrity CI now; defer complete security/dependency/deployment/observability CI to Wave23.
- **Evidence basis:** Master W02/W23; simplicity rule
- **Revisability/notes:** Expand earlier only if dependencies require it.

## ADR-037 — Codex worktree contract without guessed external config
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Use repository-local task/worktree contracts and codex/<epic>-<task>; do not commit unverified external Codex config schemas.
- **Evidence basis:** Master §50; evidence-backed change rule
- **Revisability/notes:** Tool config may be added after schema verification.

## ADR-038 — No Docker/database/orchestrator commitment in W02
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Do not add Docker, database services or orchestration frameworks solely for repository setup; evaluate them in their architecture/operations waves.
- **Evidence basis:** Master no-cargo-cult rule; W02 adaptive review
- **Revisability/notes:** This is a deferral, not a permanent rejection.

## ADR-039 — Safe prior-wave verification before extraction
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Verify binding hash/next-wave and reject unsafe archive members before extraction; future sessions should use executable verification tooling.
- **Evidence basis:** Master §65; pack security hardening
- **Revisability/notes:** Protected pack-integrity behavior.



# Wave 03 decisions

## ADR-040 — Offline-first modular monolith
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Use one modular local application/repository as the default Phases 1-4 deployment; split services only on demonstrated operational need.
- **Evidence basis:** W03 alternative comparison; local hardware; simplicity rule
- **Revisability/notes:** Revisable if independent scaling/security/latency evidence appears.

## ADR-041 — Immutable snapshot serving
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Pregame API/dashboard serves immutable forecast snapshots rather than synchronous online feature construction/model execution.
- **Evidence basis:** Prediction snapshot principle; reproducibility; local-first
- **Revisability/notes:** W22 may choose UI/API technology without changing snapshot boundary.

## ADR-042 — Parquet plus DuckDB early analytical stack
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Prefer native immutable raw files, partitioned Parquet analytical zones and DuckDB local querying for early phases.
- **Evidence basis:** Master storage defaults; local hardware; W03 comparison
- **Revisability/notes:** Physical implementation remains evidence-revisable.

## ADR-043 — PostgreSQL deferred behind storage port
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Do not make PostgreSQL mandatory now; W07/W22/W23 may adopt a relational adapter if transactional/concurrent workflows justify it.
- **Evidence basis:** W03 storage comparison; no-cargo-cult rule
- **Revisability/notes:** Supersedes any implication that PostgreSQL is mandatory from initial defaults.

## ADR-044 — Provider ports and canonical boundary
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Keep source-provider acquisition/parsing behind adapters; provider schemas do not directly define football/model interfaces.
- **Evidence basis:** Recon canonical source rules; W03 boundaries
- **Revisability/notes:** Source adapters remain replaceable after Wave06 source research.

## ADR-045 — PIT state as hard feature gateway
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** All historical/inference features obtain mutable observations through explicit as-of/PIT state contracts.
- **Evidence basis:** PIT invariant; recon temporal rules
- **Revisability/notes:** W08 owns detailed implementation, not whether the gateway exists.

## ADR-046 — Explicit national-to-A&M specialization contract
- **Status:** ACCEPTED
- **Constraint class:** A/B boundary
- **Decision:** National foundation and A&M high-resolution specialization communicate through an explicit representation/adjustment contract; A&M cannot fork canonical truth.
- **Evidence basis:** Protected national+A&M objective; recon source precedence
- **Revisability/notes:** W14/W16 select residual/multitask/MoE implementation.

## ADR-047 — Forecast assembly owns cross-target coherence
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Use a forecast-distribution assembly boundary to keep score, margin, win and BAS-related outputs coherent.
- **Evidence basis:** Joint-score invariant; master target architecture
- **Revisability/notes:** W16 selects statistical family.

## ADR-048 — Research plane isolated from protected production
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Research can produce candidates/proposals but enters production only through protected evaluation/promotion gates.
- **Evidence basis:** Research-agent governance
- **Revisability/notes:** No research component is a required import of production forecast runtime.

## ADR-049 — LLM assistive plane only
- **Status:** ACCEPTED
- **Constraint class:** A/B boundary
- **Decision:** LLMs may assist evidence extraction/research/explanations but are not required for deterministic core forecast refresh and cannot decide PIT/promotion rules.
- **Evidence basis:** Source logs; deterministic-service principle
- **Revisability/notes:** Future LLM use must preserve evidence/provenance and deterministic validation.

## ADR-050 — Read-serving boundary cannot query raw/model internals
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Serving surfaces consume immutable forecast snapshots and lineage, not raw provider/PIT/feature/model internals.
- **Evidence basis:** Reproducibility and snapshot architecture
- **Revisability/notes:** W22 implementation must honor this boundary.

## ADR-051 — Future live plane isolated
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Future in-game modeling is a separate chronological lane and cannot feed same-game pregame features.
- **Evidence basis:** Live modeling invariant
- **Revisability/notes:** Phase5 may reuse pregame priors through an explicit one-way interface.

## ADR-052 — Stable semantic namespaces without empty implementation sprawl
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Define future core/data/features/models/forecasting/tamu/evaluation/research/serving namespace ownership but instantiate only architecture contracts in W03.
- **Evidence basis:** W02 anti-premature-freezing decision; W03 package review
- **Revisability/notes:** ADR-031 is refined: logical boundaries are now accepted, implementation packages remain created by owning waves.

## ADR-053 — No distributed infrastructure requirement for pregame v1
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Do not require Kafka, Redis, Kubernetes, online feature stores or microservices for the current pregame architecture.
- **Evidence basis:** No-cargo-cult; snapshot serving; local-first
- **Revisability/notes:** These are not permanently banned; later evidence may justify them.

## ADR-054 — Machine-readable architecture registry
- **Status:** ACCEPTED
- **Constraint class:** A/B boundary
- **Decision:** Maintain component/interface/data-zone/dependency rules in configs/architecture_registry.json and validate them in tests.
- **Evidence basis:** W03 adaptive review; anti-drift
- **Revisability/notes:** Registry captures logical architecture, not all later domain schemas.

## Wave 04 decisions

- **ADR-055:** Requirement constraint class, lifecycle state and acceptance evidence state are separate dimensions.
- **ADR-056:** Acceptance controls and REQ/ADR/RISK mappings are machine-readable and validated.
- **ADR-057:** Quantitative thresholds remain blank/TBD until the evidence-owning wave can justify them.
- **ADR-058:** PIT/leakage/split/BAS temporal failures fail closed and block affected release/promotion.
- **ADR-059:** Protected test periods and promotion criteria are sealed before protected-result inspection.
- **ADR-060:** Acceptance evidence may be static, test, replay, science, benchmark or manual review.
- **ADR-061:** External/source/LLM-derived inputs cross an explicit trust boundary and source content is never executed.
- **ADR-062:** Forecast reproducibility is defined by immutable lineage/replay evidence rather than current-state reruns.
- **ADR-063:** Runtime/RAM/storage budgets are benchmark-derived on target hardware, not invented in W04.
- **ADR-064:** Every REQ, ADR and RISK maps to acceptance controls.


# Wave 05 decisions

## ADR-065 — Capability phases are organizational, waves remain execution authority
- **Status:** ACCEPTED
- **Decision:** Use five capability phases to organize work while the exactly-25-wave program remains the execution/control sequence.
- **Evidence:** master W05 + REQ-001/REQ-234

## ADR-066 — Stable epic/task IDs and machine-readable WBS
- **Status:** ACCEPTED
- **Decision:** Use stable EPIC/TASK IDs in CSV/JSON as the canonical implementation backlog.
- **Evidence:** W05 planning need

## ADR-067 — DAG/gates instead of fabricated calendar schedule
- **Status:** ACCEPTED
- **Decision:** Represent implementation order using dependencies/readiness gates; do not invent hour/date estimates.
- **Evidence:** master W05

## ADR-068 — Critical path means dependency-critical spine
- **Status:** ACCEPTED
- **Decision:** Critical path is a dependency/gating spine, not a duration-optimized CPM calculation without task durations.
- **Evidence:** REQ-221/236

## ADR-069 — Five complexity classes describe coupling and risk
- **Status:** ACCEPTED
- **Decision:** C1-C5 classify scope/coupling/uncertainty/protected-contract risk, not elapsed time.
- **Evidence:** W05 adaptive review

## ADR-070 — Mandatory W06 implementation replan gate
- **Status:** ACCEPTED
- **Decision:** W06 source research must explicitly revalidate source-dependent future tasks before they become ready.
- **Evidence:** master W05/W06

## ADR-071 — Source-dependent tasks provisional until W06
- **Status:** ACCEPTED
- **Decision:** Mark W07+ source/schema-dependent tasks PLANNED_REVALIDATE_AFTER_W06.
- **Evidence:** master W05/W06

## ADR-072 — Codex packets are bounded implementation slices
- **Status:** ACCEPTED
- **Decision:** Use work packets spanning coherent task slices with outputs/tests/acceptance/stop conditions; avoid micro-handoff prompt fragmentation.
- **Evidence:** master W05 + W02 worktree contract

## ADR-073 — Serialize unfrozen shared-contract mutations
- **Status:** ACCEPTED
- **Decision:** Only one workstream mutates an unfrozen shared contract at a time; parallelism targets independent modules or stable interfaces.
- **Evidence:** architecture integrity

## ADR-074 — Bounded adaptive parallelism over fixed concurrency
- **Status:** ACCEPTED
- **Decision:** Run as many independent worktrees as dependencies/local resources allow; do not hard-code a concurrency count that ignores current constraints.
- **Evidence:** local-first constraint

## ADR-075 — Evidence gate required before DONE/integration
- **Status:** ACCEPTED
- **Decision:** Task completion requires required test/evidence controls, not code presence alone.
- **Evidence:** W04 acceptance architecture

## ADR-076 — W05 backlog is revisable evidence-controlled plan
- **Status:** ACCEPTED
- **Decision:** Treat W05 ordering/task details as a strong implementation baseline that can change through W06/later evidence-backed revisions without losing IDs/history.
- **Evidence:** adaptive mandate

## W06 decisions
- ADR-077..088 accepted from fresh data-universe research.
- Recent official conference/CFP availability reports become primary evidence when policy-covered.
- Historical forecast weather uses issued model runs.
- Lower-division official stats strengthen bounded priors.
- Regulatory environment expands beyond playing rules.
- Commercial advanced feeds stay optional/nonblocking.
- W03 modular-monolith architecture is retained.

## W07 canonical identity decisions

### ADR-089 — Opaque prefixed UUID surrogate is current canonical-ID representation default
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Use type-prefixed UUID4 hex as the dependency-free representation default for surrogate canonical IDs; the protected invariants are opacity/stability/no source coupling and the representation may change before real IDs are materialized.
- **Evidence:** W07 entity design

### ADR-090 — Source mappings are first-class append-only decision records
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Represent source-system/type/key to canonical mappings as auditable records with evidence, method, state and supersession rather than overwriting a lookup table in place.
- **Evidence:** Recon canonical rules; W07

### ADR-091 — Direct source IDs are mapping evidence only after contract validation
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** A provider ID may support deterministic mapping only after its semantics/uniqueness/scope are validated; canonical IDs never become aliases for unverified source IDs.
- **Evidence:** Recon join contracts

### ADR-092 — Fuzzy/name matching is candidate generation, not canonical truth
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Disable fuzzy auto-accept in W07; only verified existing/direct/crosswalk mapping classes auto-accept, while ambiguous candidates enter review.
- **Evidence:** REQ-266/278; THR-008

### ADR-093 — Human identity is separated from roles, teams and mutable attributes
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Player transfers and coach role/team changes are episodes/observations linked to stable human identity.
- **Evidence:** Recon canonical registry/roster identity policy

### ADR-094 — Identity corrections use merge/split/supersession history
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Never destructively delete/reuse assigned canonical identities; corrections preserve old decisions/data versions and add redirects or split mappings.
- **Evidence:** W07 correction design

### ADR-095 — Game identity represents the underlying contest, not current schedule fields
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Retain game identity through supported reschedule/venue/status changes; create a new identity for replacement matchups; annotate forfeit/vacated results without changing identity.
- **Evidence:** Master game edge cases; recon join contracts

### ADR-096 — Mutable source evidence uses layered identity
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Separate source system, resource, publication version, raw capture and parsed source observation so edited reports/pages and retrieval events remain reconstructible.
- **Evidence:** ADR-086; W06 research

### ADR-097 — PostgreSQL remains deferred for canonical identity workflow
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Current single-writer append-only mapping/decision workflow does not justify a relational server; retain Parquet/DuckDB default behind storage ports and reopen on real concurrent transactional need.
- **Evidence:** W03 ADR-043; W07 workload evaluation

### ADR-098 — Review queue is a derived view over immutable candidate/decision events
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Do not require a mutable queue table; derive current unresolved/review state from append-only candidates and latest non-superseded decisions.
- **Evidence:** W07 resolution/storage evaluation

### ADR-099 — No graph database is required for canonical relationships
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Represent identity relationships/episodes as normalized tables/contracts; adopt graph infrastructure only if a later measured workload justifies it.
- **Evidence:** No-cargo-cult rule; W07

### ADR-100 — W07 identity contracts are frozen for W08 but implementation benchmark remains W19
- **Status:** ACCEPTED
- **Constraint class:** A/B boundary
- **Decision:** W08 may rely on canonical identity/evidence layers; W19 still owns materialized resolver/storage throughput benchmarks and any labeled fuzzy auto-accept threshold.
- **Evidence:** W07 gate

## W08 decisions
- **ADR-101 — Bitemporal knowledge and validity axes:** Represent public knowability separately from real-world validity/effectivity; both participate in PIT selection.
- **ADR-102 — first_known evidence policy:** Use defensible first-known evidence; retrieval is conservative fallback when earlier public availability cannot be proven.
- **ADR-103 — prediction_eligible_at is derived metadata:** Treat prediction_eligible_at as policy-versioned derived/cache metadata, never a raw source truth or sufficient sole predicate.
- **ADR-104 — Deterministic fail-closed as-of selector:** As-of selection applies domain ban, knowledge cutoff, target validity, revision state and deterministic precedence; ambiguity fails closed.
- **ADR-105 — Revision replay uses as-known version:** Later source corrections/reports do not rewrite historical snapshots; select versions known at the cutoff.
- **ADR-106 — Immutable cutoff object:** Forecast/training/replay cutoffs are immutable versioned lineage records including target, lane, policy and data snapshot.
- **ADR-107 — Issued weather run contract:** Weather pregame evidence requires exact model initialization/availability/valid-time lineage; realized weather cannot substitute.
- **ADR-108 — Availability policy/version contract:** Official availability is versioned and policy/game scoped; noncoverage means UNKNOWN and later versions affect later cutoffs only.
- **ADR-109 — Market labels are descriptive not temporal authority:** Opening/current/closing labels never override provider observation knowability; pure and market lanes remain separate.
- **ADR-110 — Regulatory/resource dual-time contract:** Regulatory effective intervals and resource reporting periods are separate from publication/first-known time.
- **ADR-111 — Retrospective evidence fail-closed:** Retrospective/current pages require dated corroboration before historical PIT use.
- **ADR-112 — Completed-game chronology for historical aggregates:** Current/future-game outputs are banned; prior outputs require game completion and source knowability before cutoff.
- **ADR-113 — PIT gateway becomes protected feature boundary:** CMP-006 feature construction may consume temporal state only through CMP-005 PIT gateway contracts.
- **ADR-114 — Synthetic PIT PASS is not production data proof:** Synthetic leakage tests validate contract behavior but real historical materialization/replay remains later evidence.

## Wave 09 decisions
- **ADR-115** — Raw-field registry is metadata not production feature lifecycle
- **ADR-116** — Stable source-scoped raw-field IDs
- **ADR-117** — Recon temporal classification has precedence over scanner heuristics
- **ADR-118** — Unmaterialized W06 endpoint schemas remain pending
- **ADR-119** — Sample missingness remains non-population evidence
- **ADR-120** — Exact-name overlap creates review clusters only
- **ADR-121** — Join paths require canonical identity semantics
- **ADR-122** — Schema scanner separates documented and observed type
- **ADR-123** — Standard-library scanner core with optional Parquet plugin
- **ADR-124** — Nested JSON uses deterministic dotted paths
- **ADR-125** — W09 W10-candidate handoff remains behind W08 PIT gateway
- **ADR-126** — W09 feature-registry gate frozen for W10


## Wave 11 decisions

### ADR-139 — Separate prior/underlying/available/form state
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Team state explicitly separates prior, underlying, available strength and current-form evidence.
- **Evidence:** Source chat distinction; W11 state contract

### ADR-140 — Team state is immutable PIT snapshot
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Team-state snapshots are cutoff/version bound and consume only W08-eligible evidence.
- **Evidence:** W08 PIT architecture

### ADR-141 — Composite Week-1 prior with no frozen component weights
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Register multiple prior components but leave their weights empirical.
- **Evidence:** Source chat early-season prior; resource strategy

### ADR-142 — Early-season blend schedule remains empirical
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Compare prior/observed blend candidates chronologically; do not hard-code week-specific weights.
- **Evidence:** No fabricated parameter rule

### ADR-143 — National training utility differs from current-team relevance
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Old games may remain nationally useful while being heavily downweighted for present-team identity/state.
- **Evidence:** Source chat historical weighting

### ADR-144 — Recency/regime/change-point representations remain candidates
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Freeze candidate families and interfaces, not a winning formula or decay parameter.
- **Evidence:** W10 empirical lifecycle philosophy

### ADR-145 — Change points shrink/inflate uncertainty before hard reset
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Do not automatically discard history after staff/QB/scheme/performance change; reset only if later evidence supports it.
- **Evidence:** Robustness/reproducibility

### ADR-146 — Bounded FBS/FCS/lower-division hierarchy
- **Status:** ACCEPTED
- **Constraint class:** A/B boundary
- **Decision:** FBS full, FCS strong secondary, then progressively coarser lower-division priors.
- **Evidence:** Master architecture; W06 source research

### ADR-147 — Cross-division translation is data-driven with uncertainty
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** No fixed FCS/D-II/D-III penalty; translation functions/priors require empirical cross-level evidence.
- **Evidence:** Source chat lower-division design

### ADR-148 — Resources are upstream prior candidates
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Evaluate reliable resource variables mainly as program/preseason priors, not weekly points bonuses.
- **Evidence:** Recon program resource strategy

### ADR-149 — W12 owns detailed available-strength player adjustment
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** W11 freezes the available-strength port but leaves player availability/effectiveness/usage/replacement mechanics to W12.
- **Evidence:** Wave ownership

### ADR-150 — Team-state subsystem stays inside modular monolith
- **Status:** ACCEPTED
- **Constraint class:** B
- **Decision:** Add a logical Python team_state package/contract; no new deployable service/database is justified.
- **Evidence:** W03 modular-monolith architecture

### ADR-151 — W11 gate freezes semantics, not empirical parameterization
- **Status:** ACCEPTED
- **Constraint class:** A
- **Decision:** Downstream waves may rely on interfaces; real winner/parameter selection remains W17/W19 evidence.
- **Evidence:** Honest completion/no fabricated metrics


## Wave 12 decisions
- **ADR-152 — Separate roster, depth, availability and participation state:** Treat these as distinct effective-dated observations, never one mutable player status.
- **ADR-153 — Position-aware player value without manual point assignments:** Register position-specific evidence interfaces; freeze no player/position point values.
- **ADR-154 — Availability uses probability, effectiveness and expected usage scenarios:** Model multiple availability/limitation scenarios instead of only active/out.
- **ADR-155 — Replacement effect is identity/value/usage specific:** Represent replacement candidate(s), redistributed usage and uncertainty; no fixed position penalty.
- **ADR-156 — Sparse availability evidence remains uncertain:** Noncoverage/missing evidence is UNKNOWN; confidence/freshness/version remain explicit.
- **ADR-157 — Rotation is first-class player state:** Support expected snap/opportunity distributions across multiple players, not starter-only depth.
- **ADR-158 — Transfer preserves canonical player identity:** Transfers create effective-dated membership/role episodes under one W07 player ID.
- **ADR-159 — Transfer translation is learned from continuous context:** Use same-player/position-aware historical design and continuous competition strength; forbid fixed conference penalties.
- **ADR-160 — Freshmen/prospects use separate priors:** Zero-college-production players use prospect/recruiting/development priors with wide uncertainty.
- **ADR-161 — Preseason honors are external-consensus candidates:** Preserve timestamped selector/honor evidence; freeze no manual honor bonus.
- **ADR-162 — Draft outcomes are lagged evidence/training targets only:** Ban eventual draft outcomes as earlier roster features; permit prior completed development evidence and leakage-safe training targets.
- **ADR-163 — Official conference availability is primary when policy covers:** Prioritize versioned official reports; A&M prioritizes SEC; noncoverage never means healthy.
- **ADR-164 — W12 source-registry provenance catch-up completes TASK-197:** Augment dataset registry with W06 owner/access/auth/license/redistribution fields before transfer/recruiting audit.
- **ADR-165 — Transfer/recruiting source use remains terms/provenance governed:** Snapshot provenance/terms context; public visibility does not imply redistribution permission.
- **ADR-166 — W12 available-strength handoff remains uncalibrated abstract value units:** Freeze structured player/availability/replacement inputs without converting gaps to game points.
- **ADR-167 — W12 gate freezes contracts, not empirical winners:** No production player-value, availability-impact, transfer translation or honor/draft weighting is selected in W12.


## Wave 13 decisions
- **ADR-168 — Coach jobs as effective-dated role episodes:** Store role/responsibility episodes; do not use one static coach rating.
- **ADR-169 — Coach effects use residuals with hierarchical confound controls:** Prefer role-conditioned performance-versus-expectation candidates with shrinkage.
- **ADR-170 — Promotions retain evidence without additive double counting:** Prior role evidence becomes context/prior; new role accumulates separate evidence.
- **ADR-171 — Scheme and play-caller state are effective-dated:** Separate official title, unit responsibility, scheme and play-caller evidence over time.
- **ADR-172 — Fourth-down/clock/halftime effects remain experimental:** Design candidates with context controls; no production effect selected W13.
- **ADR-173 — Issued forecast runs are the pregame weather lane:** Observed/reanalysis weather remains retrospective/evaluation evidence.
- **ADR-174 — Travel is differential, cumulative and DST-aware:** Use IANA/date-aware timezone context and prior travel/rest features.
- **ADR-175 — Four resource lanes R0/R1/R2/R3:** No-resource control, universal, public-enriched and latent-capacity research lanes.
- **ADR-176 — Home field is hierarchical residual, not raw home record:** National→program→venue→era candidates with partial pooling.
- **ADR-177 — Game stakes remain factual PIT context:** No narrative motivation bonus; only sourced known-at context.
- **ADR-178 — Rule era expands to regulatory environment:** Version playing, roster, eligibility, transfer and related regulatory semantics.
- **ADR-179 — Possession opportunity separated from scoring efficiency:** Expected possessions/tempo is a separate subsystem/input.
- **ADR-180 — Field-position and special-teams component accounting:** Preserve components and explicit double-count guards.
- **ADR-181 — Score-state/garbage-time policies remain challengers:** Compare no-filter, competitive-filter, leverage-weight and stratified candidates later.
- **ADR-182 — Opponent adjustment and style similarity require strict-prior evidence:** Avoid circularity and future opponent results.
- **ADR-183 — Schedule stress uses completed prior workload plus known current trip:** No future performance leakage in schedule context.
- **ADR-184 — Officiating remains experimental and fails closed:** Crew-specific feature unavailable without pregame-public assignment; no bias narratives.
- **ADR-185 — W13 is contract/reference maturity only:** No empirical coach/home/resource/mechanics/officiating winner or numeric bonus is claimed.
- **ADR-186 — Repair W14 dependency inversion:** TASK-088 depends on frozen W12/W13 contracts, not future W20 TASK-087 implementation gate.
## W14 decisions
- ADR-187–ADR-194 freeze the A&M overlay/evidence/snapshot/peer/analog and semantic specialization interfaces.
- ADR-195 makes the unchanged national forecast a mandatory no-adjustment baseline.
- ADR-196–ADR-198 preserve residual, hierarchical/multi-task and partial-pooling specialization as challengers rather than winners.
- ADR-199–ADR-202 protect shrinkage, dual scorecards, market/BAS/narrative isolation and honest W14 maturity.

## W15 scientific BAS decisions
- ADR-203..220 freeze the BAS residual/severity sign convention, chronological OOS expectation provenance, BAS-independent primary anchor, general-FBS reference, null-first Aggie Excess posture, peer/regime precommitment, candidate component boundaries and W17 stability/calibration ownership.
- `THR-006` remains blank; no BAS effect, component or calibration result is promoted in W15.
- TASK-101/TASK-116 no longer depend on future W17 TASK-040; this repairs numbered-wave execution while preserving W17 empirical authority.


## W16 decisions
ADR-221 through ADR-240 freeze coherent forecast output derivation, overtime handling, mandatory baselines, model-candidate neutrality, pure/market lane separation, scenario lineage, uncertainty/OOD governance, A&M no-adjustment preservation and W17 protocol sequencing. No empirical model winner is recorded.


## W17 protected validation and promotion decisions
- **ADR-241 — Freeze 2024-2025 as governance-protected holdout:** Protected primary holdout is seasons 2024-2025; development/tuning cannot use them.
- **ADR-242 — Add 2026+ forward operational shadow holdout:** 2026+ forecasts are committed immutably before outcomes and scored as forward shadow evidence.
- **ADR-243 — Canonical game is W17 split and pairing unit:** All mirrored/oriented representations and derived targets of one canonical game stay together.
- **ADR-244 — Use chronological development and 2023 selection lane:** Development history ends 2022; 2023 is final development selection/calibration lane before protected holdout.
- **ADR-245 — Protected holdout movement is fail-closed:** Poor results cannot move the holdout; coverage problems yield UNEVALUABLE or pre-result ADR change.
- **ADR-246 — Brier primary and log loss required for win probabilities:** Use Brier as primary win-probability proper score and log loss as required secondary score.
- **ADR-247 — Use MAE primary point error and proper distribution scores:** Margin/score point errors use MAE primary with RMSE diagnostic; distributions require proper scores.
- **ADR-248 — ECE is diagnostic not sole calibration gate:** Calibration intercept/slope/reliability are required; ECE alone cannot approve a model.
- **ADR-249 — Predeclare national A&M and diagnostic scorecards:** National and A&M scorecards plus key subgroups are frozen before protected result review.
- **ADR-250 — Compare challengers with paired canonical-game deltas:** Candidate-baseline comparisons preserve game pairing and season/game dependence.
- **ADR-251 — Freeze threshold methods without fabricating numeric values:** THR-001..007/014/015 derivation methods are frozen; numeric values stay blank until development-only evidence exists.
- **ADR-252 — Unset required thresholds block promotion:** Blank required thresholds yield BLOCKED_THRESHOLD_UNSET, never zero/waiver.
- **ADR-253 — Retain mandatory simple baseline bar:** Every challenger must beat/meet precommitted rules against simple reproducible baselines.
- **ADR-254 — BAS evaluation is null-first and multiplicity-aware:** Aggie Excess/components retain no-effect/reject/inconclusive outcomes with predeclared stability/multiplicity rules.
- **ADR-255 — A&M specialization must beat no-adjustment baseline:** A&M specialization cannot be promoted without protected incremental value against W14 no-adjustment and visible national scorecard.
- **ADR-256 — OOD/disagreement remain warning-quality candidates:** OOD/disagreement are evaluated for error/undercoverage association, not directional team strength.
- **ADR-257 — Market lanes use identical PIT evaluation cutoffs:** Pure football, market-augmented and benchmark lanes are compared under matched forecast-time rules.
- **ADR-258 — Champion/challenger gate is immutable and fail-closed:** Promotion requires sealed protocol, artifacts, thresholds and immutable evidence record.
- **ADR-259 — Reframe W17 threshold task as methodology freeze:** TASK-131 freezes threshold derivation/precommitment; numeric values require later materialized development evidence.
- **ADR-260 — Freeze W17 contract-only gate and W18 handoff:** W17 completes protected validation/promotion protocols only; TASK-134 is first READY W18 task.

## W18 experimentation and autonomous-research decisions
- **ADR-261–ADR-278** freeze deterministic experiment identity, W17 judging-rule hash seal, MLflow/Optuna replaceable adapter choices, tool-neutral reference lineage, append-only role-governed queues, isolated worktrees, development-only HPO, replay-before-adoption, negative-result retention, no self-promotion, advanced-challenger baseline gating, explicit paid-compute approval and W19 handoff.
- The research queue has no `PROMOTE` state. Production champion changes remain exclusively governed by the W17 promotion interface.
- No empirical experiment/model/feature/HPO/advanced-challenger winner is recorded in W18.

## Corrected W18 decisions

### ADR-279 — Feature tournament is explicit subsystem
- **Decision:** Implement target-specific feature tournament with eligibility, ablation, stability, cost, replay and research-decision stages.
- **Evidence:** Master W18 feature tournament requirement

### ADR-280 — Feature tournament cannot directly promote
- **Decision:** Tournament can retain/reject/adopt challenger but cannot set CORE/SUPPORTED/PROMOTE.
- **Evidence:** W10 lifecycle + W17 promotion boundary

### ADR-281 — Model tournament requires simple comparator ladder
- **Decision:** Every model tournament retains strong simple baselines and coherent comparison semantics.
- **Evidence:** Master W18 model tournament + simplicity rule

### ADR-282 — A&M tournament requires TAMU-SP-00
- **Decision:** No-adjustment A&M baseline is mandatory in A&M specialization tournament.
- **Evidence:** W14 protected fallback

### ADR-283 — Market tournament lanes remain isolated
- **Decision:** PURE_FOOTBALL, MARKET_AUGMENTED and MARKET_BENCHMARK remain distinct.
- **Evidence:** W16 market architecture

### ADR-284 — Version HPO search spaces before execution
- **Decision:** Parameter domains and conditional relationships are immutable study inputs.
- **Evidence:** Reproducibility + no result-dependent search

### ADR-285 — HPO remains development-only
- **Decision:** Protected and forward-shadow evidence cannot drive search/pruning.
- **Evidence:** W17 one-way protected evidence boundary

### ADR-286 — Use Optuna as replaceable HPO adapter
- **Decision:** Optuna remains preferred adapter; canonical study identity remains tool-neutral.
- **Evidence:** Current official Optuna capabilities

### ADR-287 — Use MLflow as replaceable tracking adapter
- **Decision:** MLflow remains preferred local-first tracking adapter; canonical experiment IDs/promotion remain external.
- **Evidence:** Current official MLflow capabilities

### ADR-288 — Explicit hypothesis lifecycle and deduplication
- **Decision:** Hypotheses and experiment identities are append-only; exact duplicate runs are blocked/linked.
- **Evidence:** Autonomous research reproducibility

### ADR-289 — Experiment artifact manifests externalize large binaries
- **Decision:** Store hashes/locations/metadata in repo; keep large data/model artifacts outside cumulative packs.
- **Evidence:** Repository size/rights/reproducibility

### ADR-290 — Replay failure is typed and nonwaivable
- **Decision:** Replay mismatches/blockers are explicit evidence and block challenger adoption.
- **Evidence:** Reproducibility

### ADR-291 — Worktree/source-snapshot isolation with protected paths
- **Decision:** Experiment mutations occur in isolated worktree/snapshot and reject protected W17 path mutation.
- **Evidence:** Research governance

### ADR-292 — Bound research resources and paid compute
- **Decision:** Every experiment declares resource budget; paid remote compute requires explicit user approval.
- **Evidence:** Local-first/cost governance

### ADR-293 — Tournament comparison requires semantic compatibility
- **Decision:** Incompatible targets/splits/data/metrics/lanes are INCOMPARABLE rather than numerically ranked.
- **Evidence:** Statistical validity

### ADR-294 — Retain negative and dominated results
- **Decision:** Search history preserves rejected, failed, pruned and dominated candidates.
- **Evidence:** Search bias/reproducibility

### ADR-295 — Reject thin W18 draft and issue corrected revision
- **Decision:** Corrected W18 v0.18.1 supersedes incomplete first W18 draft while preserving exact W17 parent.
- **Evidence:** Correction audit

### ADR-296 — Corrected W18 requires explicit master-coverage matrix
- **Decision:** Wave gate includes machine-readable coverage of every W18 master design item.
- **Evidence:** Avoid silent scope omission

## W18 full-rebuild ADRs

### ADR-297 — Use transactional local SQLite experiment metadata reference store
- **Decision:** Use SQLite for local experiment metadata/reference persistence; keep interfaces replaceable and prohibit distributed/NFS coordination usage.
- **Class:** B
- **Evidence:** W18 local-first reference implementation

### ADR-298 — Queue events use append-only hash chain
- **Decision:** Experiment queue history is immutable/event-sourced and chained by previous hash.
- **Class:** A
- **Evidence:** W18 research-governance threat model

### ADR-299 — Separate attempt retries from scientific child experiments
- **Decision:** Operational retry increments attempt; scientific identity changes create child experiment.
- **Class:** A
- **Evidence:** W18 lineage semantics

### ADR-300 — Resource admission is explicit and fail-closed
- **Decision:** Scheduler checks dependencies, owner wave, seal, locks, local resources and paid-compute permission before admission.
- **Class:** A
- **Evidence:** W18 local compute policy

### ADR-301 — Use file/worktree locks for shared mutation conflicts
- **Decision:** Local reference concurrency uses explicit locks; distributed locking deferred until operational evidence requires it.
- **Class:** B
- **Evidence:** W18 worktree strategy

### ADR-302 — Result comparison requires semantic compatibility keys
- **Decision:** Research ranking rejects incomparable split/data/feature/lane/BAS/A&M semantics.
- **Class:** A
- **Evidence:** W18 tournament science

### ADR-303 — Avoid arbitrary scalar composite tournament scores
- **Decision:** Retain Pareto/multi-metric tradeoffs unless later science justifies a fixed composite.
- **Class:** B
- **Evidence:** W18 tournament science

### ADR-304 — Artifact manifests separate evidence from large bytes
- **Decision:** Repository stores hashes/URIs/metadata; large binaries/matrices remain external.
- **Class:** A
- **Evidence:** Master no-large-data rule + W18 replay

### ADR-305 — Research packets exclude protected-result feedback
- **Decision:** Protected metrics can move only one-way to external promotion review.
- **Class:** A
- **Evidence:** W17 protected science + W18 governance

### ADR-306 — Replay tolerance is predeclared
- **Decision:** Stochastic replay tolerance cannot be chosen after observing mismatch.
- **Class:** A
- **Evidence:** W18 reproducibility

### ADR-307 — Local JSONL tracker is fallback, not canonical truth
- **Decision:** Provide dependency-free append-only tracking fallback; canonical IDs/governance remain tool-neutral.
- **Class:** B
- **Evidence:** W18 resilience

### ADR-308 — MLflow remains replaceable and non-authoritative
- **Decision:** MLflow state is convenience UI/tracking, not champion or governance source.
- **Class:** B
- **Evidence:** Fresh W18 official tool review

### ADR-309 — Optuna remains replaceable and exports canonical evidence
- **Decision:** Optuna executes search; canonical study/experiment evidence remains Aggie-owned.
- **Class:** B
- **Evidence:** Fresh W18 official tool review

### ADR-310 — Retain nested search multiplicity
- **Decision:** Outer and inner searches remain linked/countable to prevent hidden selection multiplicity.
- **Class:** A
- **Evidence:** W18 research validity

### ADR-311 — Query negative experiment history before rerun
- **Decision:** Automation should detect identical/near-identical dead ends and require reason to repeat.
- **Class:** B
- **Evidence:** W18 autonomy efficiency

### ADR-312 — Operational failure never equals scientific rejection
- **Decision:** Failure taxonomy separates infrastructure/data/rights/governance from empirical result.
- **Class:** A
- **Evidence:** W18 evidence integrity

### ADR-313 — Worktree deletion follows evidence persistence
- **Decision:** Experiment scratch/worktrees can be deleted only after required lineage/evidence is persisted.
- **Class:** A
- **Evidence:** W18 worktree policy

### ADR-314 — Advanced challenger admission requires conventional baseline evidence
- **Decision:** Complex candidates remain blocked until baseline/data/hypothesis/resource/rights gates pass.
- **Class:** A
- **Evidence:** Master Phase-5 challenger rule

### ADR-315 — Full W18 gate requires executable reference subsystems
- **Decision:** Wave completion requires code/tests for every major W18 subsystem, not prose-only placeholders.
- **Class:** A
- **Evidence:** W18 correction audit

### ADR-316 — Supersede all earlier W18 draft artifacts
- **Decision:** Only final full-rebuild pair is valid W19 parent; rejected draft hashes remain documented.
- **Class:** A
- **Evidence:** User correction + cumulative integrity



## W21 decisions
- **ADR-326** — Use dependency-free durable local orchestration kernel for W21.
- **ADR-327** — Fail closed on quarantined or failed weekly steps.
- **ADR-328** — Separate promotion evaluation from promotion application.
- **ADR-329** — Use immutable forecast publication with content collision protection.
- **ADR-330** — Postmortem automation is proposal-only research input.


## W22 decisions

### ADR-331 — Version published forecast envelope while preserving W21 readability
- **Decision:** Add v2 optional product fields while preserving v1/default parsing for W21 artifacts.

### ADR-332 — Optional FastAPI + static dashboard
- **Decision:** FastAPI is the selected optional HTTP/static adapter over a dependency-free serving core; Streamlit/React remain alternatives.

### ADR-333 — Freshness threshold remains evidence-driven
- **Decision:** THR-010 stays blank/TBD; the product exposes exact age and never calls an unclassified snapshot current.

### ADR-334 — Explanation serving is precomputed and non-causal
- **Decision:** Request paths render published explanation evidence only.

### ADR-335 — File-backed product repository retained
- **Decision:** PostgreSQL remains conditional because the W22 workload is immutable single-host reads.

## W24 decisions

### ADR-341 — Execute W24 under explicit user sequencing override while carrying AC-038
- **Decision:** W24 may depend on completed W23 implementation substrate TASK-162 rather than TASK-163. The target-hardware blocker is not cleared.

### ADR-342 — Cross-layer readiness uses the real starter boundaries
- **Decision:** W24 synthetic E2E exercises W19 data/PIT/features, W20 joint-score forecast, W21 immutable publication and W22 read-only serving directly.

### ADR-343 — Target-game output identity is a PIT hard guard
- **Decision:** The predicted game's own historical output is ineligible regardless of malformed timestamps.

### ADR-344 — SportsDataverse raw sibling is upstream provenance
- **Decision:** `cfbfastR-cfb-raw` is recorded as upstream of `cfbfastR-cfb-data`; the pair is not independent corroboration.

### ADR-345 — Open-Meteo access/ensemble semantics refined
- **Decision:** Preserve access lane and run semantics; ensemble mean/spread is optional recent/current uncertainty research, not mandatory long-history training.

### ADR-346 — Keep the learned core architecture into W25
- **Decision:** Make only evidence-backed W24 refinements and carry unresolved AC-038 honestly into final consolidation if necessary.


## W25 final decisions

### ADR-347 — W25 is the terminal numbered wave
- **Decision:** No Wave 26. Post-W25 work is implementation against the final handoff.

### ADR-348 — Final maturity is explicit and target-hardware readiness remains conditional
- **Decision:** Implemented/reference/starter/awaiting-data/awaiting-validation/deferred states remain visible; AC-038 is not cleared without the declared target evidence.

### ADR-349 — Evidence-first implementation order
- **Decision:** Materialize real data, replay PIT history and establish protected conventional baselines before advanced neural/graph/live complexity.
