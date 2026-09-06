# CFBProgramSpecifications BAS changeset proposal (Cycle #28)

Classification: `PLAN_STRUCTURE_PRESENT_SUBSTANTIVE_BAS_INTEGRATION_INCOMPLETE`

Implementation authority: `CFIP_IMPLEMENTATION_AUTHORITY_REQUIRED`

The current `C:\All-22\repos\CFBProgramSpecifications` checkout is dirty. Cycle #28 did not overwrite it and did not open or merge a CFIP PR.

## Per-file gap audit (all 12 `50_BAS_INTEGRATION` documents)

Each file currently has `source_atoms: []` and generic L1 template structure (~54 lines). Required substantive additions:

| File | Required normative additions |
|---|---|
| `00_BAS_FILM_INTEGRATION_PLAN.md` | BAS owns official context/PIT/forecasts; Film is candidate-only; release BOM; quarantine; no local-path runtime |
| `01_CONTEXT_PUBLISHING.md` | `BASContextExportV1` grain, identities, known-at, rights, ordered participants |
| `02_FILM_PACKAGE_IMPORT.md` | `BASFilmImportReceiptV1`; reject drifted/uncommissioned snapshots |
| `03_FILM_PIT_SEMANTICS.md` | known-at <= cutoff; no future-known; no Sunday-into-Monday undeclared updates |
| `04_FILM_FEATURE_REGISTRY.md` | model-required-field coverage against admitted registry; no auto-admission |
| `05_FILM_MODEL_ABLATION.md` | chronological ablation; Week 1 outcomes cannot select/promote |
| `06_PLAYER_STATE_INTEGRATION.md` | official availability vs roster vs film inference; absence ≠ healthy |
| `07_COACH_TEAM_STATE.md` | `StaffRoleEpisodeV1`; no play-caller-from-OC; CFBD head-coach only |
| `08_MATCHUP_INTEGRATION.md` | national population freeze; current FBS + scheduled lower-division opponents |
| `09_MODEL_PROMOTION.md` | independent acceptance; operator hold; no champion claim |
| `10_END_TO_END_FORECAST_FLOW.md` | atomic source receipts; game-grain metrics; dependency invalidation |
| `11_ACCEPTANCE.md` | producer/validator independence; cross-output coherence; CFIP vs BAT close rules |

Empty `source_atoms` must not be accepted once BAS-integration source evidence is mapped. Generated indexes are not proof of completeness.

## Program-level files that must change after CFIP authority

- program scope / end-to-end architecture
- authority matrix (BAT scientific authority; CFIP specifications/contracts)
- repository architecture (active BAS checkout vs isolated integration clone)
- capability graph, critical path, global Definition of Done, milestones/schedule

Do not hand-edit generated ProgramSpecifications registries. Rebuild through owned tooling after normative sources change.

## Cycle #28 deliverable

This proposal plus `C01_BAS_EXCHANGE_CONTRACT_RFC.md`. No CFIP merge.
