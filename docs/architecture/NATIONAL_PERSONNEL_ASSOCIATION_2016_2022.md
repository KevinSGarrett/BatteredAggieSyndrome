# National posthoc personnel/history association 2016-2022

BAT-732 bounded research contribution to BAT-415, BAT-416 and BAT-423 (Cycle #61, TP61-A01). This is separately
authorized exploratory retrospective association research, `POSTHOC_ROSTER_ASSOCIATION_NOT_FORECAST`. It is not a
forecast, not PIT admitted, not calibrated, and it makes no predictive-skill, champion or causal personnel claim. It
does not complete BAT-415, BAT-416, BAT-423 or any forecast, availability, talent, transfer or coaching capability.

## Authority and time

The C59 season roster snapshots were observed in 2023 (source repository commit `2023-05-05T03:50:21Z`), after every
study game (the latest study contest is dated 2023-01-09). Target-season roster membership is therefore never pregame
knowledge. Every parent `target_game_feature_eligible`, `protected_eligible` and original-transition PIT flag stays
false and is carried unchanged. Every record carries `RETROSPECTIVE_RESEARCH`, `UNTRUSTED_SHADOW`, `PIT_NOT_ADMITTED`
and predictive skill `NOT_ESTABLISHED`; the release adds `NOT_CALIBRATED`, `NOT_A_FORECAST`, `NO_CHAMPION_SELECTED`,
`NO_CAUSAL_PERSONNEL_CONCLUSION` and `RETAIN_PROTECTED_LANE_BLOCKED`. 2021-2022 is an already-exposed retrospective
development comparison, never blind. No 2023 study row, score or fit exists. Adverse and null results are completed
results.

The research/data contract is `configs/national_personnel_association_2016_2022_contract.json`. It was committed before
the first real fit, prediction, score or canonical write. The reader (`aggie_analytics.retrospective_baseline.
personnel_association`) pins its SHA-256 through the generated `personnel_association_anchors` module and refuses any
drift.

## Inputs (read only, each verified by its accepted reader)

* The accepted C56 national retrospective reference release, verified with the accepted C39 history and C38 population
  databases it binds: its 2016-2022 feature records (the same-season, strictly earlier-date history counts with target
  exclusion and contributing-key lineage), its separately governed label records and the unchanged C47 fixed-model
  estimate records.
* The accepted C59 national personnel evidence release: its 1,760 program-season coverage records, 982 returning
  summaries and 5,867 components.

## Derivation

1. Qualification. Every C59 program-season is qualified exactly. FBS, FCS, qualified and unqualified chains are all
   included. A side joins only its own season's `<season>|org:<id>` program-season with `QUALIFIED_EXACT_CHAIN`. That
   program-season's own `returning_target_summary_key` must name a summary of the same target season and canonical
   team. Otherwise its state is `NO_SAME_SEASON_RETURNING_SUMMARY`, `CHAIN_NOT_QUALIFIED` or `SUMMARY_LINK_MISMATCH`;
   a study side with no program-season at all is `NO_PROGRAM_SEASON`. There are no fuzzy names, no name borrowing
   across seasons and no nearest-year fill. Retention (`returning/prior`), Jaccard (`returning/union`) and arrival
   (`arrival/current`) are recomputed from the integer set counts, both as Python float division and as exact
   rationals. The parent's stored rates must equal them. Signed passing, receiving and rushing yardage ratios and the
   count shares stay raw and unclipped, with their semantics; they are never model columns. Missing is null, never
   zero.
2. Features. Each of the 10,174 accepted target views takes both sides' history counts and contributing keys from the
   C56 feature record. It adds the smoothed history log-odds `ell = log(2W + T + 2) - log(2L + T + 2)` (the logit of the
   unchanged C47 `q`) and each side's roster block (null without a joinable summary). The A-minus-B history difference
   and three roster-rate differences follow, with the common-support state (both sides joinable). View B is the exact
   negation of view A.
3. Fits. The FIT cohort is the common-support 2016-2020 games with a decisive label. Each column's scale is
   `sqrt(fsum(0.5 * x * x) / N_fit_games)` over the paired A and B FIT rows. There is no centering; a zero scale is 1
   and marked constant. Both models share the history scale. Exactly two frozen zero-intercept lambda-1 L2 logistic
   fits use the accepted C56 `reference_fit.fit_logistic` unchanged: `POSTHOC_HISTORY_L2_V1` (history only) and
   `POSTHOC_HISTORY_ROSTER_L2_V1` (history plus the three roster-rate differences). Each game contributes its paired
   rows of weight 1/2. Comparison years never enter a fit, a scale or a constant. A genuine numerical failure is
   recorded as the parameter state, never as a successful or no-lift fit, and that model then abstains on every game
   (`ABSTAIN_FIT_FAILED`).
4. Estimates. Every target, model and orientation (40,696 expected) is built game grain first. `NULL_HALF_V1` is exactly
   1/2. `SMOOTHED_HISTORY_ODDS_V1` is the unchanged C47 exact rational, equal to the accepted C47 record. A fitted model
   serves its sigmoid as a decimal12 string. The reverse orientation is the exact complement. Outside common support
   all four models abstain (`ABSTAIN_OUTSIDE_COMMON_SUPPORT`).
5. Scores. There is one A-oriented score per target and model (20,348 expected). Brier is an exact rational of the
   served probability. Log loss clips only its argument to `[1e-15, 1 - 1e-15]` (`CLIPPED_LOG_ARGUMENT_1E-15`).
   Abstentions, ties and missing labels stay explicitly unscored.
6. Parameters and summary. The parameters record scales, coefficients, convergence, objective, gradient and trajectory.
   The summary has per-model rows by season and by `FIT`/`COMPARISON` partition, with descriptive differences on
   identical game keys. The primary difference is augmented minus history Brier mean on the pooled 2021-2022
   `COMPARISON` partition: negative means a lower descriptive Brier, zero equal and positive higher. No significance,
   bootstrap, calibration, champion, causal or predictive-skill conclusion follows. FIT-partition rows of the fitted
   models are fitted-data (in-sample) summaries.

## Consumer

```
bas-retrospective-baseline-query --personnel-association <data>/canonical/national_personnel_association_2016_2022/sha256/<id>/national_personnel_association.sqlite --grain personnel-summary --partition COMPARISON
```

Grains and selectors:

| Grain | Records | Selectors |
| --- | --- | --- |
| `personnel-qualification` | every program-season | `--season`, `--team` |
| `personnel-feature` | every target view | `--season`, `--team`, `--contest`, `--partition` |
| `personnel-estimate` | every target, model and orientation | `--season`, `--team`, `--contest`, `--model`, `--partition` |
| `personnel-parameter` | the four models | `--model` |
| `personnel-score` | every target and model | `--season`, `--team`, `--contest`, `--model`, `--partition` |
| `personnel-summary` | the summary rows and comparisons | `--season`, `--team`, `--contest`, `--model`, `--partition` |

An inapplicable selector is refused (`FILTER_NOT_APPLICABLE`), never ignored. Selectors intersect. An unknown or
disjoint valid selection serves zero rows. A team name resolves only within the season that carries it. At the summary
grain any game selector re-derives the rows and comparisons over exactly the selected games' verified score records
(`summary_selection`). Paging uses `--limit`, `--offset` and `--all`, with exact totals. `--require-pit` is refused
(`ASSOCIATION_PIT_NOT_ADMITTED`). Combining the option with `--database`, `--history-database`, `--reference-comparison`
or another explicit mode is refused (`ASSOCIATION_MODE_CONFLICT`).

The reader needs no data root. Before any row is served, it checks the literal local location (the BAT-717 policy for
the database and an explicit `--manifest`), the run manifest, the database bytes, the schema and meta claims, and every
record's exact members and JSON types. Malformed JSON (a lone surrogate, nesting beyond the decoder, a non-finite or
over-long number) is a controlled refusal. It also checks the complete expected collection of every grain, every
qualification and feature rule, a fresh refit, and the complete re-derivation of every estimate, score, parameter and
summary record. Last come the content document, the database identity document and the pinned canonical profile. Each
forgery is refused for its own cause.

The module is imported only when the option is named. Invocations without it keep their parsers, answers and refusals;
only the original parser's `--help` gains one paragraph naming the mode.

## Outputs and identity

* SQLite `national_personnel_association.sqlite` with `meta` and `blocks`: one zlib block of canonical JSON lines per
  record table and season (qualifications, features, estimates, scores), plus the global parameters and summary.
* It is written create-only and content addressed under
  `canonical/national_personnel_association_2016_2022/sha256/<id>/`, with its run manifest under `manifests/`. A
  rebuild of an identical release reports `ALREADY_PRESENT_IDENTICAL`; different bytes at an existing identity are
  `REFUSED_IMMUTABLE_COLLISION`.

The build is `tools/build_national_personnel_association.py`. Its reverse-order, shuffled, chunked and
interrupted-and-resumed variants reproduce every byte. The release's identities and counts are pinned in the anchors
module's canonical profile after the first canonical write, and recorded in
`artifacts/data_lake/national_personnel_association_2016_2022_gate.json`.
