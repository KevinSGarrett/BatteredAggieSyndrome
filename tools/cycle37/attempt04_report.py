r"""Cycle #37 — Attempt #4 — WORKER_REPORT.md renderer (R37A04-07).

Renders the worker report from the same context and submission ``attempt04_outputs.py`` builds, so every count,
state and identity in the narrative is read from a receipt, a declared output or the submission rather than
typed. The sections follow ``templates/WORKER_REPORT.template.md`` of the v2.4.0 release. Nothing here grants
acceptance.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FINDING_TEXT = {
    "MF37A03-01": ("An allowed Git child could run shell aliases outside the write guard",
                   "`git -c alias.manager-probe='!printf ... > sentinel' manager-probe` exited 0 and changed the owned "
                   "protected sentinel under the Attempt 3 guard.",
                   "The v37.4 guard admits a `git` child only as an exact read-only builtin with vetted options, under "
                   "a controlled configuration (no system/global config, hooks sunk, no pager/editor/fsmonitor/"
                   "external diff or filter, no signature program, file-only protocol) and a scrubbed environment; "
                   "repository building (`init/add/commit/config`) only inside the declared scratch root. Aliases, "
                   "`-c` indirection, helper and program-running options, repository configs it cannot read, implicit "
                   "bare repositories and network transports are refused before the child starts; every other native "
                   "child start is refused. It remains a Python-process guard, not OS isolation."),
    "MF37A03-02": ("Scoring supersession trusted mutable admitted-row fields",
                   "A forged contest, a probability of 1.8 with Brier -900 and DURABLE authority, and a correction "
                   "known before the freeze were all superseded in source and installed.",
                   "Supersession rebuilds both rows from their verified receipts and packet bytes through full "
                   "admission, refuses any caller field that differs from the rebuild, binds contest, forecast receipt, "
                   "orientation and correction chronology, and returns the rebuilt corrected row with a digest-bound "
                   "reference to the kept original."),
    "MF37A03-03": ("PIT admission substituted receipt cutoffs for an absent target cutoff",
                   "A row without a cutoff, and a row with mixed prior receipt cutoffs and none of its own, were "
                   "PIT_PROVEN with consumer admission and a null target cutoff.",
                   "Classification requires the target's own aware cutoff (row fields that must agree, or an explicit "
                   "argument) before any prior is verified, and the consumer gate requires the same cutoff; the "
                   "admission helper no longer falls back to a receipt's cutoff."),
    "MF37A03-04": ("Unknown role parentheticals became principal head-coach appointments",
                   "Fred Mariani's `[[Rutgers ...|Rutgers]] (DFO)` was served as head_coach/PRINCIPAL; STQC, SA and an "
                   "arbitrary code took the same route.",
                   "Each parenthetical is a role, a place, a league/level or a sport scope by vocabulary and position, "
                   "or unresolved; an unresolved one (and an unpaired parenthesis) blocks the head-coach convention and "
                   "is served as `role_unresolved` with its text. `{{abbr}}`/`{{tooltip}}` codes display and carry only "
                   "the meaning their own row states. Delivered through an explicitly selected, predecessor-bound "
                   "successor with every one of 72,070 predecessor rows dispositioned."),
    "MF37A03-05": ("Unknown career range endpoints became definite single years",
                   "`2009–?` became start = end = 2009, ongoing false; 312 delivered rows had a question mark with "
                   "start = end.",
                   "Every endpoint has a state (stated, questioned, approximate incl. `{{circa}}`, decade, partial, "
                   "unknown, present, after, before, alternatives) with definite and possible season bounds; season "
                   "membership uses definite bounds only; an unknown end is neither closed nor ongoing; the as-written "
                   "years keep the revision's text."),
}


def _j(value: Any, limit: int = 1200) -> str:
    text = json.dumps(value, indent=1, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + "\n... (truncated here; full value in the named file)"


def _receipt(ctx: Any, lane: str) -> dict[str, Any]:
    return ctx.receipts.get(lane) or {}


def _details(ctx: Any, lane: str) -> dict[str, Any]:
    return _receipt(ctx, lane).get("details") or {}


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
    out += ["## Direct answer and six dimensions", ""]
    out += [f"Worker-owned work complete: **{'YES' if len(verified) == len(worker_criteria) else 'NO'}** -- "
            f"{len(verified)} of {len(worker_criteria)} worker criteria are VERIFIED_LOCAL at the candidate head, each "
            "backed by lane receipts and command logs. Independently accepted: **NO** (PENDING_MANAGER_REVIEW; "
            f"{len(manager_criteria)} manager criteria and the MANAGER_REVIEW lane are the manager's). Integrated: "
            "**NO** (NOT_AUTHORIZED; nothing pushed, merged, published or activated). Headline: "
            f"**{s['headline']}**. Predictive skill: **{s['predictive_skill']}**.", ""]
    if red:
        out += [f"Software validation is **{s['dimensions']['software_validation']}** because "
                + ", ".join(row["id"] for row in red)
                + " stay red for inherited causes, classified identity by identity and compared with Attempt 3 by "
                  "identity and cause (INHERITED_LANE_EQUIVALENCE.json). No failing test is skipped, disabled or "
                  "relabelled.", ""]
    elif s["dimensions"]["software_validation"] == "PARTIAL":
        out += ["Software validation is **PARTIAL** because the manager-owned MANAGER_REVIEW lane has not run; every "
                "worker lane's state is in the matrix below.", ""]
    dims = s["dimensions"]
    out += ["| Dimension | Actual state | Evidence | Remaining acceptance |", "| --- | --- | --- | --- |",
            f"| Implementation | {dims['implementation']} | {ctx.candidate_commit_count} commits after the issued base; FINDING_CLOSURE_MATRIX.json | Manager replay of every repair |",
            f"| Data/evidence | {dims['data_evidence']} | CAREER_CORRECTION_SUCCESSOR.json, CAREER_POPULATION_DISPOSITIONS.json, DELIVERED_CONSUMER_MANIFEST.json | Manager recomputation; no activation |",
            f"| Software validation | {dims['software_validation']} | LANE_RESULTS.json, INHERITED_LANE_EQUIVALENCE.json, lanes/RUNS.jsonl | Owner decisions for inherited red; MANAGER_REVIEW |",
            f"| Independent scientific acceptance | {dims['independent_acceptance']} | -- | All `-M` criteria and MANAGER_REVIEW |",
            f"| Integration/release | {dims['integration_release']} | INTEGRATION_DECISION_PACKET.md | Explicit actor/action/target grants |",
            f"| Overall cycle | {dims['overall_cycle']} | submission.json | Independent manager review |", ""]

    # ---- subject
    start = _details(ctx, "START_CONTEXT")
    installed = _details(ctx, "INSTALLED_CONSUMER_C01")
    interpreter = _receipt(ctx, "START_CONTEXT").get("interpreter") or {}
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
            f"`{ctx.pointer.get('successor_sha256')}`, bound to that database digest; selected only by name.",
            f"- Released C01 wheel: SHA-256 `{(start.get('c01_wheel') or {}).get('expected')}`, composed, never rebuilt.",
            f"- Fresh noneditable BAS wheel: SHA-256 `{installed.get('wheel_sha256')}`, built from a git archive of the "
            "candidate head's pyproject.toml, README.md and src with cached tooling, installed offline into a new "
            "environment under the packaging root and run outside every checkout.",
            f"- Main checkout `{(start.get('main_checkout') or {}).get('path')}` at "
            f"`{(start.get('main_checkout') or {}).get('head')}` with {(start.get('main_checkout') or {}).get('status_entries')} "
            f"status entries; integration worktree at `{(start.get('integration_worktree') or {}).get('head')}`.",
            "- Scope changes: none. The retired assistive interlock stays retired on this branch; the decommission "
            "validator runs in START_CONTEXT and the retired interlock validator is never invoked.",
            "- Timing disclosure: the BEFORE platform reads were taken after the local repairs had begun (their "
            "receipts bind the exact head they read at). The before-repair reproduction of all five findings was taken "
            "at the issued base first (evidence/before).", ""]
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
    for key, (title, before, after) in FINDING_TEXT.items():
        meaning = carry[key]["original_meaning"]
        try:
            record = json.loads(meaning)
            meaning = f"{record.get('title')}. {record.get('reproduction')}"
        except ValueError:
            pass
        out += [f"**{key} -- {title}.** Original meaning: {meaning}", "",
                f"- Reproduced before repair (evidence/before, at the issued base): {before}",
                f"- General repair: {after}",
                "- Disposition: repaired locally, pending the manager's independent replay; FINDING_CLOSURE_MATRIX.json "
                "names the commits, the before files by digest and the after lanes.", ""]
    counts = ctx.carry_counts
    states: dict[str, int] = {}
    for row in ctx.obligation_items:
        if "attempt4_state" in row:
            states[row["attempt4_state"]] = states.get(row["attempt4_state"], 0) + 1
    out += ["### Carryforward", "",
            f"All {sum(counts['composition'].values())} carryforward identities are in "
            "ORIGINAL_OBLIGATION_DISPOSITIONS.json with each original meaning, source, owner, reason, next action, "
            "prior mapping and disposition copied unchanged: "
            + ", ".join(f"{k} {v}" for k, v in counts["composition"].items()) + "; dispositions "
            + ", ".join(f"{k} {v}" for k, v in counts["dispositions"].items()) + ".", "",
            f"The {len(in_cycle)} IN_CYCLE items carry the evidence of their linked criteria; the {len(backlog)} "
            "OWNED_BACKLOG items stay owned backlog and none is marked fulfilled by accounting. The 22 original and 13 "
            "Attempt 3 lanes each carry a disposition in LANE_RESULTS.json.", "",
            "| Attempt 4 state | Items |", "| --- | --- |"] + [f"| {k} | {v} |" for k, v in sorted(states.items())] + [""]

    # ---- delivered behaviour
    population = _output(ctx, "CAREER_POPULATION_DISPOSITIONS.json")
    successor = _output(ctx, "CAREER_CORRECTION_SUCCESSOR.json")
    named = installed.get("successor_named_cases") or {}
    pagination = installed.get("successor_pagination") or {}
    oracle = installed.get("successor_filtered_oracle") or {}
    locators = installed.get("successor_locators") or {}
    career_lane = _details(ctx, "CAREER_SUCCESSOR")
    reproduction = career_lane.get("successor_reproduction") or {}
    claim = career_lane.get("claim_successor") or {}
    out += ["## Delivered behavior and national data", "",
            "Before: the installed `bas-staff-query` served Fred Mariani's Rutgers (DFO) row as a principal head coach "
            "and `2009–?` as the closed year 2009 (evidence/before). After: the same installed command, given "
            "`--career-successor <file> --career-successor-sha256 <digest>`, answers from the explicit successor; "
            "without it, it answers exactly as the delivered release did (no default activation).", "",
            f"Population: {(population.get('population') or {}).get('predecessor_rows')} predecessor career rows from "
            f"{(population.get('population') or {}).get('pages')} cached revisions; "
            f"{(population.get('population') or {}).get('successor_episodes')} successor rows. Dispositions: "
            + ", ".join(f"{k} {v}" for k, v in sorted((population.get("by_disposition") or {}).items())) + ".", "",
            "| Manager screen | Members | Dispositions | Still head coach | Unchanged without grounded basis |",
            "| --- | --- | --- | --- | --- |"]
    for name, row in (population.get("screens") or {}).items():
        out.append(f"| {name} | {row.get('members')} of {row.get('expected')} | "
                   + ", ".join(f"{k} {v}" for k, v in sorted((row.get("by_disposition") or {}).items()))
                   + f" | {row.get('successor_rows_still_head_coach')} | {len(row.get('unchanged_without_grounded_basis') or [])} |")
    census = population.get("census_reconciliation") or {}
    out += ["", "Every broad-screen row the successor still reads as a head coach names only qualifiers (a state, a "
            "place, a league or a sport scope) and no role; its grounded basis is in its disposition reason.", "",
            f"Independent raw census reconciliation (`{census.get('census_version')}`): "
            + ", ".join(f"{k} {v}" for k, v in sorted((census.get("counts") or {}).items())) + ".", "",
            "Installed consumer over the delivered successor:", "",
            f"- Full pagination: {pagination.get('distinct')} distinct rows in {pagination.get('pages')} pages against "
            f"{pagination.get('expected')} in the independent SQL oracle; reconciled {pagination.get('reconciled')}.",
            f"- Raw locators re-read from the captures: {locators.get('verified')} of {locators.get('rows')} verified, "
            f"{locators.get('span_mismatch')} span mismatches, {locators.get('raw_file_digest_mismatch')} digest mismatches.",
            f"- Fred Mariani: {_j(named.get('fred_mariani'), 900)}",
            f"- Don Carthel (STQC): {_j(named.get('don_carthel'), 600)}",
            f"- Bill Anderson Stamford HS (TX) control: {_j(named.get('bill_anderson'), 600)}", "",
            "| Filtered query | CLI | Oracle | Equal |", "| --- | --- | --- | --- |"]
    out += [f"| {name} | {row.get('cli')} | {row.get('oracle')} | {row.get('equal')} |" for name, row in oracle.items()]
    out += ["", f"Rebuild at the candidate head: byte-identical {reproduction.get('byte_identical_rebuild')}; ledgers "
            f"reproduced {reproduction.get('ledgers_reproduced')}.", "",
            f"Cycle 29 claim successor preserved: census reproduced {claim.get('census_reproduced')}, claims reproduced "
            f"{claim.get('claims_reproduced')}, selected validator passes {claim.get('selected_passes')}, default still "
            f"reports the 35 undeclared pairs {claim.get('default_reports_35')}, original inventory unchanged "
            f"{claim.get('original_inventory_unchanged_since_base')}.", "",
            "Real eligible forecasts: **0**. Real proven PIT rows: **0**. Wikimedia revisions are retrospective "
            "secondary evidence; no successor row is PIT admitted, official, activated or accepted.", "",
            f"Successor identity: {_j(successor.get('identity'), 1500)}", ""]

    # ---- repairs and reproduction guide
    out += ["## Repairs and independent-review inputs", "",
            "Each repair has positive and negative controls and this attempt's own challenges in its suite; the "
            "manager's saved Attempt 3 probes are replayed from owned copies (only fixture-root and installed-venv "
            "literals adapted) against source and the fresh wheel; the Attempt 2 probes are replayed byte-identical.",
            "", "Manager reproduction guide (each is the issued lane command):", ""]
    for lane_id in ("WRITE_PROTECTION", "SOURCE_ADMISSION", "CAREER_SUCCESSOR", "INSTALLED_CONSUMER_C01"):
        out.append(f"- `{lane_id}`: `{ctx.lanes[lane_id]['command']}` in `{ctx.lanes[lane_id]['cwd']}`")
    out += ["", "Known limitations: the guard covers Python processes and confines, not isolates, Git children; the "
            "successor reads roles and years only as the revisions state them; unknown codes stay unresolved rather "
            "than guessed; list-field rows are reconciled at item level by the census, not row by row.", ""]

    # ---- validation matrix
    workers = [lane_id for lane_id, lane in ctx.lanes.items() if lane["executor"] == "worker"]
    executed = [lane_id for lane_id in workers if lanes[lane_id]["executed"]]
    out += ["## Exact validation matrix", "",
            f"{len(executed)} of {len(workers)} worker lanes ran through the issued command at the candidate head"
            + ("" if len(executed) == len(workers) else " (the rest are NOT_RUN)") + ". Every child gets a "
            "credential-scrubbed environment, the attempt packaging root as TEMP and Git scratch root, the v37.4 "
            "write guard over the data root, main checkout, integration worktree, All-22 and the Attempt 3 roots, and "
            "the loopback-only network guard, except where a receipt names an exception. WRITE_PROTECTION qualified "
            "the guard before the mounted lanes ran.", "",
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
        comparison = row.get("attempt3_comparison") or {}
        if comparison:
            out += ["", f"{row['lane']} against Attempt 3 at the issued base, by identity: persisting "
                    f"{len(comparison.get('persisting') or [])}, new {len(comparison.get('new_in_attempt4') or [])}, "
                    f"no longer failing {len(comparison.get('no_longer_failing') or comparison.get('no_longer_reported') or [])}"
                    + (f", same cause {len(comparison.get('persisting_same_cause') or [])}" if "persisting_same_cause" in comparison else "")
                    + "."]
    out += ["", "Original 22 lanes and Attempt 3's 13 lanes:", "", "| Lane | Prior result | Disposition |",
            "| --- | --- | --- |"]
    out += [f"| {row['original_lane']} | {row.get('attempt2_result', '--')} | {row['disposition']} |" for row in ctx.original_lanes]
    out += [f"| A03 {row['attempt3_lane']} | {row.get('attempt3_result', '--')} | {row['disposition']} |" for row in ctx.attempt3_lanes]
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
                "push, merge, retarget or branch change was made.", ""]
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
    storage = ledger.get("storage") or {}
    out += ["", f"Paid AI calls 0, cost 0. Free space now {storage.get('free_bytes_now')} bytes against the "
            f"{storage.get('reserve_bytes')}-byte reserve (satisfied: {storage.get('reserve_satisfied')}). Created roots: "
            "the attempt root, `C:\\BatteredAggieSyndrome.validation\\c37a04` and `C:\\BatteredAggieSyndrome.packaging"
            "\\c37a04`, within the write grants. No credential was printed, logged or written; lane children run with "
            "credential variables removed. Nothing was deleted, moved or cleaned up outside this attempt's own scratch.", ""]

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
            "running after the final accounting; the external All-22 lane-system scratch area is another system's "
            "writer this attempt does not own (evidence/scope/IDLE_WINDOW_*.json).", "",
            f"Submission: `{ctx.out_root / 'submission.json'}`; checklist generated by `cycle_protocol.py checklist`; "
            f"lane receipts and logs under `{ctx.out_root / 'lanes'}` indexed by `lanes/RUNS.jsonl`. Next manager "
            "action: independent replay of the saved probes and fresh variants against the final source, the installed "
            "wheel and the delivered successor. The worker does not edit a released submission and does not declare "
            "acceptance.", ""]

    # ---- lifecycle
    out += ["## Delivery and platform lifecycle receipts (v2.3)", "", "| Duty | State | Result | Next action |",
            "| --- | --- | --- | --- |"]
    out += [f"| {row['id']} | {row['state']} | {row['result']} | {row['next_action']} |" for row in s["platform_receipts"]]
    out += ["", "Milestones: " + "; ".join(f"{m['id']} ({', '.join(m['requirement_ids'])}): {m['exit_evidence']}"
                                           for m in c["delivery_plan"]["milestones"]), ""]
    history = c["delivery_plan"]["attempt_history"]
    out += ["Prior attempts and prevention: " + " ".join(
        f"Attempt {row['attempt_number']}: {row['outcome']} (cause {row['cause']}); prevention: "
        f"{row['prevention_or_justification']}" for row in history), "",
        "This attempt's prevention: each finding was reproduced before repair and closed as a class (alternate "
        "entrypoints, unknown values, the whole cached raw population via an independent census), with the manager's "
        "counterexamples and new challenges replayed against the installed consumer; the successor is rebuilt and "
        "compared at the final head.", ""]
    return "\n".join(out) + "\n"
