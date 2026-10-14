# National retrospective reference comparison 2016-2023

BAT-423 bounded research contribution (Cycle #56, TP56-A01 revision 2026-10-14.1). This is research only: it is not a
forecast, not PIT admitted, and it makes no predictive-skill, calibration or champion claim. It does not complete
BAT-423, BAT-422, historical F1 or any other baseline family.

## What it is

One immutable, content-addressed comparison over the 5,875 accepted 2016-2023 FBS-versus-FBS targets of the BAT-711
history prefix, both orientations, and the 11,528 eligible prior-pool games. It keeps:

| Model | Kind | Fitted |
| --- | --- | --- |
| `NULL_HALF_V1` | C47 fixed constant 1/2 (records byte for byte) | no |
| `SMOOTHED_HISTORY_ODDS_V1` | C47 fixed smoothed record odds (records byte for byte) | no |
| `SITE_BLIND_ELO_REFERENCE_V1` | season Elo, 1500 start, K 20, base 10, scale 400, no site bonus, no offseason carry | no |
| `PAIRED_ZERO_INTERCEPT_L2_LOGISTIC_V1` | zero-intercept L2 logistic win probability | 2016-2022 only |
| `PAIRED_ZERO_INTERCEPT_RIDGE_MARGIN_V1` | zero-intercept ridge expected margin (no probability) | 2016-2022 only |

The 788 targets of 2023 are an already-exposed, out-of-fit development comparison, never a blind test. 2024 and 2025
are not untouched protected data; no 2024, 2025 or 2026 outcome is read.

The research contract is `configs/national_retrospective_reference_2016_2023_contract.json`; the reader
(`aggie_analytics.retrospective_baseline.reference`) pins its SHA-256 and refuses any drift.

## Inputs

* The accepted history prefix (C39), verified through the accepted C47 loader: targets, views, target labels and
  pool-member exclusions, plus its protected out-of-scope payload (keys and seasons only).
* The accepted C38 parent population database, verified through the accepted population reader; only its 2016-2023
  contest rows are selected. The seven frozen BAT-711 predicates applied to them must reproduce the history's pool key
  for key (FBS, FCS, outside-division opponents and 2020 spring games included).
* The accepted C47 benchmark, at build time only: its estimate and label lines must equal the reference's copies byte
  for byte, and the old/new target keys must agree exactly.

## Derivation

1. Each side's prior record is rederived from the parent rows: every pool game of that organization in the same
   season label dated strictly before the target date, with key, date, role, opponent, contemporaneous division label
   and points. It must equal the accepted history view exactly.
2. Side features: games played, win rate `(2W + T) / (2G)`, points-for, points-against and margin means. A rate of a
   cold start is missing: value 0 plus indicator 1. The design is five team-minus-opponent value differences and five
   missing-indicator differences; the B row is the exact negation.
3. Elo processes each pool game once. All games of one date use the start-of-date ratings and their updates
   (`math.fsum` per organization) apply after the date. A target's estimate precedes its own date's updates.
4. Fits use only the 2016-2022 targets. Columns are scaled by their training root-mean-square (no centering, a zero
   scale uses 1). Each game contributes its A and B rows with weight 1/2.
   * Logistic: mean weighted cross-entropy plus `(1/2) sum(beta^2)`, Newton from zero with the C37 deterministic
     partial-pivot solve, halving backtracking (at most 30) until the objective does not increase, converged at a
     gradient infinity norm of at most 1e-10 within 100 steps. A failure is recorded, never accepted.
   * Ridge: mean weighted squared margin error divided by two plus `(1/2) sum(beta^2)`, solved from its normal
     equations with a residual of at most 1e-8.
   The fit interface is `aggie_analytics.retrospective_baseline.reference_fit`. The accepted C37, BAT-655 and BAT-693
   modules, gates and outputs are unchanged.
5. Estimates serve one canonical game-grain value rounded half-even to 12 decimals and its exact decimal complement
   (probability) or negation (margin). Training-sample learned estimates are `IN_SAMPLE_TRAINING_NOT_A_LABEL_ANCHOR`;
   2023 learned estimates are `OUT_OF_FIT_EXPOSED_2023`.
6. Scores: one A-oriented record per target and model. Brier uses the served probability. Log loss clips only its
   logarithm argument to `[1e-15, 1 - 1e-15]` (`CLIPPED_LOG_ARGUMENT_1E-15`). Ridge has absolute and squared margin
   errors.
7. Summary: slices `NATIONAL`, `TEXAS_AM` (org:697 on either side), `FIRST_FOUR_TEAM_GAMES` (either side has fewer than
   four prior games) and `COLD_START` (either side has none), each by season, development partition and pooled scope.
   The four probability families are compared on identical game keys, with fixed decile calibration tables. The ridge
   reports MAE, MSE and RMSE in its own scope. Descriptive model-minus-null differences are included. Empty scopes have
   null means; adverse and null results are kept.

## Consumer

```
bas-retrospective-baseline-query --reference-comparison <data>/canonical/national_retrospective_reference_2016_2023/sha256/<id>/national_retrospective_reference.sqlite --history-database <accepted history sqlite> --population-database <accepted parent sqlite> --grain reference-summary --slice TEXAS_AM --season 2023
```

Grains: `reference-feature`, `reference-estimate`, `reference-parameter`, `reference-score` and `reference-summary`.
Filters: `--season`, `--team`, `--contest`, `--model`, `--partition` and, on the summary only, `--slice`. Paging uses
`--limit`, `--offset` and `--all`, with exact totals. An unknown valid key returns zero rows; `--require-pit` is refused.
Before any row is served, the reader re-derives every record (the refit included) and the content and database
identities. Each forgery is refused for its own cause. Invocations without the option keep their bytes.

## Outputs and identity

* Payloads `features.jsonl.gz`, `estimates.jsonl.gz`, `labels.jsonl.gz`, `parameters.jsonl.gz`, `scores.jsonl.gz`
  and `summary.json`.
* SQLite `national_retrospective_reference.sqlite` with `meta` and `blocks`: one zlib block per record table and
  season, plus the global parameters and summary.
* Both are written create-only and content addressed under
  `canonical/national_retrospective_reference_2016_2023/sha256/<id>/`, with run manifests under `manifests/`.

The build is `tools/build_national_retrospective_reference.py`. Its reverse-order, shuffled, chunked (1, 17 and 257)
and interrupted-and-resumed variants reproduce every byte.
