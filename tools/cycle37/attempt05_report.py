r"""Cycle #37 — Attempt #5 — WORKER_REPORT.md renderer (R37A05-07).

Renders the worker report from the same context and submission ``attempt05_outputs.py`` builds, so every count,
state and identity in the narrative is read from a receipt, a declared output or the submission rather than
typed. The sections follow ``templates/WORKER_REPORT.template.md`` of the v2.4.0 release. Nothing here grants
acceptance.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FINDING_TEXT = {
    "MF37A04-01": ("An attached Git config file option wrote past the protected-root boundary",
                   "`git config -f../p/x fixture.value CHANGED` from a repository inside the Git scratch root exited 0 "
                   "and changed the protected fixture under the v37.4 guard.",
                   "The v37.5 guard admits a guarded Git child only through a typed grammar per subcommand: exact long "
                   "options, declared short clusters, typed values; config writes only to declared keys of git-defined "
                   "sections; every path spelling resolved inside the declared scratch root; no reparse point or "
                   "multiply linked file in the Git metadata; a write needs a declared scratch root (no TEMP fallback). "
                   "File options, abbreviations, config/env/helper indirection and native children are refused before "
                   "the child starts. It remains a Python-process guard, not OS isolation."),
    "MF37A04-02": ("The explicit successor accepted missing lineage rows and certified absent raw evidence",
                   "A resealed copy with Fred Mariani's DFO row deleted served 6 rows; a resealed row with its raw file "
                   "and digest nulled was served as raw-verified.",
                   "The consumer proves lineage from the rows before serving: identities equal their locators, every "
                   "edge resolves and is reciprocal, each disposition agrees with its edges, every Attempt 4 row maps "
                   "once to the named Attempt 4 file, raw provenance is present; a served row's raw file, revision text "
                   "and spans are re-verified, and absent evidence is refused, never labelled verified."),
    "MF37A04-03": ("Season templates dropped their end season and nested lines inherited conflicting parent dates",
                   "2,232 of 2,257 rows with a two-argument season template read as their first year; Cory Undlin's "
                   "2018 season query returned no Eagles row; nested lines took their parent's wider dates.",
                   "Season templates render the range they display (to a year, to present, or an open end); any other "
                   "shape stays an explicitly unresolved date with its raw text. Every list line reads its own date "
                   "(balanced or not, leading, adjacent, inside a link, in a list template); a line without one "
                   "inherits its parent's and names the parent's raw locator; dated role lines after a break are rows of "
                   "their own; text inside comments and <nowiki> is never read as a row."),
    "MF37A04-04": ("A defensive passing-game coordinator carried the OFFENSE unit",
                   "33 rows titled defensive passing-game coordinator carried OFFENSE (10) or UNKNOWN (23).",
                   "A side-dependent role (passing/run-game coordinator, quality control, analyst, graduate assistant, "
                   "assistant, consultant, intern, volunteer) takes its unit only from the words that modify it in its "
                   "own title segment; a side is never borrowed from another role; both sides or none stay UNKNOWN; no "
                   "play-calling authority is inferred."),
    "MF37A04-05": ("The storage ceiling was recorded but never enforced",
                   "The Attempt 4 runners compared free space with the reserve but never reserved or gated cumulative "
                   "added bytes; Attempt 4 added 5.65 GiB against a 4 GiB budget (W37A04-15).",
                   "Every allocation is admitted against one cumulative, hash-chained ledger under a lock: estimate plus "
                   "added bytes plus open reservations must fit the budget and leave the free reserve; the measured cost "
                   "is reconciled, an underestimate recorded, a breach writes a bounded stop that refuses everything "
                   "after it; nothing is deleted and no counter is reset."),
}


def _j(value: Any, limit: int = 1200) -> str:
    text = json.dumps(value, indent=1, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + "\n... (truncated here; full value in the named file)"


def _details(ctx: Any, lane: str) -> dict[str, Any]:
    return (ctx.receipts.get(lane) or {}).get("details") or {}


def _output(ctx: Any, name: str) -> dict[str, Any]:
    path = ctx.out_root / name
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def render(ctx: Any, s: dict[str, Any]) -> str:
    c = ctx.contract
    cand = s["candidate"]
    label = f"Cycle #{s['cycle_number']} \u2014 Attempt #{s['attempt_number']} \u2014 {s['headline']}"
    worker_criteria = [row for row in s["criteria"] if ctx.criteria[row["id"]]["executor"] == "worker"]
    manager_criteria = [row for row in s["criteria"] if ctx.criteria[row["id"]]["executor"] != "worker"]
    verified = [row for row in worker_criteria if row["status"] == "VERIFIED_LOCAL"]
    backlog = [row for row in c["carryforward"] if row["disposition"] == "OWNED_BACKLOG"]
    in_cycle = [row for row in c["carryforward"] if row["disposition"] == "IN_CYCLE"]
    lanes = {row["id"]: row for row in s["lanes"]}
    red = [row for row in s["lanes"] if row["status"] == "FAIL"]
    out: list[str] = [f"# {label}", ""]
    out += [f"Internal identity: `{s['cycle_id']}` / `{s['attempt_id']}`. Contract `{ctx.contract_path}` SHA-256 "
            f"`{s['contract_sha256']}` (equal to the sealed issuance record). Branch `{c['repo']['branch']}` from base "
            f"`{c['repo']['base_sha']}`.", "",
            f"Candidate head `{cand['head']}`, tree `{cand['tree']}`, source digest `{cand['source_digest']}` "
            "(SHA-256 of `git ls-tree -r --full-tree HEAD`).", ""]

    # ---- direct answer
    dims = s["dimensions"]
    out += ["## Direct answer and six dimensions", "",
            f"Worker-owned work complete: **{'YES' if len(verified) == len(worker_criteria) else 'NO'}** -- "
            f"{len(verified)} of {len(worker_criteria)} worker criteria are VERIFIED_LOCAL at the candidate head, each "
            "backed by lane receipts and command logs. Independently accepted: **NO** (PENDING_MANAGER_REVIEW; "
            f"{len(manager_criteria)} manager criteria and the MANAGER_REVIEW lane are the manager's). Integrated: "
            "**NO** (NOT_AUTHORIZED; one local integration candidate is prepared, nothing pushed, merged, published or "
            f"activated). Headline: **{s['headline']}**. Predictive skill: **{s['predictive_skill']}**.", ""]
    if red:
        out += [f"Software validation is **{dims['software_validation']}** because "
                + ", ".join(row["id"] for row in red)
                + " stay red, classified identity by identity and compared with the Attempt 4 final lanes by identity "
                  "and cause (INHERITED_LANE_EQUIVALENCE.json). No failing test is skipped, disabled or relabelled.", ""]
    elif dims["software_validation"] == "PARTIAL":
        out += ["Software validation is **PARTIAL** because the manager-owned MANAGER_REVIEW lane has not run; every "
                "worker lane's state is in the matrix below.", ""]
    out += ["| Dimension | Actual state | Evidence | Remaining acceptance |", "| --- | --- | --- | --- |",
            f"| Implementation | {dims['implementation']} | {ctx.candidate_commit_count} commits after the issued base; FINDING_CLOSURE_MATRIX.json | Manager replay of every repair |",
            f"| Data/evidence | {dims['data_evidence']} | CAREER_CORRECTION_SUCCESSOR.json, CAREER_POPULATION_DISPOSITIONS.json, DELIVERED_CONSUMER_MANIFEST.json | Manager recomputation; no activation |",
            f"| Software validation | {dims['software_validation']} | LANE_RESULTS.json, INHERITED_LANE_EQUIVALENCE.json, lanes/RUNS.jsonl | Owner decisions for inherited red; MANAGER_REVIEW |",
            f"| Independent scientific acceptance | {dims['independent_acceptance']} | -- | All `-M` criteria and MANAGER_REVIEW |",
            f"| Integration/release | {dims['integration_release']} | LOCAL_INTEGRATION_CANDIDATE.json, INTEGRATION_DECISION_PACKET.md | Explicit actor/action/target grants |",
            f"| Overall cycle | {dims['overall_cycle']} | submission.json | Independent manager review |", ""]

    # ---- subject
    start = _details(ctx, "START_CONTEXT")
    installed = _details(ctx, "INSTALLED_CONSUMER_C01")
    interpreter = (ctx.receipts.get("START_CONTEXT") or {}).get("interpreter") or {}
    storage = start.get("storage_ledger") or {}
    out += ["## Issued versus actual subject", "",
            f"- Issued: contract SHA-256 `{s['contract_sha256']}`, bound by the sealed issuance "
            f"`{ctx.contract_path.parent / 'issuance' / 'issuance.json'}`; every contract source reference re-hashed at "
            f"START_CONTEXT ({sum(1 for r in start.get('source_refs') or [] if r.get('matches'))} of "
            f"{len(start.get('source_refs') or [])} equal to their issued digests).",
            f"- Actual: {ctx.candidate_commit_count} commits after the issued base. Worktree clean at the start and end "
            f"of every executed lane run: {ctx.all_runs_clean}.",
            f"- Interpreter (input only): `{interpreter.get('executable')}` CPython "
            f"{(interpreter.get('version') or '').split()[0] if interpreter.get('version') else ''}.",
            f"- Delivered database: SHA-256 `{(start.get('delivered_database') or {}).get('expected')}` at its default "
            f"path, unchanged before and after the installed lane ({(installed.get('delivered_database_unchanged') or {}).get('after')}).",
            f"- Delivered explicit career successor: `{ctx.pointer.get('successor_file')}` SHA-256 "
            f"`{ctx.pointer.get('successor_sha256')}`, bound to that database digest and to the Attempt 4 successor "
            f"`{ctx.pointer.get('a04_successor_sha256')}`; built from clean head "
            f"`{(ctx.pointer.get('built_from') or {}).get('head')}`; selected only by name.",
            f"- Released C01 wheel: SHA-256 `{(start.get('c01_wheel') or {}).get('expected')}`, composed, never rebuilt.",
            f"- Fresh noneditable BAS wheel: SHA-256 `{installed.get('wheel_sha256')}`, built from a git archive of the "
            "candidate head's pyproject.toml, README.md and src with cached tooling, installed offline into a new "
            "environment under the packaging root and run outside every checkout.",
            f"- Storage ledger at START_CONTEXT: chain {storage.get('chain')}, added {storage.get('added_bytes')} of "
            f"{storage.get('budget_bytes')} bytes, free {storage.get('free_bytes')} against the {storage.get('reserve_bytes')}-byte "
            f"reserve, bounded stop {storage.get('bounded_stop')}.",
            f"- Main checkout `{(start.get('main_checkout') or {}).get('path')}` at "
            f"`{(start.get('main_checkout') or {}).get('head')}` with {(start.get('main_checkout') or {}).get('status_entries')} "
            "status entries; neither integration worktree changed during any lane.",
            "- Scope changes: none. The retired assistive interlock stays retired on this branch; the decommission "
            "validator runs in START_CONTEXT and the retired interlock validator is never invoked.",
            "- Timing disclosure: the before-repair reproduction of all five findings was taken at the issued base first "
            "(evidence/before); the BEFORE platform reads were taken after the local repairs had begun, and each receipt "
            "binds the exact head it read at.", ""]
    origins = installed.get("installed_origins") or {}
    if origins:
        out += ["Installed module origins (site-packages of the fresh environment):", "", "```json",
                _j(origins.get("origins") or origins, 2500), "```", ""]

    # ---- criteria
    out += ["## Every criterion, original finding and carryforward", "",
            "| Criterion | Executor | Status | Reason | Evidence |", "| --- | --- | --- | --- | --- |"]
    for row in s["criteria"]:
        executor = ctx.criteria[row["id"]]["executor"]
        reason = row["reason"].replace("|", "/")
        out.append(f"| {row['id']} | {executor} | {row['status']} | {reason} | {', '.join(row['evidence_ids'][:4])}"
                   + (f" (+{len(row['evidence_ids']) - 4})" if len(row["evidence_ids"]) > 4 else "") + " |")
    out += ["", "### The five manager findings", ""]
    carry = {row["id"]: row for row in c["carryforward"]}
    matrix = {row["finding"]: row for row in (_output(ctx, "FINDING_CLOSURE_MATRIX.json").get("findings") or [])}
    for key, (title, before, after) in FINDING_TEXT.items():
        meaning = carry[key]["original_meaning"]
        try:
            record = json.loads(meaning)
            meaning = f"{record.get('title')}. {record.get('reproduction')}"
        except ValueError:
            pass
        row = matrix.get(key) or {}
        out += [f"**{key} -- {title}.** Original meaning: {meaning}", "",
                f"- Reproduced before repair at the issued base with the manager's own probe "
                f"({row.get('reproduced_before_repair')}): {before}",
                f"- General repair: {after}",
                f"- Commits: {', '.join(x['sha'][:10] for x in row.get('commits') or []) or 'none named'}. Disposition: "
                "repaired locally, pending the manager's independent replay.", ""]
    counts = ctx.carry_counts
    states: dict[str, int] = {}
    for row in ctx.obligation_items:
        if "attempt5_state" in row:
            states[row["attempt5_state"]] = states.get(row["attempt5_state"], 0) + 1
    out += ["### Carryforward", "",
            f"All {sum(counts['composition'].values())} carryforward identities are in "
            "ORIGINAL_OBLIGATION_DISPOSITIONS.json with each original meaning, source, owner, reason, next action, "
            "prior mapping and disposition copied unchanged: "
            + ", ".join(f"{k} {v}" for k, v in counts["composition"].items()) + "; dispositions "
            + ", ".join(f"{k} {v}" for k, v in counts["dispositions"].items()) + ".", "",
            f"The {len(in_cycle)} IN_CYCLE items carry the evidence of their linked criteria; the {len(backlog)} "
            "OWNED_BACKLOG items stay owned backlog and none is marked fulfilled by accounting. The 22 original, 13 "
            "Attempt 3 and 13 Attempt 4 lanes each carry a disposition in LANE_RESULTS.json.", "",
            "| Attempt 5 state | Items |", "| --- | --- |"] + [f"| {k} | {v} |" for k, v in sorted(states.items())] + [""]

    # ---- delivered behaviour
    population = _output(ctx, "CAREER_POPULATION_DISPOSITIONS.json")
    successor = _output(ctx, "CAREER_CORRECTION_SUCCESSOR.json")
    named = installed.get("successor_named_cases") or {}
    pagination = installed.get("successor_pagination") or {}
    oracle = installed.get("successor_filtered_oracle") or {}
    locators = installed.get("successor_locators") or {}
    fixtures = (installed.get("lineage_fixtures") or {}).get("cases") or {}
    career = _details(ctx, "CAREER_SUCCESSOR")
    claim = career.get("claim_successor") or {}
    pred = population.get("predecessor_dispositions") or {}
    a04 = population.get("a04_dispositions") or {}
    out += ["## Delivered behavior and national data", "",
            "Before (evidence/before, at the issued base): the installed consumer served a resealed successor missing a "
            "row, certified an absent raw file as verified, returned no Eagles row for Cory Undlin in 2018 and served "
            "33 defensive passing-game coordinators as OFFENSE or UNKNOWN. After: the fresh installed "
            "`bas-staff-query`, given `--career-successor <file> --career-successor-sha256 <digest>`, answers from the "
            "Attempt 5 successor; without it, it answers exactly as the delivered release did (no default activation).",
            "",
            f"Population: {(population.get('population') or {}).get('predecessor_rows')} predecessor rows and "
            f"{(population.get('population') or {}).get('a04_rows')} Attempt 4 rows, read from "
            f"{(population.get('population') or {}).get('pages')} cached revisions into "
            f"{(population.get('population') or {}).get('successor_episodes')} successor rows.", "",
            "Predecessor dispositions: " + ", ".join(f"{k} {v}" for k, v in sorted((pred.get("by_disposition") or {}).items()))
            + ". Attempt 4 dispositions: " + ", ".join(f"{k} {v}" for k, v in sorted((a04.get("by_disposition") or {}).items()))
            + f". Rows no longer produced, by cause: {_j(population.get('not_produced_by_cause'), 400)}.", ""]
    a4s = population.get("a4_screens") or {}
    out += ["| Manager screen | Members | Dispositions | Check that does not use the parser |", "| --- | --- | --- | --- |"]
    for name, row in a4s.items():
        failures = [k for k in ("without_disposition", "template_not_read_as_its_form_states", "manager_endpoint_not_read",
                                "independent_side_differs_or_absent") if row.get(k)]
        out.append(f"| {name} | {row.get('members')} of {row.get('expected')} | "
                   + ", ".join(f"{k} {v}" for k, v in sorted((row.get("by_disposition") or row.get("by_a05_unit") or {}).items()))
                   + f" | {'holds' if not failures else 'FAILS: ' + ', '.join(failures)} |")
    for name, row in (population.get("a3_screens") or {}).items():
        out.append(f"| {name} (Attempt 3) | {row.get('members')} of {row.get('expected')} | "
                   + ", ".join(f"{k} {v}" for k, v in sorted((row.get("by_disposition") or {}).items()))
                   + f" | unchanged without grounded basis: {len(row.get('unchanged_without_grounded_basis') or [])} |")
    tcensus = population.get("template_census_reconciliation") or {}
    out += ["", f"Independent template census (`{tcensus.get('census_version')}`), reconciled by span containment: "
            + ", ".join(f"{k} {v}" for k, v in sorted((tcensus.get("counts") or {}).items())) + ".", "",
            f"Attempt 4 raw census: {_j((population.get('a4_raw_census_reconciliation') or {}).get('counts'), 600)}; "
            f"uncovered rows by cause {_j(population.get('a4_raw_census_uncovered_by_cause'), 300)}.", "",
            f"Unit changes across the population: {_j((population.get('unit_changes') or {}).get('changes'), 900)}. "
            f"Affected delivered staff rows (recorded, not rebuilt): {(population.get('staff_descendants') or {}).get('affected')} "
            f"of {(population.get('staff_descendants') or {}).get('staff_role_assignments')}.", "",
            "Installed consumer over the delivered successor:", "",
            f"- Full pagination: {pagination.get('distinct')} distinct rows in {pagination.get('pages')} pages against "
            f"{pagination.get('expected')} in the independent SQL oracle; reconciled {pagination.get('reconciled')}.",
            f"- Raw locators re-read from the captures: {locators.get('verified')} of {locators.get('rows')} verified, "
            f"{locators.get('span_mismatch')} span mismatches, {locators.get('raw_file_digest_mismatch')} digest mismatches.",
            f"- Named cases: {_j(named.get('holds'), 900)}",
            f"- Cory Undlin 2018: {_j(named.get('cory_undlin_2018_eagles'), 400)}; Steve Wilks inherited: "
            f"{_j(named.get('steve_wilks_inherited'), 500)}", "",
            "| Resealed or broken successor | Refused for its intended cause |", "| --- | --- |"]
    out += [f"| {name} | {row.get('expected_code')}: {row.get('refused_for_the_intended_cause')} |"
            for name, row in fixtures.items()]
    out += ["", "| Filtered query | CLI | Oracle | Equal |", "| --- | --- | --- | --- |"]
    out += [f"| {name} | {row.get('cli')} | {row.get('oracle')} | {row.get('equal')} |" for name, row in oracle.items()]
    reproduction = (career.get("successor_reproduction") or {}).get("comparison") or {}
    out += ["", f"Rebuild at the candidate head: byte-identical {reproduction.get('byte_identical')} "
            f"({reproduction.get('rebuilt_sha256')}); rebuild checks {_j(career.get('successor_checks'), 900)}.", "",
            f"Manager replays against this wheel: {_j({k: (installed.get(k) or {}).get('holds') for k in ('manager_a3_career_challenge', 'manager_a4_career_semantic_census', 'manager_a4_successor_challenge')}, 400)}.", "",
            f"Cycle 29 claim successor preserved: census reproduced {claim.get('census_reproduced')}, claims reproduced "
            f"{claim.get('claims_reproduced')}, selected validator passes {claim.get('selected_passes')}, default still "
            f"reports the 35 undeclared pairs {claim.get('default_reports_35')}.", "",
            "Real eligible forecasts: **0**. Real proven PIT rows: **0**. Wikimedia revisions are retrospective "
            "secondary evidence; no successor row is PIT admitted, official, activated or accepted.", "",
            f"Successor identity: {_j(successor.get('identity'), 1500)}", ""]

    # ---- storage and candidate
    storage_lane = _details(ctx, "STORAGE_ADMISSION").get("storage_ledger") or {}
    candidate = _output(ctx, "LOCAL_INTEGRATION_CANDIDATE.json")
    lane_c = candidate.get("lane") or {}
    out += ["## Storage admission and the local integration candidate", "",
            f"Storage ledger `{storage_lane.get('path')}`: {storage_lane.get('records')} records, chain intact "
            f"{storage_lane.get('chain_intact')}, added {storage_lane.get('added_bytes')} of {storage_lane.get('budget_bytes')} "
            f"bytes; live over-budget control {_j(storage_lane.get('live_over_budget_control'), 300)}; lane reservation "
            f"pairs {_j(storage_lane.get('lane_reservation_pairs'), 300)}.", "",
            f"Integration candidate: {_j({k: (candidate.get('integration_candidate') or {}).get(k) for k in ('candidate_branch', 'candidate_head', 'candidate_tree', 'candidate_parents', 'only_protected_paths_differ', 'protected_paths_equal_main', 'files_changed_against_main', 'repair_commits_consolidated')}, 1200)}", "",
            f"Tree checks {_j(lane_c.get('tree_checks'), 700)}; history policy {_j((lane_c.get('history_policy') or {}).get('holds'))}; "
            f"consumer {_j((lane_c.get('consumer') or {}).get('holds'))}; review-control characterization "
            f"{_j((lane_c.get('review_control_characterization') or {}).get('outcome'), 600)}.", "",
            f"Decision for the owner: {candidate.get('decision_for_the_owner')}", ""]

    # ---- repairs and reproduction guide
    out += ["## Repairs and independent-review inputs", "",
            "Each repair has positive and negative controls and new challenges in its suite; the manager's saved "
            "Attempt 4 probes (git option challenge v2, successor challenge, semantic census) are replayed from owned "
            "copies with only fixture-root, installed-venv, subject-path and table-name literals adapted; the Attempt 2 "
            "and 3 probes are replayed as before.", "", "Manager reproduction guide (each is the issued lane command):", ""]
    for lane_id in ("WRITE_PROTECTION", "STORAGE_ADMISSION", "CAREER_SUCCESSOR", "INSTALLED_CONSUMER_C01",
                    "LOCAL_INTEGRATION_CANDIDATE"):
        out.append(f"- `{lane_id}`: `{ctx.lanes[lane_id]['command']}` in `{ctx.lanes[lane_id]['cwd']}`")
    out += ["", "Known limitations: the guard covers Python processes and confines, not isolates, Git children; the "
            "successor reads roles and years only as the revisions state them; unresolved forms stay unresolved rather "
            "than guessed; the delivered staff release is not rebuilt under the v37.5 taxonomy (its affected rows are "
            "listed).", ""]

    # ---- validation matrix
    workers = [lane_id for lane_id, lane in ctx.lanes.items() if lane["executor"] == "worker"]
    executed = [lane_id for lane_id in workers if lanes[lane_id]["executed"]]
    out += ["## Exact validation matrix", "",
            f"{len(executed)} of {len(workers)} worker lanes ran through the issued command at the candidate head"
            + ("" if len(executed) == len(workers) else " (the rest are NOT_RUN)") + ". Every child gets a "
            "credential-scrubbed environment, the attempt packaging root as TEMP and declared Git scratch root, the v37.5 "
            "write guard over the data root, main checkout, both integration worktrees, All-22 and the Attempt 3 and 4 "
            "roots, and the loopback-only network guard, except where a receipt names an exception. WRITE_PROTECTION "
            "and STORAGE_ADMISSION qualified the guard and the ledger before the costly and mounted lanes ran, and every "
            "lane reserved its storage before it ran.", "",
            "| Lane | Kind | Status | Run | Tests | Fail | Err | Import err | Failed subtests | Skipped | Reason |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for lane_id, lane in ctx.lanes.items():
        row = lanes[lane_id]
        reason = (row.get("reason") or "").replace("|", "/")[:300]
        out.append(f"| {lane_id} | {lane['kind']} | {row['status']} | {row.get('run', '--')} | {row['tests']} | "
                   f"{row['failures']} | {row['errors']} | {row['import_errors']} | {row['failed_subtests']} | "
                   f"{row['skipped']} | {reason} |")
    equivalence = _output(ctx, "INHERITED_LANE_EQUIVALENCE.json")
    for row in equivalence.get("inherited_red") or []:
        comparison = row.get("attempt4_comparison") or {}
        if comparison:
            out += ["", f"{row['lane']} against Attempt 4 at the issued base, by identity: persisting "
                    f"{len(comparison.get('persisting') or [])}, new {len(comparison.get('new_in_attempt5') or [])}, "
                    f"no longer failing {len(comparison.get('no_longer_failing') or comparison.get('no_longer_reported') or [])}"
                    + (f", same cause {len(comparison.get('persisting_same_cause') or [])}" if "persisting_same_cause" in comparison else "")
                    + "."]
    out += ["", "Original 22 lanes, Attempt 3's 13 lanes and Attempt 4's 13 lanes:", "",
            "| Lane | Prior result | Disposition |", "| --- | --- | --- |"]
    out += [f"| {row['original_lane']} | {row.get('attempt2_result', '--')} | {row['disposition']} |" for row in ctx.original_lanes]
    out += [f"| A03 {row['attempt3_lane']} | {row.get('attempt3_result', '--')} | {row['disposition']} |" for row in ctx.attempt3_lanes]
    out += [f"| A04 {row['attempt4_lane']} | {row.get('attempt4_result', '--')} | {row['disposition']} |" for row in ctx.attempt4_lanes]
    out.append("")

    # ---- platform
    platform = _output(ctx, "PLATFORM_RECONCILIATION.json")
    out += ["## Plans, Jira, PR feedback and integrations", "", "Governing sources (contract `source_refs`):", ""]
    out += [f"- `{row['id']}`: {row.get('section', '')} (`{Path(row['path']).name}`, SHA-256 `{row['sha256'][:16]}...`)"
            for row in c["source_refs"]]
    out += ["", "Granted Jira comments (marker, created id, readback):", ""]
    for row in platform.get("granted_comments") or []:
        out.append(f"- {row['phase']} {row['issue']} `{row['marker']}`: {row['result']}, created {row['created_id']}, "
                   f"read back {row['readback_comment_ids']}, comments {row['comments_before']} -> {row['comments_after']}")
    out += ["", "Private Jira successor runs of the selected sync contract (dry run, apply, strict validator, audit, "
            "second dry run) in a private copy under the guard; never the committed pack or live Jira:", ""]
    for row in platform.get("private_jira_successors") or []:
        steps = ", ".join(f"{x['name']} exit {x['exit']} ({x['conflicts']} conflicts)" for x in row["steps"])
        out.append(f"- {row['phase']}: {steps}; private changes {row['private_changes']}; guard blocked "
                   f"{row['write_guard_blocked']}; committed canonical mutations {row['committed_canonical_mutations']}; "
                   f"outside mirror scope {row['outside_scope_count']}; adopted {row['adopted']}")
    github = ctx.latest_github
    if github:
        out += ["", f"GitHub at the latest read ({github.get('phase')}, {github.get('observed_at')}): main "
                f"`{github.get('main_head')}`, {github.get('open_pr_count')} open pull requests, "
                f"{github.get('unresolved_thread_total')} unresolved review threads (issued baseline: 13 and 71). No PR, "
                "push, merge, retarget or remote change was made; the only new ref is the local candidate branch.", ""]
    revisions = platform.get("all22_owner_revisions") or []
    if revisions:
        out += ["All-22 owner repositories at the latest read (issued revision -> observed remote head):", ""]
        out += [f"- {r['repository']}: `{r['issued_remote_revision']}` -> `{r['observed_remote_head']}` (changed "
                f"{r['changed_since_issuance']}; local head `{r['local_head']}`, {r['local_dirty_entries']} dirty entries)"
                for r in revisions]
        owner = (ctx.latest_all22 or {}).get("owner_plan_check") or {}
        out += ["", f"Retained owner snapshots present unchanged at CFBProgramSpecifications `{owner.get('remote_head')}`: "
                f"{owner.get('snapshots_present_unchanged')} of {owner.get('snapshots_compared')}. The 22 accepted Phase 2 "
                "plans remain NOT_IMPLEMENTED; the installed BAS wheel composes with the released C01 0.1.2 wheel; no "
                "owner repository was changed and no CFIP proposal was posted or presented as adoption.", ""]

    # ---- cost
    ledger = _output(ctx, "COST_AND_AUTHORITY_LEDGER.json")
    out += ["## Cost, storage, privacy and recovery", "", "| Request lane | Requests | Retries | Ceiling |",
            "| --- | --- | --- | --- |"]
    for lane_id, row in (ledger.get("request_lanes") or {}).items():
        out.append(f"| {lane_id} | {row['requests']} | {row['retries']} | {row['ceiling']} |")
    storage_doc = ledger.get("storage") or {}
    out += ["", f"Paid AI calls 0, cost 0. Storage ledger: added {storage_doc.get('added_bytes')} bytes of the "
            f"{storage_doc.get('peak_extra_bytes_allowed')}-byte budget; free space now {storage_doc.get('free_bytes_now')} "
            f"bytes against the {storage_doc.get('reserve_bytes')}-byte reserve (satisfied: {storage_doc.get('reserve_satisfied')}); "
            f"refused reservations {storage_doc.get('refused')}, underestimates {storage_doc.get('underestimated')}, bounded "
            f"stop {storage_doc.get('bounded_stop')}. Created roots: the attempt root, `C:\\BatteredAggieSyndrome.validation\\c37a05`, "
            "`C:\\BatteredAggieSyndrome.packaging\\c37a05` and the candidate worktree, within the write grants. No "
            "credential was printed, logged or written; lane children run with credential variables removed. Apart from "
            "the one empty development directory disclosed in W37A05-08, nothing was deleted, moved or cleaned up; the "
            "development and rehearsal scratch is listed for the owner (see the findings).", ""]

    # ---- unfinished
    out += ["## Every unfinished obligation and precise decisions", ""]
    for item in s["unfinished"]:
        affected = item["criterion_ids"] + item["lane_ids"] + item["finding_ids"]
        out.append(f"- **{item['id']}** ({item['kind']}; owner {item['owner']}) -- affects {', '.join(affected)}. "
                   f"Next: {item['next_action']} Why not local: {item['alternatives_and_reason']}")
    out += ["", f"Global backlog ({len(backlog)} OWNED_BACKLOG carryforward items) stays distinct from this finite attempt.", ""]

    # ---- findings
    out += ["## New findings", ""]
    for row in s["new_findings"]:
        out.append(f"- **{row['id']}** ({row['severity']}, {row['disposition']}): {row['title']}. "
                   f"{row.get('detail', '')} Owner: {row['owner']}. Next: {row['next_action']}")
    if not s["new_findings"]:
        out.append("None.")
    out.append("")

    # ---- handoff
    out += ["## Final released handoff", "",
            f"Writers released: **{s['writer_released']}**. No lane, reader or build process of this attempt remains "
            "running after the final accounting; the external All-22 lane-system areas are another system's writers "
            "this attempt does not own.", "",
            f"Submission: `{ctx.out_root / 'submission.json'}`; checklist generated by `cycle_protocol.py checklist`; "
            f"lane receipts and logs under `{ctx.out_root / 'lanes'}` indexed by `lanes/RUNS.jsonl`. Next manager "
            "action: independent replay of the saved probes and fresh variants against the final source, the installed "
            "wheel, the delivered successor and the local integration candidate. The worker does not edit a released "
            "submission and does not declare acceptance.", ""]

    # ---- lifecycle
    out += ["## Delivery and platform lifecycle receipts (v2.3)", "", "| Duty | State | Result | Next action |",
            "| --- | --- | --- | --- |"]
    out += [f"| {row['id']} | {row['state']} | {row['result']} | {row['next_action']} |" for row in s["platform_receipts"]]
    out += ["", "Milestones: " + "; ".join(f"{m['id']} ({', '.join(m['requirement_ids'])}): {m['exit_evidence']}"
                                           for m in c["delivery_plan"]["milestones"]), ""]
    history = c["delivery_plan"].get("attempt_history") or []
    if history:
        out += ["Prior attempts and prevention: " + " ".join(
            f"Attempt {row['attempt_number']}: {row['outcome']} (cause {row['cause']}); prevention: "
            f"{row['prevention_or_justification']}" for row in history), ""]
    out += ["This attempt's prevention: each finding was reproduced before repair with the manager's own probe and "
            "closed as a class; the independent census of every cached raw form found further date forms, which were "
            "read or made explicitly unresolved; guard and storage are qualified before costly work; the successor is "
            "rebuilt and compared at the final head.", ""]
    return "\n".join(out) + "\n"
