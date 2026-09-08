# Cycle #30 Cursor handoff — READY_FOR_MANAGER_REVIEW

**Not `MANAGER_VERIFIED`.** Operator hold remains **ACTIVE**. No merge, no scientific Done, no BAT-523 completion comment, no model recommendation, no protected-lane activation, no public/private cutover.

## Stack

| Layer | Identity |
|---|---|
| Canonical main | `55e12a5aad3a7e843204fcba619c3cb3d3d6194d` |
| Preserved predecessor | PR678 `4b6f823f` ← PR679 `c69a7db9` ← PR680 `2236ca41` ← PR681 `b37444e4` ← PR685 `0b957ea1` |
| Cycle #30 branch | `cursor/cycle30-neutral-national-kernel` |
| Worktree | `C:\BatteredAggieSyndrome.data\worktrees\cycle30-scr` |
| Materialization bind SHA | recorded in `CYCLE30_PREFLIGHT_AND_PRESERVATION.json` `head_sha` |
| Review state | `READY_FOR_MANAGER_REVIEW` |

Fort Knox/assistive pipeline was not used. No paid API review. No-API attestation is `PENDING_BLOCKED` (`CYCLE30_CODEX_CLOUD_REVIEW_ATTESTATION.json`) and is not scientific review.

## Commands

```
set PYTHONPATH=<worktree>\src
python -m unittest discover -s tests -p "test_cycle30*.py"
python -m unittest discover -s tests -p "test_cycle29*.py"
python tools/acquire_cycle30_national.py
python tools/materialize_cycle30.py
python tools/validate_cycle30_gates.py --mode BOTH
python -m ruff check src/aggie_analytics/cycle30 src/aggie_analytics/scientific_reference/cycle30 tests/test_cycle30_adversarial_controls.py tools/materialize_cycle30.py tools/validate_cycle30_gates.py tools/acquire_cycle30_national.py
```

Offline science validation uses this worktree `src` first on `PYTHONPATH` and does not write mounted authority. External bulk rows: `C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs`.

PYTHONHASHSEED 0 and 1: Cycle #30 adversarial suite exit 0 / 0; 36 tests; no discovery difference.

## A — Cycle29 defects

Mapped in `CYCLE30_FINDING_SUCCESSOR_LEDGER.json` with reproducers in `tests/test_cycle30_adversarial_controls.py`. Claim discovery is artifact+pointer+row+field. Science vs containment are split. Empty files cannot PASS science. Ties use `EXCLUDE_TIES_FROM_BINARY_ESTIMAND` (490 historical ties). Pair counts are derived home→away and match the source-provided 41576/2287/52/2238/800 FBS-route classes; FCS–FCS on that route remains 0. Contest-scoped Final, row-bound coaches, midnight≠date-only, future-append rebuild, and independent reconstruction are covered.

## B — Neutral / venue / travel

1,966 provider-neutral historical games reconstructed from the 46,953-row parent (prior cited 1,822 is not re-hardcoded). Ordinary home exposure is 0 on verified neutrals. Current 2026: 1,737 contest-context rows, 3,474 travel rows, 3,439 with coordinates, 35 missing-coordinate gaps. Travel is available and **not consumed**. Lambeau permutation is a labeled `SYNTHETIC_FIXTURE`.

## C — National populations

CFBD `/teams?classification=` does not filter; response `classification` in {fbs,fcs} yields **N=266** (138 FBS / 128 FCS) for 2026, not hardcoded 266 and not Week1's 182 appearances. 417 non-DI identities in the unfiltered payload are excluded and counted. Historical 2013–2023: 2,785 FBS/FCS program-seasons. CFBD FCS–FCS games acquired: 7,198. Parent FCS-involved subset: 2,267. Capture inventory: **990 declared / 990 mounted** (exact paths, not 990−980 subtraction). 1963–2012 membership remains `BLOCKED_SOURCE_TASK`. Synthetic P1–P6 are not in real denominators.

## D — Coaching

Predecessor conservation: 2,251 accepted + 2,382 provisional = 4,633. Current matrix **798 = 3×266**. CFBD 2026 coaches used for HC only; OC/DC remain `NOT_ATTEMPTED`/`UNKNOWN_NOT_LISTED`. Attempt ledger count = 50, all HTTP 200. Official staff/media-guide HTML: **266 programs NOT_ATTEMPTED** because `metered_scraper_credits=0` (`OFFICIAL_STAFF_SOURCE_ATTEMPT_SUMMARY.json`). Coaching not modeled. Availability: no report = UNKNOWN, owner BAT-414, 0 report routes acquired.

## E — Kernel

Estimand: 2006–2023 observed FBS–FBS binary win, in-window priors, ties excluded, 2024/25 exposed excluded. **13,244 retrospective unique-game rows**, independent reconstruction matched 26,488 team-rows. **Proven PIT rows = 0** (no source publication receipts) → `PRIMARY_KERNEL_OBJECTIVE_INCOMPLETE`. Fitted untrusted-shadow candidates on 5,344 train / 2,872 eval games; intercept-only eval Brier ≈ 0.244; prior-margin+ordinary-home ≈ 0.221. No champion/production/A&M claim. Predecessor 89,855 / 90,198 payload `national_pit_eligible_team_features.jsonl` is **not mounted**; identities were not invented by subtraction.

## F — Week1

Forecast payload rehashed: 91 contests, 455 opportunities, 84 p=0.5 excluded from directional skill. Old forecasts immutable. No post-kickoff forecast created. SMU/FSU is not recaptured as an on-time T-90.

## G — Contracts / plans

GameContextV2, StaffSnapshotV2, CoachStateV2 proposed. C01 36/7 vs catalog 105/8 recorded, not patched. CFIP RFC in `docs/cycle30/CFIP_RFC_CYCLE30.md`; CFBProgramSpecifications / CFBIntelligenceContracts **not modified**. BAS plan docs 29/30/33/36 updated on this isolated branch. `C:\All-22` not used as runtime.

## H — Review / Jira / coverage

PR685: 19 inline threads captured; latest five P1s independently retested against Cycle 30 code. Codecov 66.98895% informational; thresholds not restored. Worktrees retained (no deletion). Private Jira delta is local-only; live comments posted through In Review owners without Done or BAT-523 completion.

## Audit units (reconstruction evidence only)

`C30_AUDIT_REGISTER.json` names C30-AUDIT-01..04 plus explicit remaining units for FCS, discontinued programs, injuries/availability, official HC/OC/DC sources, career/position history, and plan-tail domains. Each unit has source/artifact/claim sets, period/population, manager reviewer, implementation owner, blocker, next action, and affected-use restriction. Three result slots (scope/provenance, semantic, adversarial) are filled as Cursor reconstruction vs `PENDING_MANAGER`. **Do not treat this as audited.**

## Explicit non-claims

Hold ACTIVE. No merge. No Done. No BAT-523 completion comment. No model recommendation. Whole-project scientific trust unrecovered. Current fitted forecast trust unrecovered.
