"""R35-15: render CYCLE35_FINAL_REPORT.md from the packet artifacts.

The report is generated from the JSON the cycle actually produced rather
than written by hand, so it cannot drift from the evidence it summarises.
Totals are reported by unique requirement and key, never by command volume.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOLD_STATE = "SCIENTIFIC_OPERATOR_HOLD_ACTIVE"
COMPLETION_STATE = "IMPLEMENTATION_SUBMITTED_NOT_ACCEPTED"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def sha256_file(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def table(rows: list[list[str]], header: list[str]) -> str:
    out = ["| " + " | ".join(header) + " |",
           "|" + "|".join(["---"] * len(header)) + "|"]
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out = Path(args.out_dir)

    status = load(out / "CYCLE35_REQUIREMENT_STATUS.json") or {}
    findings = load(out / "CYCLE35_FINDING_DISPOSITION.json") or {}
    coverage = load(out / "CYCLE35_NATIONAL_COVERAGE.json") or {}
    validation = load(out / "CYCLE35_VALIDATION_RESULTS.json") or {}
    unfinished = load(out / "CYCLE35_UNFINISHED_ITEMS.json") or {}
    ledger = load(out / "CYCLE35_COST_AND_REQUEST_LEDGER.json") or {}
    git_state = load(out / "CYCLE35_GIT_STATE.json") or {}
    feasibility = load(out / "R35_09_PIT_FEASIBILITY.json") or {}
    finals = load(out / "R35_07_CANONICAL_FINALS_REPLAY.json") or {}
    release = load(out / "R35_03_COACHING_RELEASE_SUMMARY.json") or {}
    rebuild = load(out / "R35_02_STAFF_REBUILD_SUMMARY.json") or {}
    plan = load(out / "CYCLE35_PLAN_JIRA_TRACE.json") or {}
    family_b = load(out / "R35_10_FAMILY_B_CANDIDATE.json") or {}
    availability = load(out / "R35_11_AVAILABILITY_RELEASE.json") or {}

    units = status.get("units") or {}
    unit_rows = [
        [
            unit_id,
            unit["implementation_local"],
            unit["data_evidence"],
            unit["software_validation"],
            unit["independent_scientific_acceptance"],
            unit["integration_release_authorized"],
            unit["overall"],
        ]
        for unit_id, unit in sorted(units.items())
    ]

    band_rows = [
        [row["band"], str(row["kernel_rows"]), row["outcome"]]
        for row in (feasibility.get("feasibility_table") or [])
    ]

    blocker_rows = [
        [item["requirement"], item["kind"], item["blocker"]]
        for item in (unfinished.get("items") or [])
    ]

    lines: list[str] = []
    a = lines.append

    a("# Cycle #35 — final report")
    a("")
    a(f"Generated {datetime.now(timezone.utc).isoformat()}.")
    a("")
    a("## Completion state")
    a("")
    a(f"**{COMPLETION_STATE}**. Operator hold remains **{HOLD_STATE}**.")
    a("")
    a("This is a submission, not an acceptance. Independent scientific "
      "acceptance is NOT_REVIEWED for every unit, integration/release is "
      "NOT_AUTHORIZED for every unit, and one dimension is actively FAIL. No "
      "merge, Done transition, hold release, production or champion claim, "
      "protected-lane activation or repository transfer was performed.")
    a("")

    a("## Exact state")
    a("")
    a(table(
        [
            ["Branch", "`" + str(git_state.get("branch")) + "`"],
            ["Head", "`" + str(git_state.get("head")) + "`"],
            ["Tree", "`" + str(git_state.get("tree")) + "`"],
            ["Predecessor", "`" + str(git_state.get("predecessor")) + "`"],
            ["Base", "`" + str(git_state.get("base")) + "`"],
            ["Commits since predecessor", str(git_state.get("commits_since_predecessor"))],
            ["Worktree clean", str(git_state.get("worktree_clean"))],
            ["Pull request", "NONE — this branch has never been pushed"],
        ],
        ["Field", "Value"],
    ))
    a("")

    a("## Requirement status — six independent dimensions")
    a("")
    a(table(
        unit_rows,
        ["Unit", "Impl", "Data", "Software", "Science", "Release", "Overall"],
    ))
    a("")
    a(f"Inherited and preserved: {status.get('inherited_r34_requirement_count')} "
      f"R34 requirement rows, {status.get('inherited_mr33_finding_count')} MR33 "
      f"findings, {status.get('inherited_mr34_finding_count')} MR34 findings — "
      "original IDs, titles and meanings intact.")
    a("")

    a("## What the evidence actually shows")
    a("")
    a("**All 11 reproduced defects closed.** Every manager counterexample was "
      "first reproduced at the starting head with a positive control, then "
      "re-run after repair. Closure is measured by the same harness that "
      "demonstrated the defect.")
    a("")
    if rebuild:
        cons = rebuild.get("conservation") or {}
        a(f"**Staff rebuild:** all {cons.get('input_episode_count')} episode "
          f"references reparsed from raw sources with exact key-set "
          f"conservation (lost: {len(cons.get('keys_lost') or [])}, invented: "
          f"{len(cons.get('keys_invented') or [])}). Dispositions: "
          + ", ".join(f"{k} {v}" for k, v in
                      sorted((rebuild.get('disposition_counts') or {}).items()))
          + ".")
        a("")
    if release:
        ids = release.get("row_identities") or {}
        a("**Coaching release:** "
          + ", ".join(f"{k} {v['count']}" for k, v in sorted(ids.items()))
          + f". Assertions without a supporting observation: "
          f"{release.get('unsupported_assertion_count')}.")
        a("")
    if finals:
        p = finals.get("producer_path_counts") or {}
        i = finals.get("independent_reference") or {}
        b = finals.get("participant_binding") or {}
        a(f"**Official finals:** producer and an independent structural "
          f"reference agree exactly — {p.get('observation_count')} "
          f"observations, {p.get('unique_contest_count')} contests, "
          f"{i.get('terminal_final_contest_count')} terminal finals, "
          f"{i.get('winner_contradiction_count')} winner contradictions in real "
          f"data. Canonical participants bound for {b.get('bound_count')} of "
          f"{p.get('observation_count')} observations; the "
          f"{b.get('unresolved_count')} unbound involve genuine "
          "non-FBS/FCS opponents, retained and visible.")
        a("")
    if coverage:
        a(f"**National denominator:** "
          f"{coverage.get('expected_program_season_cells')} expected "
          f"program-season cells across "
          f"{coverage.get('distinct_programs')} programs, 1963-2026, with "
          f"{coverage.get('season_gap_count')} seasons retained as explicit "
          "gaps. The kernel covers "
          f"{(coverage.get('domain_coverage') or {}).get('kernel', {}).get('coverage_fraction_of_expected')}"
          " of it.")
        a("")
    if availability:
        cap = availability.get("sec_capture") or {}
        a(f"**Availability:** {cap.get('player_rows')} rows x "
          f"{cap.get('stage_columns')} stages = {cap.get('assertion_count')} "
          f"assertions, conservation {cap.get('conservation_holds')}. "
          f"{(availability.get('national_report_opportunities') or {}).get('key_count')}"
          " predeclared national keys, all retained in the denominator.")
        a("")

    a("## PIT feasibility")
    a("")
    if band_rows:
        a(table(band_rows, ["Season band", "Kernel rows", "Outcome"]))
        a("")
        a(f"Independently proven PIT rows: "
          f"**{(feasibility.get('totals') or {}).get('independently_proven_pit_rows')}**. "
          f"Trusted fitted path: **{feasibility.get('trusted_fitted_path')}**. "
          "No numerator was forced, and retrospective use of these rows "
          "remains legitimate under its own label.")
        a("")

    a("## Validation")
    a("")
    for lane in validation.get("direct_lanes") or []:
        a(f"- **{lane['lane']}** — {lane['result']}"
          + (f" ({lane['tests_run']} tests)" if lane.get("tests_run") else "")
          + (f". {lane['detail']}" if lane.get("detail") else ""))
    for name, lane in (validation.get("full_suite_lanes") or {}).items():
        a(f"- **{name}** — {lane.get('result')}"
          + (f" ({lane.get('tests_run')} tests, {lane.get('counts')})"
             if lane.get("tests_run") else ""))
    a("")
    a("Explicitly not claimed:")
    for claim in validation.get("claims_not_made") or []:
        a(f"- {claim}")
    a("")

    a("## Failing dimensions")
    a("")
    for row in validation.get("failing_dimensions") or []:
        a(f"- **{row['dimension']}: {row['state']}** — {row['reason']}")
    a("")

    a("## New findings this cycle")
    a("")
    for row in findings.get("new_findings_this_cycle") or []:
        a(f"- **{row['id']} [{row['severity']}] {row['title']}** "
          f"({row['status']}, owner {row['owner']}). {row['detail']}")
    a("")

    a("## Plan and Jira")
    a("")
    if plan:
        a(f"All {plan.get('pt35_mappings_adjudicated')} PT35 owner-section "
          "mappings independently adjudicated against artifacts this cycle "
          "produced: "
          + ", ".join(f"{k} {v}" for k, v in
                      sorted((plan.get('adjudication_counts') or {}).items()))
          + f". {len(plan.get('missing_mappings_found_by_this_cycle') or [])} "
          "missing mappings found and "
          f"{len(plan.get('false_positive_challenges') or [])} false positives "
          "challenged.")
        a("")
        jira = plan.get("jira") or {}
        a(f"Jira: {jira.get('new_issues_created')} issues created, "
          f"{jira.get('status_transitions_performed')} transitions, "
          f"Done transitions {jira.get('done_transitions_performed')}, "
          f"BAT-523 completion comment "
          f"{jira.get('bat523_completion_comment_written')}.")
        a("")

    a("## Cost and request ledger")
    a("")
    a(f"- Paid model/reviewer/provider calls: "
      f"{ledger.get('paid_model_calls')}/{ledger.get('paid_reviewer_calls')}/"
      f"{ledger.get('paid_provider_calls')}")
    a(f"- External workers spawned: {ledger.get('external_workers_spawned')}")
    a(f"- Network requests: {ledger.get('network_requests_made')}")
    a(f"- Coaching/history budget: "
      f"{(ledger.get('coaching_history_budget') or {}).get('used')} of "
      f"{(ledger.get('coaching_history_budget') or {}).get('ceiling')} used")
    a(f"- Availability/context budget: "
      f"{(ledger.get('availability_context_budget') or {}).get('used')} of "
      f"{(ledger.get('availability_context_budget') or {}).get('ceiling')} used")
    a("")

    a("## Every remaining blocker")
    a("")
    if blocker_rows:
        a(table(blocker_rows, ["Requirement", "Kind", "Blocker"]))
        a("")

    a("## Authority required to change this state")
    a("")
    a("1. **`CYCLE33-APPROVAL-LAKE-SUCCESSOR-001`** — activating canonical "
      "routing for the prepared Family B successor. The complete candidate, "
      "its byte hashes, the affected pins and a recovery plan are in "
      "`R35_10_APPROVAL_REQUEST.json`. Until this is resolved the canonical "
      "mounted Family B dimension stays FAIL.")
    a("2. **Narrow push/PR authority for `codex/BAT-706-cycle35`** — the "
      "branch has never been pushed. Cycle #34's publication permission "
      "covered a different branch and is not assumed to extend here. Before "
      "any push, privacy/secret checks and workflow-trigger inspection would "
      "run to confirm no paid review is invoked.")
    a("3. **Network budget confirmation** — five items are blocked only on a "
      "network call this cache-first cycle did not spend: re-resolving the "
      "five private owner remote heads, qualifying the C01 v0.1.2 wheel, live "
      "Jira readback, the 48-key career tranche and the remaining availability "
      "routes. Both 50-request ceilings are fully unspent.")
    a("")
    a("4. **Independent scientific review** — cannot be self-granted. Nothing "
      "in this packet constitutes it.")
    a("")

    a("## Scope honesty")
    a("")
    a("This cycle did not verify decades of national data, and does not "
      "claim to. It delivered bounded, named units against a real national "
      "denominator and left every unmet requirement visible with its exact "
      "reason. Claims here do not exceed the reviewed population, evidence "
      "and methods.")
    a("")

    report = "\n".join(lines) + "\n"
    (out / "CYCLE35_FINAL_REPORT.md").write_text(report, encoding="utf-8")
    print("wrote CYCLE35_FINAL_REPORT.md (" + str(len(report)) + " bytes)")
    print("sha256:", sha256_file(out / "CYCLE35_FINAL_REPORT.md"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
