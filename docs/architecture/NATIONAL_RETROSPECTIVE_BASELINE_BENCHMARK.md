# National retrospective baseline benchmark (BAT-719)

Cycle #47 — Attempt #1, TP47-A01 revision 2026-10-09.1. Contract:
`configs/national_retrospective_baseline_2016_2023_contract.json` (pinned by SHA-256 in
`aggie_analytics.retrospective_baseline.benchmark.ANCHORS`).

## What it is

A fixed, games-only **retrospective** baseline and its null comparison over every accepted 2016–2023 national FBS
target of the BAT-711 history prefix: 5,875 targets (733, 753, 766, 769, 524, 767, 775 and 788 by season), 11,750
oriented views, 23,500 oriented model estimates, 5,875 separately classified labels and 11,750 game-grain scores.

Every record carries `RETROSPECTIVE_DATE_ORDER_ONLY_NOT_PIT_NOT_SKILL`. Calendar order is not publication time, so
nothing here is PIT eligible, a forecast, calibrated uncertainty or evidence of predictive skill. A correct
unfavourable or null comparison is a complete result; no minimum improvement is required.

## Inputs and authority

Only the accepted history-prefix database (targets, history views, target labels, exclusions), read through the
accepted history reader's full verification and pinned to its identities, plus the history's own `out_of_scope.jsonl`
payload, which names the protected 2024/2025 canonical contests by key and season only. No ranking, venue, market,
held matrix, fitted weight, contaminated prediction or metric is read. A contest named by the protected payload is
refused wherever it appears, whatever season label it carries (actual canonical membership outranks labels).

Partitions follow `governance/PROTECTED_SPLIT_REGISTRY.csv` (SHA-256 bound): SPLIT-DEV-HIST 2016–2022 and
SPLIT-DEV-SEL 2023. 2024–2025 (protected) and 2026+ (forward) never enter. 2020 and postseason games keep their
parent season labels.

## Derivation (each step reads only what it names)

1. **Features** — per target and view, each side's accepted same-season strictly earlier-date games G, wins W,
   losses L and ties T, the exact contributing contest keys and the retained excluded inputs with reasons. Before use
   the accepted counts are re-verified: JSON integers only (a boolean or `1.0` is not an integer), nonnegative,
   W + L + T = G, contributing contests numbering G, each an accepted same-season pool contest of that team dated
   strictly before the target and never the target itself, results consistent with points, the contributing set equal
   to every accepted pool contest of that team dated before the target, cold start exactly when G = 0, mirror-image
   views, mirrored contributions and no protected key.
2. **Estimates** — from the features and the frozen models only, at game grain in A orientation, then both oriented
   rows (p_B = 1 − p_A exactly). No label is in scope.
   * `NULL_HALF_V1`: p_A = p_B = 1/2.
   * `SMOOTHED_HISTORY_ODDS_V1`: q = (W + T/2 + 1)/(G + 2) per side;
     p_A = q_A(1 − q_B) / (q_A(1 − q_B) + q_B(1 − q_A)). A cold start gives q = 1/2 and is flagged; the target stays.
   Nothing is fitted, tuned, calibrated or selected; there is no home bonus. Exact rationals in lowest terms plus a
   12-place half-even decimal display.
3. **Labels** — from the accepted target-label table only: DECISIVE (y = 1 when A wins, 0 when A loses), TIE,
   MISSING or UNSUPPORTED. A label that contradicts the points the accepted history later counts for the same contest
   is a refused input.
4. **Scores** — one A-oriented record per target and model: Brier (p_A − y)² as an exact rational and log loss
   −[y ln p_A + (1 − y) ln(1 − p_A)] as the `repr()` of the binary64 value. Ties, missing and unsupported labels stay
   explicit UNSCORED records with their reason; mirrored rows are never scored.
5. **Summary** — per model, for each season, each development partition and pooled 2016–2023: population, scored and
   unscored denominators (by reason), Brier totals and means (exact), log-loss totals (`math.fsum` in canonical order)
   and means, cold-start counts, and a descriptive smoothed-minus-null difference. No p-value, interval, calibration
   or skill claim.

## Storage and identity

Content stage (`canonical/national_retrospective_baseline_2016_2023/sha256/<content id>/`): `features.jsonl.gz`,
`estimates.jsonl.gz`, `labels.jsonl.gz`, `scores.jsonl.gz` (deterministic gzip, no file name, mtime 0) and
`summary.json`. Database stage (`.../sha256/<database id>/national_retrospective_baseline.sqlite`): `meta` plus one
`blocks` row per (record table, season) holding the season's canonical JSONL lines as a zlib block with its record
count, first and last key and the SHA-256 of the uncompressed lines. Per-season blocks keep the database about a
tenth of a row-per-record layout, so the coordinated forgery family fits the issued storage allocation.

Identities are the SHA-256 of canonical JSON identity documents (`sort_keys`, `(",", ":")` separators, UTF-8);
documents are compared as canonical bytes, so `13` and `13.0` are different documents. Materialization is
create-only; an existing identity is verified and never rewritten. Builds are byte-identical under reversed or
shuffled inputs, checkpoint chunks of 1, 17 or 257 targets and an interrupted then resumed build (CPython 3.12.10,
SQLite 3.49.1, zlib 1.3.1).

## Consumer

`bas-retrospective-baseline-query` and `python -m aggie_analytics.retrospective_baseline.query` with an explicit
`--database` (the benchmark) and `--history-database` (the accepted history); never a default. Before serving, the
reader verifies and pins the history, verifies the benchmark location, manifest, bytes, schema and meta claims, and
re-derives every record, the summary, the content identity and the contract-defined database identity document;
each difference is refused with its own stable code (exit 2, `{"refused": ...}` on stderr). Grains: `feature`,
`estimate`, `score`, `summary`; filters `--season`, `--team` (org key, digits or a team name of the record's own
season), `--contest`, `--model`, `--partition`; exact totals with `--limit`/`--offset`/`--all`. Filters intersect: on
the summary grain `--season` with `--partition` selects that season's rows when the contract split places the season
in that partition and nothing otherwise, and `--partition` alone selects the partition's rows. `--require-pit` is
always refused. BAT-717 literal read-only SQLite locations apply (long and extended-length Windows paths); a missing
database is never created. The five accepted query commands are unchanged.
