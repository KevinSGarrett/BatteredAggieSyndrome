# Cycle 27 numbered final report

Revision: `C27-PREGAME-COACHING-20260904`
Issued: 2026-09-05T15:51:51Z (America/Chicago 2026-09-05T10:51:51)
Operator hold: **ACTIVE**. Merge unauthorized. Scientific Done unauthorized. Protected-lane remains `RETAIN_PROTECTED_LANE_BLOCKED`.

This is not a Cycle 26 restart. Predecessor C26 evidence, PR 678, and live sleepers were preserved.

## 1. Heads, PRs, CI

- Starting live capture head: `3fcc710438a75f15abc23392c6136ac077f25e7b` (scheduler push 2026-09-04T15:20:35Z).
- Pack review-source head (PR 678 lineage): `7e3e9cc2bb81d6dafe2903bd1b3dc0b316e42f82`.
- Canonical main base for that lineage: `55e12a5aad3a7e843204fcba619c3cb3d3d6194d`.
- Live capture owner PR 678 head: `0d099bd9303ecc77fefa8dbec0cde761aa9db6af` (A&M T-24H evidence, `forecast_frozen=false`).
- Stacked merge on PR 679: `b44c013a54087bf4325c7e93a408c7c6ae26b935` parents `17380c22` and `0d099bd9`. This packet is a post-merge classification/report bind and does not invent a self-referential SHA for the commit that lands it.
- Exact-head reviewed stacked scientific head: `b32c0cce9fcd78319667c8344daa878d2d968e06`. Later heads are explicit deltas.
- Stacked repair branch: `codex/BAT-690-c27-scr` stacked on live `codex/BAT-690-c26-scr`, not on main.
- Pending PR 678: https://github.com/KevinSGarrett/BatteredAggieSyndrome/pull/678 — OPEN, capture owner, not amended in place.
- Stacked PR 679: https://github.com/KevinSGarrett/BatteredAggieSyndrome/pull/679 — OPEN, base `codex/BAT-690-c26-scr`, mergeable after stacking `0d099bd9`.
- PR 654: untouched (OPEN, MERGEABLE BEHIND, unrelated).
- Hosted `repository-ci` on `b44c013a` **FAILURE**: `CONSECUTIVE_PROCESS_ONLY_LIMIT_EXCEEDED` because the merge subject used `[process]` while bringing the A&M T-24H receipt. Exact-commit historical correction classifies that merge as `[material]`. Product-adapter SUCCESS. CodeQL SUCCESS. `codex-review` was IN_PROGRESS at bind time.
- CONTROL-07: base checker still masks FAIL as success. Trusted-control bootstrap is `PREPARATION_NOT_APPROVED`.

## 2. Hold and containment

- Hold remains ACTIVE. No merge, hold release, parent completion comment, champion/production/BAS claim, or protected-lane activation.
- Historical PR-671 release is not authority for PR 678 or Cycle 27.
- Trusted-control bootstrap is `PREPARATION_NOT_APPROVED`. This pack is not that approval.

## 3. Calendar and ownership

Durable owners (do not kill):

| Checkpoint | Wake UTC | Cutoff UTC | Owner |
| --- | --- | --- | --- |
| Friday T-90M / T-24H clusters already bound | in-window | passed | C27 receipts under `ops/cycle27/receipts/`; do not duplicate |
| A&M T-24H contest `6607349` | 2026-09-04T22:15Z | 2026-09-04T23:00Z | **DONE** EVIDENCE_CAPTURED `0400f8b0…`; not FORECAST_FROZEN |
| Remaining T-24H clusters | armed | 01:00Z–23:30Z Sep5 and Sun 23:30Z | `run_t24h_cluster_capture.ps1` + watchdog T24 restart |
| Earliest Saturday T-90M | 2026-09-05T13:45Z | 2026-09-05T14:30Z | `run_t90m_cluster_capture.ps1` contest `6590890` |
| Remaining Sat/Sun/Mon T-90M | armed | through Mon 22:00Z | armed clusters + watchdog; skip Sat 21:30Z national duplicate |
| A&M T-90M contest `6607349` | 2026-09-05T20:45Z | 2026-09-05T21:30Z | C26 primary + failover; C27 binds after verified capture |
| Overnight heartbeat | running | n/a | `run_cycle26_overnight_heartbeat.ps1` |
| Cluster watchdog | running through 2026-09-08T00:00Z | n/a | T90 + T24 restart; no backfill |
| Git publication coordinator | after verified capture | n/a | CYCLE27_CURSOR_AGENT |

Saturday earliest T-24H capture issued 15:20:10Z before 16:00Z: **EVIDENCE_CAPTURED** for that cluster (10 contests), not FORECAST_FROZEN. Later T-24H cutoffs do not inherit that receipt.

T24 states: {"ABSTAINED_AT_CHECKPOINT": 6, "CAPTURE_IN_PROGRESS": 3, "EVIDENCE_CAPTURED": 46, "MISSED_CUTOFF_NO_BACKFILL": 36}.
T90 states: {"ABSTAINED_AT_CHECKPOINT": 2, "CAPTURE_IN_PROGRESS": 43, "EVIDENCE_CAPTURED": 26, "MISSED_CUTOFF_NO_BACKFILL": 8, "NOT_OPEN": 12}.

Next action: remaining Saturday T-90M clusters from 17:00Z, A&M T-90M wake 20:45Z Sep5, then T-24H 23:30Z Sep5 and Sun 23:30Z. Calendar waiting uses live sleepers, leases, and the watchdog, not an unverified promise to check later.

## 4. Finding dispositions

See `artifacts/scientific_integrity/cycle27/CYCLE27_FINDING_DISPOSITION_MATRIX.json`.

Confirmed and repaired in the stacked branch (unmerged): CONTROL-01, 02, 03, 04, 05, 06; hold/review tests; failover policy in `src/aggie_analytics/operations/checkpoint_failover_policy.py`.

P1 containment this packet:

- Coaching census no longer stores unresolved source IDs as `canonical_team_id`.
- Saturday 15:20Z receipt covers only the 60-minute capture window of each contest cutoff.
- Official-final scoring admits terminals only from independently hashed acquisition receipts; pin-field `retrieved_at_utc` is not acquisition authority.

Confirmed and not hosted-fixed: CONTROL-07 masked Codex FAIL. Bootstrap prepared, not approved.

R26-22 remains **BLOCKED** (0 proven-PIT training rows). Pin successor semantically binds audit `e77195d8...` and does not accept mismatched `0070c1...`.

Ridge 80%/95% mismatch: new interval-label successor identities; predecessors not rewritten.

D2: C26 Week 1 materializer still copies C24 rows. Cycle 27 remaining-checkpoint binder **does** execute `build_current_contest_row` (182 calls / 91 contests) and issues `ABSTAIN_SCIENTIFIC_TRUST_GATE_BLOCKED` / `UNTRUSTED_SHADOW`, not a new FORECAST_FROZEN.

## 5. Data / feature authority

- Coaching staff: planned domain, `SOURCE_ABSENT` nationally, **NOT_CONSUMED** by the active five-candidate path. `coaches_poll_rank` is a poll ranking.
- A&M official coaches URL remains blocked/wrong-resource; HC/OC/DC remain **UNKNOWN** (not NONE). Missouri State coaches page retrieved; titles remain titles, not play-callers.
- Current-contest helper is **not** consumed by the C26 Week 1 materializer. The Cycle 27 remaining-checkpoint binder consumes the helper without issuing a trusted forecast.
- Weather is candidate-only. Roster/availability/recruiting/travel absent as consumed features.
- No market-line tuning. No Week 1 outcome training.

## 6. Candidate coverage and packets

C26 forecast gate `aa4ff84b...` / dataset `770d2544...` preserved (455/399).

Scoring predecessor gate `b5f20df4...` / dataset `1b1adb9e...` preserved (50 joined / 41 scored). Cycle 27 scoring successor gate `e5ae2490f7aed35f443deab91684355043eef6cf5b4fb2db81819a0a70264aa4` / dataset `4fedbdc265a458ba03c72d77e3ff5fbf9b5c6cd9e3e4ed4d6feb2c54c530c49c` admits **0** terminals because the pin has no independently hashed acquisition receipts (pin-field `retrieved_at_utc` is not acquisition authority). Publication `UNTRUSTED_SHADOW`. This is not a rewrite of the C26 scoring payloads.

A&M 6607349 C26 ridge: P(home)≈0.89513, margin≈+22.2506, emitted interval label 0.95 vs declared 0.8. Trust `UNTRUSTED_SHADOW`. Control `national_base_rate` is a control, never a recommendation.

`independent_predicted_score = null` (`NO_ELIGIBLE_WEEK1_JOINT_SCORE_OR_TOTAL_CANDIDATE`). Market-line implied score withheld (`INCOMPATIBLE_SCORE_REFERENCE` / missing book identity).

Interim `PREGAME_RESEARCH_REPORT.md` is **not** T-24H or T-90M.

Postgame residual methodology is predeclared: prediction error `predicted-actual`, result residual `actual-predicted`. Repeated checkpoints are not independent games.

## 7. Tests and reproductions

Candidate-head `b32c0cce` (`BAT-690-c27-head`, that checkout's `src` first on PYTHONPATH):

- Cycle 27 discover `test_cycle27_*.py`: 96 OK (PYTHONHASHSEED=0 and 1).
- Official-final scoring: 14 OK, including pin-only time rejected as `CALLER_SUPPLIED_TIME_NOT_ACQUISITION_AUTHORITY`.
- Hold: 12 OK. Review-gate: 6 OK, including newer in-progress rerun over older success.
- Failover policy: 22 OK. Trusted-control protocol: 9 OK. Execution-focus: 10 OK.
- Independent scoring validator on rematerialized pin: PASS, 0 findings.
- Mounted critical suite twice with no repo writes: 35/35 identical PASS both runs. Committed mounted-acceptance gate validator: PASS.
- Jira control-plane `--strict --require-live`: PASS, 0 findings.
- Full mounted unittest discover: **3300 tests, skipped=51, OK** in 757.786s.
- Scoring tests under `python -W error`: 14 OK.
- Hosted PR 679 at `b32c0cce`: core-validation ubuntu+windows SUCCESS; security-policy SUCCESS; codecov/patch SUCCESS. `codex-review` FAILURE with schema-valid FAIL (P1: stale report/readback vs bound head). PR checker exit 1 is enforcement, not masked success.
- CONTROL-07: base checker still exits 0 on schema-valid FAIL for `7e3e9cc2` and `3fcc7104`; hosted green on FAIL is not acceptance.

Saved-pair independent validator no longer imports producer helpers. Invalid p=2/3 is not normalized to .4/.6. Independent scoreboard reconstruction no longer imports `modeling.week_zero_official_final_scoring`.

Local `validate_repository.py --strict` with `AGGIE_ANALYTICS_DATA_ROOT` unset still falls back to the real lake and is not claimed as an unmounted run.

## 8. Jira

Local/live statuses preserved under the hold. No new BAT keys. Substantial C27 work grouped under BAT-690 (In Review). BAT-523 remains In Progress. No Cycle 26/27 completion comment.

## 9. Unfinished work / follow-up required

Do not read this as “no follow-up needed.”

1. Remaining T-24H clusters after 00:00Z and all T-90M clusters including A&M 21:30Z remain owned by live sleepers plus the watchdog; bind C27 receipts after each verified capture; do not duplicate or backfill.
2. Hosted CONTROL-07 checker bootstrap still needs independent reviewer approval; until then hosted green FAIL remains non-acceptance.
3. R26-22 / primary fitted-path trust remains incomplete; keep UNTRUSTED_SHADOW. C26 materializer remains a C24 copy.
4. C27 scoring successor currently admits zero terminals until independently hashed acquisition receipts exist; do not invent timestamps or treat pin-field time as authority.
5. Exact-head Codex review of `b32c0cce` is FAIL (P1 report/readback disagreement repaired in a post-review delta). Later capture publication needs an explicit follow-on exact-head review; do not invent a self-referential SHA.
6. National historical coaching acquisition and an eligible joint score model remain follow-on, not Week 1 prerequisites.
7. Merge remains blocked until explicit exact-scope user authorization, independent GitHub review, and required checks.
8. A&M T-90M readable packet is issued only after that window is actually met; the T-24H evidence report is not a T-90M freeze.

## 10. Non-claims

No BAS, champion, production, causal coaching effect, predicted final score, pre-market freeze, or protected 2024/2025 claim.
