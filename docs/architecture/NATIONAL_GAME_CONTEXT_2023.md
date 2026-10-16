# National 2023 game context (BAT-729, Cycle #58 TP58-A01)

Cycle #58 — Work round #1 — ORIGINAL DELIVERY (canonical Cycle #58 — Attempt #1). Bounded contribution to BAT-417 and
BAT-419; it does not complete either.

## What it is

One immutable, create-only, content-addressed release over the **788 accepted 2023 FBS targets** of the accepted
national history prefix (aba0384f) and their **1,576 oriented team views**, served read-only by the installed
`bas-game-context-query` (also `python -m aggie_analytics.game_context.query`). Every record carries
`RETROSPECTIVE_RESEARCH`, `UNTRUSTED_SHADOW`, `PIT_NOT_ADMITTED` and predictive skill `NOT_ESTABLISHED`.

* Committed data contract: `configs/national_game_context_2023_contract.json` (rules, labels, complete expected key
  list, pinned inputs and source clocks, field schemas, layout and identity documents). The reader pins its SHA-256.
* Producer and reader: `src/aggie_analytics/game_context/context.py`; builder: `tools/build_national_game_context.py`.
* Pinned canonical identities: `artifacts/data_lake/national_game_context_2023_gate.json` (identities and counts only).

## Inputs (all retained; no source request)

| Input | Identity | Role |
| --- | --- | --- |
| Accepted history prefix | aba0384f / sqlite e137208c | target membership, dates, both views, accepted eligible prior pools |
| Accepted parent population (C38) | 3baff07f / sqlite 9c517af9 | parent rows: participants, site, documented CFBD game ids, every earlier same-season contest |
| C38 identity bindings | 5d15acf7 | `org_id` -> `cfbd_team_id` (NAME_CONFIRMED_BY_SCHEDULE or SCHEDULE_FINGERPRINT_ONLY) |
| 2023 CFBD FBS games | ebf9ea17 (capture `cap_2c82aa51…`, retrieved 2026-08-09T16:57:56Z) | documented provider game row: participants, neutral flag, start claim, venue id |
| 2023 CFBD teams | 5daa333c (C30 ledger CACHE_HIT 2026-09-09T18:08:44Z) | later-observed team reference origin (`location`) |
| CFBD venues | dfc8daff (C30 ledger CACHE_HIT 2026-09-09T18:08:43Z) | later-observed venue reference coordinate |
| Accepted C56 reference | ad01a42f / content fe303a90 | the frozen 2023 game-grain scores (score block only) |

The teams request's `year=2023` parameter does not make its geography historically effective; both classification
requests returned the same bytes. The ledger times are cache-use records, not original retrieval or historical times.

## Records

* **contest context** — accepted parent role (`HOME_A`/`HOME_B`/`NEUTRAL`) and the separate provider claim with an
  explicit `site_agreement`; the documented provider join and its reason when unsupported; the provider start claim
  with the declared date window `[D-1 10:00Z, D+1 12:00Z)` (any real UTC offset; no timezone inferred); the venue and its
  later-observed coordinate; game-level strata assignments.
* **team context** — each team's binding, parent and provider roles, calendar interval since its latest strictly earlier
  eligible same-season contest (`calendar_interval_days`, `intervening_calendar_days`; `NO_ELIGIBLE_SAME_SEASON_PRIOR`
  and `AMBIGUOUS_LATEST_PRIOR` keep null intervals), exclusions with reasons, its own later-observed reference origin
  and the spherical great-circle reference distance to the venue (R = 6,371,008.8 m, integer metre, half-even). A
  neutral venue never becomes a home campus; the home team's distance may be nonzero.
* **context witness** — per subject and source the exact raw members, locator, state and reason (null raw with the
  reason when a source is absent), plus the three pinned source clocks.
* **score strata** — the frozen C56 A-oriented score of every target and model counted once per family: `ALL`,
  `SITE` (`NEUTRAL`, `NON_NEUTRAL_HOME_AWAY`), `MIN_CALENDAR` (1–6, 7, 8–13, 14+ days, `NO_PRIOR`, `UNSUPPORTED`) and
  `MAX_DISTANCE` (0–499,999, 500,000–1,499,999, 1,500,000+ m, `UNSUPPORTED`). Exact rational Brier and decimal-string
  log loss for the four probability models; exact absolute/squared error for the ridge margin model (never a
  probability or Brier score). Each family partitions the 788 games of every model.
* **census** — state counts.

## Query

```
bas-game-context-query --database <data>\canonical\national_game_context_2023\sha256\<id>\national_game_context.sqlite
    --data-root <data> --grain {contest-context,team-context,context-witness,context-score-summary}
    [--season 2023] [--contest ncaa:<id>] [--team org:<id>] [--orientation A|B] [--source <witness source>]
    [--model <model id>] [--family ALL|SITE|MIN_CALENDAR|MAX_DISTANCE] [--limit N] [--offset N] [--all]
    [--manifest <run_manifest.json>] [--expect-identity <id>]
```

Selectors intersect; an unknown or disjoint valid selection serves no row (the summary included); other seasons are
`SEASON_NOT_YET_AUDITED`; malformed or inapplicable selectors and `--require-pit` are refused (exit 2,
`{"refused": CODE}` on stderr) before any file is read. With `--contest`/`--team` the summary is re-derived over exactly
the selected games. The database, manifest and data root pass the BAT-717 literal local-file policy; the release is
opened read-only and a missing file is never created. A literal local location beyond the classic Windows path limit
(a plain long spelling) is opened through its extended-length form and serves exactly what the short spelling serves;
an SQLite open failure is refused as `CONTEXT_DATABASE_UNREADABLE` / `CONTEXT_INPUT_UNREADABLE`, never a traceback.

Valid JSON in the release can still be malformed data: a string holding an escaped lone surrogate decodes but is not
Unicode text (it cannot be encoded as UTF-8 for the exact canonical comparison), and nesting can exceed the JSON
decoder or encoder depth. The boundary that read it refuses it with its own code -- `CONTEXT_RECORD_MALFORMED` (a block
record), `CONTEXT_META_MALFORMED` (a meta claim) or `CONTEXT_MANIFEST_MALFORMED` (the run manifest) -- and the reason
`JSON_LONE_SURROGATE` or `JSON_NESTING_TOO_DEEP`, never a traceback (the manifest's existing malformed rule already
refused an unencodable identity document with the codec's own message). Genuine Unicode -- BMP or non-BMP, raw or as a
valid escaped surrogate pair -- is ordinary text compared by its field's rule; a non-JSON record line stays
`CONTEXT_RECORD_TYPE_INVALID`; a meta claim that is not JSON is refused by that claim's own rule; the census line is
compared as raw text.

Before any row is served the reader verifies the location, manifest identity, database bytes, schema, every meta claim,
every pinned input under the data root, complete membership and multiplicity of every table, every record, the census,
the content identity and the contract-defined database identity document (canonical bytes) against a complete
re-derivation. Refusal codes include `CONTEXT_INPUT_TAMPERED`, `CONTEXT_<TABLE>_ROW_MISSING`/`_EXTRA`,
`CONTEXT_DUPLICATE_ROW`, `CONTEXT_ORDER_MISMATCH`, `CONTEXT_RECORD_SHAPE_INVALID`, `CONTEXT_RECORD_TYPE_INVALID`,
`CONTEXT_PARTICIPANT_MISMATCH`, `CONTEXT_DATE_MISMATCH`, `CONTEXT_SITE_MISMATCH`, `CONTEXT_PROVIDER_CLAIM_MISMATCH`,
`CONTEXT_GEOGRAPHY_MISMATCH`, `CONTEXT_DISTANCE_MISMATCH`, `CONTEXT_CALENDAR_MISMATCH`, `CONTEXT_SOURCE_CLOCK_MISMATCH`,
`CONTEXT_PIT_CLAIM_INVALID`, `CONTEXT_MIRROR_DOUBLE_COUNT`, `CONTEXT_STRATA_PARTITION_INVALID`,
`CONTEXT_RIDGE_PROBABILITY_INVENTED`, `CONTEXT_SCORE_METRIC_MISMATCH`, `CONTEXT_IDENTITY_DOCUMENT_MISMATCH`,
`CONTEXT_IDENTITY_MISMATCH`, `CONTEXT_RECORD_MALFORMED`, `CONTEXT_META_MALFORMED` and `CONTEXT_MANIFEST_MALFORMED`.

## Not claimed

No actual travel, itinerary, routing, timezone burden, physiological rest, crowd, home-field or travel effect; no
historically effective campus or venue; no PIT admission, forecast, refit, tuning, calibration, model selection or
skill; no protected evaluation; no activation. Weather, personnel, recruiting/transfers, coaching, resources, A&M/BAS,
lower divisions, deeper history and every other plan domain keep their owners.
