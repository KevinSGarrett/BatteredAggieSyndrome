# 10 — Five-Phase Implementation Master Plan

Status: **W05 ACCEPTED IMPLEMENTATION BASELINE**  
Plan version: `w05-plan-v1.0`  
Maturity: **planning/backlog contracts; later-wave source/data/model evidence is not fabricated**

## Purpose
Wave 05 converts the accepted W03 architecture and W04 acceptance architecture into a Codex-ready implementation dependency plan. It does **not** execute Wave 06 research or later football implementation.

## Governing interpretation
- The 25 numbered waves remain the execution authority.
- The five phases organize capability dependencies and may span non-contiguous owner waves.
- Task order is expressed through a DAG and evidence gates, not unsupported calendar estimates.
- `critical path` in W05 means the **dependency-critical gate spine**; it is not a duration-based CPM promise.
- The W06 source replan gate is cleared. W07 canonical identity contracts are now frozen; W08 is the next dependency-critical owner.

## Five capability phases
- **PHASE-1 — Foundation**: Materialize governed source evidence, canonical/PIT state, feature lifecycle, team state and strong reproducible baseline capability. Primary waves: W06-W11; W16-W20 realization.
- **PHASE-2 — Advanced Football Intelligence**: Add player, roster, availability, transfers, coaching, context and game-mechanics intelligence with uncertainty-aware missingness. Primary waves: W12-W13; W19-W20 realization.
- **PHASE-3 — Texas A&M Specialization**: Create disproportionately high-resolution A&M state, specialization, calibration, BAS science and A&M-specific evaluation without replacing national truth. Primary waves: W14-W15; W20 realization.
- **PHASE-4 — Production & Autonomy**: Make selected models/evaluation/research/weekly orchestration/product/operations reproducible, governed and locally operable. Primary waves: W16-W23.
- **PHASE-5 — Advanced Research & Finalization**: Provide gated challenger/live research, full replay/readiness challenge and final Codex handoff without destabilizing proven baselines. Primary waves: W18, W24-W25; optional post-baseline research.

## Backlog scale
- Phases: **5**
- Epics: **33**
- Tasks: **189**
- Dependency edges: **298**
- Requirements traced to tasks: **240/240**
- Acceptance controls traced to tasks: **56/56**
- Codex work packets: **33**

## Canonical machine-readable artifacts
- `configs/implementation_plan.json`
- `governance/IMPLEMENTATION_PHASES.csv`
- `governance/EPIC_CATALOG.csv`
- `governance/IMPLEMENTATION_WBS.csv`
- `governance/TASK_DEPENDENCIES.csv`
- `governance/REQUIREMENT_TASK_TRACEABILITY.csv`
- `governance/ACCEPTANCE_TASK_TRACEABILITY.csv`
- `governance/CODEX_WORK_PACKET_QUEUE.csv`
- `governance/SHARED_CONTRACT_OWNERSHIP.csv`
- `governance/CRITICAL_PATH.csv`

## Readiness state
W06 replan is complete and W07 identity packet is complete. W08 PIT packet is the next eligible dependency-critical work; later packets remain dependency-gated by their predecessors impact and backlog dependencies.

## Definition of DONE
A task is not done because code exists. It requires its declared outputs, required tests/evidence, acceptance-control updates, absence of forbidden artifacts/secrets, and successful integration under current shared-contract ownership.
