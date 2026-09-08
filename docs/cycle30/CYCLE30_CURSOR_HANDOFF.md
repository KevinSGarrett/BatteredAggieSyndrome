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
python tools/acquire_cycle30_historical_membership.py
python tools/acquire_cycle30_availability_reports.py
python tools/acquire_cycle30_official_staff.py
python tools/materialize_cycle30.py
python tools/validate_cycle30_gates.py --mode BOTH
python -m ruff check src/aggie_analytics/cycle30 src/aggie_analytics/scientific_reference/cycle30 tests/test_cycle30_adversarial_controls.py tools/materialize_cycle30.py tools/validate_cycle30_gates.py tools/acquire_cycle30_national.py tools/acquire_cycle30_historical_membership.py tools/acquire_cycle30_official_staff.py tools/acquire_cycle30_availability_reports.py
```

Offline science validation uses this worktree `src` first on `PYTHONPATH` and does not write mounted authority. External bulk rows: `C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs`.

PYTHONHASHSEED 0 and 1: Cycle #30 adversarial suite 41/41 pass; Cycle #29 33/33 pass; no discovery difference.

New reconstruction artifacts in this bundle: raw-to-normalized semantic trace (73 compared, 0 join/score/tie failures across seasons 1963/1972/1978/2006/2013/2019/2023); expected-game universe identity `83fe56a3…` (9,924 contests; 895 outside-opponent games retained); remaining 2026 schedule cohort after 2026-09-08T00:00:00Z (1,480 contests, not A&M-only, no new scheduler job); Wikimedia revision-bound current staff pages (266 programs, 532 MediaWiki attempts, 251 candidate HeadCoach episodes, not PIT); official HTML staff directories attempted for all 266 current programs via direct GET (no scrapfly): 131 captured, 119 empty-parse, 16 no athletics URL, 0 `NOT_ATTEMPTED`.

## A — Cycle29 defects

Mapped in `CYCLE30_FINDING_SUCCESSOR_LEDGER.json` with reproducers in `tests/test_cycle30_adversarial_controls.py`. Claim discovery is artifact+pointer+row+field. Science vs containment are split. Empty files cannot PASS science. Ties use `EXCLUDE_TIES_FROM_BINARY_ESTIMAND` (490 historical ties). Pair counts are derived home→away and match the source-provided 41576/2287/52/2238/800 FBS-route classes; FCS–FCS on that route remains 0. Contest-scoped Final, row-bound coaches, midnight≠date-only, future-append rebuild, and independent reconstruction are covered.

## B — Neutral / venue / travel

1,966 provider-neutral historical games reconstructed from the 46,953-row parent (prior cited 1,822 is not re-hardcoded). Ordinary home exposure is 0 on verified neutrals. Current 2026: 1,737 contest-context rows, 3,474 travel rows, 3,439 with coordinates, 35 missing-coordinate gaps. Travel is available and **not consumed**. Lambeau permutation is a labeled `SYNTHETIC_FIXTURE`.

## C — National populations

CFBD `/teams?classification=` does not filter; response `classification` in {fbs,fcs} yields **N=266** (138 FBS / 128 FCS) for 2026, not hardcoded 266 and not Week1's 182 appearances. 417 non-DI identities in the unfiltered payload are excluded and counted. Historical 2013–2023: 2,785 FBS/FCS program-seasons. Historical 1963–2012: **9,409** CFBD year-membership rows across **50/50 years attempted** (`CFBD_TEAMS_YEAR_ATTEMPTED`; pre-1978 source classification is not era proof). CFBD FCS–FCS games acquired: 7,198. Parent FCS-involved subset: 2,267. Capture inventory: **990 declared / 990 mounted** (exact paths, not 990−980 subtraction). Synthetic P1–P6 are not in real denominators.

## D — Coaching

Predecessor conservation: 2,251 accepted + 2,382 provisional = 4,633. Stratified sample: 3 parser families, 6 records, 0 expanded family failures (counts are not content validation). Current matrix **798 = 3×266**. CFBD 2026 coaches used for HC only. Official staff HTML: **266/266 programs attempted** (direct GET, `metered_scraper_credits=0`); 131 captured with row-bound people, 119 empty-parse, 16 no WebsiteURL; **OC/DC `NOT_ATTEMPTED` = 0**. Remaining OC/DC cells are `UNKNOWN_NOT_LISTED` or confirmed from official HTML. Wikimedia: 266 revision-bound pages, 251 candidate episodes, `pit_admitted=false`. Coaching not modeled. Availability: 9 public conference/CFP policy routes attempted (all HTTP 200); 118 current programs covered by those routes; player rows not joined to verified roster; no report = UNKNOWN; owner BAT-414.

## E — Kernel

Estimand: 2006–2023 observed FBS–FBS binary win, in-window priors, ties excluded, 2024/25 exposed excluded. **13,244 retrospective unique-game rows**, independent reconstruction matched 26,488 team-rows. **Proven PIT rows = 0** (no source publication receipts) → `PRIMARY_KERNEL_OBJECTIVE_INCOMPLETE`. Fitted untrusted-shadow candidates on 5,344 train / 2,872 eval games; intercept-only eval Brier ≈ 0.244; prior-margin+ordinary-home ≈ 0.221. No champion/production/A&M claim. Predecessor 89,855 / 90,198 payload `national_pit_eligible_team_features.jsonl` is **not mounted**; identities were not invented by subtraction.

## F — Week1

Forecast payload rehashed: 91 contests, 455 opportunities, 84 p=0.5 excluded from directional skill. Old forecasts immutable. No post-kickoff forecast created. NCAA direct box-score GETs for remaining contests 6602874 / 6620581 / 6594400 returned HTTP 403 (`ACQUISITION_FAILED`); Cycle 29 successor still admits ND/Wisconsin and Louisville/Ole Miss official finals and leaves SMU/FSU `AWAITING_OFFICIAL_FINAL`. Fresh CFBD Florida State 2026 row for SMU remains `completed=false` and is **not** NCAA official Final. SMU T-90 lease `C28_SMU_T90M_PRIMARY_PID_56060` expired 2026-09-07T23:39:23Z; not recaptured as on-time; no Cycle 30 takeover; no new scheduler job.

## G — Contracts / plans

GameContextV2, StaffSnapshotV2, CoachStateV2 proposed. C01 36/7 vs catalog 105/8 recorded, not patched. CFIP RFC in `docs/cycle30/CFIP_RFC_CYCLE30.md`; CFBProgramSpecifications / CFBIntelligenceContracts **not modified**. BAS plan docs 29/30/33/36 updated on this isolated branch. `C:\All-22` not used as runtime.

## H — Review / Jira / coverage

PR685: 19 inline threads captured; latest five P1s independently retested against Cycle 30 code. Codecov 66.98895% informational; thresholds not restored. Worktrees retained (no deletion). Private Jira delta is local-only; live comments posted through In Review owners without Done or BAT-523 completion.

## Audit units (reconstruction evidence only)

`C30_AUDIT_REGISTER.json` names C30-AUDIT-01..04 plus explicit remaining units for FCS, discontinued programs, injuries/availability, official HC/OC/DC sources, career/position history, and plan-tail domains. Each unit has source/artifact/claim sets, period/population, manager reviewer, implementation owner, blocker, next action, and affected-use restriction. Three result slots (scope/provenance, semantic, adversarial) are filled as Cursor reconstruction vs `PENDING_MANAGER`. **Do not treat this as audited.**

## Explicit non-claims

Hold ACTIVE. No merge. No Done. No BAT-523 completion comment. No model recommendation. Whole-project scientific trust unrecovered. Current fitted forecast trust unrecovered.
