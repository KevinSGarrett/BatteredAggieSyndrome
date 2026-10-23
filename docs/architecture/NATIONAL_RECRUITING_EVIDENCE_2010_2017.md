# National recruiting evidence 2010-2017 (BAT-735, Cycle #64 TP64-A01)

Private, create-only retained source qualification of the provider (CFBD, SRC-002) recruiting players arrays of the
requested cohort years 2010-2017 and the explicit installed reader mode
`bas-personnel-evidence-query --recruiting-evidence`. Every record and answer is RETROSPECTIVE_RESEARCH,
UNTRUSTED_SHADOW and PIT_NOT_ADMITTED; predictive skill is NOT_ESTABLISHED. It is a bounded contribution to BAT-414
(program-event materialization), BAT-415 (future feature consumption) and BAT-416 (identity/time/source-scale
qualification); it completes none of them, nor BAT-413, the national recruiting/transfer/freshman capability, a model or
a feature.

## What the release is and is not

* **Is:** every one of the retained recruiting observations of the eight captured arrays (28,093 expected by the
  manager's readiness census; re-derived, never forced), each with its capture, zero-based original raw-array ordinal,
  whole-raw-row SHA-256, the permitted public fields with their exact JSON kinds, and one qualification of its source
  person correspondence, its named-program correspondence, its typed value states and its (unknown) historical times;
  all 34 requested dataset/parameter cells of the original acquisition ledger (15 captured, 19 provider-quota missing,
  including seven distinct empty 2010-2016 portal captures); every pinned source file and every referenced core
  registry row as a witness; selected-observation summaries; one census.
* **Is not:** a national FBS/FCS recruit, signing, enrollment or program-season universe (NOT_ESTABLISHED); a roster,
  enrollment, availability, transfer or production record; a commitment, signing, enrollment, decommitment, portal or
  rating-publication history (none exists in the source); a talent prior, class score, rank-to-rating conversion or
  cross-source normalization; a forecast, fit, feature, model or PIT admission.

## Sources and frozen contract

`configs/national_recruiting_evidence_2010_2017_contract.json` is generated from the original sources by
`tools/cycle64/make_recruiting_contract.py` before any qualification and restates the module's rules
(`recruiting.rules_document()`, hashed as `rules_sha256`). It pins, by whole-file SHA-256 and bytes, the acquisition
ledger, the 15 capture receipts (each equal to its ledger entry) and arrays, the BAT-388 people and BAT-387 core
registries (through their repository manifests), the SRC-002 private-research rights row and the legacy builder
(lineage only). Its `expected` member is the source key universe only: the 34 requested cells, the 15 captures (with
their receipt clocks and HTTP Date headers) and, per captured recruiting season, the row count and the digest of the key
sequence `SRC-002|<capture>|<ordinal>|<recruit id>`. No person, program, value or time decision is in the contract. The
manager's readiness counts were known before the rules were frozen; no blind design is claimed.

The derived records and their content, database and profile identities arise only in the first authorized canonical
build. A separate commit then pins exactly that build's identities as `RECRUITING_PROFILE` (`--profile`); every later
build must reproduce them (ALREADY_PRESENT_IDENTICAL) and the reader refuses any release that is not that profile.

## Qualification rules

* **Observation:** `source_recruit_id` (raw `id`, an opaque 1-12 digit string, never integer-normalized),
  `source_athlete_id` (raw `athleteId`: absent, null or an optionally signed 1-12 digit string; the 5,339 negative
  spellings are valid provider IDs), `name`, `recruit_type`, `cohort_year`, `position`, `school`, `committed_to`,
  `rating` (integer or finite float kept as its kind: an integer 1 and a float 1.0 differ), `ranking`, `stars`, the
  per-field JSON kind (`absent` distinct from `null`) and the sorted raw member names. City, state, country, height,
  weight and home location are bound only through the raw row hash and never copied.
* **Person:** the athlete namespace `PLAYER|SRC-002|<athleteId>` when an athlete ID exists, otherwise the recruit-only
  namespace `PLAYER|SRC-002|RECRUIT|<recruitId>`; never a fallback between them and never a name, rating, team or
  position. QUALIFIED_EXISTING_SOURCE_PERSON needs exactly one accepted PERSON row with that key whose record id is its
  canonical id, whose slot `people-v1:player:<8 digits>` derives it (`player_` + uuid5), whose hashes reproduce and whose
  slot and id no other PERSON row carries, and exactly one accepted SRC-002 SOURCE_MAPPING row for the entity key that
  agrees with it. Any failure keeps the observation retrievable as UNSUPPORTED_SOURCE_PERSON with every reason; no
  identity is minted and no registry row is repaired. The existing RECRUITING_OBSERVATION row is a lineage witness only;
  its ASCII-normalized team join is compared, never adopted.
* **Program:** the raw `committedTo` string equals a core TEAM_ALIAS row's `alias` exactly (no case folding, ASCII
  stripping, whitespace normalization, substring or fuzzy rule). EXACT_ALIAS_CORRESPONDENCE needs a source-backed
  witness, no witness integrity failure, one distinct canonical team among all exact witnesses and one verified TEAM
  entity row (`team_` + uuid5 of its slot). Otherwise SOURCE_PROGRAM_LABEL_NULL / _ABSENT, NO_EXACT_SOURCE_BACKED_ALIAS,
  AMBIGUOUS_ALIAS_CANDIDATES, ALIAS_WITNESS_INTEGRITY_FAILED or TEAM_RECORD_UNSUPPORTED. Every exact witness keeps its
  source system, effective interval, label and hashes. A correspondence names a program; historical membership,
  commitment, signing and enrollment stay UNQUALIFIED even where an alias interval and the cohort year overlap.
* **Values:** rating WITHIN/OUTSIDE_DECLARED_UNIT_INTERVAL, ranking POSITIVE/NONPOSITIVE_INTEGER, stars
  INTEGER_ZERO_TO_FIVE/OUTSIDE_ZERO_TO_FIVE (null and absent stay null); the triplet ALL_PRESENT, JOINT_NULL or MIXED;
  scale SOURCE_AS_SERVED_SCALE_UNVERIFIED, system version null, upstream independence NOT_ESTABLISHED.
* **Time:** the capture receipt's 2026-08-10 retrieval clocks and response Date are carried as such; every historical
  known-at, rating publication/update, commitment, signing, enrollment, decommitment, portal-event and effective time
  is null and `pit_eligible` is false. The cohort year never becomes a date.

## Storage and identity

One SQLite file (`meta`, `blocks`; page size 4096, no journal) at
`<root>/canonical/national_recruiting_evidence_2010_2017/sha256/<database identity>/national_recruiting_evidence.sqlite`
with its run manifest at `<root>/manifests/.../sha256/<database identity>/run_manifest.json`. Records are canonical JSON
lines in zlib blocks (observations and qualifications per request season; partitions, sources, summary and census
global). The content identity binds the contract, the pinned inputs and source key universe, the rules digest, the row
counts and every line digest; the database identity binds the content identity, the database bytes and the table
counts. Materialization is create-only. Processing-order variants (reverse, shuffle), checkpoint chunk sizes and an
interrupted, resumed build reproduce the same bytes; every observation keeps its original ordinal.

## Reader and query (explicit mode only)

`bas-personnel-evidence-query --recruiting-evidence <database> --grain <grain> [--season N] [--team team_<32 hex>]
[--player player_<32 hex>] [--recruit <digits>] [--limit N] [--offset N] [--all] [--manifest <file>]
[--expect-identity <sha256>]`, also `python -m aggie_analytics.personnel_evidence.query`. The exact token
`--recruiting-evidence` (or `--recruiting-evidence=<path>`) routes before the unchanged legacy parser; the legacy
`--help` gains exactly one appended paragraph and every other legacy invocation is byte-identical.

* Grains: `recruiting-observation`, `recruiting-qualification`, `recruiting-partition`, `recruiting-source`,
  `recruiting-summary`. Season, team, player and recruit apply to observations, qualifications and summaries and
  intersect exact observation keys before summaries and paging; partitions accept only `--season` (exact single-year
  cells; the two coach range cells have season null); sources accept no selector. An inapplicable selector is
  FILTER_NOT_APPLICABLE; an unknown valid selection serves `rows=[]`, total 0, next_offset null (never a zero summary).
* Selector values: a raw Cc control or lone surrogate refuses before anything else; only U+0020 spaces trim; seasons
  are four ASCII digits 1000-9999; team and player are exact lower-hex canonical IDs (there is no name selector:
  Unicode names are served as record text only); a recruit is 1-12 ASCII digits kept as the exact string.
* Paging: limit 50 and offset 0 by default; `--all` with an explicit `--limit` or `--offset` is PAGING_CONFLICT;
  `--limit 0` is count-only (next_offset = offset when offset < total, else null).
* Refusal precedence: parser and mode conflict (`--database`, even empty), `--require-pit`, any `--as-of` (even
  empty), grain, season, team, player, recruit, applicability, paging conflict, limit, offset, expected identity, the
  database then the explicit manifest literal spelling, native existence and layout, then the manifest, identity, bytes,
  schema and complete collection. Every refusal is exit 2 with one JSON object `{"refused", "error"}` on stderr.
* Locations: both the database and an explicit manifest pass the BAT-717 literal local-file policy before any file
  access (network, device and other namespaces are refused; a non-normal extended spelling is NOT_LITERAL); the layout
  and identity are checked on the genuine native names (8.3 and case-equivalent spellings, junction components and
  long, extended, relative or Unicode spellings of the same release answer identically); a missing file is never
  created.
* Verification before any row: location, manifest, database bytes, schema, meta claims (labels, inputs, rules), every
  record's exact members and JSON types, the pinned key universe of every grain, every observation rule (keys, capture
  binding, ID grammars, uniqueness, kinds), the exact re-derivation of every qualification from its observation and
  witnesses, of every partition and file source from the pinned contract, of every core-row witness's identity and
  hashes and of the summaries and census, the content and database identity documents and the pinned profile.
  Witness integrity flags of person, mapping and legacy rows are build-time facts bound by the profile (the reader has
  no registry); a fully coordinated value forgery is refused only by the pinned profile.
