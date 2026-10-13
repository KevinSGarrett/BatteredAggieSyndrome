# Official schedule evidence successor for the frozen October 17 shadow (BAT-727)

Cycle #55 — Attempt #1. TP55-A01 revision 2026-10-13.1 sections 1-6. Contract
`configs/official_shadow_schedule_expansion_20261017_contract.json`; reader
`src/aggie_analytics/retrospective_baseline/schedule_expansion.py`; builder `tools/build_official_shadow_schedule.py
build-expansion`; gate `artifacts/data_lake/official_shadow_schedule_expansion_20261017_gate.json` (packaged after
materialization).

## What it is

A private, create-only, content-addressed, explicitly selected successor to the accepted BAT-726 official schedule
evidence (`a99d7076…`, policy V1) for all 25 events of the accepted BAT-725 UNTRUSTED_SHADOW snapshot `174f0861…`. It
re-qualifies the retained Cycle 54 capture only: the complete V1 sidecar (journal of 46 attempts, 40 raw bodies, its
contract and `schedule.json`) is bundled byte for byte under `predecessor/<V1 identity>/` and verified at every read by
the accepted BAT-726 reader with its own pinned contract and profile. Zero source requests: nothing is captured,
refetched or retried, and every original URL, status, redirect, error, time and body identity stays as captured.

It is served only through the existing explicit option of the baseline query:

```text
bas-retrospective-baseline-query --prospective-shadow <shadow snapshot.json>
  --schedule-evidence <...official_shadow_schedule_expansion_20261017\sha256\<identity>\schedule.json>
  --grain shadow-schedule|shadow-schedule-source --cutoff <instant with zone> [--season 2026]
  [--event espn:event:<id>] [--team espn:team:<id>] [--limit N] [--offset N] [--all] [--expect-identity <sha256>]
```

The query selects the successor reader only when the named sidecar's own bundled contract names this profile
(`selects`); a V1 sidecar keeps the V1 reader, its answers and refusals byte for byte. Neither profile widens the other.

## The successor policy (frozen before any successor decision)

Authored after a disclosed inspection of the retained pages and frozen in the committed contract at its
`policy_frozen_utc` before any successor decision was derived from the retained pages. The V1 policy, its decisions and
their times are not rewritten. Additions, each exact:

- **Documented institution identity.** An own-team name statement that the V1 rule does not bind (an athletics brand
  such as `Texas Tech Athletics` or `Army West Point`, or a truncated school name such as `Boston`, `Bowling Green State`
  or `at Buffalo`) verifies the owner only through an exact contract decision for that NCAA institution whose
  same-document identity members (Sidearm `siteSettings.siteName` and `mascotPlural`, the page's `og:site_name`) are
  present with their decided values; every decided value is bound to the institution by a declared basis (official
  name plus `Athletics`, the official name's leading clause, the provider display name or team name, the directory
  athletics host brand) checked at derivation. A page whose declared records state no owner name (logo-only WMT views:
  LSU, Clemson, Virginia Tech) is owned through an exact page-identity decision. Identity members establish who owns the
  schedule and never supply an opponent, date, role, venue or time. `Boston` alone never binds; `at Buffalo` is never
  read by stripping `at`.
- **One opponent transformation.** After the V1 leading poll rank, a final separately delimited known event annotation
  (only `(Homecoming)`) is removed in the opponent field only when the remaining exact name binds the event's own
  provider opponent. Unknown parentheticals (`Miami (OH)`, `(Senior Day)`) are never removed; the original string and
  every transformation stay with the witness.
- **Four declared layouts.** The classic SIDEARM schedule object (the JSON object of the inline script registering
  `vue-schedules`, bound by its own `season.title` and `sport.shortname`), and the WMT default-event, team-default and
  event-block views (both grid/list and table rows), bound by an exact declared season heading: `2026 Football
  Schedule`, `2026-27 Football Schedule` (football season 2026, only with complete own dates under the season-year
  rule and a matching weekday) or `Football 2026 Schedule Schedule` (the retained heading text exactly as published).
  A WMT result label is a time statement only when it reads as a time or TBA; a past result is never retained. An
  event-block view's clock is not a time statement (a placeholder for TBA events). A `vs.` divider does not
  distinguish home from neutral and states no designation.
- **JSON-LD.** Never a field source. Its SportsEvent role orientation is censused per document; on the event date a
  JSON-LD event naming the bound opponent on the side opposite the bound designation leaves the designation
  CONFLICTING with both values.

Everything else is the V1 rule: separate field states (season, opponent, event date, designation, venue facility,
venue location, scheduled time) from each record's own members; repeated equal witnesses support a value; conflicts
keep every value; an instant only from an explicit offset or a stated zone designator on the record's own time member;
naive times, TBA and ambiguous zones stay as such; no zone is inferred from a campus.

## Timing

The retained LOCAL_CAPTURE_OBSERVATION bound (re-derived by the V1 reader) and the successor's own `policy_frozen_utc`
are kept separately. The effective availability is the later of the two: a cutoff before the observation bound refuses
`SCHEDULE_UNAVAILABLE_BEFORE_OBSERVATION_BOUND`, a cutoff before the policy-frozen time refuses
`SCHEDULE_UNAVAILABLE_BEFORE_POLICY_FROZEN`, and at or after both the same immutable evidence is served. Rebuilds reuse
the frozen contract time, never the current clock. Nothing claims the successor interpretation existed at the original
capture or at the shadow anchor; the shadow's 100 predictions and anchor are unchanged.

## Records and identity

Each event record keeps the V1 provider claims, owner and opponent blocks, its requests and documents, the successor
disposition and fields with every witness and occurrence, the verified V1 disposition and field states
(`predecessor`) and the movement (`PRESERVED_RECORD_BOUND`, `NEWLY_RECORD_BOUND`,
`STILL_UNSUPPORTED_SAME_DISPOSITION`, `STILL_UNSUPPORTED_DISPOSITION_REFINED`, `RECORD_BOUND_FIELDS_CHANGED`,
`SUPPORT_LOST`; per field `UNCHANGED`, `NEWLY_STATED`, `STATE_CHANGED`). Source records keep every V1 request, hop,
failure and zero-request decision unchanged with the successor document census (structures, owner verification,
identity members, JSON-LD census) and the V1 document state.

`schedule.json` is canonical JSON plus one LF. The identity is the SHA-256 of the canonical document `{schema,
population, contract_id, contract_sha256, predecessor_identity, shadow_identity, policy_frozen_utc, schedule_file,
schedule_sha256, bundle}` over the successor contract and every predecessor file. The reader verifies the predecessor
with the V1 reader, the committed successor contract (its rules equal the frozen code), the cohort and shadow pins,
every decision basis, re-derives `schedule.json` and compares canonical bytes (integer, float, boolean and string
identities differ; the first differing family names the refusal), recomputes the identity and requires the sidecar
pinned by the packaged gate. Builds are staged and renamed once; same-input rebuilds are `ALREADY_PRESENT_IDENTICAL`;
processing order, chunking and interrupted/resumed builds reproduce identical bytes; a rehoused copy serves.

Every row carries `UNTRUSTED_SHADOW`, `PIT_NOT_ADMITTED`, `PREDICTIVE_SKILL_NOT_ESTABLISHED`,
`SCHEDULE_NOT_ACTUAL_KICKOFF`, `CURRENT_OBSERVATION_NOT_ORIGINAL_PUBLICATION`, `NO_RETROACTIVE_ANCHOR_AUTHORITY` and
`SUCCESSOR_POLICY_NOT_ORIGINAL_INTERPRETATION` with national coverage `UNKNOWN`; `--require-pit` is always refused. A
source-data improvement is not a forecast improvement, a skill claim or a scientific hold release.

## Delivered successor

Successor `f1e8bf469572ee3d1732905e58d5c5ac0697be08bdfa5401c4bb03e545640580` (first canonical write BUILD_SCHEDULE_EVIDENCE stage=materialize `20261013T051826419004Z`), bundling the V1 sidecar `a99d70767971b653261c921f57422cc19a749ec53a7ee3ccc8c9c9d5e1c5663e` byte for byte: 25 events, 24 record bound (15 preserved, 9 newly bound, 0 with changed fields, 0 lost), 1 still unsupported; 40 source records, 46 retained attempts, 0 new requests. Observation bound `2026-10-12T18:33:49.597278Z`, policy frozen `2026-10-13T04:34:48.093870Z`, effective availability `2026-10-13T04:34:48.093870Z`. The packaged gate and the reader's `EXPANSION_PROFILE` pin this profile; the values stay in the private data root.
