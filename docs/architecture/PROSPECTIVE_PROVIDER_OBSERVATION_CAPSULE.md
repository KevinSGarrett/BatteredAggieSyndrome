# Prospective provider-observation capsule (BAT-723)

Cycle #51 — Attempt #1. Governing plan: TP51-A01 revision 2026-10-11.1 sections 1–6. Contract:
`configs/prospective_provider_observation_20261011_contract.json` (`BAT-723-PROSPECTIVE-PROVIDER-OBSERVATION-20261011-V1`).
Reader: `aggie_analytics.national_source_time.prospective`. Builder: `tools/build_prospective_provider_observation.py`.

## What it is and is not

One immutable JSON capsule that makes the single retained ESPN college-football scoreboard observation of
2026-10-11 (request 18:15:55.264959–18:15:55.744674 UTC, HTTP 200, for 2026-10-17) usable through the existing
`bas-source-time-query` console and `python -m aggie_analytics.national_source_time.query`, explicitly selected with
`--prospective-evidence <capsule.json>`. It holds the exact 25 provider event keys and 50 participant overall records
of that response.

It is a provider claim. It is not an official NCAA result, independent corroboration, proof of first publication, a
PIT admission, a forecast input admission or a national coverage claim: 25 events and the requested `limit=1000` do not
prove national completeness, and coverage beyond the retained response is UNKNOWN. Provider identifiers are namespaced
(`espn:event:<id>`, `espn:team:<id>`); equal numeric IDs or similar names never authorize NCAA or CFBD joins. The
response's top-level `provider` object is the odds provider (DraftKings) and is recorded only as
`ODDS_PROVIDER_OBJECT_NOT_SCOREBOARD_PROVENANCE`; provenance is the ESPN endpoint and retained receipt.

## Authority and layout

Authority is the exact raw response bytes, the retained capture receipt, the manager-frozen expected cohort and the
committed contract. The contract pins the raw, receipt and cohort SHA-256 values and the exact membership (25 event
keys, 50 `(event, side, team)` tuples). The reader pins the committed contract's SHA-256
(`prospective.CONTRACT_SHA256`; a test requires it to equal the committed file).

```
canonical/prospective_provider_observation_20261011/sha256/<capsule identity>/
    capsule.json                    canonical capsule document
    raw/provider-response.json      byte copy of the retained response
    raw/provider-receipt.json       byte copy of the retained receipt
    inputs/EXPECTED_COHORT.json     byte copy of the frozen cohort
    inputs/contract.json            byte copy of the committed contract
manifests/prospective_provider_observation_20261011/sha256/<capsule identity>/run_manifest.json
```

The capsule directory is portable: the reader needs nothing else (no manager directory, no manifest), so a rehoused
copy of the directory serves identically, including at long and extended-length (`\\?\`) Windows locations.

`capsule.json` is `json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)`
encoded UTF-8 plus one LF. Its top-level members are exactly `schema, population, contract, source, observation,
labels, bundle, events, participants, counts`. The identity document is exactly `schema, population, contract_id,
contract_sha256, capsule_file, capsule_sha256, bundle`; the capsule identity is the SHA-256 of its canonical bytes and
names the directory.

## Verification before any row is served

1. The given path goes through the accepted literal-location rules (`aggie_analytics.readonly_sqlite.literal_path`):
   network, device and non-literal spellings are refused before any access (`EVIDENCE_LOCATION_UNSUPPORTED`,
   `EVIDENCE_LOCATION_NOT_LITERAL`); a missing file is never created (`EVIDENCE_MISSING`). The file must be
   `capsule.json` in a 64-hex identity directory (`EVIDENCE_LOCATION_INVALID`) with the four bundle members at their
   fixed names (`BUNDLE_MEMBER_MISSING`).
2. The bundled contract must be byte-identical to the committed contract (`CONTRACT_NOT_COMMITTED_AUTHORITY`); the raw,
   receipt and cohort must hash to its pins (`RAW_NOT_PINNED_ORIGINAL`, `RECEIPT_NOT_PINNED_ORIGINAL`,
   `COHORT_NOT_PINNED_ORIGINAL`). A coordinated forgery that rehashes every outer identity therefore still fails at the
   pin it cannot change.
3. The complete expected capsule is re-derived from those inputs (`prospective.derive`): every event, participant,
   record, pointer, collection multiplicity, count, label and the observation interval. The supplied file must equal
   the canonical bytes of that document. Otherwise the first difference by family is refused as
   `CAPSULE_<FAMILY>_MISMATCH` (SCHEMA, CONTRACT, SOURCE, OBSERVATION, LABELS, BUNDLE, EVENT_MEMBERSHIP, EVENT_IDENTITY,
   EVENT_SEASON, EVENT_SCHEDULE, EVENT_STATUS, EVENT_ROLES, EVENT_SUPPORT, PARTICIPANT_MEMBERSHIP, PARTICIPANT_IDENTITY,
   PARTICIPANT_RECORD, PARTICIPANT_SUPPORT, COUNTS, CANONICAL_FORM). Values are compared by their canonical serialized
   bytes, so `25`, `25.0`, `true` and `"25"` differ; a duplicate JSON member is `CAPSULE_MALFORMED`.
4. The identity document is recomputed; the directory name must equal it (`CAPSULE_IDENTITY_MISMATCH`); an optional
   `--expect-identity` pin must match (`STALE_CAPSULE_IDENTITY`).

Rows come only from the verified re-derived document.

## Derivation rules (frozen in the contract)

Event grain (`prospective-event`): `event_key, source_event_id, source_pointer, competition_count, competition_pointer,
source_competition_id, season_year, season_type, scheduled_utc, scheduled_literal, time_valid, event_status,
competition_status, home, away, support_state, unsupported_reasons`.

* Exactly one competition is supported (`COMPETITION_COUNT_NOT_ONE`).
* `season_year`/`season_type` are the event's own integers (booleans are not integers).
* `scheduled_utc` only when the event and competition dates are both strict UTC instants, equal, and `timeValid` is
  true; otherwise null with `SCHEDULED_TIME_NO_VALID_ZONE`, `EVENT_COMPETITION_DATE_CONTRADICTION`,
  `TIME_VALID_MISSING` or `SCHEDULED_TIME_NOT_VALID_PER_SOURCE`. Literals are preserved; no kickoff is invented.
* Event and competition statuses are both exposed; a difference is `EVENT_COMPETITION_STATUS_CONTRADICTION`.
* Home/away from `homeAway`: exactly one of each among exactly two competitors with valid IDs; otherwise explicit
  `ROLE_*` / `COMPETITOR_COUNT_NOT_TWO` reasons and both role blocks null. No role is ever selected silently.

Participant grain (`prospective-team-record`): `event_key, side, team_key, source_competitor_id, source_team_id,
source_name, participant_pointer, record_pointer, candidate_record_pointers, overall_record, support_state,
unsupported_reasons`.

* `team_key` from the competitor's own ID; a differing `team.id` is `TEAM_ID_DISAGREEMENT`.
* The record is the competitor's own row with name exactly `overall` and type exactly `total`: none is
  `RECORD_OVERALL_TOTAL_MISSING`, several are `RECORD_OVERALL_TOTAL_MULTIPLE` (none selected; every candidate pointer
  kept). The literal summary is preserved. A strict two-integer `W-L` declares ties 0 by rule
  (`TWO_INTEGER_FORM_TIES_ZERO_BY_RULE`); a strict three-integer `W-L-T` states ties (`THREE_INTEGER_FORM_TIES_STATED`);
  anything else is `RECORD_SUMMARY_MALFORMED`. Home/Away/conference records, substring or case-insensitive matches,
  floats, negatives and fabricated zero records are never used.
* Score placeholders, odds, ranks, statistics, leaders, venue, neutral site and every other unassigned raw field are
  not consumed; changing them changes no record.

Determinism: records are sorted (events by key; participants by event key, team key, side, pointer), so processing
order and read chunking never change a byte.

## Query mode

```
bas-source-time-query --prospective-evidence <...\sha256\<identity>\capsule.json> --grain prospective-event
    --cutoff 2026-10-12T00:00:00Z [--season 2026] [--event espn:event:<id>] [--team espn:team:<id>]
    [--limit 50 | --all] [--offset 0] [--expect-identity <identity>]
```

* `--cutoff` is required: an ISO-8601 instant with an explicit zone, compared as an exact instant (equivalent offsets
  are equal). Before the retained request start the observation is `UNAVAILABLE_BEFORE_REQUEST_START`; from the start
  up to but excluding the end `INDETERMINATE_WITHIN_REQUEST_INTERVAL`; at or after the end
  `AVAILABLE_AT_OR_AFTER_REQUEST_END`. A later cutoff never refreshes the snapshot and the current clock is never read.
  First publication is not inferred.
* `--season 2026` serves; any other season is `NOT_YET_AUDITED` with no rows. `--event` and `--team` are exact and
  conjunctive on both grains; an unknown valid key serves no rows; a malformed key refuses (`EVENT_KEY_INVALID`,
  `TEAM_KEY_INVALID`). Paging is exact (`total`, `returned`, `next_offset`; negative paging refuses).
* Every served row carries `SOURCE_OBSERVATION_ONLY`, `PIT_NOT_ADMITTED`, the provider-claim authority, the coverage
  limit, the observation interval and the source body hash.
* Combining `--prospective-evidence` with `--database`, `--archive-evidence`, `--expect-archive-identity` or
  `--expect-contract` is `PROSPECTIVE_MODE_CONFLICT`; historical filters are `FILTER_NOT_APPLICABLE`; a historical
  grain with the capsule is `PROSPECTIVE_GRAIN_REQUIRED`; the prospective grains or `--event` without the capsule are
  `PROSPECTIVE_EVIDENCE_REQUIRED`; `--require-pit` is `PIT_ADMISSION_AUTHORITY_ABSENT`.
* Without `--prospective-evidence` every existing invocation, default view and accepted data identity is unchanged;
  the prospective module is not even imported.

## Build

The builder refuses a contract that is not the committed authority, derives the capsule with the reader's own
derivation, writes every member create-only into `canonical/.../.staging/<identity>-<pid>-<ns>`, re-reads it and
publishes it with one directory rename to `sha256/<identity>`. An existing identity directory must be byte-identical
(`ALREADY_PRESENT_IDENTICAL`) or the build refuses (`EXISTING_IDENTITY_DIFFERS`). An interrupted build leaves no
directory at the identity path and a resumed build yields identical bytes. The run manifest records the build clock
as `BUILD_CLOCK_ONLY_NOT_OBSERVATION_TIME`; nothing is backdated to the receipt.
