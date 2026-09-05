#!/usr/bin/env python3
"""Refresh Cycle 27 packet reports from rematerialized ledger/scoring identities."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ART = REPO / "artifacts" / "scientific_integrity" / "cycle27"
OPS27 = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle27")
ISSUED = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
CHICAGO = timezone(timedelta(hours=-5))


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    dest = OPS27 / path.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")


def main() -> int:
    ledger = load(ART / "CYCLE27_CONTEST_CHECKPOINT_LEDGER.json")
    scoring = load(ART / "CYCLE27_WEEK1_OFFICIAL_FINAL_SCORING.json")
    postgame = load(ART / "CYCLE27_POSTGAME_RESIDUAL_METHODOLOGY.json")
    binding = load(ART / "CYCLE27_CURRENT_CONTEST_CHECKPOINT_BINDING.json")
    census = load(ART / "COACHING_DATA_AND_CONSUMPTION_CENSUS.json")

    packet = {
        "artifact_type": "CYCLE27_NATIONAL_CHECKPOINT_PACKET",
        "revision": "C27-PREGAME-COACHING-20260904",
        "issued_at_utc": ISSUED,
        "label": "EVIDENCE_AND_DISPOSITION_PACKET_NOT_T24H_NOT_T90M_FORECAST_FREEZE",
        "hold": "ACTIVE",
        "merge_authorized": False,
        "scientific_done_unauthorized": True,
        "universe_contest_count": ledger["contest_count"],
        "universe_source": (
            "artifacts/scientific_integrity/cycle27/CYCLE27_CONTEST_CHECKPOINT_LEDGER.json"
        ),
        "raw_collection_is_not_forecast_frozen": True,
        "early_week1_forecast_may_not_be_relabeled_t24_or_t90": True,
        "preserved_c26_forecast": {
            "gate_identity": "aa4ff84b16e9f00b1e68965cef7ea8730adc456ad16bda6ed1ff564b5bcdcb43",
            "dataset_identity": (
                "770d25449a89f55353749c8c1f920253a509adb42a336c9c0f9dfc7dd4143939"
            ),
            "checkpoint_label": "EARLY_WEEK1",
            "opportunities": 455,
            "non_null_forecasts": 399,
            "rewritten": False,
        },
        "saturday_t24h": {
            "state": "EVIDENCE_CAPTURED",
            "not": "FORECAST_FROZEN",
            "issued_at_utc": "2026-09-04T15:20:10Z",
            "cutoff_utc": "2026-09-04T16:00:00Z",
            "completed_before_cutoff": True,
            "completed_count": ledger["saturday_t24h_completed_count"],
            "receipt": "CYCLE26_SEP5_SATURDAY_T24H_FREEZE_RECEIPT",
            "publication_commit": "3fcc710438a75f15abc23392c6136ac077f25e7b",
            "later_cutoffs_do_not_inherit_this_receipt": True,
        },
        "t24h_state_counts": ledger["t24h_state_counts"],
        "t90m_state_counts": ledger["t90m_state_counts"],
        "focus_contest_6607349": {
            "kickoff_utc": "2026-09-05T23:00:00Z",
            "t24h_state": next(
                row["t24h_state"]
                for row in ledger["contests"]
                if row["ncaa_contest_id"] == "6607349"
            ),
            "t90m_state": next(
                row["t90m_state"]
                for row in ledger["contests"]
                if row["ncaa_contest_id"] == "6607349"
            ),
            "forecast_at_this_packet": (
                "PREDECESSOR_EARLY_WEEK1_UNTRUSTED_SHADOW_NOT_A_NEW_T24_FREEZE"
            ),
            "readable_report": (
                "artifacts/scientific_integrity/cycle27/PREGAME_RESEARCH_REPORT.md"
            ),
        },
        "current_contest_binding": {
            "binding_identity": binding.get("binding_identity"),
            "helper_call_count": binding.get("helper_call_count"),
            "contest_count": binding.get("contest_count"),
            "new_forecast_frozen_count": binding.get("new_forecast_frozen_count"),
        },
        "coaching_census_identity": census.get("census_identity"),
        "publication_label": "UNTRUSTED_SHADOW",
        "primary_trust_recovery": "PRIMARY_TRUST_RECOVERY_INCOMPLETE",
        "scoring_successor": {
            "gate_identity": scoring["gate_identity"],
            "dataset_identity": scoring["dataset_identity"],
            "scored_row_count": scoring["summary"]["scored_row_count"],
            "unique_scored_games": scoring["summary"]["unique_scored_games"],
            "rejected_receipt_before_kickoff_count": scoring["summary"][
                "rejected_receipt_before_kickoff_count"
            ],
            "reason": (
                "Pinned scoreboard HTML is not admitted from pin-field "
                "retrieved_at_utc. Independently hashed acquisition receipts are "
                "required; the current pin has none, so terminals stay rejected."
            ),
            "predecessor_preserved": {
                "gate": "b5f20df45d939d71e0b72b31ee558d87e0b696608816b1e56806c1ac09d4c27c",
                "dataset": (
                    "1b1adb9e3c7da9269ec176d4c7aa3029db00a2d35352623a6dd44f37c95b293b"
                ),
            },
        },
        "postgame_methodology_identity": postgame.get("methodology_identity"),
    }
    dump(ART / "CYCLE27_NATIONAL_CHECKPOINT_PACKET.json", packet)

    matrix = load(ART / "CYCLE27_FINDING_DISPOSITION_MATRIX.json")
    matrix["issued_at_utc"] = ISSUED
    for finding in matrix.get("findings") or []:
        if finding.get("id") == "TRACK_C_SCORING_SUCCESSOR":
            finding["gate_identity"] = scoring["gate_identity"]
            finding["dataset_identity"] = scoring["dataset_identity"]
            finding["scored_row_count"] = scoring["summary"]["scored_row_count"]
            finding["status"] = (
                "ISSUED_PINNED_MANIFEST_UNTRUSTED_SHADOW_ZERO_ADMITTED_TERMINALS"
            )
            finding["rejected_missing_retrieved_at"] = scoring["summary"][
                "rejected_receipt_before_kickoff_count"
            ]
            finding["pin_retrieved_at_is_not_acquisition_authority"] = True
            finding["acquisition_receipt_required"] = True
        if finding.get("id") == "SATURDAY_T24H_CAPTURE":
            finding["completed_count"] = ledger["saturday_t24h_completed_count"]
            finding["later_windows_not_covered_by_1520z_receipt"] = True
        if finding.get("id") == "A4_COACHING_CENSUS":
            finding["census_identity"] = census.get("census_identity")
            finding["canonical_bind_state_required"] = True
            finding["source_id_is_not_canonical"] = True
            finding["am_staff_packet"] = (
                "RETRIEVED_FOOTBALL_SCOPED_STAFF_DIRECTORY_CONTEXT_ONLY"
            )
            finding["missouri_staff_packet_frozen"] = True
            finding["play_caller_not_inferred"] = True
        if finding.get("id") == "HOSTED_CI_PR679":
            finding["reviewed_head"] = "b32c0cce9fcd78319667c8344daa878d2d968e06"
            finding["core_validation"] = "SUCCESS"
            finding["security_policy"] = "SUCCESS"
            finding["codecov_patch"] = "SUCCESS"
            finding["codex_review"] = "FAILURE_SCHEMA_VALID_FAIL_NOT_ACCEPTANCE"
            finding["status"] = "CORE_GREEN_CODEX_FAIL_ENFORCEMENT_NOT_MERGED"
    extra_findings = {
        "R27-P1-PIN-RETRIEVED-AT-NOT-ACQUISITION-AUTHORITY": {
            "id": "R27-P1-PIN-RETRIEVED-AT-NOT-ACQUISITION-AUTHORITY",
            "severity": "P1",
            "status": "CODE_FIXED_IN_STACKED_C27_NOT_MERGED",
            "result": (
                "Pin-field retrieved_at_utc is CALLER_SUPPLIED_TIME_NOT_"
                "ACQUISITION_AUTHORITY. Admission requires an independently hashed "
                "acquisition receipt bound to the HTML bytes."
            ),
        },
        "R27-P1-VALIDATOR-IMPORTS-PRODUCER-PARSER": {
            "id": "R27-P1-VALIDATOR-IMPORTS-PRODUCER-PARSER",
            "severity": "P1",
            "status": "CODE_FIXED_IN_STACKED_C27_NOT_MERGED",
            "result": (
                "Independent scoring validator reconstructs scoreboard cards "
                "from scientific_reference.ncaa_scoreboard_cards and forbids "
                "importing modeling.week_zero_official_final_scoring."
            ),
        },
        "R27-P1-EXACT-HEAD-REPORT-READBACK": {
            "id": "R27-P1-EXACT-HEAD-REPORT-READBACK",
            "severity": "P1",
            "status": "REPAIRED_POST_REVIEW_DELTA_NOT_MERGED",
            "reviewed_head": "b32c0cce9fcd78319667c8344daa878d2d968e06",
            "codex_verdict": "FAIL",
            "result": (
                "Codex FAIL on b32c0cce because the numbered report/readback bound "
                "the pack review-source instead of the CI head. This packet binds "
                "b32c0cce as the reviewed scientific head and refreshes the exact "
                "PR 679 check JSON. It is not merge acceptance."
            ),
        },
        "R27-P1-NEWER-INPROGRESS-RERUN": {
            "id": "R27-P1-NEWER-INPROGRESS-RERUN",
            "severity": "P1",
            "status": "CODE_FIXED_IN_STACKED_C27_NOT_MERGED",
            "result": (
                "Latest-head review gate sorts by started_at/completed_at recency "
                "and treats incomplete attempts without timestamps as latest, so a "
                "queued or in-progress rerun cannot hide behind an older success."
            ),
        },
    }
    by_id = {item.get("id"): item for item in matrix.get("findings") or []}
    for finding_id, payload in extra_findings.items():
        if finding_id in by_id:
            by_id[finding_id].update(payload)
        else:
            matrix.setdefault("findings", []).append(payload)
    dump(ART / "CYCLE27_FINDING_DISPOSITION_MATRIX.json", matrix)

    dimensions = load(ART / "CYCLE27_ACCEPTANCE_DIMENSIONS.json")
    dimensions["issued_at_utc"] = ISSUED
    for item in dimensions.get("dimensions") or []:
        if item.get("id") == 1:
            item["notes"] = (
                "91-contest ledger joined to verified C27 receipts. Saturday "
                "earliest cluster remains EVIDENCE_CAPTURED after cutoff "
                f"({ledger['saturday_t24h_completed_count']} contests). Later "
                "T-24H cutoffs do not inherit the 15:20Z receipt. Friday T90, "
                "A&M T24, and subsequent in-window T24 clusters are "
                "EVIDENCE_CAPTURED where receipts verify. Remaining T24/T90 "
                "clusters stay armed. No T24/T90 forecast freeze this packet."
            )
        if item.get("id") == 6:
            item["notes"] = (
                "C27 scoring successor unique games n="
                f"{scoring['summary']['unique_scored_games']} because pinned "
                "captures lack independently hashed acquisition receipts. C26 "
                "predecessor 41 scored rows are preserved and not rewritten. Week1 "
                "outcomes are not training/tuning data."
            )
    dump(ART / "CYCLE27_ACCEPTANCE_DIMENSIONS.json", dimensions)

    ops_preflight = OPS27 / "CYCLE27_PREFLIGHT_AND_OWNERSHIP.json"
    preflight = load(ops_preflight) if ops_preflight.is_file() else {}
    preflight["issued_at_utc"] = ISSUED
    preflight["revision"] = "C27-PREGAME-COACHING-20260904"
    preflight.setdefault("hold", {})["operator_hold"] = "ACTIVE"
    preflight.setdefault("live_owners", {})
    preflight["live_owners"]["friday_t90m_owner"] = "COMPLETED_EVIDENCE_CAPTURED"
    preflight["live_owners"]["am_t24h"] = "COMPLETED_EVIDENCE_CAPTURED_0400f8b0"
    preflight["live_owners"]["am_t90m"] = "ARMED_C26_PRIMARY_AND_FAILOVER"
    preflight["live_owners"]["watchdog"] = "T90_AND_T24_RESTART_NO_BACKFILL"
    preflight["live_owners"]["do_not_kill"] = True
    preflight["stacked_repair"] = {
        "worktree": str(REPO),
        "branch": "codex/BAT-690-c27-scr",
        "pr": "https://github.com/KevinSGarrett/BatteredAggieSyndrome/pull/679",
        "strategy": "STACKED_ON_PR678_DO_NOT_MUTATE_LIVE_CAPTURE_OWNER",
    }
    dump(ART / "CYCLE27_PREFLIGHT_AND_OWNERSHIP.json", preflight)

    replay = preflight.get("codex_fail_replay") or {}
    enforcement = {
        "artifact_type": "REVIEW_ENFORCEMENT_EVIDENCE",
        "issued_at_utc": ISSUED,
        "hold": "ACTIVE",
        "merge_authorized": False,
        "masked_fail_confirmed": replay.get("masked_fail_confirmed", True),
        "base_validator_sha256": replay.get("base_validator_sha256"),
        "base_treats_schema_valid_fail_as_success": True,
        "cases": replay.get("cases") or [],
        "cli": replay.get("cli") or [],
        "hosted_green_on_fail_is_not_acceptance": True,
        "trusted_control_bootstrap": "PREPARATION_NOT_APPROVED",
        "source": "ops/cycle27/CYCLE27_PREFLIGHT_AND_OWNERSHIP.json",
    }
    dump(ART / "REVIEW_ENFORCEMENT_EVIDENCE.json", enforcement)

    chicago = datetime.now(CHICAGO).strftime("%Y-%m-%dT%H:%M:%S")
    report = f"""# Cycle 27 numbered final report

Revision: `C27-PREGAME-COACHING-20260904`
Issued: {ISSUED} (America/Chicago {chicago})
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

Saturday earliest T-24H capture issued 15:20:10Z before 16:00Z: **EVIDENCE_CAPTURED** for that cluster ({ledger["saturday_t24h_completed_count"]} contests), not FORECAST_FROZEN. Later T-24H cutoffs do not inherit that receipt.

T24 states: {json.dumps(ledger["t24h_state_counts"], sort_keys=True)}.
T90 states: {json.dumps(ledger["t90m_state_counts"], sort_keys=True)}.

Next action: remaining Saturday T-90M clusters from 18:15Z, A&M T-90M wake 20:45Z Sep5, then T-24H 23:30Z Sep5 and Sun 23:30Z. Calendar waiting uses live sleepers, leases, and the watchdog, not an unverified promise to check later.

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

D2: C26 Week 1 materializer still copies C24 rows. Cycle 27 remaining-checkpoint binder **does** execute `build_current_contest_row` ({binding.get("helper_call_count")} calls / {binding.get("contest_count")} contests) and issues `ABSTAIN_SCIENTIFIC_TRUST_GATE_BLOCKED` / `UNTRUSTED_SHADOW`, not a new FORECAST_FROZEN.

## 5. Data / feature authority

- Coaching staff: planned domain, `SOURCE_ABSENT` nationally, **NOT_CONSUMED** by the active five-candidate path. `coaches_poll_rank` is a poll ranking.
- A&M official coaches URL remains blocked/wrong-resource; HC/OC/DC remain **UNKNOWN** (not NONE). Missouri State coaches page retrieved; titles remain titles, not play-callers.
- Current-contest helper is **not** consumed by the C26 Week 1 materializer. The Cycle 27 remaining-checkpoint binder consumes the helper without issuing a trusted forecast.
- Weather is candidate-only. Roster/availability/recruiting/travel absent as consumed features.
- No market-line tuning. No Week 1 outcome training.

## 6. Candidate coverage and packets

C26 forecast gate `aa4ff84b...` / dataset `770d2544...` preserved (455/399).

Scoring predecessor gate `b5f20df4...` / dataset `1b1adb9e...` preserved (50 joined / 41 scored). Cycle 27 scoring successor gate `{scoring["gate_identity"]}` / dataset `{scoring["dataset_identity"]}` admits **0** terminals because the pin has no independently hashed acquisition receipts (pin-field `retrieved_at_utc` is not acquisition authority). Publication `UNTRUSTED_SHADOW`. This is not a rewrite of the C26 scoring payloads.

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
"""
    report_path = ART / "CYCLE27_FINAL_REPORT.md"
    report_path.write_text(report, encoding="utf-8")
    shutil.copyfile(report_path, OPS27 / "CYCLE27_FINAL_REPORT.md")
    print(
        json.dumps(
            {
                "issued_at_utc": ISSUED,
                "scoring_gate": scoring["gate_identity"],
                "saturday_t24h_completed_count": ledger[
                    "saturday_t24h_completed_count"
                ],
                "t24h_state_counts": ledger["t24h_state_counts"],
                "t90m_state_counts": ledger["t90m_state_counts"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
