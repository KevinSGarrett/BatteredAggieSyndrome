# Official schedule evidence for the frozen October 17 shadow (BAT-726)

Cycle #54 — Attempt #1. TP54-A01 revision 2026-10-12.1 sections 1-6. Contract
`configs/official_shadow_schedule_20261017_contract.json`; reader
`src/aggie_analytics/retrospective_baseline/schedule.py`; builder `tools/build_official_shadow_schedule.py`;
gate `artifacts/data_lake/official_shadow_schedule_20261017_gate.json` (packaged after materialization).

## What it is

A private, create-only, content-addressed sidecar of bounded official 2026 football schedule observations for all 25
events of the accepted BAT-725 UNTRUSTED_SHADOW snapshot `174f0861…`. It is served only through the existing baseline
query:

```text
bas-retrospective-baseline-query --prospective-shadow <shadow snapshot.json> --schedule-evidence <schedule.json>
  --grain shadow-schedule|shadow-schedule-source --cutoff <instant with zone> [--season 2026]
  [--event espn:event:<id>] [--team espn:team:<id>] [--limit N] [--offset N] [--all] [--expect-identity <sha256>]
```

`shadow-schedule` returns one record per event (both participants' frozen provider names and keys, the frozen provider
claims, the event disposition, seven separately qualified fields with their exact witnesses, and every retained
occurrence). `shadow-schedule-source` returns every logical request (each redirect hop with URL, status, headers, body
digest/length, UTC start/end and monotonic stamps), every failure, stop and zero-request decision, and each retained
document's structure census. Event and team selectors are conjunctive; unknown or disjoint keys return an empty page;
other seasons report `NOT_YET_AUDITED`. Invocations without `--schedule-evidence` keep their parsers, outputs and help
byte for byte.

## Authority and limits

- Every scheduled instant is an `OFFICIAL_SCHEDULE_CLAIM`, never an actual kickoff.
- Observations are `LOCAL_CAPTURE_OBSERVATION` bounds, not original publication. The availability bound is the
  maximum response end time of every attempt in the journal; a cutoff before it is refused, at or after it the same
  immutable evidence is served (no refresh, no current clock).
- The bound follows the shadow's anchor: nothing is retroactively as of that anchor; the shadow's 100 predictions,
  its anchor and its `PRE_PROVIDER_REPORTED_START` basis are unchanged.
- Every row carries `UNTRUSTED_SHADOW`, `PIT_NOT_ADMITTED`, `PREDICTIVE_SKILL_NOT_ESTABLISHED`,
  `SCHEDULE_NOT_ACTUAL_KICKOFF`, `CURRENT_OBSERVATION_NOT_ORIGINAL_PUBLICATION` and `NO_RETROACTIVE_ANCHOR_AUTHORITY`,
  with national coverage `UNKNOWN`. `--require-pit` is always refused.
- Incidental past results on a season page stay raw page bytes only; they are never extracted, scored or used.

## Acquisition grant (TP54 section 2)

At most 80 anonymous public GET attempts in total (each redirect hop, failure, truncated and interrupted attempt
counts) to the selected owner institution's official athletics host family only (bare and `www.` forms of the NCAA
directory athletics host of the institution the frozen provider names as home; that selection is not proof of the
official home role). A host family answering 401/403/429/451 is stopped for the rest of the attempt; redirects are
followed only inside the family (at most 5 hops); bodies up to 12 MiB; 60-second timeout; at least 2 seconds between
attempt starts by the monotonic clock. Routes: the 2026 season route for every event; for an event with no qualified
document, an explicit same-family 2026 football schedule link found in a retained body, then the landing route. The
reader re-derives and enforces all of this from the journal.

## Declared record structures (frozen before the capture)

| Structure | Season binding (own field) | Owner name | Records |
| --- | --- | --- | --- |
| `SIDEARM_NUXT_SCHEDULE` | `season.title` = `2026` of a football schedule record in the page's `__NUXT_DATA__` | `school_name` | `games` |
| `SIDEARM_TEXT_TABLE` | `<h1>` of `#scheduleTextPage` = `2026 Football Schedule` | (another declared structure of the document) | table rows (Date, Time, At, Opponent, Location) |
| `WMT_SCHEDULE_LIST` | `h1.schedule-hero__title` = `2026 Football Schedule` | each item's `--current` team name | `div.schedule-event-item` of the list view |

Everything else in a page (other views, JSON-LD, widgets, navigation, titles, countdowns) is retained as raw bytes
only and never supplies a field. Unsupported structures stay unsupported.

## Qualification

- Owner: every own-team name statement of a document must bind the frozen provider home team (display, short or
  location name) or the NCAA official name.
- Opponent: a record's own opponent must equal the frozen provider away team's display, short or location name
  (a leading poll rank is removed; abbreviations, mascots, numeric identifiers and fuzzy matches never bind).
- A record binds when its opponent binds and its own local date is in the provider date set (the provider instant's
  calendar dates at -04:00 to -10:00). Records of the opponent on other dates are retained date conflicts (never
  borrowed); an unbindable opponent name on the event date is retained and leaves the opponent unsupported.
- Fields: season, opponent, event date, the owner's HOME/AWAY/NEUTRAL designation, venue facility, venue location and
  scheduled time are qualified separately: SUPPORTED when every bound witness stating the field agrees, CONFLICTING
  (all values kept) when they differ, UNSUPPORTED otherwise. Each field is compared with the frozen provider claim
  (AGREES, DISAGREES, TEXT_DIFFERS for venue names, NOT_COMPARABLE).
- Time: a UTC instant only from an explicit offset/Z or a stated US zone designator on the record's own time field
  (generic ET/CT/PT by the US daylight rule on the record's own date; specific designators must agree with that rule;
  generic MT is ambiguous; transition gaps/folds are ambiguous). Naive local times, TBA and ambiguous designators stay
  as such; no zone is inferred from a campus or site.

## Identity and verification

`schedule.json` is canonical JSON plus one LF. The identity is the SHA-256 of the canonical document
`{schema, population, contract_id, contract_sha256, shadow_identity, schedule_file, schedule_sha256, bundle}` over the
bundled contract, every journal segment and every raw body (`raw/<sha256>.gz`, canonical `gzip.compress(body,
mtime=0)`). The reader verifies the selected shadow with the accepted BAT-725 reader, the committed contract, the exact
bundle, every body against the journal, the journal against the grant and route policy, re-derives `schedule.json`
and compares canonical bytes (integer, float, boolean and string identities differ), recomputes the identity and
requires the sidecar pinned by the packaged gate. Builds are staged and renamed once; a rebuild of the same capture is
`ALREADY_PRESENT_IDENTICAL`; processing order, chunking and interrupted/resumed builds reproduce identical bytes; a
rehoused copy serves identically.

## Delivered sidecar (packaged gate)

One bounded capture (46 of the 80 granted attempts; 40 logical requests: 32 retained documents, 3 HTTP 404, 5 redirects
outside the official host family not followed; no host stopped) was built once, create-only, into sidecar
`a99d70767971b653261c921f57422cc19a749ec53a7ee3ccc8c9c9d5e1c5663e` (43 files), availability bound
`2026-10-12T18:33:49.597278Z`. The gate pins its profile (identity, schedule SHA-256, journal SHA-256, attempts, bound)
and counts only. Dispositions: RECORD_BOUND 15, OWNER_NOT_VERIFIED 6 (a record's own owner name such as an athletics
brand or a truncated school name does not bind; a matched container without declared list items states no owner),
NO_DECLARED_STRUCTURE 3, UNBOUND_OPPONENT_ON_EVENT_DATE 1. Scheduled times: SUPPORTED_INSTANT 4 (each equal to the
frozen provider instant), NAIVE_LOCAL_TIME_ONLY 10, TBA 1, UNSUPPORTED 10. These are official schedule claims, never
actual kickoffs; nothing is retroactive to the shadow anchor.
