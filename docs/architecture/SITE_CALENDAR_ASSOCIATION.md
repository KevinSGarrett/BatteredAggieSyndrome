# National retrospective site/calendar association 2016-2023 (BAT-734, Cycle #63)

Bounded research contribution to BAT-417 (context inputs), BAT-419 (context correctness/eligibility) and BAT-423 (model
baselines) under TP63-A01. It does not complete any of them, BAT-171's learned hierarchical home-field/venue design,
BAT-182's broader schedule stress or BAT-418's mechanics/resources/lower-division priors.

## Authority and limits

Every record and answer is RETROSPECTIVE_RESEARCH, UNTRUSTED_SHADOW, PIT_NOT_ADMITTED, NOT_A_FORECAST, NOT_CALIBRATED and
predictive skill NOT_ESTABLISHED. The 2023 comparison is ALREADY_EXPOSED_RETROSPECTIVE_2023_NOT_BLIND, and the
complete-case support and the design were chosen with the full 2016-2023 source census (2023 included) in view and frozen
in the committed contract before any fit or metric. No champion, calibration, significance, causal site, rest or travel
claim follows. Adverse and null results are completed results; a numerical or integrity failure stays a failure.

* The agreed designated source site is a source-claim designation: the provider's neutral flag and bound home side must
  equal the accepted parent role. It is never a physical home field, stadium familiarity or causal bonus.
* A calendar interval is the date gap to the side's unique latest eligible accepted same-season prior (the accepted C39
  history pool). It is never physiological rest, actual travel or a count of every game played; excluded earlier inputs
  are counted, and those after the latest eligible prior are counted separately.
* The provider start is a scheduled claim checked against the accepted calendar date window [D-14h, D+36h) with no
  timezone inferred for D; never an actual kickoff. The eight provider captures were retrieved in August 2026, after
  every target; CFBD agreement is not independent upstream confirmation or historical first-known evidence.
* Whole-file hashing of the accepted parents reads their 2024/2025 bytes; no 2024/2025 target, feature, label, design,
  fit or score is selected or derived.

## Inputs (pinned by whole-file SHA-256 and bytes in the contract)

| Input | Accepted identity |
| --- | --- |
| C38 parent population (contest rows 2016-2023) and its run manifest | `3baff07f...` |
| C38 participant identity bindings | program season `711e9dfc...` |
| C39 history prefix (targets, both history views, eligible same-season priors) and run manifest | `aba0384f...` |
| C56 retrospective reference (features, labels, five parent game scores) and run manifest | `ad01a42f...` |
| Eight full FBS provider game captures 2016-2023 and their eight capture receipts | `raw/SRC-002/games/sha256_<sha>.json` |

## Derivation

1. **context-qualification** (5,875 records): unique accepted bindings of both participants, the sole documented provider
   game in its own season's capture with typed claims, the provider site claim beside the parent role and their
   agreement, the date window, each side's C56 history counts and latest-prior calendar block, the source clock, the label
   identity and the common-support state with every reason in a fixed order.
2. **context-feature** (11,750): `h = ell_A - ell_B`, `ell = log(2W+T+2) - log(2L+T+2)`; `s` = +1 / -1 / 0 for the agreed
   designated home of the view's team, of its opponent, or neutral; `c = interval_A - interval_B` (exact integers). View B
   is the exact negation of view A (negative zero normalized). Outside common support the design is null, never zero.
3. **context-parameter** (2): CTX-HISTORY-LOGIT-V1 on (h) and CTX-SITE-CALENDAR-LOGIT-V1 on (h, s, c), fitted on the
   common-support 2016-2022 games with decisive labels only: paired rows of weight 1/2, FIT-only RMS scales (no
   centering, the history scale shared), zero intercept, lambda 1 and the unchanged accepted
   `reference_fit.fit_logistic` (interface `BAS-REFERENCE-FIT-v56.1`). A fit failure is recorded and its model abstains.
4. **context-estimate** (23,500): every target, new model and orientation; B is the exact decimal complement of A.
5. **context-score** (41,125): 11,750 new A-oriented scores (exact rational Brier of the served probability, log loss with
   only its argument clipped to [1e-15, 1 - 1e-15]) and 29,375 unchanged C56 parent game-score witnesses (the exact
   accepted record and its line SHA-256; ridge margin-only).
6. **context-summary** (70): seven models over SEASON 2016..2023, PARTITION FIT and PARTITION COMPARISON, each on exactly
   the common-support games of its window. Only the CTX-SITE-CALENDAR-LOGIT-V1 row carries its delta to
   CTX-HISTORY-LOGIT-V1 on identical games; the primary result is that delta's Brier mean on the 2023 window.

## Release and reader

`<data>/canonical/national_site_calendar_association_2016_2023/sha256/<identity>/national_site_calendar_association.sqlite`
with its run manifest under `manifests/`; create-only and content addressed (an identical rebuild is
ALREADY_PRESENT_IDENTICAL, differing bytes REFUSED_IMMUTABLE_COLLISION). The SQLite file holds `meta` and one zlib block
per seasonal table and season (plus GLOBAL parameters, summary and census blocks). The reader needs no data root: it
verifies the location (BAT-717 literal policy and the native Windows spelling rule), the manifest, bytes, schema, meta
claims, every record's exact members and JSON types, every collection, every qualification rule the records can
re-derive, the frozen common cohort, the features, the parent witness binding, a fresh refit, every estimate, score,
summary and census record, the content and identity documents and the pinned canonical profile before serving.

Build: `python -B tools/cycle63/build_national_site_calendar_association.py --contract
configs/national_site_calendar_association_2016_2023_contract.json --data-root <data> --output-root ... --manifest-root
...` (order, chunk and interrupted/resumed checkpoint variants reproduce the same bytes). Contract and reader anchors:
`python -B tools/cycle63/make_site_calendar_contract.py` (source only, never a fit).

## Query

`bas-retrospective-baseline-query --context-association <database> --grain <grain>` (also
`python -m aggie_analytics.retrospective_baseline.query`). Invocations without the option keep their parsers, answers and
refusals byte for byte, the original `--help` included: TP63 allows one added help paragraph, but the accepted Cycle 61
test pins that help text exactly, so the allowance is not used; `--context-association <file> --help` describes the
mode.

| Grain | Selectors |
| --- | --- |
| context-qualification | season, partition, team (either participant), contest; no model |
| context-feature | season, partition, team (the view's team), contest; no model |
| context-parameter | model (the two new models only); no game selector |
| context-estimate | season, partition, team (the view's team), contest, model (the two new models) |
| context-score | season, partition, team (either participant), contest, model (all seven) |
| context-summary | season, partition, team, contest, model (all seven); re-derived over the selected games |

Refusals are exit 2 with `{"refused": CODE, "error": text}` on stderr, before any file access for every selection error,
in the frozen precedence of `context_association.PRECEDENCE`: ARGUMENT_INVALID, CONTEXT_PIT_NOT_ADMITTED,
CONTEXT_MODE_CONFLICT, TEMPORAL_FLAG_UNSUPPORTED / SELECTOR_NOT_APPLICABLE for --event, --orientation and --slice,
UNKNOWN_GRAIN, paging (LIMIT_INVALID, OFFSET_INVALID, NEGATIVE_LIMIT, NEGATIVE_OFFSET, PAGING_CONFLICT for --all with an
explicit --limit or --offset), MODEL_INVALID (an unknown model, an explicit empty one included), INVALID_SELECTOR
(malformed season, partition, team or contest, an explicit empty one included), SELECTOR_NOT_APPLICABLE (the
applicability matrix above) and STALE_CONTEXT_IDENTITY. A well-formed unknown or disjoint selection serves no row,
summaries included (`rows = []`); a well-formed season outside 2016-2023 is SEASON_OUTSIDE_RELEASE and an incompatible
season/partition pair SEASON_AND_PARTITION_DISJOINT, both with no row.
