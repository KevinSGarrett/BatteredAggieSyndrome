# National observed-weather evidence 2024 (BAT-731, Cycle #60 TP60-A01)

Cycle #60 — Work round #1 — ORIGINAL DELIVERY (canonical Cycle #60 — Attempt #1). Bounded contribution to BAT-417 and
BAT-419; it does not complete either.

## What it is

One immutable, create-only, content-addressed release of the complete retained 2024 observed-weather evidence, served
read-only by the installed `bas-weather-evidence-query` (also `python -m aggie_analytics.weather_evidence.query`).
Every record carries `RETROSPECTIVE_RESEARCH`, `UNTRUSTED_SHADOW`, `PIT_NOT_ADMITTED` and predictive skill
`NOT_ESTABLISHED`, plus the observation-kind, station, association-clock, venue and exposure labels below.

* Committed data contract: `configs/national_observed_weather_evidence_2024_contract.json` (rules, labels, every pinned
  input, the 157 raw station-year captures, parent contracts, source clocks and rights, the expected collection of
  every grain with the pinned original/relation/clock/assignment digests, field types, layout, selectors, refusals and
  identity documents). The reader pins its SHA-256.
* Producer and reader: `src/aggie_analytics/weather_evidence/evidence.py`; pinned authority (generated):
  `src/aggie_analytics/weather_evidence/anchors.py`; builder: `tools/build_national_observed_weather_evidence.py`.
* Pinned canonical identities: `artifacts/data_lake/national_observed_weather_evidence_2024_gate.json` (identities,
  counts and the census only).

## Inputs (all retained; no source request)

| Input | Identity | Role |
| --- | --- | --- |
| Accepted parent population (BAT-710) | 3baff07f / sqlite 9c517af9 | all 1,672 season-2024 contests (participants, site, date, status; scores never read) |
| Accepted C48 alias reconciliation | c1e83fda / sqlite 142edbed | parent and provider records; the promoted one-to-one relation is the only join authority |
| SRC-002 2024 FBS games capture + receipt | 6a49d6e1 / 93cbc39c | 920 provider rows: scheduled start and TBD flag (captured 2026-08-09T16:58:08Z) |
| Original observed-weather pilot | 47dea7e7, payload 7a2f886a | 920 rows, every original field preserved (issued 2026-08-12T09:15:00Z) |
| Pilot capture manifest | bd1c15be | the 157 station-year captures (149 for calendar 2024, 8 adjacent 2025 files) |
| Game coordinates / station candidates | e307d2c3 / a23eee74 | game and current-catalog venue fields; rank-one candidate stations (reference only) |
| 2024 coverage acquisition manifest | e4ff69a7 | the 149 calendar-2024 raw captures (issued 2026-08-12T08:55:00Z) |
| Raw NOAA ISD global-hourly CSVs (SRC-029) | 157 files, 1,251,673,376 bytes | streamed in place; never copied, never committed |
| Official ISD format document (2018-01-12) | 1be604b0 | scaled fields, sentinels, quality codes and report types |

Parquet is decoded only by the pinned Polars 1.43.2 (imported by the builder's input loader alone; the reader and query
import no third-party package). Every decode, ranking, selection, join and rule is plain Python.

## Observation rules (the frozen pilot rules, reproduced from raw rows)

TMP/DEW are tenths of a degree Celsius (sentinel `+9999`), SLP tenths of a hectopascal (`99999`), VIS metres
(`999999`), WND direction degrees (`999`) and speed tenths of a metre per second (`9999`); a sentinel, empty or
non-integer value decodes to null with its raw string and quality code kept. Calm (`C`, speed `0000`) and variable
(`999`/`V`) wind keep their raw type. AA precipitation groups stay raw text (never an hourly total). Among rows sharing a
timestamp the row with the most decoded common fields wins, then the lower report type, source code and row number.
Before is the latest observation at or before the association clock, after the earliest at or after it, and nearest
is the before candidate when it is not farther (earlier wins a tie). Only the kickoff calendar year's file is searched;
there is no maximum time distance, acceptance threshold, quality promotion or alternate station. Quality codes and
report types carry their official meanings; suspect/erroneous flags and summary (SOD/SOM) rows are reported, never
promoted or dropped.

## Grains

* **contest-weather** — one record per accepted parent contest (1,672): parent provenance without scores, the alias
  disposition and conflicts, the relation state (882 `PROMOTED_ONE_TO_ONE`, 38 `CANDIDATE_NOT_PROMOTED`, 752
  `NO_PROVIDER_ROW` outside the FBS route), the associated pilot row and nearest observation for the promoted relations
  only, the candidate station (reference only) and every unsupported reason. The 790 parents without promoted weather
  keep null observations: never a zero, a default or a no-weather assertion.
* **pilot-weather** — one record per original pilot row (920, the 38 unpromoted rows included with their candidate
  contest kept separately): every original field under `original_`, the exact provider-capture join, the association
  clock and its agreement with the capture, the relation decision, the independently reconstructed
  before/after/nearest candidates under `verified_` with their discrepancy disposition (all 920 reproduce exactly),
  quality and report meanings, missing-candidate reasons and the witness keys of the selected raw rows. 11 football
  season 2024 games kick off in calendar 2025 and are searched in the 2025 file.
* **station-year** — all 157 captures: station, calendar year, raw/request/snapshot hashes, header, data, duplicate and
  malformed rows, report types, decoded, sentinel and quality-code counts, raw precipitation presence, observation span,
  candidate station metadata (reference only) and the source clocks and rights.
* **source-witness** — 1,874 ordered witnesses: every pinned input, parent contract and raw file, and the 1,699 raw CSV
  rows the reconstruction selected (file SHA-256, CSV row number, the governed raw strings, the row's own decode, the
  full duplicate-timestamp ranking and the pilot selections that cite it).
* **census** — counts of every grain and state. The 882 promoted relations and the 882 pilot rows whose nearest
  observation lies within 30 minutes are different sets (845 in common, 37 on each side only).

## Query

```
bas-weather-evidence-query --database <data>\canonical\national_observed_weather_evidence_2024\sha256\<id>\national_observed_weather_evidence.sqlite
    --grain {contest-weather,pilot-weather,station-year,source-witness}
    [--season 2024] [--contest ncaa:<id>|nolink:2024:<date>:org:<a>|org:<b>] [--provider-game <id>]
    [--station <usaf>-<wban>] [--limit N] [--offset N] [--all] [--manifest <run_manifest.json>]
    [--expect-identity <id>]
```

Selector matrix: contest-weather and pilot-weather — season, contest, provider game, station; station-year and
source-witness — season, station. Selectors intersect; an unknown or disjoint valid selection serves no row (an
unpromoted pilot row is not served under its candidate contest); a season outside the release is
`SEASON_OUTSIDE_RELEASE`; an inapplicable selector is `FILTER_NOT_APPLICABLE` and malformed ones are refused before any
file is read; `--require-pit` is always refused (`WEATHER_PIT_NOT_ADMITTED`) and there is no historical as-of
selector. Every answer states the source clocks.

The reader needs no data root. Before any row is served it verifies the location (BAT-717 literal local-file policy for
the database and the explicit manifest), the run manifest members and identity, the database bytes, schema and every
meta claim, every record's exact members and JSON types, the complete expected collection of every grain, every rule
the records can re-derive (raw-row decoding, duplicate ranking, candidate order, distances and the tie rule,
discrepancies, reasons and meanings, relations and associations, transplants, clocks, labels and the census), the
rebuilt content document, the contract-defined database identity document and the pinned canonical profile. A
coordinated rehash of changed records the reader cannot re-derive is refused only by the pinned profile
(`WEATHER_PROFILE_MISMATCH`): a raw-row hash, or a comparison of an original pilot field with a build input the release
does not carry (the current-catalog venue fields, the candidate station metadata, the venue-to-station distance), which
the builder checks against the pinned inputs. Lone surrogates, excessive nesting, NaN, Infinity and oversized numbers are refused at
their decoding boundary (`WEATHER_RECORD_MALFORMED`, `WEATHER_META_MALFORMED`, `WEATHER_MANIFEST_MALFORMED`), never a
traceback.

## Not claimed

A candidate station measurement is not a stadium condition; the provider scheduled start is not the actual kickoff;
current catalog venues and roof flags are not historically effective facts; observed 2024 weather is not a 2023 or any
forecast input. No acquisition, no outcome-based derivation, no PIT admission, no model fit, forecast, calibration or
skill, no UI/API expansion and no activation. Forecast weather, station acceptance, roof state, other seasons and
models keep their owners.
