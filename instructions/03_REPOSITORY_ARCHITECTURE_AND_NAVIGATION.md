# Repository Architecture, Traceability, and Navigation

The repository is large by design. Autonomous reliability comes from precise retrieval, not repeatedly loading all files. The machine map is `instructions/catalogs/repository_navigation.json`.

## 1. Top-level map

| Area | Purpose and authority |
|---|---|
| `.codex/` | Small compatibility pointers for Codex workflow; not a competing instruction system |
| `.github/` | PR/issue templates, CODEOWNERS, and CI/security workflows |
| `artifacts/` | Small committed evidence/contracts only; large local outputs remain ignored |
| `configs/` | Machine-readable architecture, acceptance, data, feature, model, operation, and repository policy |
| `data/` | Repository-safe samples/contracts; real raw/interim/processed lakes are local/outside Git |
| `docs/` | Architecture, research, product, operations, readiness, historical waves, and final handoff |
| `fixtures/` | Tiny deterministic test fixtures, including PIT/BAS/experiment examples |
| `governance/` | Requirements, ADRs, acceptance controls, dependencies, protected rules, state, risk, source/provenance policy |
| `jira/` | Sanitized live-Jira mirror metadata plus generated internal traceability index |
| `provenance/` | Repository file manifests, hashes, tree, and project provenance |
| `requirements/` | Requirement source documents/records where applicable |
| `schemas/` | Canonical, temporal, feature, model, BAS, TAMU, player, team, experiment, and validation schemas |
| `scripts/` | Platform/runbook automation, including target Windows benchmark |
| `sql/` | Experiment/storage schemas and queries |
| `src/aggie_analytics/` | Executable reference and functional-starter package |
| `tests/` | Governance, reference behavior, integration, operations, readiness, and handoff tests |
| `tools/` | Validators, replay/experiment/product/backup utilities and autonomous-control tooling |
| `instructions/` | This single autonomous operating system |

## 2. Registry counts and semantics

Current terminal registries contain:

- 745 requirements in `governance/REQUIREMENTS_INDEX.csv`;
- 349 ADRs in `governance/ADR_INDEX.csv`;
- 234 acceptance controls in `governance/ACCEPTANCE_CONTROL_CATALOG.csv`;
- 201 WBS tasks in `governance/IMPLEMENTATION_WBS.csv`;
- 33 epics in `governance/EPIC_CATALOG.csv`;
- 323 dependency edges in `governance/TASK_DEPENDENCIES.csv`;
- 33 historical Codex work packets;
- 14 terminal post-W25 handoff items.

Do not rely on the historical WBS status alone for product maturity. Join it with final maturity/gaps/backlog and live Jira using `jira/internal_task_catalog.jsonl`.

## 3. Task-centered retrieval sequence

For an active `BAT-###` issue:

1. Read the live issue and parent chain.
2. Resolve mappings in `jira/issue_source_map.json`.
3. Render internal context:

   ```powershell
   python -B tools\render_task_context.py --repo-root . --task TASK-###
   ```

4. Read linked REQ rows and source documents.
5. Read linked ADRs, distinguishing direct issue links from indirect acceptance-derived relationships.
6. Read linked acceptance controls and evidence expectations.
7. Read hard/soft dependencies and shared-contract ownership.
8. Inspect only the affected source modules, schemas, fixtures, tests, and validators.
9. Expand retrieval only when an interface or conflict requires it.

For a terminal handoff item:

```powershell
python -B tools\render_task_context.py --repo-root . --handoff HANDOFF-###
```

## 4. Runtime subsystem map

| Subsystem | Code | Principal governed sources | Validators |
|---|---|---|---|
| Source/raw evidence | `src/aggie_analytics/data/` | W06 research, raw-field/source registries | `validate_data_research.py`, `validate_w19_foundation.py` |
| Canonical entities | `src/aggie_analytics/entities/` | entity registry, canonical schemas/catalogs | `validate_entities.py` |
| PIT/known-at state | `src/aggie_analytics/temporal/` | temporal registry, PIT policy, target-feature policy | `validate_temporal.py`, `verify_replay_inputs.py` |
| Features | `src/aggie_analytics/features/` | feature registry/lifecycle/screening | feature validators |
| Team/player/context | respective package directories | team/player/context registries and schemas | respective validators |
| TAMU specialization | `src/aggie_analytics/tamu/` | TAMU contracts, slices, overfit guards | `validate_tamu_specialization.py` |
| BAS | `src/aggie_analytics/bas/` | BAS labels, anti-circularity, null policy | `validate_bas_science.py` |
| Modeling | `src/aggie_analytics/modeling/` | model candidates, targets, score contracts | model/W20 validators |
| Protected validation | `src/aggie_analytics/validation/` | W17 registry, protected split and seal | `verify_judging_seal.py`, validation-science validator |
| Experimentation | `src/aggie_analytics/experimentation/` | identity, replay, HPO/tournament/promotion policy | experimentation/admission validators |
| Weekly MLOps | `src/aggie_analytics/orchestration/` | W21 contracts | `validate_w21_mlops.py` |
| Product | `src/aggie_analytics/product/`, `api/` | W22 product contracts | `validate_w22_product.py` |
| Operations/readiness | `operations/`, `readiness/` | W23/W24 readiness and target thresholds | operations/readiness validators |

The exact paths are machine-listed in `instructions/catalogs/repository_navigation.json`.

## 5. Read budget

### Always read

`AGENTS.md`, `instructions/START_HERE.md`, current state, and active issue/branch/PR context.

### At task selection

This document, [05_TASK_SELECTION_AND_SEQUENCING.md](05_TASK_SELECTION_AND_SEQUENCING.md), final backlog/priority, and only the candidate mappings.

### At task execution

Only linked parent/dependency/REQ/ADR/AC/source/code/test/schema surfaces.

### When triggered

Git reconciliation, Jira operations, scientific governance, architecture, security, release, or a specific runbook.

### Historical provenance

Read older wave documents only when linked, delegated by a current source, or needed to resolve provenance/supersession.

## 6. Context-efficiency rules

- Filter large CSV/JSONL registries; do not paste all 745 requirements or 201 task records into a session.
- Persist stable IDs and links rather than copying full source text into shadow summaries.
- Do not create broad “AI memory” files. Jira, Git, PRs, governance, tests, provenance, task packets, and lightweight handoffs are the durable record.
- After context compaction, reread the always-read set and current packet; do not reconstruct critical facts from inference.
- Never treat a search snippet as full authority when the complete linked record is needed.
