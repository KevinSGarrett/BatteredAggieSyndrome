# Fixed-profile C37 2026 availability source-assertion query (BAT-733)

Cycle #62 — Attempt #1 (TP62-A01). Package `aggie_analytics.availability_evidence`; console script
`bas-availability-evidence-query`; module `python -m aggie_analytics.availability_evidence.query`; governed contract
`configs/availability_evidence_2026_contract.json` (equal to `profile.render_contract()`).

## What it serves

A read-only query over the **existing** Cycle 37 corrected national release tables — nothing is acquired, parsed
again, refit or rematerialized, and no canonical store is created:

| Grain | Table | Population | Order |
|---|---|---:|---|
| `statement` | `availability_statement_successor` | 1,592 source-cell assertions (398 raw player rows x 4 status columns) | `availability_row_id` |
| `opportunity` | `availability_opportunity` | 3,474 retained schedule-record x program-side occurrences (3,220 business keys; 254 keys occur twice as byte-identical assertions) | `canonical_contest_id, team_id, side, original_sqlite_rowid` |
| `policy` | `availability_policy` | 13 retained policy observations | `policy_id` |
| `profile` | — | one coverage record: the exact fixed population and scope | singleton |

Every row returns `original_record` — every column of the original table row, in the original order, with JSON-text
columns strictly decoded and 0/1 Boolean columns served as false/true, every other value in its exact storage class —
beside a separate `qualification` object. Opportunity rows add `source_occurrence` = {database SHA-256, table,
original SQLite rowid}: it identifies each occurrence in the pinned database bytes and is never inserted into the
original record. Exact duplicate assertions are both served and never deduplicated; the opportunity table's 3,474
occurrences represent 1,737 retained schedule-record occurrences of 1,610 distinct game IDs (127 IDs occur twice).

Every response carries `HISTORICAL_SOURCE_AND_PARSER_ASSERTIONS_ONLY`, `FIXED_2026_CAPTURED_REPORT_OPPORTUNITY_SLICE`,
`availability_state_asserted=false`, `pit_admission=NOT_ADMITTED`, `model_feature_admission=NOT_ADMITTED`,
`healthy_default=false` and predictive skill `NOT_ESTABLISHED`. A source `Available`, a blank (`-`) cell, source
silence, roster presence or an empty query result is never a healthy or available player.

## Trust: one builtin profile

`C37_2026_AVAILABILITY_ASSERTIONS_V1` (`profile.PROFILE`) is the only trust authority: the database's whole-file
SHA-256 `757d4b5f…d331` and size, the three closed table schemas (ordered columns and permitted storage classes,
JSON/Boolean columns, keys and row counts), the frozen population and the five small report/posting witnesses at frozen
POSIX paths under the caller's `--data-root`:

| Witness | Role |
|---|---|
| `SEC_RAW_CAPTURE` | primary tab-separated report table (63 rows; locator `row[N]`) |
| `ACC_ARCHIVE`, `BIG12_ARCHIVE`, `BIGTEN_ARCHIVE` | primary rendered JSON report tables (218/54/63 rows; locator `rows[N]`) |
| `ACC_CURRENT_POSTING` | the later posting-view capture (one INITIAL REPORT card, three REPORT PENDING cards) |

`--database`, `--data-root` and `--grain` are required literal local inputs. No environment variable, manifest or
network location is consulted, and a missing file is never created. `--profile` accepts only the builtin profile;
`--expect-sha256` only adds a constraint and can never bless other bytes. The 31 roster and 13 policy witnesses and the
2026 schedule stay bound offline qualification inputs: they are not re-read at query time and their proof is labeled
`RETAINED_OFFLINE_EVIDENCE_NOT_PRESENT_QUERY_RAW_AUDIT`.

Verification order (each refusal for its own cause): network/device/namespace spellings refused before any filesystem
access (the BAT-717 literal-location core, so genuine relative, case, 8.3 short, junction, Unicode/special-character,
long and native extended-length local spellings of the same bytes are accepted, and the validated absolute location is
used for every file operation); the whole-file database SHA-256 (`DATABASE_IDENTITY_MISMATCH`) before the caller pin
(`EXPECTED_SHA256_MISMATCH`); each witness read once, verified and parsed from the same bytes; the closed schemas,
storage classes, keys, counts, contiguous rowids and strict decoding; a second whole-file hash after reading
(`INPUT_CHANGED_DURING_SESSION`); the re-derived population; the frozen rules and profile identities; and, once pinned
in `audit.py`, the qualified audit identity of the builtin profile's complete per-row qualification collection (an
internal injected synthetic profile is bound only by an audit identity passed with it). Qualification is computed from
the records in their pinned original SQLite rowid order, so occurrence ordinals, sibling lists, audit lines and the
re-derived population never depend on input order. A coordinated record/schema forgery always refuses first at the
whole-file anchor. Request refusals exit 2; input integrity failures
exit 3; both print `{"refused", "refusal_class", "error"}` on stderr.

## Qualifications (separate from the original records)

* `source_cell` — `VERIFIED_RETAINED_SOURCE_CELL` when the source digest, locator, stage, conference, retrieval
  observation, source URL, embedding page, raw Team/Date/Opponent/Number/Player, the stage cell and the presence all
  agree with the pinned witness coordinate; otherwise `DISPUTED_AGAINST_PINNED_WITNESS` with each conflicting field, the
  original kept unchanged. A raw `-` is `source_empty` whichever normalized form (null or the SEC `UNKNOWN`) the producer
  stored.
* `stage_time` `SOURCE_COLUMN_ONLY_PUBLICATION_INSTANT_UNKNOWN`; `effective_time` `EFFECTIVE_TIME_UNKNOWN`;
  `first_known` `FIRST_KNOWN_NOT_ESTABLISHED`; `pit` `NOT_ADMITTED`.
* `publication` — `SOURCE_POSTING_CLAIM_WITNESSED_IN_LATER_CAPTURE` for the 19 original claims matched to exactly one
  INITIAL REPORT entry (team column, jersey, player, status heading, game date, a weekday-consistent posted line whose
  US Eastern conversion equals the claim, a capture later than the claim), with the card/column/entry coordinate;
  `PUBLICATION_TIME_UNKNOWN` otherwise. A posting claim is never first-known time, a version seal or PIT permission.
* `identity` — `RETAINED_PARSER_IDENTITY_CLAIM` or the original `UNRESOLVED_*` reason; source-scoped IDs only, global
  person identity `NOT_QUALIFIED`. `contest` — `RETAINED_PARSER_CONTEST_CLAIM` or
  `CONTEST_NOT_QUALIFIED_SELF_OPPONENT`, independent of identity. `joint` keeps the 1,512 retained person+contest
  bindings, 40 person-unresolved and the separate 40 self-opponent assertions distinct. `quarantine_flag`
  `IDENTITY_ONLY_FLAG_NOT_WHOLE_ROW_QUALIFICATION`.
* Opportunities: occurrence multiplicity/siblings, `RETAINED_FIXED_AS_OF_DENOMINATOR_ASSERTION` (as of
  2026-09-23T10:45:16.941Z, not current coverage), the state meaning, the `statements_ingested` reconciliation with the
  statement table, and the policy foreign key with `POLICY_OBSERVATION_NOT_REPORT_COMPLETENESS_PROOF`.
* Policies: `POLICY_OBSERVATION_NOT_REPORT_COMPLETENESS_PROOF`, the original or unstated policy season, the absence-rule
  limit and the opportunity references.

## Selectors, paging and time

The applicability matrix is `RULES["selectors"]`; every supplied selector intersects the query or is refused
(`SELECTOR_NOT_APPLICABLE`). Text selectors are exact code-point matches (no substring, folding or alias:
`Texas A&M` never matches `East Texas A&M`). Malformed values are `INVALID_SELECTOR`; well-formed keys or names not
represented in the fixed profile are `KEY_NOT_IN_PROFILE`; foreign seasons are `SEASON_NOT_IN_PROFILE`; represented
selectors with an empty intersection answer `rows=[]`, `total_count=0` and an explicit `empty_match`. Paging (default
100, 1–1,000, offset within signed 64 bits, `--all` exclusive of explicit paging) applies after filtering; an offset
beyond the population keeps the exact total. `--cutoff <instant with offset>` (statement grain) compares the primary
capture observation, the later posting capture, the reported posting claim and the unknown effective/first-known times
with the cutoff (`BEFORE`/`AT`/`AFTER`/`UNKNOWN`) and filters nothing. `--as-of`, `--current`, `--latest`,
`--require-pit` and `--forecast-input` are always refused.

Input validation at the public boundary (C62-CONT-01, Cycle #62 — Work round #2 — FIRST REPAIR; no rule, profile,
audit or data change). A cutoff whose offset minutes exceed 59 (`+00:60` would otherwise be carried into the hours),
an invalid date or time, a trailing newline, and an instant whose UTC conversion leaves the representable range (year
1 with a positive offset, year 9999 with a negative one) are `INVALID_SELECTOR`, exit 2, before any input is read;
representable boundary instants (`0001-01-01T00:00:00Z`, `9999-12-31T23:59:59.999999Z`, year 1 with a negative or
year 9999 with a positive offset), offsets up to `±23:59` and fractions keep their exact UTC instant and clock
comparison. Every explicitly supplied `--as-of` value is refused as `AS_OF_STATE_NOT_SUPPORTED` (presence, not
truthiness: an empty value included), before any input is read; an absent option keeps the exact answers, and the
other temporal refusals, duplicate-option refusals and their precedence are unchanged. The program component of an
`OFFICIAL:<program>:<season>:<number>` person ID follows the LITERAL_TEXT character rule: a control character
(U+0000 to U+001F, U+007F) or a lone surrogate is `INVALID_SELECTOR` before any input is read (and before the season
check), while program spaces, other valid Unicode (non-BMP included), CFBD IDs, well-formed unknown keys
(`KEY_NOT_IN_PROFILE`) and inapplicable grains (`SELECTOR_NOT_APPLICABLE`) answer as before. NUL cannot be passed in
a Windows process argument, so that case is exercised through the public `main` with an access sentinel.

## Qualified audit pin and gate

The first real qualification (QUALIFY_SOURCE_ASSERTIONS run 20261020T154352516976Z at 5a86bf4b, after the contract
commit) observed the complete per-row qualification collection of the builtin profile: 5,079 canonical lines
(1,592 statement, 3,474 opportunity and 13 policy qualifications), SHA-256
`cf8975ae98f5b5a009b1ad825f86139631b7973f3f24032cd93cbdaf5ffef7d2`. `audit.py` pins exactly that identity (rules
digest, database digest, line count, line digest and qualification summary) without changing any rule, and the reader
recomputes the collection on every session and refuses one that differs (`QUALIFICATION_AUDIT_MISMATCH`).
`artifacts/data_lake/availability_evidence_2026_gate.json` records the same identities, the frozen population counts
and the labels; it carries no record body, raw source text, health, availability or PIT claim.
