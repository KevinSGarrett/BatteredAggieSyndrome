# Source of Truth Map

## Optional assistive development providers

- `configs/assistive_provider_registry.json` is authoritative for provider separation and adapter ownership.
- `configs/openrouter_assist_policy.json` is authoritative for OpenRouter authority, privacy/routing defaults, external storage, Batch state, and the separately governed USD 0.00 budget.
- `configs/openrouter_task_registry.json` and `schemas/assistive/*.schema.json` are authoritative for OpenRouter task eligibility and machine-consumed candidate contracts.
- `governance/OPENROUTER_ASSISTIVE_PLANE.md` is the governing OpenRouter authority and Definition-of-Done contract.
- `configs/openai_assist_policy.json` and `governance/OPENAI_ASSISTIVE_PLANE.md` remain authoritative for the independent direct OpenAI plane; no OpenRouter policy transfers or overrides its budget or operational evidence.

## Precedence
1. Latest explicit user instruction.
2. Approved Level-A invariants.
3. Current governance rules in this repository.
4. Current evidence-backed ADRs/decision ledger.
5. Latest accepted project documentation.
6. Verified reconnaissance/current research findings.
7. Current hydration state.
8. Master prompt Level-B defaults.
9. Historical source conversation.
10. Unaccepted proposals/speculation.

## Wave 01 governing inputs
- Master prompt: `Pasted markdown(20260808-140900).md` — SHA-256 `02c2b01ae02b99fd1d8f8b8081eed7c6f201586998fd0f53646c657edb6b0239`
- Source chat ZIP: `Initial_Chat_Log(2).zip` — SHA-256 `454381eeff86a01668cfb2b181729683d2fc84b64ef564bd484c2bb65198868e`
- Recon ZIP: `Aggie_Analytics_Data_Reconnaissance_Pack_FINAL_v1_2(1)(1)(2).zip` — SHA-256 `341d4b97bfa89d7e8710c07d559b7dbb62b61f8ed0ac6fb1aad3a00efe4fb14a`; internal edition `FINAL_v1.2_PRE_25_WAVE`

## Identity notes
- Chat chronology is numeric filename order 001→020.
- Recon host filename copy suffixes are non-semantic; internal edition, required structure and hashes establish identity.
- `final/manifests/FINAL_FILE_MANIFEST.csv` and `FINAL_FILE_HASHES.sha256` are the authoritative recon integrity evidence for Wave 01.

## Wave 03 architecture source of truth
Within the repository, architecture interpretation order is:
1. Level-A invariants and current governance.
2. Current accepted ADRs.
3. `configs/architecture_registry.json` for logical component/interface/dependency facts.
4. `docs/01_ARCHITECTURE.md` and `docs/architecture/` for rationale and semantic detail.
5. Later-wave implementation only when it conforms to or explicitly revises the above through an ADR.

The architecture registry does not outrank a later explicit user instruction or Level-A invariant.

## W04 acceptance source of truth
For acceptance/governance questions, use this order within the existing project precedence:
1. protected Level-A requirements and current evidence-backed ADRs;
2. `configs/acceptance_registry.json` + `ACCEPTANCE_CONTROL_CATALOG.csv`;
3. `REQUIREMENT_ACCEPTANCE_MATRIX.csv`, ADR/risk acceptance mappings;
4. `ACCEPTANCE_THRESHOLD_REGISTRY.csv` for quantitative threshold status;
5. owning-wave evidence artifacts.

A blank/TBD threshold is authoritative evidence that no justified numeric threshold has been frozen yet; it must not be filled from intuition.


## W05 implementation-plan source of truth
For implementation-order/backlog questions, use this order within the project precedence:
1. current user instruction + Level-A invariants;
2. accepted architecture/acceptance governance;
3. `configs/implementation_plan.json`;
4. `governance/IMPLEMENTATION_WBS.csv` + `TASK_DEPENDENCIES.csv`;
5. requirement/acceptance task traceability;
6. Codex packet queue/shared-contract ownership;
7. later evidence-backed plan revisions.

The W05 plan is intentionally revisable. W06 must update source-dependent W07+ tasks after fresh current research; stable IDs/history should be preserved rather than silently replaced.

## W06 current-source research
For current data-provider status and source feasibility, `docs/data_research/w06/DATA_UNIVERSE_MASTER.csv` + `SOURCE_RESEARCH_LOG.csv` + source-specific W06 matrices supersede older assumptions while preserving the reconnaissance pack as starting evidence. Official rules/availability/governing-body publications outrank aggregator interpretations for those facts.


## W06 current source-universe baseline
For current source status as researched on 2026-08-08, use `docs/data_research/w06/DATA_UNIVERSE_MASTER.csv` plus `SOURCE_RESEARCH_LOG.csv`, access/PIT matrices and `RESEARCH_EVIDENCE_INDEX.csv`. These supersede stale current-status assumptions from the source chat/reconnaissance while preserving reconnaissance evidence/history. They do **not** supersede Level-A project invariants or claim permanent future availability. W24 must refresh this baseline.


## Wave 07 canonical identity source of truth
- Machine-readable identity contract: `configs/entity_registry.json`
- Entity catalog: `governance/CANONICAL_ENTITY_CATALOG.csv`
- Relationship catalog: `governance/CANONICAL_RELATIONSHIP_CATALOG.csv`
- Mapping methods: `governance/SOURCE_MAPPING_METHODS.csv`
- Resolution states/policy: `governance/ENTITY_RESOLUTION_STATES.csv` + `docs/16_ENTITY_RESOLUTION_AND_REVIEW.md`
- Storage decision: `docs/17_ENTITY_STORAGE_EVALUATION.md`
- W08 may add temporal semantics but must not silently replace these identities.

## W08 temporal source of truth
For temporal eligibility and as-of behavior, the current authority is:
1. Level-A PIT/no-leakage requirements and protected acceptance controls;
2. `configs/temporal_registry.json`;
3. W08 temporal schemas and `governance/PIT_*` / temporal semantic catalogs;
4. W07 source-evidence identity and canonical entity contracts;
5. W06 source-specific findings and reconnaissance temporal policies;
6. source-specific implementation evidence produced in later materialization waves.

A source's current page or latest value never outranks historical version/first-known evidence for replay.

## W09 raw-field registry
- `configs/raw_feature_registry.json` governs W09 registry/handoff semantics.
- `governance/RAW_FIELD_REGISTRY.csv` is the canonical imported raw-field metadata baseline.
- W08 temporal policy outranks scanner inference for temporal safety.
- W07 canonical identity policy outranks name/key heuristics for joins.
- W06 source/access/license decisions remain upstream source context.
- W10+ empirical evidence decides feature adoption; W09 does not.


## W10 feature lifecycle source of truth
- `configs/feature_lifecycle_registry.json` defines transformation/screening/lifecycle contract semantics.
- `governance/FEATURE_CANDIDATE_SEEDS.csv` is candidate permission only, never promotion evidence.
- W08 temporal policy and W09 raw-field registry remain upstream authorities.
- W17 protected empirical evidence decides target-specific production promotion.
- `THR-007` remains authoritative as TBD/blank until evidence justifies a value.


## W12 player-intelligence source of truth
- `configs/player_intelligence_registry.json` defines W12 player/availability/transfer contract semantics.
- W07 canonical player identity outranks source/team/name changes.
- W08 PIT/report-version policy outranks current-page or later participation evidence.
- W09 source/access/license metadata and W06 source decisions remain upstream provenance.
- Official covered conference availability reports outrank secondary inference for the same cutoff; noncoverage remains UNKNOWN.
- W17/W19 empirical evidence decides player-value, availability-impact and transfer-translation promotion; W12 synthetic tests do not.
## W14 A&M specialization
Texas A&M uses the same W07 canonical team/player/coach/game identities and W08 PIT state as the national system. A&M-specific sources can provide higher-resolution observations and source priority, but they cannot create a second canonical truth. Missing high-resolution state falls back to national/unknown/degraded state with uncertainty.

## W25 terminal handoff
The final cumulative W25 repository is the canonical end-of-program state. `docs/final/CODEX_HANDOFF.md`, `FINAL_COMPONENT_MATURITY.csv`, `FINAL_KNOWN_GAPS.*`, and `FINAL_IMPLEMENTATION_PRIORITY.md` govern post-wave implementation. No Wave 26 artifact may supersede this program state.

## Post-W25 feature/source/research execution

`governance/FEATURE_SOURCE_RESEARCH_EXECUTION_CONTRACT.md` and `configs/feature_source_research_program.json` govern the current post-W25 feature, source, and dependency-gated research expansion. They implement newer explicit user direction without creating a Wave 26 or rewriting W25 evidence. Current verified immutable evidence outranks proposal-time observations; W17 protected judging, W08 PIT rules, canonical identity, empirical adoption, and the exposure-aware 2024-2025 development boundary remain controlling.
