# National personnel evidence 2004–2022 (BAT-730, Cycle #59 TP59-A01)

Cycle #59 — Work round #1 — ORIGINAL DELIVERY (canonical Cycle #59 — Attempt #1). Bounded contribution to BAT-411 and
BAT-415; it does not complete either. Cycle #59 — Work round #2 — FIRST REPAIR (C59-CONT-01, MF59A01-01) adds the
reader's numeric and program-key domain checks described under Query; no rule, record or identity changed.

## What it is

One immutable, create-only, content-addressed release of the complete retained personnel evidence, served read-only by
the installed `bas-personnel-evidence-query` (also `python -m aggie_analytics.personnel_evidence.query`). Every record
carries `RETROSPECTIVE_RESEARCH`, `UNTRUSTED_SHADOW`, `PIT_NOT_ADMITTED` and predictive skill `NOT_ESTABLISHED`.

* Committed data contract: `configs/national_personnel_evidence_2004_2022_contract.json` (rules, labels, every pinned
  input, the raw capture chains, parent contracts, the expected collection of every grain, field types, layout,
  selectors, refusals and identity documents). The reader pins its SHA-256.
* Producer and reader: `src/aggie_analytics/personnel_evidence/evidence.py`; pinned authority (generated):
  `src/aggie_analytics/personnel_evidence/anchors.py`; builder: `tools/build_national_personnel_evidence.py`.
* Pinned canonical identities: `artifacts/data_lake/national_personnel_evidence_2004_2022_gate.json` (identities and
  counts only).

## Inputs (all retained; no source request)

| Input | Identity | Role |
| --- | --- | --- |
| Season-roster membership parent (BAT-546) | 3e3da7de, payload 2b450c58 | 154,387 admitted memberships 2004–2022 (30 physical fields) |
| Nonadmitted quarantine (same parent) | 17544cc7 | 52,386 source-only, ambiguous, conflicting or invalid-core rows (never promoted) |
| Candidate reconciliation (BAT-523) | 17e42ac1, 19 season files | each row's raw source row number; the complete admitted/quarantined partition |
| Raw cfbfastR roster captures | 19 capture manifests + payloads | repository commit 2023-05-05T03:50:21Z, captured 2026-08-10 |
| Player event metric parent (BAT-542) | c6baa76b, payload 3e29ee7e | 289,897 sparse 2014–2022 rows (2020 partial) |
| Raw cfbfastR player-stat captures | 9 capture manifests + payloads | the metric parent's sources |
| Original returning-production research (BAT-415) | 4eb29ad4 | compared, never the source of a recomputed value |
| Accepted parent population (C38) | 3baff07f / sqlite 9c517af9 | every 2016–2022 contest and both participants' source divisions |
| C38 identity bindings | 5d15acf7 | `org_id` → `cfbd_team_id` (NAME_CONFIRMED_BY_SCHEDULE / SCHEDULE_FINGERPRINT_ONLY only) |
| BAT-387 core registry | 10d0bd0a | `TEAM|SRC-002|<cfbd id>` ENTITY rows → canonical team (SRC-001 SOURCE_MAPPING never joins) |

Parquet is decoded only by the pinned Polars 1.43.2 (an optional data dependency, imported by the builder's input
loader alone; the reader and query import no third-party package). Every set, sum, join and rule is plain Python.

## Grains

* **roster-membership** — every admitted parent row with all 30 parent fields (missing physical, class and position
  values null), its raw source row number and capture witness, its same-season team count (199 multi-team
  player-seasons kept as distinct associations) and its census association (or the reason it has none).
* **roster-exclusion** — one safe keyed record per nonadmitted row: observation ID, raw source row number, season,
  source-scoped athlete ID, the retained nullable canonical IDs under `UNRESOLVED_OR_NONADMITTED`, disposition,
  admission state and lineage, plus duplicate source-key counts. No name, team label, physical, hometown, geocode,
  headshot, recruiting or current-comparison member.
* **program-season-coverage** — all 1,760 program-seasons of both participants of every accepted parent contest
  2016–2022 with a source FBS/FCS division (905 FBS, 855 FCS): names, divisions, contest witnesses and dispositions, the
  documented chain and its state, admitted roster presence (not completeness), returning-transition presence and
  reasons. An unqualified chain keeps its counts null (unknown, never zero).
* **returning-component** — the 5,867 recomputed components of the six frozen category/stat pairs over canonical player
  sets: numerator, denominator, binary64 share, semantics and unit-interval flag (13 signed-yardage ratios outside [0,1]
  kept; count shares bounded), metric player and row counts, the partial-2020 flag and the agreement with the original.
* **returning-summary** — the 982 recomputed team transitions 2015–2022: prior, current, returning, departed, arrival and
  union counts, the three rates, the six shares (an absent pair null, never zero), the original research identity and
  agreement, both seasons' census associations and the census scope (2015 and its prior 2014 sit outside the census).
* **source-witness** — every pinned input and parent contract: locator, SHA-256, bytes, rows, dataset identity, capture,
  repository commit time, capture time, parent build time, rights source IDs and the grains it supports.
* **census** — counts of every grain and state, the 8 recomputed transition coverage rows and the original agreement.

## Query

```
bas-personnel-evidence-query --database <data>\canonical\national_personnel_evidence_2004_2022\sha256\<id>\national_personnel_evidence.sqlite
    --grain {roster-membership,roster-exclusion,program-season-coverage,returning-component,returning-summary,source-witness}
    [--season N] [--team team_<32 hex>] [--program org:<id>] [--player player_<32 hex>]
    [--limit N] [--offset N] [--all] [--manifest <run_manifest.json>] [--expect-identity <id>]
```

Selector matrix: membership — season, team, program, player; exclusion — season, team, player; coverage — season,
team, program; component and summary — season (target), team, program (target census association); witness — season.
Selectors intersect; an unknown or disjoint valid selection serves no row (the summary's transition coverage
included); a season outside the grain's seasons is `SEASON_OUTSIDE_RELEASE`; an inapplicable selector is
`FILTER_NOT_APPLICABLE` and malformed ones are refused before any file is read; `--require-pit` is always refused. Every
answer states the source time (repository commit 2023-05-05T03:50:21Z, capture and parent build clocks, season grain).

The reader needs no data root. Before any row is served it verifies the location (BAT-717 literal local-file policy for
the database and the explicit manifest; long, extended, relative and special-character local paths serve the same
file; network and device paths are refused; a missing file is never created), the run manifest members and identity,
the database bytes, schema and every meta claim, every record's exact members and JSON types (an integral float, a
boolean or an extra member is refused), the complete expected collection of every grain, every rule the records can
re-derive (returning sets, rates and shares, component and summary links, census associations, coverage counts and
states, chain links and exact namespace, duplicate diagnoses, witnesses and the census), the rebuilt content document,
the contract-defined database identity document and the pinned canonical profile. A coordinated rehash of changed
records is internally consistent and is refused only by the pinned profile (`PERSONNEL_PROFILE_MISMATCH`). Escaped
lone surrogates, excessive nesting, NaN, Infinity, float literals beyond binary64 and integers beyond the digit limit
are refused at their decoding boundary (`PERSONNEL_RECORD_MALFORMED`, `PERSONNEL_META_MALFORMED`,
`PERSONNEL_MANIFEST_MALFORMED`), never a traceback. JSON integers otherwise decode exactly and are compared by their
field's rule; where the reader converts one, the domain is checked first: a returning-component total the binary64
share would convert (its denominator positive) that has no finite binary64 value (magnitude at least
2**1024 - 2**970) is `PERSONNEL_RECORD_MALFORMED` with `JSON_NONFINITE_NUMBER`, and a program key whose body is not a
decimal digit string within the integer conversion limit (a superscript or circled digit, an oversized digit run) is
ordered after every numeric key, so the collection order (`PERSONNEL_ORDER_MISMATCH`) or the program grammar
(`PERSONNEL_KEY_MISMATCH`) refuses it, as it always refused a non-digit key. The refusal catalogue is part of the
contract rules.

## Not claimed

No roster completeness, national completeness, game availability, depth, starter, snap, injury, eligibility, transfer
order or transfer episode; no recruiting/transfer completeness; no 2023–2025 or current rosters; no PIT admission or
backcast of the parent's development-only admission; no model fit, composite weight, target-game feature, forecast,
calibration or skill; no activation. Recruiting/transfer histories, availability, player value, weather, coaching,
NIL, models, A&M/BAS and deeper history keep their owners.
