# BAS project plans and implementation status

This is a navigation index, not a new plan, acceptance contract or completion declaration. The original technical plans remain under `docs/`; their stable requirement, task, domain and acceptance IDs remain in force unless an explicit later decision changes them.

## Start with the right authority

- Original mission and full scope: [project charter](docs/00_PROJECT_CHARTER.md), [architecture](docs/01_ARCHITECTURE.md), [master implementation plan](docs/10_IMPLEMENTATION_MASTER_PLAN.md), and [source-universe research](docs/data_research/w06/DATA_UNIVERSE_MASTER.csv).
- Complete requirements and tasks: [requirements](governance/REQUIREMENTS_INDEX.csv), [requirement-to-task traceability](governance/REQUIREMENT_TASK_TRACEABILITY.csv), [work breakdown](governance/IMPLEMENTATION_WBS.csv), [dependencies](governance/TASK_DEPENDENCIES.csv), and [acceptance controls](governance/ACCEPTANCE_CONTROL_CATALOG.csv).
- Original end-of-design handoff: [W25 handoff](docs/final/CODEX_HANDOFF.md), [W25 component maturity](docs/final/FINAL_COMPONENT_MATURITY.csv), [known gaps](docs/final/FINAL_KNOWN_GAPS.md), and [implementation priorities](docs/final/FINAL_IMPLEMENTATION_PRIORITY.md). These preserve the architecture/starter milestone; they are not a current whole-system completion report.
- Post-design source and feature work: [execution contract](governance/FEATURE_SOURCE_RESEARCH_EXECUTION_CONTRACT.md) and [evidence registry](configs/feature_source_research_program.json). These retain completed, negative and promising research, including weather, returning production, home field and schedule stress. Reuse requires checking the named artifacts and current dependencies; presence in this registry is not model adoption.
- Public capability and scientific limits: [status](docs/public/STATUS.md), [data domains](docs/public/DATA_DOMAINS.md), and [technical usage](docs/public/GETTING_STARTED.md). Read the as-of date on every status statement.
- Current private manager authority: `C:\BatteredAggieSyndrome.data\ops\manager_review\CURRENT_PROTOCOL.json` selects the release; `C:\BatteredAggieSyndrome.data\ops\manager_review\OPERATING_STATE.md` records current issued work. Resolve the selected release rather than hardcoding its version. The issued worker contract and amendments govern that assignment. These private paths are navigation only and are not exported project data.

## Full product scope

| Area | Governing detail |
|---|---|
| National identity, history, FBS/FCS and lower-division context | [identity](docs/14_CANONICAL_ENTITY_ARCHITECTURE.md), [lower divisions](docs/32_LOWER_DIVISION_STRENGTH_AND_UNCERTAINTY.md), [52 original data domains](docs/data_research/w06/DATA_DOMAIN_COVERAGE_MATRIX.csv) |
| Knowledge time, historical replay and immutable versions | [PIT architecture](docs/18_POINT_IN_TIME_DATA_ARCHITECTURE.md), [as-of contract](docs/19_ASOF_QUERY_AND_CUTOFF_CONTRACT.md), [mutable-domain policies](docs/20_MUTABLE_DOMAIN_SNAPSHOT_POLICIES.md) |
| Team strength, early-season priors and historical regimes | [team state](docs/29_TEAM_STATE_ARCHITECTURE.md), [early season](docs/30_EARLY_SEASON_PRIORS_AND_BLENDING.md), [regime weighting](docs/31_HISTORICAL_WEIGHTING_AND_REGIME.md) |
| Players, injuries/availability, recruiting, transfers and continuity | [player/roster/depth](docs/34_PLAYER_ROSTER_DEPTH_ARCHITECTURE.md), [value and replacement](docs/35_PLAYER_VALUE_REPLACEMENT_AND_AVAILABILITY.md), [availability](docs/36_AVAILABILITY_EVIDENCE_AND_OFFICIAL_REPORTS.md), [recruiting/transfers](docs/37_RECRUITING_TRANSFER_AND_FRESHMAN_INTELLIGENCE.md) |
| Weather, travel, home field, resources, coaching and rules | [environment/context](docs/30_ENVIRONMENT_RESOURCE_CONTEXT_ARCHITECTURE.md), [coaching](docs/29_COACHING_INTELLIGENCE_ARCHITECTURE.md), [regulatory environment](docs/31_REGULATORY_ENVIRONMENT_ARCHITECTURE.md) |
| Opponents, possessions, special teams, hidden yards and officiating | [game mechanics](docs/32_GAME_MECHANICS_ARCHITECTURE.md), [opponents/style/schedule](docs/33_OPPONENT_STYLE_SCHEDULE_OFFICIATING.md) |
| A&M specialization and scientific BAS | [A&M architecture](docs/40_TEXAS_AM_SPECIALIZATION_ARCHITECTURE.md), [BAS](docs/45_SCIENTIFIC_BAS_SPECIFICATION.md), [cross-fitting](docs/46_BAS_CROSSFIT_LABELING_AND_ANTI_CIRCULARITY.md), [Aggie Excess](docs/47_BAS_GENERAL_FBS_AGGIE_EXCESS_AND_PEERS.md) |
| Win, score, margin, uncertainty, calibration and evaluation | [model targets](docs/51_MODEL_TARGETS_AND_OUTPUT_COHERENCE.md), [joint scores](docs/53_JOINT_SCORE_AND_SIMULATION.md), [uncertainty](docs/54_UNCERTAINTY_OOD_AND_MARKET_LANES.md), [scoring](docs/57_SCORING_CALIBRATION_AND_SCORECARDS.md) |
| Weekly operation, API, dashboard and recovery | [weekly MLOps](docs/105_W21_AUTONOMOUS_WEEKLY_MLOPS.md), [product](docs/107_W22_SNAPSHOT_SERVING_PRODUCT.md), [API](docs/product/API_CONTRACT.md), [operations](docs/109_W23_LOCAL_PRODUCTION_OPERATIONS.md) |

## Read completion statements at their declared maturity

A finished design, adapter, dataset, query, empirical experiment, scientific acceptance and usable integrated product are different deliverables. Historical `DONE` rows retain their original scope. A supported data record or passing packet does not establish that weather, availability, transfers, BAS, model calibration or the dashboard are complete. Current manager decisions must name the actual population, artifact, consumer and next unmet dependency.

The W01-W25 wave program ended. Numbered BAS implementation cycles continue under the current protocol; they are not a forbidden Wave 26. Historical source documents remain preserved and useful, while later explicit user instructions and accepted successor decisions control their affected operational clauses. Retired assistive execution stays inactive. CPU, RAM and disk observations do not reinstate the withdrawn automatic host-admission policy. Existing task-specific grants, scientific holds and immutable data boundaries still apply.
