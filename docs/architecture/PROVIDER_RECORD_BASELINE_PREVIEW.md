# Provider-record baseline preview (BAT-724)

Cycle #52 — Attempt #1. Governing plan: TP52-A01 revision 2026-10-11.1 sections 1–6. Contract:
`configs/provider_record_baseline_preview_20261011_contract.json` (`BAT-724-PROVIDER-RECORD-BASELINE-PREVIEW-20261011-V1`).
Reader: `aggie_analytics.retrospective_baseline.preview`. Builder: `tools/build_provider_record_baseline_preview.py`.

## What it is and is not

One immutable, content-addressed JSON preview that connects the accepted BAT-723 provider observation (the retained
ESPN scoreboard response of 2026-10-11 for games the provider scheduled on 2026-10-17: 25 events and their 50 participant
overall records) to a deterministic fixed calculation. It is served only through the existing
`bas-retrospective-baseline-query` console and `python -m aggie_analytics.retrospective_baseline.query`, explicitly
selected with `--prospective-preview <preview.json>`. It holds 50 source-bound participant features, 25 game-grain rows
and 100 oriented estimates (25 events x 2 fixed models x 2 sides) with complete support and abstention accounting.

Every output is `PROVIDER_RECORD_BASELINE_PREVIEW_NOT_FORECAST`, `PIT_NOT_ADMITTED`,
`PREDICTIVE_SKILL_NOT_ESTABLISHED` and `NOT_CALIBRATED`. It is an illustrative fixed calculation: not a genuine issued
or frozen pregame forecast, not a baseline trained on historical PIT inputs, not a protected evaluation and not a
betting recommendation. The provider's reported counts are claims, not reconstructed game histories; opponent strength
and the completeness of a team's underlying history are not established, and national coverage is UNKNOWN. Historical
milestone F1 (5875 accepted 2016–2023 targets) remains unmet; BAT-423 remains the broader baseline milestone.

## Models

Nothing is fitted, tuned, calibrated or chosen after results; there is no home advantage, margin, score or interval.

- `PROVIDER_PREVIEW_NULL_HALF_V1`: p_home = p_away = 1/2. It reads no record but still needs supported event and
  participant identity.
- `PROVIDER_RECORD_SMOOTHED_ODDS_PREVIEW_V1`: q_X = (W_X + T_X/2 + 1)/(G_X + 2) from side X's own provider-reported
  overall/total record (G = W + L + T); p_home = q_home(1-q_away) / (q_home(1-q_away) + q_away(1-q_home));
  p_away = 1 − p_home exactly. It reuses only the accepted C47 pure arithmetic (`benchmark.strength_q`,
  `smoothed_probability`, `decimal_text`); no C47 model identity, label, score or database is read. A supported 0-0
  record is a labelled cold start (q = 1/2).

The model identities are distinct from the C47 historical models (`NULL_HALF_V1`, `SMOOTHED_HISTORY_ODDS_V1`): the
inputs here are provider-reported counts, not reconstructed histories.

## Support and abstention

Estimates are built at game grain in home orientation and derived into both orientations. A missing, ambiguous or
unsupported input never becomes a zero; the affected model abstains with `{input, team_key, reason, detail}`:

| Reason | Effect |
| --- | --- |
| `EVENT_UNSUPPORTED_IN_CAPSULE` (detail: the capsule event reason) | both models abstain |
| `EVENT_SEASON_NOT_IN_SCOPE` | both models abstain |
| `ROLE_UNRESOLVED`, `ROLE_PARTICIPANT_NOT_BOUND` | both models abstain |
| `PARTICIPANT_IDENTITY_UNSUPPORTED` (detail: the capsule participant reason) | both models abstain |
| `RECORD_UNSUPPORTED` (detail: the capsule record reason), `RECORD_COUNTS_INVALID` | the smoothed model abstains |
| `EVENT_NOT_PRE_GAME_AT_OBSERVATION` (the record may already contain the target game) | the smoothed model abstains |

The genuine accepted capsule currently supports all 25 comparisons; the counts are derived, never hardcoded.

## Authority and layout

Authority is the accepted capsule — verified completely by the accepted reader
`prospective.verify_capsule` against the capsule identity, file hash and observation-contract pin the preview contract
names — plus the committed preview contract, whose SHA-256 the reader pins (`preview.CONTRACT_SHA256`; a test requires
it to equal the committed file and its models, labels, numeric contract, reasons and fields to equal the code).

```
canonical/provider_record_baseline_preview_20261011/sha256/<preview identity>/
    preview.json                          canonical preview document
    inputs/contract.json                  byte copy of the committed preview contract
    capsule/<capsule identity>/...        byte copy of the accepted capsule directory (capsule.json + 4 bundle members)
manifests/provider_record_baseline_preview_20261011/sha256/<preview identity>/run_manifest.json
```

The preview directory is portable (no manager directory or the original capsule root is needed), so a rehoused copy
serves identically, including at long and extended-length (`\\?\`) Windows locations. No other file may be present.
`preview.json` is canonical JSON (`sort_keys`, compact separators, UTF-8, no NaN) plus one LF; its top-level members are
exactly `schema, population, contract, input, models, numeric_contract, labels, bundle, features, games, estimates,
summary, counts`. The identity document is exactly `schema, population, contract_id, contract_sha256, preview_file,
preview_sha256, bundle`; the preview identity is the SHA-256 of its canonical bytes. Before any row is served the reader
re-derives the complete expected preview from the verified capsule and the contract and compares canonical bytes field
family by field family (integer, float and boolean differ), checks the exact bundle membership and recomputes the
identity; the build clock lives only in the run manifest.

## Query

```
bas-retrospective-baseline-query --prospective-preview <preview.json> --grain preview-estimate
    --cutoff 2026-10-12T00:00:00Z [--season 2026] [--event espn:event:<id>] [--team espn:team:<id>]
    [--model <preview model>] [--orientation home|away] [--limit 50] [--offset 0] [--all]
```

- `--cutoff` is required and matched as a whole string (seconds and an explicit zone; a trailing newline is refused).
  Before the retained request start the preview is refused (`PREVIEW_UNAVAILABLE_BEFORE_OBSERVATION`); within the
  request interval it is refused (`PREVIEW_INDETERMINATE_WITHIN_OBSERVATION`); at or after its end the same retained
  snapshot is served. Equivalent offsets agree; a later cutoff never refreshes the snapshot or creates a forecast time;
  the current clock is never read. `--require-pit` is always refused (`PREVIEW_PIT_NOT_ADMITTED`).
- Filters are conjunctive: feature (season, event, team, orientation = side), estimate (season, event, team, model,
  orientation), summary (season, event, team, model). An inapplicable filter refuses (`FILTER_NOT_APPLICABLE`), a
  malformed key, model or orientation refuses; an unknown valid key serves no rows; another season is `NOT_YET_AUDITED`.
- `preview-summary` reports per model the exact distinct events of the selected game set (two orientations are not two
  games), their features and estimates, supported/abstained games and estimates and abstention reasons.
- Combining the mode with `--database`, `--history-database` or `--manifest` is `PREVIEW_MODE_CONFLICT`; `--contest`
  and `--partition` are `FILTER_NOT_APPLICABLE`. Without `--prospective-preview` the original parser handles the
  invocation, so every existing answer and refusal is byte-identical; only `--help` gains an epilog naming the mode.
- Network and device locations are refused before access; a missing file is never created.
