# Cycle 27 numbered final report

Revision: `C27-PREGAME-COACHING-20260904`
Issued: 2026-09-04T17:53:44Z (America/Chicago 2026-09-04T12:53:44)
Operator hold: **ACTIVE**. Merge unauthorized. Scientific Done unauthorized. Protected-lane remains `RETAIN_PROTECTED_LANE_BLOCKED`.

This is not a Cycle 26 restart. Predecessor C26 evidence, PR 678, and live sleepers were preserved.

## 1. Heads, PRs, CI

- Starting live capture head: `3fcc710438a75f15abc23392c6136ac077f25e7b` (scheduler push 2026-09-04T15:20:35Z).
- Review source head: `7e3e9cc2bb81d6dafe2903bd1b3dc0b316e42f82`.
- Base: `55e12a5aad3a7e843204fcba619c3cb3d3d6194d`.
- Stacked repair branch: `codex/BAT-690-c27-scr` based on `3fcc7104`, not on main.
- Pending PR 678: https://github.com/KevinSGarrett/BatteredAggieSyndrome/pull/678 — OPEN, capture owner, not amended in place.
- Stacked PR 679: https://github.com/KevinSGarrett/BatteredAggieSyndrome/pull/679 — OPEN, base `codex/BAT-690-c26-scr`.
- PR 654: untouched.
- Prior stacked head `8f16ca9dee02349f0f828f35831b5580fa5909c8` hosted core-validation/security-policy/codex-review **FAILURE**: unsealed Cycle 27 files, C26 report/watchdog dirty-hash mismatch inherited from `3fcc7104`, unclassified commit subjects, and numpy imports in core coaching/pregame tests.
- Repair packet head: `c9862b203ea4314bb807381bbbffc3810020276e` (this follow-up only binds that SHA; it does not predict the follow-up commit SHA).
- CONTROL-07: hosted green on FAIL remains not acceptance.

## 2. Hold and containment

- Hold remains ACTIVE. No merge, hold release, parent completion comment, champion/production/BAS claim, or protected-lane activation.
- Historical PR-671 release is not authority for PR 678 or Cycle 27.
- Trusted-control bootstrap is `PREPARATION_NOT_APPROVED`. This pack is not that approval.

## 3. Calendar and ownership

Durable owners (do not kill):

| Checkpoint | Wake UTC | Cutoff UTC | Owner |
| --- | --- | --- | --- |
| Friday T-90M contest `6594366` | 2026-09-04T20:15Z | 2026-09-04T21:00Z | primary 40708 / failover 41416; no git commit from sleeper |
| A&M T-24H contest `6607349` | 2026-09-04T22:15Z | 2026-09-04T23:00Z | primary 28372 / failover 27724 |
| A&M T-90M | 2026-09-05T20:45Z | 2026-09-05T21:30Z | primary 24528 / failover 32428 |
| Overnight heartbeat | running | n/a | 22176 |
| Git publication coordinator | after verified capture | n/a | CYCLE27_CURSOR_AGENT |

Saturday T-24H capture issued 15:20:10Z before 16:00Z: **EVIDENCE_CAPTURED** for the earliest Saturday cluster (10 contests), not FORECAST_FROZEN. Later T-24H cutoffs do not inherit that receipt.

T24 states: {"ABSTAINED_AT_CHECKPOINT": 4, "CAPTURE_IN_PROGRESS": 1, "EVIDENCE_CAPTURED": 11, "MISSED_CUTOFF_NO_BACKFILL": 20, "NOT_OPEN": 55}.
T90 states: {"ABSTAINED_AT_CHECKPOINT": 2, "CAPTURE_IN_PROGRESS": 19, "EVIDENCE_CAPTURED": 1, "MISSED_CUTOFF_NO_BACKFILL": 8, "NOT_OPEN": 61}.

Next action: Friday T-90M at 20:15Z for contest `6594366`. Then A&M T-24H at 22:15Z. Calendar waiting uses the existing sleepers and leases, not an unverified promise to check later.

## 4. Finding dispositions

See `artifacts/scientific_integrity/cycle27/CYCLE27_FINDING_DISPOSITION_MATRIX.json`.

Confirmed and repaired in the stacked branch (unmerged): CONTROL-01, 02, 03, 04, 05, 06; hold/review tests; failover policy in `src/aggie_analytics/operations/checkpoint_failover_policy.py`.

P1 containment this packet:

- Coaching census no longer stores unresolved source IDs as `canonical_team_id`.
- Saturday 15:20Z receipt covers only the 60-minute capture window of each contest cutoff.
- Official-final scoring rejects terminals without `retrieved_at_utc`.

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

Scoring predecessor gate `b5f20df4...` / dataset `1b1adb9e...` preserved (50 joined / 41 scored). Cycle 27 scoring successor gate `203436873d86589367f0b0bd324b8bde508cde8a28a5de7c85d9742ec3120d43` / dataset `0aadd884f7a56e11105bbefeaa9ca0c7edb5d7cd23401f7545afbc14248ca2ed` admits **0** terminals because pinned captures have `retrieved_at_utc=null`. Publication `UNTRUSTED_SHADOW`. This is not a rewrite of the C26 scoring payloads.

A&M 6607349 C26 ridge: P(home)≈0.89513, margin≈+22.2506, emitted interval label 0.95 vs declared 0.8. Trust `UNTRUSTED_SHADOW`. Control `national_base_rate` is a control, never a recommendation.

`independent_predicted_score = null` (`NO_ELIGIBLE_WEEK1_JOINT_SCORE_OR_TOTAL_CANDIDATE`). Market-line implied score withheld (`INCOMPATIBLE_SCORE_REFERENCE` / missing book identity).

Interim `PREGAME_RESEARCH_REPORT.md` is **not** T-24H or T-90M.

Postgame residual methodology is predeclared: prediction error `predicted-actual`, result residual `actual-predicted`. Repeated checkpoints are not independent games.

## 7. Tests and reproductions

See the commit that lands this packet for exact local counts. CONTROL-07: base checker still exits 0 on schema-valid FAIL for `7e3e9cc2` and `3fcc7104`; PR checker exits 1. Hosted green is not acceptance.

Saved-pair independent validator no longer imports producer helpers. Invalid p=2/3 is not normalized to .4/.6. Coaching/pregame modules no longer import numpy at module load.

Local `validate_repository.py --strict` with `AGGIE_ANALYTICS_DATA_ROOT` unset still falls back to the real lake and is not claimed as an unmounted run.

## 8. Jira

Local/live statuses preserved under the hold. No new BAT keys. Substantial C27 work grouped under BAT-690 (In Review). BAT-523 remains In Progress. No Cycle 26/27 completion comment.

## 9. Unfinished work / follow-up required

Do not read this as “no follow-up needed.”

1. Execute Friday T-90M at 20:15Z and A&M T-24H at 22:15Z under existing leases; publish only after exact receipt verification and an explicit delta review.
2. Hosted CONTROL-07 checker bootstrap still needs independent reviewer approval; until then hosted green FAIL remains non-acceptance.
3. R26-22 / primary fitted-path trust remains incomplete; keep UNTRUSTED_SHADOW. C26 materializer remains a C24 copy.
4. C27 scoring successor currently admits zero terminals until receipts carry post-kickoff `retrieved_at_utc`; do not invent timestamps.
5. Exact-head GitHub review of stacked PR 679 after this reseal; later capture publication needs an explicit delta review.
6. National historical coaching acquisition and an eligible joint score model remain follow-on, not Week 1 prerequisites.
7. Merge remains blocked until explicit exact-scope user authorization, independent GitHub review, and required checks.
8. Remaining Friday T90 clusters after 21:00Z and Saturday T90 national clusters still require dedicated owners before those windows.

## 10. Non-claims

No BAS, champion, production, causal coaching effect, predicted final score, pre-market freeze, or protected 2024/2025 claim.
