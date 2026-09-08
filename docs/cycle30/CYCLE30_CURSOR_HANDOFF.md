# Cycle #30 Cursor handoff — READY_FOR_MANAGER_REVIEW

**Not `MANAGER_VERIFIED`.** Operator hold remains **ACTIVE**. No merge, no scientific Done, no BAT-523 completion comment, no model recommendation, no protected-lane activation, no public/private cutover.

## Stack

| Layer | Identity |
|---|---|
| Canonical main | `55e12a5aad3a7e843204fcba619c3cb3d3d6194d` |
| Preserved predecessor | PR678 `4b6f823f` ← PR679 `c69a7db9` ← PR680 `2236ca41` ← PR681 `b37444e4` ← PR685 `0b957ea1` |
| Cycle #30 branch | `cursor/cycle30-neutral-national-kernel` |
| Worktree | `C:\BatteredAggieSyndrome.data\worktrees\cycle30-scr` |
| Materialization bind SHA | `da515b22a9f77f621efdb7a03ece68e8da65e091` recorded in `CYCLE30_PREFLIGHT_AND_PRESERVATION.json` `head_sha` |
| Review state | `READY_FOR_MANAGER_REVIEW` |

Fort Knox/assistive pipeline was not used. No paid API review. No-API attestation is `PENDING_BLOCKED` (`CYCLE30_CODEX_CLOUD_REVIEW_ATTESTATION.json`) and is not scientific review.

## Commands

```
set PYTHONPATH=<worktree>\src
python -m unittest discover -s tests -p "test_cycle30*.py"
python -m unittest discover -s tests -p "test_cycle29*.py"
python tools/acquire_cycle30_historical_membership.py
python tools/acquire_cycle30_availability_reports.py
python tools/acquire_cycle30_historical_wikimedia.py --reparse
python tools/acquire_cycle30_wiki_coach_graph.py
python tools/acquire_cycle30_sportradar_staff.py
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

New reconstruction artifacts in this bundle: raw-to-normalized semantic join of **every mounted SRC-002 game capture** (**46,953 compared**, 0 unexplained canonical-absent rows, 1 **known parent exclusion** `SRC-002:GAME:312472199` / C26-7A7-FALSE-QUARANTINE successor, 0 score/tie/site-flag disagreements); parent duplicate/conflict audit (**0 duplicate canonical IDs**, **8 pair+calendar-date collision groups**, **0 score conflicts**, **6 site-class conflicts** on same-score distinct IDs); predecessor `national_pit_eligible_team_features.jsonl` **MOUNTED** (90,198 oriented / 89,855 PIT_FEATURE_ELIGIBLE; sha256 matches gate `0b19735d…`); kernel-vs-predecessor feature compare disagreements recorded, not copied; expected-game universe identity `83fe56a3…` (9,924 contests; 895 outside-opponent games retained); remaining 2026 schedule cohort after 2026-09-08T00:00:00Z (1,480 contests, not A&M-only, no new scheduler job); Wikimedia current staff pages (266 programs, **397** candidate episodes from infobox + staff-table parser); official HTML staff directories attempted for all 266 current programs via direct GET (no scrapfly): **266 captured**, 0 empty-parse, 0 no-URL, 0 `NOT_ATTEMPTED`. Presto/WMT `aria-label` Full-Bio cards and s-table body rows (name and title in the same node) recovered CCSU, Tennessee Tech, Colgate (`colgateathletics.com` host fallback), Southeast Missouri State, and Massachusetts after AWS WAF interstitials were treated as non-directories. Wikidata P856 recovered Utah Tech; soccer-club hosts (richmondfc.com.au, sandiegofc.com) are rejected. Historical Wikimedia season pages: **9,298 pages**, **5,993 revision-bound**, **22,241** staff-table/infobox candidate episodes for **1993–2026 complete** current-DI titles (1992 = 254/266 when the 6,000 live-request ceiling was reached). **1963–1991 remain queued** (`NOT_ATTEMPTED` / incomplete). Wikipedia is revision-bound candidate history, not PIT and not official confirmation. **1,428 PAGE_MISSING** season titles are recorded gaps, not vacancies. CFBD membership presence delta: 25 historical programs absent from 2026 N. NCAA discontinued-program directory APIs returned **0 discontinued JSON rows**; Wikipedia list pages yield 2,560 name rows and are **not an NCAA discontinued census**. Historical C-tranche travel: **1,286/1,342** rows with origin+venue coordinates. 1963–2012 backlog travel remains **650/2,302** with coordinates and **1,647 `MISSING_VENUE`**: parent↔CFBD id overlay hits, and bowl/site notes join 20 additional venues by exact name index; remaining CFBD rows still lack `venueId`.

## A — Cycle29 defects

Mapped in `CYCLE30_FINDING_SUCCESSOR_LEDGER.json` with reproducers in `tests/test_cycle30_adversarial_controls.py`. Claim discovery is artifact+pointer+row+field. Science vs containment are split. Empty files cannot PASS science. Ties use `EXCLUDE_TIES_FROM_BINARY_ESTIMAND` (490 historical ties). Pair counts are derived home→away and match the source-provided 41576/2287/52/2238/800 FBS-route classes; FCS–FCS on that route remains 0. Contest-scoped Final, row-bound coaches, midnight≠date-only, future-append rebuild, and independent reconstruction are covered.

## B — Neutral / venue / travel

1,966 provider-neutral historical games reconstructed from the 46,953-row parent (prior cited 1,822 is not re-hardcoded). Ordinary home exposure is 0 on verified neutrals. All 1,966 audit rows now join parent `venue_id` to `CFBD_VENUES.jsonl`: **1,103 have a venue_id**, **1,100 have coordinates** (explicit gaps otherwise; not defaults). Current 2026: 1,737 contest-context rows, 3,474 travel rows, **3,439 with coordinates**, **35 `MISSING_ORIGIN`**, 0 missing venue. C-tranche (2013–2023) verified neutrals: **671 contests / 1,342 travel rows**, **1,286 with coordinates**, **56 `MISSING_VENUE`**, 0 missing origin. 1963–2012 backlog travel is materialized separately: **1,151 contests / 2,302 travel rows**, **650 with coordinates**, **1,647 `MISSING_VENUE`**, 5 missing both; CFBD 1963–2012 games were overlaid by source id, plus bowl-note venue-name joins where the note uniquely contains a venue name of length ≥10. Not a completeness claim. Travel is available and **not consumed**. Lambeau permutation is a labeled `SYNTHETIC_FIXTURE`.

## C — National populations

CFBD `/teams?classification=` does not filter; response `classification` in {fbs,fcs} yields **N=266** (138 FBS / 128 FCS) for 2026, not hardcoded 266 and not Week1's 182 appearances. 417 non-DI identities in the unfiltered payload are excluded and counted. Historical 2013–2023: 2,785 FBS/FCS program-seasons. Historical 1963–2012: **9,409** CFBD year-membership rows across **50/50 years attempted** (`CFBD_TEAMS_YEAR_ATTEMPTED`; pre-1978 source classification is not era proof). CFBD FCS–FCS games acquired: 7,198. Parent FCS-involved subset: 2,267. Capture inventory: **990 declared / 990 mounted** (exact paths, not 990−980 subtraction). Synthetic P1–P6 are not in real denominators.

## D — Coaching

Predecessor conservation: 2,251 accepted + 2,382 provisional = 4,633. Stratified sample: 3 parser families, 6 records, 0 expanded family failures (counts are not content validation). Current matrix **798 = 3×266** with dispositions CONFIRMED_APPOINTMENT 726 / CONFIRMED_CO_SHARED_ROLE 31 / CANDIDATE_ONLY 26 / UNKNOWN_NOT_LISTED 15. The 26 `CANDIDATE_ONLY` cells are 2026 Wikipedia season-page coordinators where official HTML did not list OC/DC; they are not official confirmation and are not PIT. CFBD 2026 coaches used for HC only. Official staff HTML: **266/266 programs attempted and captured** (direct GET, `metered_scraper_credits=0`); 0 no-URL, 0 empty-parse. SportsRadar NCAAFB v7 `full_roster` (production, `SPORTSRADAR_API_KEY` from local dotenv, key never stored in Git): **266/266 programs matched and captured**; the feed returned **266 Head Coach / Interim Head Coach objects and 0 OC/DC positions**. Those HC rows fill remaining matrix HC cells; OC/DC still come from official HTML where parsed, else Wikimedia candidates. **OC/DC `NOT_ATTEMPTED` = 0**. Exact source titles are retained. Historical Wikimedia season pages: **9,298 pages**, **5,993 revision-bound**, **22,241** candidate episodes (HC 5,687 / OC 5,255 / DC 3,343 plus position coaches) overlaid onto the opportunity lattice without shrinking it (**35,575** retrospective candidate cells of 219,492). **1993–2026** current-DI titles are complete attempts; **1963–1991 queued**, **1992 = 254/266** when the 6,000 live MediaWiki ceiling was reached. Program-category × coach-career graph: **75/266** categories enumerated, **3,927** unique coach pages, **37,140** expanded career-season episodes, **27,185** lattice matches; remaining categories stayed unattempted at the 4,000 live-request ceiling. `present` is stored open-ended (`end_year=null`). Missing Wikipedia staff is not a vacancy. Coaching not modeled. Availability: **11** public conference/CFP policy routes attempted (all HTTP 200); live refresh plus PDF follow-ups extracted **0** verified player names; **0 joined**; no report = UNKNOWN; roster membership is not availability; owner BAT-414.

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
