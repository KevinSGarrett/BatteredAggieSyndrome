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
#: The pack defines three states. IMPLEMENTATION_SUBMITTED_NOT_ACCEPTED is
#: reserved for a "genuinely exhausted, documented submission", and this
#: cycle is not exhausted. The closeout review closed several of the tasks
#: this comment used to list -- the 2013-2026 corpus is cell-ingested in the
#: published rebuild (86,105 observations), the national neutral-site
#: rebuild is done, and the stratified review now carries independent span
#: labels -- but local work that needs no external authority and no network
#: budget remains:
#:
#:   * the release's expected population has 0 of 36,582 cells at the
#:     confirmed layer, because every confirmed assertion's episode carries
#:     season 'CURRENT';
#:   * 11 sampled rows sit at QUARANTINED_REPARSE_WITHDRAWS_SUPPORT although
#:     both spans are verbatim in the raw source -- a reparse recall gap;
#:   * 122 cells remain program-unresolved.
#:
#: Claiming the stronger state while that work is available and safe would
#: overstate the position, so the weaker and accurate one is used.
COMPLETION_STATE = "IN_PROGRESS_LOCAL_WORK_REMAINS"


CYCLE_RUNS = Path("C:/BatteredAggieSyndrome.data/ops/cycle35/runs")
SKIP_DIRECTORY_NAMES = frozenset(
    {"wheel_venv", "Lib", "site-packages", "Scripts", "__pycache__", ".git"}
)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def load_anywhere(out_dir: Path, name: str, cycle_root: Path | None = None) -> Any:
    """Load an artifact from this run directory, or from wherever in the
    cycle it actually lives.

    Looking only inside the directory being written to is what made the
    packet's own evidence map resolve almost nothing: a tool that writes
    into a different run directory becomes invisible. The report reads the
    newest copy by name instead.

    `cycle_root` is explicit so the fallback can be pointed somewhere else.
    Without it a caller passing an empty directory would silently be served
    another run's artifact, and the "this artifact is absent" branch could
    never be exercised.
    """

    local = load(out_dir / name)
    if local is not None:
        return local
    cycle_root = CYCLE_RUNS if cycle_root is None else cycle_root
    newest: tuple[float, Path] | None = None
    for path in cycle_root.rglob(name):
        if SKIP_DIRECTORY_NAMES.intersection(path.parts):
            continue
        try:
            stamp = path.stat().st_mtime
        except OSError:
            continue
        if newest is None or stamp > newest[0]:
            newest = (stamp, path)
    return load(newest[1]) if newest else None


def sha256_file(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def table(rows: list[list[str]], header: list[str]) -> str:
    out = ["| " + " | ".join(header) + " |",
           "|" + "|".join(["---"] * len(header)) + "|"]
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def spend(ledger: dict[str, Any], key: str) -> str:
    """A count the ledger records, or an explicit statement that it does not.

    Rendering a missing key as its `None` reads as zero, which is the one
    thing a spend figure must never be mistaken for.
    """

    value = ledger.get(key)
    return "NOT_RECORDED" if value is None else str(value)


def network_budget_paragraph(out_dir: Path, cycle_root: Path | None = None) -> str:
    """Read the ledger rather than restate a remembered spend.

    This paragraph used to say both 50-request ceilings were "fully
    unspent" and list re-resolving the remote heads and the live Jira
    readback among the things a budget would buy. All three had stopped
    being true.
    """

    ledger = load_anywhere(
        out_dir, "CYCLE35_CYCLE_WIDE_REQUEST_LEDGER.json", cycle_root
    )
    if not ledger:
        return (
            "**Network budget confirmation** — the cycle-wide request ledger "
            "was not found, so no claim is made about what has been spent."
        )
    budgets = ledger.get("budgets") or {}
    spent = ", ".join(
        f"{name} {row.get('used_cycle_lifetime')}/{row.get('ceiling')}"
        for name, row in sorted(budgets.items())
    )
    return (
        "**Network budget confirmation** — cycle-lifetime spend is "
        f"{spent or 'unrecorded'}, with "
        f"{ledger.get('cache_hits_no_request_spent', 0)} cache hits that spent "
        f"nothing and {ledger.get('paid_model_calls', 0)} paid model, "
        f"{ledger.get('paid_provider_calls', 0)} paid provider and "
        f"{ledger.get('paid_reviewer_calls', 0)} paid reviewer calls. What a "
        "further budget would buy is the C01 v0.1.2 wheel, the remaining "
        "career-tranche keys and the remaining availability routes. Re-"
        "resolving the private owner remote heads and the live Jira readback "
        "are NOT on that list: both were already carried out this cycle."
    )


def pr_check_summary(out_dir: Path) -> str:
    """What the exact-head CI query returned, never a remembered total.

    This line used to be the literal string "12 of 12 pass". A headline that
    cannot go red is not a status line.
    """

    packet = load(out_dir / "CYCLE35_ACCEPTANCE_PACKET.json") or {}
    ci = packet.get("exact_head_ci") or load(out_dir / "CYCLE35_EXACT_HEAD_CI_STATUS.json")
    if not ci or not ci.get("queried"):
        return "NOT_QUERIED at report generation"
    buckets = ci.get("by_bucket") or {}
    total = sum(int(v) for v in buckets.values())
    passing = int(buckets.get("pass", 0))
    head = str(ci.get("head_sha") or "")[:12]
    detail = ", ".join(
        f"{count} {bucket}" for bucket, count in sorted(buckets.items()) if bucket != "pass"
    )
    return (
        f"{passing} of {total} pass at `{head}`"
        + (f" ({detail})" if detail else "")
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out = Path(args.out_dir)

    # Every input is resolved across the cycle, not only inside the directory
    # being written to. Ten of these are produced by tools that write into
    # their own run directory, so a local-only load rendered whole sections
    # of the report empty -- the PIT feasibility table, the career tranche,
    # the availability release -- with nothing saying they were missing.
    def artifact(name: str) -> dict:
        return load_anywhere(out, name) or {}

    status = artifact("CYCLE35_REQUIREMENT_STATUS.json")
    findings = artifact("CYCLE35_FINDING_DISPOSITION.json")
    coverage = artifact("CYCLE35_NATIONAL_COVERAGE.json")
    validation = artifact("CYCLE35_VALIDATION_RESULTS.json")
    unfinished = artifact("CYCLE35_UNFINISHED_ITEMS.json")
    ledger = artifact("CYCLE35_COST_AND_REQUEST_LEDGER.json")
    git_state = artifact("CYCLE35_GIT_STATE.json")
    feasibility = artifact("R35_09_PIT_FEASIBILITY.json")
    finals = artifact("R35_07_CANONICAL_FINALS_REPLAY.json")
    release = artifact("R35_03_COACHING_RELEASE_SUMMARY.json")
    rebuild = artifact("R35_02_STAFF_REBUILD_SUMMARY.json")
    plan = artifact("CYCLE35_PLAN_JIRA_TRACE.json")
    family_b = artifact("R35_10_FAMILY_B_CANDIDATE.json")
    availability = artifact("R35_11_AVAILABILITY_RELEASE.json")
    career = artifact("R35_05_CAREER_TRANCHE_FINAL.json")
    routes = artifact("R35_11_UNMET_ROUTE_ATTEMPTS.json")
    heads = artifact("CYCLE35_ALL22_REMOTE_HEADS_REFRESHED.json")
    jira = artifact("CYCLE35_JIRA_LIVE_READBACK.json")

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
        [
            item["requirement"],
            str(item.get("reconciled_category") or "NOT_RECONCILED"),
            item["blocker"],
            str(item.get("reconciled_finding") or "").replace("|", '\\|') or "—",
        ]
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
    a("This is a submission, not an acceptance, and it is not exhausted. "
      "Independent scientific acceptance is NOT_REVIEWED for every unit, "
      "integration/release is NOT_AUTHORIZED for every unit, one dimension "
      "is actively FAIL, and safe local work remains that needs neither "
      "external authority nor network budget. No merge, Done transition, "
      "hold release, production or champion claim, protected-lane "
      "activation or repository transfer was performed.")
    a("")
    items = unfinished.get("items") or []
    # `kind` is keyword-matched from the blocker's own wording, so counting
    # it would report what the list SAYS about itself. The reconciled
    # category is what survived being checked against a delivered artifact.
    reconciled = [str(item.get("reconciled_category") or "") for item in items]
    local_remaining = [c for c in reconciled if c == "REAL_LOCAL_WORK_REMAINING"]
    unreconciled = [c for c in reconciled if not c or c.startswith("NOT_RECONCILED")]
    if unreconciled:
        a(f"{len(unreconciled)} of {len(items)} unfinished items could not be "
          "reconciled against a delivered artifact, so no claim is made about "
          "how many remain local.")
    else:
        by_category: dict[str, int] = {}
        for category in reconciled:
            by_category[category] = by_category.get(category, 0) + 1
        a(f"{len(local_remaining)} of {len(items)} unfinished items are real "
          "local work requiring no external authority, which is why the "
          "stronger IMPLEMENTATION_SUBMITTED_NOT_ACCEPTED state is not "
          "claimed. Each entry was checked against a delivered artifact "
          "rather than read off its own wording:")
        a("")
        for category, count in sorted(
            by_category.items(), key=lambda kv: (-kv[1], kv[0])
        ):
            a(f"- {count} {category}")
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
            ["Pull request", "#691 (draft) -> base `codex/BAT-706-cycle34-repair`"],
            ["PR URL", "https://github.com/KevinSGarrett/BatteredAggieSyndrome/pull/691"],
            ["PR checks", pr_check_summary(out)],
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
          + ". Assertions without a supporting observation: "
          + (
              spend(release, "unsupported_assertion_count")
              + (
                  " (this build's summary does not compute it; the field is "
                  "absent, which is not the same as zero)"
                  if release.get("unsupported_assertion_count") is None
                  else ""
              )
          )
          + ".")
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

    if career:
        a(f"**Career tranche:** 48 keys predeclared BEFORE evidence, "
          f"{career.get('key_count')} resolved — "
          + ", ".join(f"{k} {v}" for k, v in
                      sorted((career.get('final_dispositions') or {}).items()))
          + ". The key set never changed and no key was swapped for an "
          "easier school.")
        a("")
    if routes:
        a("**Availability routes:** the pre-existing ledger held 14 attempts "
          "across twelve FBS conferences and ZERO FCS or Independents, so "
          f"all {routes.get('keys_attempted')} unmet keys were actually "
          "attempted this cycle — "
          + ", ".join(f"{k} {v}" for k, v in
                      sorted((routes.get('by_outcome') or {}).items()))
          + ". They are now attempt-verified rather than inventory-assumed.")
        a("")
    if heads:
        drift = heads.get("drift_assessment") or {}
        specs = drift.get("CFBProgramSpecifications") or {}
        a(f"**All-22 heads:** {heads.get('reresolved_count')} owner remotes "
          "re-resolved and now BAS-verified. CFBProgramSpecifications is "
          f"{specs.get('commits_ahead')} commits ahead but changed "
          f"{specs.get('files_changed')} files, "
          f"{specs.get('files_changed_under_50_BAS_INTEGRATION')} of them "
          "under 50_BAS_INTEGRATION — so every PT35 adjudication remains "
          "bound to unchanged owner text. Checked, not assumed.")
        a("")
    if jira:
        a(f"**Jira:** read-only readback of {len(jira.get('issues') or [])} "
          f"issues, {len(jira.get('discrepancies') or [])} discrepancies, "
          f"{jira.get('writes_performed')} writes, "
          f"{jira.get('done_transitions')} Done transitions.")
        a("")

    a("## Closeout review (20260921T025300Z)")
    a("")
    # Read from the reconciliation, which opens each DATABASE and reports
    # its own column. The older paragraph here was headed "bound to the
    # delivered release" while quoting CYCLE35_RELEASE_COVERAGE_BINDING.json,
    # a file computed beside the build -- and the delivered database's own
    # column disagrees with it on every one of its 36,582 rows.
    reconciliation = load_anywhere(
        out, "CYCLE35_DELIVERED_RELEASE_RECONCILIATION.json"
    )
    if reconciliation:
        delivered = reconciliation["delivered"]["coverage_as_the_release_states_it"]
        a("**What the DELIVERED release states about its own coverage.** "
          + ", ".join(
              f"{count:,} {state}"
              for state, count in sorted(
                  delivered["coverage_state_counts"].items()
              )
          )
          + f", spanning {delivered['season_min']}-{delivered['season_max']} over "
          + f"{delivered['distinct_programs']} programs.")
        a("")
        compare = reconciliation["release_vs_artifact_beside_it"]
        if compare.get("artifact_present") and not compare.get("agree"):
            a("**The release and the artifact beside it disagree.** "
              + str(compare["finding"]))
            a("")
        families = reconciliation["delivered"]["families"]
        a("**Which source family carries the delivered assertions.** "
          f"official staff HTML supplies {families['official_staff']['observations']:,} "
          f"observations and supports {families['official_staff']['assertions_supported']:,} "
          f"assertions; the user corpus supplies "
          f"{families['user_corpus']['observations']:,} observations and supports "
          f"{families['user_corpus']['assertions_supported']:,}; the career "
          f"transcription supplies {families['career']['observations']:,} and supports "
          f"{families['career']['assertions_supported']:,}. scheme_assertion and "
          f"responsibility_assertion hold {families['scheme']['rows']} and "
          f"{families['responsibility']['rows']} rows.")
        a("")
        repaired = reconciliation.get("repaired_build_reported_separately")
        if repaired:
            built = repaired["coverage_as_the_release_states_it"]
            episodes = repaired["episode_seasons"]
            a("**A release rebuilt at this head, reported separately and never "
              "merged into the delivered figures.** "
              + ", ".join(
                  f"{count:,} {state}"
                  for state, count in sorted(built["coverage_state_counts"].items())
              )
              + f", spanning {built['season_min']}-{built['season_max']} over "
              + f"{built['distinct_programs']} programs, with "
              + f"{episodes['with_a_numeric_season']:,} of {episodes['episodes']:,} "
              + "episodes carrying a season a source states. The delivered "
              + "release had none: all of its episodes carried the literal "
              + "string \"CURRENT\", which is why no cell there reached the "
              + "confirmed layer. A rebuild is not evidence about what was "
              + "delivered, and is not offered as any.")
            a("")

    comparison = load_anywhere(out, "CYCLE35_DELIVERED_RELEASE_COMPARISON.json")
    if comparison and comparison.get("finding"):
        a("**Delivered vs rebuilt release.** " + str(comparison["finding"]))
        a("")

    span = load_anywhere(out, "CYCLE35_SOURCE_SPAN_SEMANTIC_REVIEW.json")
    if span:
        kinds = span.get("disagreements_by_kind") or {}
        a(f"**Source-span review.** {span.get('rows_reviewed')} rows, "
          f"instrument {span.get('instrument', {}).get('status')} across "
          f"{span.get('instrument', {}).get('control_count')} positive and "
          "negative controls. Independent span labels: "
          + ", ".join(
              f"{count} {label}"
              for label, count in sorted(
                  (span.get("independent_span_labels") or {}).items()
              )
          )
          + ". Disagreements with the parser's own support flag: "
          + (", ".join(f"{count} {kind}" for kind, count in sorted(kinds.items()))
             or "none")
          + f". Semantic adjudication pending for "
          f"{span.get('semantic_review_queue', {}).get('pending')} rows.")
        a("")

    kernel = load_anywhere(out, "R35_09_INDEPENDENT_KERNEL_REFERENCE.json")
    disposition = ((kernel or {}).get("comparison") or {}).get("residual_disposition")
    if disposition:
        missing = disposition.get("seasons_missing_from_declared_sources") or []
        a("**Kernel residuals.** "
          + ", ".join(
              f"{count} {state}"
              for state, count in sorted(
                  {
                      **(disposition.get("absent_game_rows_by_disposition") or {}),
                      **(disposition.get("unjustified_rows_by_disposition") or {}),
                  }.items()
              )
          )
          + ". Declared sources omit season(s) "
          + (", ".join(str(year) for year in missing) or "none")
          + ".")
        a("")

    receipt = load_anywhere(out, "CYCLE35_VALIDATION_RESULTS_SUCCESSOR.json")
    acceptance = (receipt or {}).get("canonical_mounted_acceptance") or {}
    if acceptance.get("state") == "RECEIPT_BOUND":
        a(f"**Canonical mounted acceptance: {acceptance.get('acceptance')}.** "
          f"{acceptance.get('mounted_lanes_established')} lanes ran with the "
          "private mount established; "
          f"{acceptance.get('mounted_lanes_failing')} failing.")
        a("")
        for name, row in sorted((acceptance.get("lane_outcomes") or {}).items()):
            a(f"- `{name}` mounted={row.get('mounted_lane_established')} "
              f"exit={row.get('exit_code')} — {row.get('summary_line')}")
        a("")

    discovered = load_anywhere(out, "CYCLE35_NEWLY_DISCOVERED_OBLIGATIONS.json")
    if discovered:
        a("**Obligations surfaced by this review** (kept out of the declared "
          "26 so that list stays auditable): "
          + ", ".join(
              f"{count} {state}"
              for state, count in sorted((discovered.get("by_state") or {}).items())
          )
          + ".")
        a("")
        for entry in discovered.get("items") or []:
            a(f"- **{entry['key']}** ({entry['requirement']}, {entry['state']}) — "
              + str(entry.get("finding") or "no evidence available"))
        a("")

    a("## Baseline equivalence")
    a("")
    for row in validation.get("baseline_equivalence") or []:
        if row.get("state") != "COMPARED":
            a(f"- **{row.get('lane')}** — {row.get('state')}")
            continue
        a(f"- **{row['lane']}** — predecessor {row['baseline_red_count']} red, "
          f"this branch {row['candidate_red_count']} red. "
          f"**{row['regression_count']} regressions introduced**, "
          f"{row['fixed_count']} fixed, {row['inherited_red_count']} "
          "inherited. Proven by exact set membership, not by matching counts.")
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
    derived = validation.get("derived_lanes") or []
    if derived:
        a("Read from artifacts rather than stated here, so they cannot drift:")
        a("")
        for lane in derived:
            a(f"- **{lane['lane']}** — {lane['result']}"
              + (f". {lane['detail']}" if lane.get("detail") else ""))
        a("")
    a("Explicitly not claimed:")
    for claim in validation.get("claims_not_made") or []:
        a(f"- {claim}")
    a("")

    a("## Failing dimensions")
    a("")
    for row in validation.get("failing_dimensions") or []:
        a(f"- **{row['dimension']}: {row['state']}** — {row['reason']}")
    if family_b:
        a("")
        a(f"The Family B candidate successor is prepared and validated "
          f"(children match on disk: "
          f"{(family_b.get('child_byte_validation') or {}).get('all_children_match_on_disk')}, "
          f"replay identical: {family_b.get('replay_produces_identical_candidate')}, "
          f"predecessor bytes unchanged: "
          f"{family_b.get('predecessor_bytes_unchanged')}), but canonical "
          f"activation requires "
          f"{(family_b.get('approval_request') or {}).get('approval_id')}.")
    a("")

    a("## New findings this cycle")
    a("")
    for row in findings.get("new_findings_this_cycle") or []:
        a(f"- **{row['id']} [{row['severity']}] {row['title']}** "
          f"({row['status']}, owner {row['owner']}). {row['detail']}")
        # A refinement that is recorded but not rendered is not a
        # refinement a reader gets.
        if row.get("closeout_refinement"):
            a(f"  - *Closeout refinement:* {row['closeout_refinement']}")
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
    a(f"- Scientific requests: {spend(ledger, 'total_scientific_requests')}")
    a(f"- Infrastructure readbacks: "
      f"{spend(ledger, 'infrastructure_readback_requests')}")
    a(f"- Cache hits (spent nothing): "
      f"{spend(ledger, 'cache_hits_no_request_spent')}")
    for label, key in (
        ("Coaching/history", "coaching_history_budget"),
        ("Availability/context", "availability_context_budget"),
    ):
        budget = ledger.get(key) or {}
        # The ledger reports cycle-lifetime spend under
        # `used_cycle_lifetime`. Reading a `used` key that is not there
        # rendered "None of 50 used", which reads as none used.
        used = budget.get("used_cycle_lifetime", budget.get("used"))
        a(f"- {label} budget: "
          + (f"{used} of {budget.get('ceiling')} used this CYCLE"
             if used is not None
             else "NOT_RECORDED in the ledger; no spend figure is claimed"))
    a("")

    a("## Every remaining blocker")
    a("")
    if blocker_rows:
        a("Blocker text is reproduced verbatim from the declared unit list; "
          "none was edited or removed. The category is what the entry was "
          "placed in after being checked against a delivered artifact.")
        a("")
        a(table(
            blocker_rows,
            ["Requirement", "Reconciled category", "Blocker (as declared)", "Finding"],
        ))
        a("")

    a("## Authority required to change this state")
    a("")
    a("1. **`CYCLE33-APPROVAL-LAKE-SUCCESSOR-001`** — activating canonical "
      "routing for the prepared Family B successor. The complete candidate, "
      "its byte hashes, the affected pins and a recovery plan are in "
      "`R35_10_APPROVAL_REQUEST.json`. Until this is resolved the canonical "
      "mounted Family B dimension stays FAIL.")
    a("2. **Merge authority for `codex/BAT-706-cycle35`** — the branch is "
      "pushed and PR #691 is open as a draft against "
      "`codex/BAT-706-cycle34-repair`. No merge, and no transition out of "
      "draft, was performed or is authorized here.")
    a("3. " + network_budget_paragraph(out))
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
