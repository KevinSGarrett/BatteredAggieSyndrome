# Requirements Baseline — Through Wave 02

The canonical machine-readable register is `governance/REQUIREMENTS_INDEX.csv` with **150 stable requirements** through Wave 02. `governance/REQUIREMENTS_TRACEABILITY.csv` maps each requirement to current evidence and planned-wave acceptance.

Wave 02 adds operational requirements for deterministic packaging/manifests, safe ZIP handling, local/CI parity, Windows bootstrap, Codex worktree isolation and deliberate deferral of domain/service architecture to Wave 03.

Requirements remain classified as Level A invariants, Level B strong defaults or Level C hypotheses/candidates. Stable IDs are never cosmetically renumbered.

## W04 hardening update

The original W01 baseline remains historical source synthesis. Wave 04 re-audited the full cumulative requirements set and established the current acceptance architecture. The authoritative current views are:

- `governance/REQUIREMENTS_INDEX.csv` — current stable requirements and Level-A/B/C classes;
- `governance/CONSTRAINT_CLASSIFICATION_AUDIT.csv` — W04 before/after classification audit;
- `governance/REQUIREMENT_ACCEPTANCE_MATRIX.csv` — requirement → acceptance controls/evidence state;
- `governance/ACCEPTANCE_CONTROL_CATALOG.csv` — acceptance criteria and gate ownership;
- `governance/ACCEPTANCE_THRESHOLD_REGISTRY.csv` — evidence-owned quantitative thresholds;
- `docs/08_REQUIREMENTS_AND_ACCEPTANCE_ARCHITECTURE.md` — acceptance semantics.

Do not infer implementation completion from the presence of an accepted requirement. Future-wave controls remain pending until real evidence exists.



## W05 implementation-planning update
The canonical requirement register now contains **240 stable requirements**. Wave05 adds implementation-plan governance requirements (`REQ-216`–`REQ-240`) while preserving all prior IDs. The W05 implementation source-of-truth artifacts are `configs/implementation_plan.json`, `governance/IMPLEMENTATION_WBS.csv`, `governance/REQUIREMENT_TASK_TRACEABILITY.csv`, and `governance/ACCEPTANCE_TASK_TRACEABILITY.csv`.

Every cumulative requirement maps to implementation/governance/research tasks, but this mapping does **not** imply that later-wave implementation evidence exists.


## Wave 07 identity hardening
W07 extends the baseline through `REQ-282`. The new requirements freeze opaque/stable canonical identity, source-scoped mappings, transfer/role/game identity rules, source publication/capture identity, conservative unresolved/fuzzy review behavior, merge/split history, and conditional relational persistence. W07 does not claim that the full entity lake or resolver has been materialized.
