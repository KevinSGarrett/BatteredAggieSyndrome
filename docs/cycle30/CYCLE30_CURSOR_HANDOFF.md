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
python tools/acquire_cycle30_historical_wikimedia.py
python tools/acquire_cycle30_official_staff.py
python tools/acquire_cycle30_availability_reports.py
python tools/acquire_cycle30_remaining_finals.py
python tools/acquire_cycle30_wikidata_websites.py
python tools/acquire_cycle30_rosters.py
python tools/acquire_cycle30_discontinued_census.py
python tools/materialize_cycle30.py
python tools/validate_cycle30_gates.py --mode BOTH
python -m ruff check src/aggie_analytics/cycle30 src/aggie_analytics/scientific_reference/cycle30 tests/test_cycle30_adversarial_controls.py tools/materialize_cycle30.py tools/validate_cycle30_gates.py tools/acquire_cycle30_national.py tools/acquire_cycle30_historical_membership.py tools/acquire_cycle30_official_staff.py tools/acquire_cycle30_availability_reports.py tools/acquire_cycle30_historical_wikimedia.py tools/acquire_cycle30_remaining_finals.py
```

Offline science validation uses this worktree `src` first on `PYTHONPATH` and does not write mounted authority. External bulk rows: `C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs`.

PYTHONHASHSEED 0 and 1: Cycle #30 adversarial suite 50/50 pass; Cycle #29 33/33 pass; no discovery difference.

New reconstruction artifacts in this bundle: raw-to-normalized semantic join of **every mounted SRC-002 game capture** (**46,953 compared**, 0 unexplained canonical-absent rows, 1 **known parent exclusion** `SRC-002:GAME:312472199` / C26-7A7-FALSE-QUARANTINE successor, 0 score/tie/site-flag disagreements); parent duplicate/conflict audit (**0 duplicate canonical IDs**, **8 pair+calendar-date collision groups**, **0 score conflicts**, **6 site-class conflicts** on same-score distinct IDs); predecessor `national_pit_eligible_team_features.jsonl` **MOUNTED** (90,198 oriented / 89,855 PIT_FEATURE_ELIGIBLE; sha256 matches gate `0b19735d…`); kernel-vs-predecessor feature compare disagreements recorded, not copied; expected-game universe identity `83fe56a3…` (9,924 contests; 895 outside-opponent games retained); remaining 2026 schedule cohort after 2026-09-08T00:00:00Z (1,480 contests, not A&M-only, no new scheduler job); Wikimedia revision-bound current staff pages (266 programs); official HTML staff directories attempted for all 266 current programs via direct GET (no scrapfly): **249 captured**, 3 empty-parse (Central Connecticut, Colgate, Southeast Missouri State), 1 HTTP-200 not-found shell (Liberty), **13 no athletics URL** (Brown, Butler, Campbell, Hawai'i, Illinois State, Long Island University, Marist, NC State, Richmond, San Diego, St. Thomas (MN), Tennessee Tech, UAlbany), 0 `NOT_ATTEMPTED`. Wikidata P856 recovered Utah Tech; soccer-club hosts (richmondfc.com.au, sandiegofc.com) are rejected. Historical Wikimedia season pages **2013–2023 complete for current DI titles**: **2,926 pages, 410 revision-bound, 1,034 HC/OC/DC candidate episodes**, 1963–2012 and 2024–2026 queued, not PIT. CFBD membership presence delta: 25 historical programs absent from 2026 N. NCAA discontinued-program directory APIs returned **0 JSON rows**; Wikipedia former-program lists yield 1,729 name rows and are **not an NCAA discontinued census**. Historical C-tranche travel: **1,286/1,342** rows with origin+venue coordinates. 1963–2012 backlog travel remains **630/2,302** with coordinates and **1,667 `MISSING_VENUE`**: parent↔CFBD id overlay hits, but CFBD also lacks `venueId` on those contests.

## A — Cycle29 defects

Mapped in `CYCLE30_FINDING_SUCCESSOR_LEDGER.json` with reproducers in `tests/test_cycle30_adversarial_controls.py`. Claim discovery is artifact+pointer+row+field. Science vs containment are split. Empty files cannot PASS science. Ties use `EXCLUDE_TIES_FROM_BINARY_ESTIMAND` (490 historical ties). Pair counts are derived home→away and match the source-provided 41576/2287/52/2238/800 FBS-route classes; FCS–FCS on that route remains 0. Contest-scoped Final, row-bound coaches, midnight≠date-only, future-append rebuild, and independent reconstruction are covered.

## B — Neutral / venue / travel

1,966 provider-neutral historical games reconstructed from the 46,953-row parent (prior cited 1,822 is not re-hardcoded). Ordinary home exposure is 0 on verified neutrals. All 1,966 audit rows now join parent `venue_id` to `CFBD_VENUES.jsonl`: **1,103 have a venue_id**, **1,100 have coordinates** (explicit gaps otherwise; not defaults). Current 2026: 1,737 contest-context rows, 3,474 travel rows, **3,439 with coordinates**, **35 `MISSING_ORIGIN`**, 0 missing venue. C-tranche (2013–2023) verified neutrals: **671 contests / 1,342 travel rows**, **1,286 with coordinates**, **56 `MISSING_VENUE`**, 0 missing origin. 1963–2012 backlog travel is materialized separately: **1,151 contests / 2,302 travel rows**, **630 with coordinates**, **1,667 `MISSING_VENUE`**, 5 missing both; CFBD 1963–2012 games were overlaid by source id (836/836 missing-venue parent neutrals match), but those CFBD rows also have `venueId=None`. Not a completeness claim. Travel is available and **not consumed**. Lambeau permutation is a labeled `SYNTHETIC_FIXTURE`.

## C — National populations

CFBD `/teams?classification=` does not filter; response `classification` in {fbs,fcs} yields **N=266** (138 FBS / 128 FCS) for 2026, not hardcoded 266 and not Week1's 182 appearances. 417 non-DI identities in the unfiltered payload are excluded and counted. Historical 2013–2023: 2,785 FBS/FCS program-seasons. Historical 1963–2012: **9,409** CFBD year-membership rows across **50/50 years attempted** (`CFBD_TEAMS_YEAR_ATTEMPTED`; pre-1978 source classification is not era proof). CFBD FCS–FCS games acquired: 7,198. Parent FCS-involved subset: 2,267. Capture inventory: **990 declared / 990 mounted** (exact paths, not 990−980 subtraction). Synthetic P1–P6 are not in real denominators.

## D — Coaching

Predecessor conservation: 2,251 accepted + 2,382 provisional = 4,633. Stratified sample: 3 parser families, 6 records, 0 expanded family failures (counts are not content validation). Current matrix **798 = 3×266** with dispositions CONFIRMED_APPOINTMENT 575 / CONFIRMED_CO_SHARED_ROLE 132 / UNKNOWN_NOT_LISTED 91. CFBD 2026 coaches used for HC only. Official staff HTML: **266/266 programs attempted** (direct GET, `metered_scraper_credits=0`); **249 captured** with row-bound people (Arkansas WordPress name/title rows now parse; many captured titles remain `OTHER_POSITION` when the source does not say HC/OC/DC), 3 empty-parse (Central Connecticut, Colgate, Southeast Missouri State), 1 HTTP-200 not-found shell (Liberty), 13 no athletics WebsiteURL after Wikimedia+Wikidata P856 (generic `| website =` is not used); **OC/DC `NOT_ATTEMPTED` = 0**. Exact source titles are retained (example: ASU head-coach card title is `Swette Family Endowed Football Coach`, not inferred as HC). Historical Wikimedia **2013–2023**: 2,926 pages attempted, 410 revision-bound, 1,034 candidate episodes overlaid onto the opportunity lattice without shrinking it (2,177 retrospective candidate cells of 219,492); 1963–2012 and 2024–2026 queued. Coaching not modeled. Availability: **11** public conference/CFP policy routes attempted (all HTTP 200); CFBD 2026 roster join slice has 1,394 player rows; policy/archive pages yielded **0 player-name table rows**, so **0 joined** (`CANDIDATE_NOT_JOINED`); no report = UNKNOWN; roster membership is not availability; owner BAT-414.

## E — Kernel

Estimand: 2006–2023 observed FBS–FBS binary win, in-window priors, ties excluded, 2024/25 exposed excluded; plus 2026 Week 1 completed FBS–FBS games bound to the immutable forecast freeze receipt (`snapshot_timestamp_utc=2026-08-31T17:00:00Z` before `kickoff_bound_utc`). **13,244 retrospective unique-game rows** plus **36 freeze-bound 2026 proven PIT training rows** (`COMPLETE_NONZERO_PROVEN`). Those 36 rows are **not** historical 2013 publication recovery; they are Week 1 freeze receipts plus SRC-002 completed scores. Independent reconstruction matched **26,560** team-rows (`PIT_KERNEL_INDEPENDENT_RECONSTRUCTION.json` `matched=true`). Kernel trust classification remains `UNTRUSTED_SHADOW`. `cycle30_kernel_trust_usable=true`; `scientific_trust_recovered=false`; `project_wide_scientific_trust_recovered=false`. Fitted untrusted-shadow candidates remain on 2013–2019 / 2020–2023 folds only (2026 does not enter those folds). No champion/production/A&M claim.

## F — Week1

Forecast payload rehashed: 91 contests, 455 opportunities, 84 p=0.5 excluded from directional skill. Old forecasts immutable. No post-kickoff forecast created. Live `stats.ncaa.org` box-score GETs for remaining contests 6602874 / 6620581 / 6594400 still returned HTTP 403 (`ACQUISITION_FAILED`, GENERIC_ERROR_HTML). ncaa.com scoreboard JSON (weeks 00–03) established **Final** for all three by team-name match, with **different contest IDs**: ND/Wisconsin ncaa.com `6604115` (41–13), Louisville/Ole Miss ncaa.com `6640534` (41–38), SMU/FSU ncaa.com `6603962` (SMU 27, FSU 24). Those ncaa.com IDs are **not** stats.ncaa.org IDs and are not called CFBD NCAA Final. Cycle 29 successor still admits ND/Wisconsin and Louisville/Ole Miss official finals; SMU/FSU is ncaa.com Final in Cycle 30 and remains `AWAITING_OFFICIAL_FINAL` on the stats.ncaa.org identity. Fresh CFBD Florida State 2026 row for SMU is `completed=true` with scores 27–24 (`cfbd_id` 401858212) and is **not** NCAA official Final. SMU T-90 lease `C28_SMU_T90M_PRIMARY_PID_56060` expired 2026-09-07T23:39:23Z; not recaptured as on-time; no Cycle 30 takeover; no new scheduler job.

## G — Contracts / plans

GameContextV2, StaffSnapshotV2, CoachStateV2 proposed. C01 36/7 vs catalog 105/8 recorded, not patched. CFIP RFC in `docs/cycle30/CFIP_RFC_CYCLE30.md`; CFBProgramSpecifications / CFBIntelligenceContracts **not modified**. BAS plan docs 29/30/33/36 updated on this isolated branch. `C:\All-22` not used as runtime.

## H — Review / Jira / coverage

PR685: 19 inline threads captured; latest five P1s independently retested against Cycle 30 code. Codecov 66.98895% informational; thresholds not restored. Worktrees retained (no deletion). Private Jira delta is local-only; live comments posted through In Review owners without Done or BAT-523 completion.

## Audit units (reconstruction evidence only)

`C30_AUDIT_REGISTER.json` names C30-AUDIT-01..04 plus explicit remaining units for FCS, discontinued programs, injuries/availability, official HC/OC/DC sources, career/position history, and plan-tail domains. Each unit has source/artifact/claim sets, period/population, manager reviewer, implementation owner, blocker, next action, and affected-use restriction. Three result slots (scope/provenance, semantic, adversarial) are filled as Cursor reconstruction vs `PENDING_MANAGER`. **Do not treat this as audited.**

## Explicit non-claims

Hold ACTIVE. No merge. No Done. No BAT-523 completion comment. No model recommendation. Whole-project scientific trust unrecovered. Current fitted forecast trust unrecovered.
