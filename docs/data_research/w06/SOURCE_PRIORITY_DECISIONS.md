# Wave 06 Source Priority Decisions

Research date: 2026-08-08

Priority is a project role, not a claim that every field in a source is safe or predictive. Every adopted field still passes source contract, temporal safety, canonicalization, experimentation and promotion gates.

## PRIMARY

- **SRC-001 — SportsDataverse / cfbfastR / cfbfastR-cfb-data**: bulk historical national foundation. Current repo documents ~19 primary dataset families and ~928 columns; many feeds are derived from ESPN/raw upstream sources, so upstream provenance/rights must remain explicit.
- **SRC-002 — Rad Sports Analytics / CollegeFootballData / CollegeFootballData API**: structured API and validation/enrichment. Current Swagger v5.17.0 exposes games, PBP, drives, portal, recruiting, ratings, betting, draft, advanced metrics and live endpoints. Tier/terms are current and must be snapshot-recorded.
- **SRC-004 — Knight Commission / Newhouse / College Athletics Database**: resource context/validation. Useful for program-level resource context, not direct private-school football spending reconstruction.
- **SRC-005 — Official school athletics sites / rosters/schedules/game notes/media guides**: official team evidence and validation. Archive every retrieval/publication version; do not infer historical visibility from current edited page.
- **SRC-007 — U.S. Department of Education / EADA athletics data**: public/private program resource lane. 
- **SRC-009 — Texas A&M Athletics / A&M roster/schedule/stats/archive**: highest-resolution A&M evidence. 
- **SRC-010 — National College Football Awards Association / award watch lists/calendar**: dated consensus prior candidate. 
- **SRC-011 — Official conferences / stats/schedules/archives/game notes**: official validation/fallback and reports. 
- **SRC-013 — NCAA / Football Playing Rules + legislation/LSDBi**: effective-dated playing/regulatory environment. 
- **SRC-014 — Official gamebooks/box scores / gamebooks incl. officials/participation**: official reconciliation, officiating and participation evidence. 
- **SRC-015 — NCAA Statistics / Football Statistics & Records**: official validation + lower-division foundation. 
- **SRC-016 — NCAA / Membership Directory**: canonical institution/division/conference crosswalk support. 
- **SRC-017 — Southeastern Conference / Football Student-Athlete Availability Reports**: A&M primary structured availability evidence. 
- **SRC-018 — Big Ten Conference / Gameday Availability Reports**: national official availability lane. 
- **SRC-019 — Atlantic Coast Conference / Availability Reporting**: national official availability lane. 
- **SRC-020 — Big 12 Conference / Player Availability Reporting**: national official availability lane. 
- **SRC-021 — American Conference / Football Player Availability Reports**: national official availability lane. 
- **SRC-022 — Sun Belt Conference / Football Availability Reporting**: national official availability lane. 
- **SRC-023 — Conference USA / Football Availability Reports**: national official availability lane. 
- **SRC-024 — Mid-American Conference / Football Availability Reports**: national official availability lane. 
- **SRC-025 — College Football Playoff / CFP Student-Athlete Availability Reporting**: official postseason availability lane. 
- **SRC-026 — Open-Meteo / Previous Runs / Single Runs API**: normalized historical forecast reconstruction. 
- **SRC-027 — NOAA/NCEP/GSL / HRRR model + archives**: high-resolution historical forecast source. 
- **SRC-028 — NOAA/NCEP/ARL / NAM/GFS and forecast model archives**: longer-horizon historical forecast fallback. 
- **SRC-029 — NOAA/NCEI / GHCN Hourly / historical observations**: actual-condition label/context and weather forecast verification. 
- **SRC-030 — IANA / Time Zone Database**: historically correct venue timezone conversion. 
- **SRC-039 — Associated Press / AP Top 25 College Football Poll**: point-in-time poll feature/benchmark. 
- **SRC-041 — College Football Playoff / Selection Committee Rankings**: late-season point-in-time context/benchmark. 
- **SRC-043 — Texas A&M / official opponents / Game notes and media guides**: A&M depth/starter/staff/context reconstruction. 
- **SRC-048 — NCAA Statistics / FCS/DII/DIII Football Stats**: bounded lower-division strength/translation input. 
- **SRC-049 — NAIA / PrestoStats / NAIA Stats**: NAIA opponent/transfer translation prior. NAIA requires member schools to submit final stats via PrestoStats; 2026 partnership adds data feed to NAIA.org.
- **SRC-050 — NJCAA / NJCAA Football Statistics**: JUCO transfer translation prior. 
- **SRC-054 — NCAA Division I Governance / House settlement roster-limit implementation**: roster/resource-era semantics. 
- **SRC-055 — NCAA Division I Governance / LSDBi / Age-based eligibility and transfer legislation**: player eligibility/experience era semantics. 

## SECONDARY

- **SRC-003 — Open-Meteo / Historical Weather / Historical Forecast**: normalized weather convenience layer. Observed/reanalysis must never substitute for an earlier forecast snapshot.
- **SRC-008 — U.S. Department of Education / NCES / IPEDS**: institution identity/context/resource covariates. 
- **SRC-012 — Recognized preseason selectors / preseason all-conference/all-America**: consensus prior research candidate. 
- **SRC-031 — USGS / 3DEP / Elevation Point Query Service**: venue elevation verification. 
- **SRC-040 — American Football Coaches Association / AFCA Coaches Poll**: point-in-time consensus candidate. 
- **SRC-051 — NAIA / NAIA Football Polls**: lower-division strength prior/validation. 
- **SRC-052 — NJCAA / NJCAA Football Rankings**: JUCO strength prior/validation. 
- **SRC-053 — NCAA Statistics / Football Attendance Records**: venue/program context candidate. 
- **SRC-058 — SportsDataverse upstream recruiting assets / 247-derived recruits/team talent**: recruiting candidate with explicit upstream lineage. Must not treat public repo availability as proof of upstream redistribution rights or timeless PIT state.

## VALIDATION

- **SRC-038 — NFL / Official Draft Tracker**: completed draft outcome validation only. 
- **SRC-042 — Official conference statistics pages / Conference football statistics**: official cross-check and targeted gaps. 
- **SRC-046 — NCAA / Transfer Portal / Transfer Research Dashboard**: rules/aggregate validation; no access bypass. NCAA describes Transfer Portal as centralized database. Detailed portal is not treated as a public acquisition API.
- **SRC-060 — College Football Playoff / All-time championship game officials**: narrow officiating validation; not national assignment source. 

## FALLBACK

- None assigned in W06.

## OPTIONAL

- **SRC-032 — The Odds API / Historical Odds**: PIT-safe historical market enrichment/benchmark. 
- **SRC-033 — SportsDataIO / NCAA Football API / injuries / betting**: licensed availability/market/live fallback. Provider explicitly states no college depth charts/lineups; injuries aggregate official wires + trusted media. Betting lines include opening/movement/closing timestamps.
- **SRC-034 — Sportradar / NCAA Football API v7**: licensed fallback/live Phase-5 option. 
- **SRC-044 — IRS / Form 990 / TEOS bulk data**: private nonprofit institutional/foundation proxy context only. Never label as football spending unless filing explicitly supports that interpretation.
- **SRC-057 — FAA / U.S. DOT / Airport reference data**: travel/airport context if empirically useful. 
- **SRC-059 — CollegeFootballData / GraphQL/live subscription tier**: future live lane only. 

## RESEARCH_ONLY

- **SRC-035 — Sports Info Solutions / Advanced College Football Data**: advanced charting challenger source. Potentially supplies deeper play/player analytics; no core dependency until value/cost/rights justified.
- **SRC-036 — Stats Perform / Opta / NCAA Football Data**: commercial enrichment/fallback. 
- **SRC-037 — Teamworks / Coaching / tracking data**: advanced Phase-5 scheme/tracking research only. Current product advertises formation, motion, personnel, alignment, snap/depth and player tracking. Treat as inaccessible unless licensed.
- **SRC-045 — NCAA / Membership Financial Reporting System**: source-awareness only unless legitimate access obtained. Do not bypass access control; public alternatives remain primary.
- **SRC-047 — On3 / Transfer Portal Wire/Rankings**: manual validation/research candidate only. Public visibility does not establish automated collection/redistribution rights.
- **SRC-056 — NCAA / College Sports Commission context / NIL/House settlement policy**: regulatory context; not a fabricated team NIL-spend metric. 

## DEFERRED

- **SRC-006 — PFF / College football premium grades/data**: optional enrichment only. Explicitly deferred by project governance unless user reactivates. No implementation dependency.

## REJECTED

- None assigned in W06.

## Binding source-selection rules

- Official governing-body/conference/school evidence is preferred for identity, rule, availability and reconciliation facts when it exists.
- SportsDataverse and CFBD remain high-value practical national data foundations, but neither is canonical truth and both retain upstream/schema/terms provenance.
- Paid market, injury, live and advanced-charting feeds are adapters, not mandatory platform dependencies.
- PFF remains deferred unless the user explicitly reactivates it.
- No source is promoted to a model feature merely because W06 found it.
