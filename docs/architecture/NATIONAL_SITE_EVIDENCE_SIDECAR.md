# National official-site evidence sidecar, 2024-2025 (BAT-721)

Cycle #49 — Attempt #1. Governing plan TP49-A01 revision 2026-10-09.1 sections 1-6. Contract:
`configs/national_site_evidence_2024_2025_contract.json` (committed before the first canonical write).

The accepted BAT-720 alias successor (`national_reconciliation_aliases_2024_2025`, contract
`BAT-720-NATIONAL-RECONCILIATION-ALIASES-2024-2025-V1`) keeps every one-to-one relation whose parent and provider records
disagree on neutral status or home orientation as `RECONCILED_FIELD_CONFLICT`, both claims side by side. This sidecar is
an explicitly selected, immutable, content-addressed evidence sidecar for exactly those contests. It binds the verified
alias successor and one finite bundle of retained public NCAA and official institutional documents, and it derives,
separately, the **designated home team**, the **official neutral-site designation** and the **physical venue** of each
contest from those raw bytes. It never changes a predecessor record, relation promotion, label, score, default view or
acceptance, and it establishes neither historical publication time (PIT), independent truth nor forecasting skill.

## Inputs

| Input | Role |
| --- | --- |
| Parent query database and the accepted alias successor (with its V1 parent, cached inputs and alias evidence) | verified completely by the accepted readers; the successor's parent records name the disagreements and the original claims |
| Site evidence bundle `<data>/canonical/national_site_evidence_2024_2025/sha256/<bundle>/` | `site_evidence_sources.json` plus one deterministic gzip body per retained document, with its manifest |

The reader pins the sidecar contract (SHA-256 and contract id), the predecessor (alias successor contract SHA-256 and id,
content and database identities), the universe (the exact contest keys in predecessor order) and the evidence bundle
identity with its sources SHA-256. The bundle is read under the sidecar's own population root.

## The finite universe

Every predecessor parent record with a one-to-one relation whose `neutral_status` or `home_orientation` comparison is
`DISAGREE`, in predecessor order (season, final event date, contest key). It must equal the pinned key list
(`SITE_EVIDENCE_UNIVERSE_MISMATCH`). The original claims of each record are copied unchanged: the parent site, the
provider's neutral flag and home side, both comparison results, the field conflicts and the predecessor disposition.

## The sources document

`site_evidence_sources.json` lists every retained **document** (SHA-256 order) and every **acquisition attempt** (request
id order), including failures, redirects, denials and stopped hosts.

* A document carries its SHA-256, gzip file, byte count, media type, role (`NCAA_MEMBER_DIRECTORY` or
  `OFFICIAL_SEASON_SCHEDULE`), owner organization and season (schedules only), request URL, final URL, its 200 hop chain,
  retrieval instant and acquisition label.
* An attempt carries its request id, role, organization season, request URL, outcome, acquisition label and every hop
  (URL, status, location, retrieval instant, body SHA-256 and bytes, error).
* Every `RETAINED_200` attempt names exactly a listed document whose receipt equals the attempt's hops; every document is
  produced by at least one attempt; an outcome must agree with its last hop.
* Exactly one NCAA member directory, retrieved from an NCAA host, names each schedule owner's official athletics site
  (one object per organization). Every hop of a schedule document, and every schedule attempt's request, is inside that
  site's host family; the request path names the football sport segment and a label of its season.
* Every schedule document and attempt belongs to a participant season of a universe contest.

Retrieval time is not publication time: a document is evidence of what it showed when retrieved.

## Record schemas and event binding

A schedule document's event records are extracted from its raw bytes under the first declared schema that holds the
season's records (`SITE_RECORD_SCHEMAS`, fixed order):

* `SIDEARM_NUXT_SCHEDULE`: the single `__NUXT_DATA__` devalue payload, its record
  `pinia > schedule > schedules > "schedules-football,<season>"` whose season title is a label of the season, and that
  record's `games` (members `date`, `location_indicator` H/A/N, `neutral_hometeam`, `at_vs`, `opponent.title`,
  `opponent.website`, `facility.title`, `location`, `tournament.title`).
* `SIDEARM_CLASSIC_SCHEDULE`: a server-rendered page whose `<title>` begins with `<season label> Football Schedule`; every
  `<li>` whose class tokens include `sidearm-schedule-game` (its nested link lists are part of it), the designation being
  its single class token `sidearm-schedule-home-game`, `-away-game` or `-neutral-game`; the date is the first span of the
  opponent-date element (`Mon D (Ddd)`), its year the one of the season and the next year whose weekday matches (none or
  both: undetermined); the opponent name and link, and the location spans (city, then facility when it differs).
* `WMT_EVENT_SCHEDULE`: a server-rendered page whose `<title>` begins with `<season label> Football Schedule`; every
  `<div>` whose class tokens include `schedule-event-item`; the designation is the single venue token
  (`schedule-event-date--venue-home`, `--venue-away` or `--venue-neutral`) of its first `schedule-event-date` element;
  the date is the `datetime` attribute of its first `schedule-event-date__day` `<time>` (date part = local date); the
  opponent name, the divider and the location text `City / Facility` (split at the first ` / `; no facility without
  one). This schema was added after the two-request structure probe (amendment 01, structure only; see the contract).

A season document's request path names the football sport segment (`football`, or the WMT slug `m-footbl`) and ends
with a label of its season.

Widgets (for example `nextEvents` or an ld+json event list), other sports' records, other seasons' records and page
headers are never read. A document no schema admits is reported as `NO_DECLARED_RECORD_SCHEMA` with every schema's
reason; it is an examined, retained document, not an unavailable source.

A record is the contest's event record when its local event date (the date part of its `date` member) equals the
contest's final event date and its opponent is the other participant: the opponent's published site lies in the other
participant's NCAA athletics host family (`OFFICIAL_SITE`), or its published name (a leading poll rank `#N` or `#N/M`
is not part of the name) equals one of that participant's documented names (parent name, provider name, NCAA official
name) under the accepted BAT-554 normalization
(`DOCUMENTED_NAME`). Exactly one such record per document binds; two are `AMBIGUOUS_RECORDS_ON_DATE`; a record on the date
with another opponent is `RECORD_ON_DATE_OPPONENT_NOT_BOUND`; the opponent on another date only is
`OPPONENT_RECORD_ON_OTHER_DATE` (a stale or corrected date is reported, never borrowed); otherwise
`NO_RECORD_ON_FINAL_EVENT_DATE`. A failed attempt for a participant season is `ATTEMPT_WITHOUT_DOCUMENT`.

## Field rules

| Field | Stated by | Never stated by |
| --- | --- | --- |
| neutral designation | the owner's three-way location designation: home or away (false), neutral (true) | venue, city, facility owner, tournament or bowl title, `vs`/`at`, provider role |
| designated home | `H` (the owner), `A` (the other participant), `N` with the boolean neutral home-team member `true` (the owner) | `N` alone, a truthy string, provider role |
| physical venue | the record's facility title (whitespace runs collapsed) | city alone |
| venue location | the record's location text (whitespace runs collapsed) | — |

Each field is `SUPPORTED` when every bound record that states it states the same value, `CONFLICTING` when they differ
(every source's value kept; never a majority vote; a venue text difference is marked `TEXT_RENDERINGS_DIFFER`), and
`UNSUPPORTED` without a statement. Claim checks compare each official field with the parent's and the provider's claims
(`SUPPORTED`, `CONTRADICTED`, `CONFLICTING_EVIDENCE`, `NOT_ADDRESSED`).

The disposition is decided on the disputed field (`neutral_status` -> neutral designation, `home_orientation` ->
designated home): `PARENT_CLAIM_SUPPORTED`, `PROVIDER_CLAIM_SUPPORTED`, `OFFICIAL_SOURCES_CONFLICT`,
`UNSUPPORTED_FIELD_NOT_STATED` (a record is bound but does not state it) or `UNSUPPORTED_NO_BOUND_RECORD`. There is no
target count.

## Outputs and identities

* Content `canonical/national_site_evidence_2024_2025/sha256/<content identity>/`: `site_evidence.jsonl` (one record per
  universe contest), `site_sources.jsonl` (one record per attempt: outcome, hops, document, schema and the contests it
  was examined or bound for) and `summary.json`.
* Database `canonical/.../sha256/<database identity>/national_site_evidence.sqlite`: tables `meta`, `site_evidence`,
  `site_source` (exact DDL in `SITE_DDL`).
* Identity documents (canonical JSON bytes, SHA-256): `site_bundle_document`, `site_content_document` and
  `site_database_document`. The reader rebuilds each from trusted authority and compares canonical bytes, so an integral
  float count or an extra output is another document.

## Consumer

`bas-national-population-query --database <parent> --reconciliation <alias successor> --site-evidence
<...\national_site_evidence.sqlite> --grain site-evidence` (or `python -m aggie_analytics.national_population.query`),
with `--season`, `--team` (either source's participant name, `org:<id>`, `cfbdteam:<id>`), `--contest` (`ncaa:<id>`,
bare digits or `cfbd:<id>`), `--disposition`, `--limit`/`--offset`/`--all`, `--site-evidence-manifest` and
`--expect-site-evidence-identity`. Never a default. Refusals include `SITE_EVIDENCE_NOT_SELECTED`,
`SITE_EVIDENCE_GRAIN_REQUIRED`, `SITE_EVIDENCE_PREDECESSOR_REQUIRED`, `SITE_EVIDENCE_PREDECESSOR_MISMATCH`,
`SITE_EVIDENCE_NOT_PINNED`, `PIT_ELIGIBILITY_NOT_ESTABLISHED` and every verification code above. Without
`--site-evidence` every existing grain answers exactly as before.

## Producer

`tools/build_national_site_evidence.py` (create-only, content-addressed, deterministic under input order, chunking and an
interrupted then resumed build; the accepted V1 builder's checkpoint and materialization are reused).
