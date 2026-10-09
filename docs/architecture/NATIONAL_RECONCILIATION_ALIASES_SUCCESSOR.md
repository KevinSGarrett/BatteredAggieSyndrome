# National reconciliation alias successor, 2024-2025 (BAT-720)

Cycle #48 — Attempt #1. Governing plan TP48-A01 revision 2026-10-09.1 sections 1-6. Contract:
`configs/national_reconciliation_aliases_2024_2025_contract.json` (committed before the first canonical write).

The accepted BAT-718 sidecar (`national_population_reconciliation_2024_2025`, contract
`BAT-718-NATIONAL-POPULATION-RECONCILIATION-2024-2025-V1`) leaves 107 one-to-one relations unpromoted because 108
participant sides of 16 programs have no documented name link between the NCAA name and the provider name. This
successor is an explicitly selected, immutable, content-addressed successor of that sidecar. It is rebuilt from the
same verified parent and cached inputs plus one finite bundle of retained institutional evidence. Only a verified,
season-scoped source assertion can add a name link. Unsupported cases stay unpromoted with their recorded reason.
It never changes the parent, V1, any default view or any acceptance, and it establishes neither independent historical
truth, PIT availability nor forecasting skill.

## Inputs

| Input | Role |
| --- | --- |
| Parent query database, crosswalk, registry, both provider captures and receipts | exactly the V1 bindings (same SHA-256s), read under the parent's data root |
| Alias evidence bundle `<data>/canonical/national_reconciliation_aliases_2024_2025/sha256/<bundle>/` | `alias_assertions.json` plus one deterministic gzip body per retained document, with its manifest |

The reader pins the successor contract (SHA-256 and contract id), the parent and cached inputs, the evidence bundle
identity and the assertions SHA-256, and the predecessor V1 identities. The evidence bundle is read under the
successor's own population root (the directory that holds the selected successor database).

## The finite alias universe

The universe is exactly the set of relation participants whose V1 name link is `NO_DOCUMENTED_NAME_LINK`, keyed by
NCAA organization, bound provider team and season (`org:<id>|cfbdteam:<id>|<season>`). Each row names the exact NCAA
and provider names observed there and one disposition:

* `SUPPORTED` names exactly one assertion, proved from retained bytes (below).
* `UNSUPPORTED` names no assertion, a reason, and the documents that were examined.

An omitted, extra or duplicated row, a row whose names differ from the observed names, and a row for a season in which
the provider never observed the program (for example a 2025-only provider) are refused (`ALIAS_UNIVERSE_MISMATCH`,
`ALIAS_ASSERTION_INVALID`). Every assertion is used by exactly one supported row.

## What proves an assertion

An assertion binds organization, provider team, season, both exact names, the institution name and its official
athletics domain, and its witnesses. Every witness is an exact locator into one retained document body:

* `DELIMITED_FIELD`: the complete text between an opening delimiter (`"`, `'` or `>` ending its recorded prefix) and its
  closing delimiter (`"`, `'` or `<` starting its suffix), optionally HTML-entity decoded. A value inside a larger
  field (a substring) is refused (`ALIAS_WITNESS_NOT_DELIMITED`).
* `JSON_PATH`: an embedded JSON element (between `>` and `<`) or a whole JSON document, and a path to one member.
  `devalue` paths dereference index members of a devalue (Nuxt) payload.

The prefix, value and suffix must be byte-identical at the recorded offsets (`ALIAS_WITNESS_MISMATCH` otherwise).
Each document carries its capture receipt: a hop chain of redirects ending in HTTP 200, exact URLs and a UTC retrieval
instant (`ALIAS_EVIDENCE_RECEIPT_INVALID`). A supported assertion needs:

1. **Institution and official site** — one NCAA organization record served only by NCAA hosts
   (`ncaa.org`, `www.ncaa.org`, `stats.ncaa.org`, `web3.ncaa.org`) whose single JSON object names the organization id,
   the institution name and an athletics website whose host is the official domain or its `www.` form; an optional
   NCAA program name must equal the NCAA name (`ALIAS_INSTITUTION_UNPROVEN`, `ALIAS_DOMAIN_UNPROVEN`).
2. **Season and exact name** — one official season document whose every hop stays on that host family, whose
   requested path ends with the season (`2024`, `2024-25` or `2024-2025`), with a season witness and a program-name
   witness equal to the provider name (`ALIAS_DOMAIN_UNPROVEN`, `ALIAS_SEASON_UNPROVEN`, `ALIAS_NAME_UNPROVEN`). The
   only equivalence an assertion may declare is `APOSTROPHE_FORMS` (`'`, `‘`, `’`, `ʻ`, `ʼ` are one character); it
   never deletes or adds a character, and declaring it without using it is refused.

Schedules, scores, dates, numeric id coincidence, edit distance, global punctuation stripping and substrings are never
alias authority. Names of other programs (USC/South Carolina, Southern/Georgia Southern) cannot satisfy an assertion
keyed by another organization and provider team.

## Records

The parent, provider and alias-disposition records are derived exactly as in V1 except the name link of a universe
participant: it carries `alias_assertion` (`key`, `disposition`, `assertion_id`, `reason`), and a supported row whose
exact names are the observed names makes it `SOURCE_ASSERTION_DOCUMENTED`, which verifies the participant. Every
comparison, candidate, relation and field conflict is computed exactly as without the evidence, so V1's conflicts stay
visible; records outside the universe are byte-identical to V1's. The summary adds `alias_universe` (program-seasons,
dispositions, linked and unsupported sides, promoted relations). `alias_dispositions.jsonl` (and the
`alias_disposition` table) hold one record per universe row with its assertion, documents and the sides it applies to.

## Materialization and identity

Content: `canonical/national_reconciliation_aliases_2024_2025/sha256/<content identity>/{parent_reconciliation.jsonl,
provider_reconciliation.jsonl, alias_dispositions.jsonl, summary.json}`. Database:
`…/sha256/<database identity>/national_reconciliation_aliases.sqlite` (tables `meta`, `parent_reconciliation`,
`provider_reconciliation`, `alias_disposition`). Evidence: `…/sha256/<bundle identity>/`. Manifests under
`manifests/national_reconciliation_aliases_2024_2025/sha256/<identity>/run_manifest.json`. Every identity is the
SHA-256 of its canonical JSON identity document; identity documents are compared as canonical bytes. Materialization is
create-only; natural, reversed and shuffled input orders, any chunk size and an interrupted and resumed checkpoint
build give identical bytes.

## Reading it

```
bas-national-population-query --database <accepted parent> \
  --reconciliation <...>\national_reconciliation_aliases_2024_2025\sha256\<id>\national_reconciliation_aliases.sqlite \
  --grain parent-reconciliation [--season S] [--team T] [--contest C] [--disposition D] [--limit N --offset K | --all]
```

The same command (or `python -m aggie_analytics.national_population.query`) serves both grains with V1's filters and
paging, plus `alias_universe`, `alias_summary`, `alias_evidence` and `predecessor`. Before any row is served the reader
verifies location, manifest identity, bytes, schema, meta claims, the parent, every cached input, the evidence bundle
and every assertion, then re-derives every record, the summary and both identity documents. Any other
`--reconciliation` location is read by the V1 reader exactly as before. Until the reader pins a committed successor
contract it refuses every successor (`ALIAS_SUCCESSOR_NOT_PINNED`). `--require-pit` is always refused.

Non-claims: no PIT or known-at authority (retrieval time is not publication time, and a season document's current
rendering is not proof of in-season usage beyond what it shows), no independent historical truth, no protected
evaluation, no forecasting skill, no default activation.
