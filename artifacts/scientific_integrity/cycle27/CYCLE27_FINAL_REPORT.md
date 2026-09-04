# Cycle 27 numbered final report

Revision: `C27-PREGAME-COACHING-20260904`
Issued: 2026-09-04T17:20:00Z (America/Chicago 12:20 PM)
Operator hold: **ACTIVE**. Merge unauthorized. Scientific Done unauthorized. Protected-lane remains `RETAIN_PROTECTED_LANE_BLOCKED`.

This is not a Cycle 26 restart. Predecessor C26 evidence, PR 678, and live sleepers were preserved.

## 1. Heads, PRs, CI

- Starting live capture head: `3fcc710438a75f15abc23392c6136ac077f25e7b` (scheduler push 2026-09-04T15:20:35Z).
- Review source head: `7e3e9cc2bb81d6dafe2903bd1b3dc0b316e42f82`.
- Base: `55e12a5aad3a7e843204fcba619c3cb3d3d6194d`.
- Stacked repair branch: `codex/BAT-690-c27-scr` based on `3fcc7104`, not on main.
- Pending PR 678: https://github.com/KevinSGarrett/BatteredAggieSyndrome/pull/678 — OPEN, capture owner, not amended in place.
- PR 654: untouched.
- Hosted Codex review green check on FAIL payloads is **not** acceptance (CONTROL-07).
- Ending stacked head is the commit on `codex/BAT-690-c27-scr` after this report's files are committed; do not treat an uncommitted worktree as a reviewed SHA.

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

Saturday T-24H capture issued 15:20:10Z before 16:00Z: **EVIDENCE_CAPTURED**, not FORECAST_FROZEN. Completed receipts stay completed.

Next action: Friday T-90M at 20:15Z for contest `6594366`. Then A&M T-24H at 22:15Z. Calendar waiting uses the existing sleepers and leases, not an unverified promise to check later.

## 4. Finding dispositions

See `artifacts/scientific_integrity/cycle27/CYCLE27_FINDING_DISPOSITION_MATRIX.json`.

Confirmed and repaired in the stacked branch (unmerged): CONTROL-01, 02, 03, 04, 05, 06; hold/review tests; failover policy in `src/aggie_analytics/operations/checkpoint_failover_policy.py`.

Confirmed and not hosted-fixed: CONTROL-07 masked Codex FAIL. Bootstrap prepared, not approved.

R26-22 remains **BLOCKED** (0 proven-PIT training rows). Pin successor semantically binds audit `e77195d8...` and does not accept mismatched `0070c1...`.

Ridge 80%/95% mismatch: new interval-label successor identities; predecessors not rewritten.

## 5. Data / feature authority

- Coaching staff: planned domain, `SOURCE_ABSENT` nationally, **NOT_CONSUMED** by the active five-candidate path. `coaches_poll_rank` is a poll ranking.
- A&M official coaches URL 404; roster page retrieved but JS-rendered titles were not extractable from raw HTML, so HC/OC/DC remain **UNKNOWN** (not NONE). Missouri State coaches page retrieved; titles remain titles, not play-callers.
- Current-contest binding helper is **not** consumed by the Week 1 materializer; C24 rows are copied and p/interval mutated.
- Weather is candidate-only. Roster/availability/recruiting/travel absent as consumed features.
- No market-line tuning. No Week 1 outcome training.

## 6. Candidate coverage and packets

C26 forecast gate `aa4ff84b...` / dataset `770d2544...` preserved (455/399).

Scoring predecessor gate `b5f20df4...` / dataset `1b1adb9e...` preserved (50 joined / 41 scored). Cycle 27 scoring successor gate `96478de8...` / dataset `6bfd9926...` uses a pinned input manifest; publication `UNTRUSTED_SHADOW`.

A&M 6607349 C26 ridge: P(home)≈0.89513, margin≈+22.2506, emitted interval label 0.95 vs declared 0.8. Trust `UNTRUSTED_SHADOW`. Control `national_base_rate` is a control, never a recommendation.

`independent_predicted_score = null` (`NO_ELIGIBLE_WEEK1_JOINT_SCORE_OR_TOTAL_CANDIDATE`). Market-line implied score withheld (`INCOMPATIBLE_SCORE_REFERENCE` / missing book identity). Captured focus quotes exist (count 2) with `INSUFFICIENT_MARKET_COVERAGE`; they are not a valid same-book spread+total pair.

Interim `PREGAME_RESEARCH_REPORT.md` is **not** T-24H or T-90M.

## 7. Tests and reproductions

Focused Cycle 27 modules: checkpoint lease, ledger, trusted-control protocol, scientific validators, coaching, pregame, scoring successor, R26-22 pin, dependency trace, ridge interval successor, scheduler adversarial. Cycle 26 adversarial regressions including CONTROL-07 masking tests remain green on this worktree.

Saved-pair independent validator no longer imports producer helpers. Invalid p=2/3 is not normalized to .4/.6.

Full mounted/unmounted/warnings-as-errors GitHub suite was not a prerequisite to preserving eligible raw evidence and is not claimed as a hosted merge gate here.

## 8. Jira

Local/live statuses preserved under the hold. No new BAT keys. Substantial C27 work grouped under BAT-690 (In Review). BAT-523 remains In Progress. No Cycle 26/27 completion comment.

## 9. Unfinished work / follow-up required

Do not read this as “no follow-up needed.”

1. Execute Friday T-90M at 20:15Z and A&M T-24H at 22:15Z under existing leases; publish only after exact receipt verification.
2. Hosted CONTROL-07 checker bootstrap still needs independent reviewer approval; until then hosted green FAIL remains non-acceptance.
3. R26-22 / primary fitted-path trust remains incomplete; keep UNTRUSTED_SHADOW.
4. Exact-head GitHub review of the stacked PR after freeze; later capture publication needs an explicit delta review.
5. National historical coaching acquisition and an eligible joint score model remain follow-on, not Week 1 prerequisites.
6. Merge remains blocked until explicit exact-scope user authorization, independent GitHub review, and required checks.

## 10. Non-claims

No BAS, champion, production, causal coaching effect, predicted final score, pre-market freeze, or protected 2024/2025 claim.
