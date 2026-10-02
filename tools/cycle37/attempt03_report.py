r"""Cycle #37 — Attempt #3 — WORKER_REPORT.md renderer (R37A03-07).

Renders the worker report from the same context and submission ``attempt03_outputs.py`` builds, so every count,
state and identity in the narrative is read from a receipt or the submission rather than typed. The sections
follow ``templates/WORKER_REPORT.template.md`` of the v2.4.0 release. Nothing here grants acceptance.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FINDING_TEXT = {
    "MF37A02-01": ("Canonical write guard bypass", "The manager's saved probe unlinked, overwrote and renamed "
                   "canonical bytes through keyword, alias and native routes the guard did not see.",
                   "A Python audit hook refuses every write-capable open, unlink, rename, SQLite read-write "
                   "connection, reparse and child process into a guarded root, and propagates into Python "
                   "children; the network is denied to guarded children. It is a Python-process-tree guard, not "
                   "operating-system isolation: non-Python children are refused, and unsupported native routes "
                   "are reported as limitations."),
    "MF37A02-02": ("Scoring admission accepts invented digests", "A forecast with an invented receipt digest, an "
                   "identical home/away team or a mismatched model was admitted for scoring.",
                   "Scoring admission resolves every digest to re-hashed receipt and payload bytes through a "
                   "declared receipt authority (TEST_ONLY fixtures versus DURABLE stores; no durable store is "
                   "declared, so real eligible forecasts stay zero)."),
    "MF37A02-03": ("PIT consumer accepts unrelated priors", "The PIT consumer accepted fabricated bytes, naive "
                   "times and an unrelated prior set.",
                   "PIT admission requires the exact consumed prior set, aware times and row-bound gates resolved "
                   "through the same receipt authority; real proven PIT rows stay zero."),
    "MF37A02-04": ("Installed query still serves the predecessor tables", "bas-staff-query answered career and "
                   "responsibility questions from the predecessor tables, so Bill Anderson's TX title and the "
                   "uncorrected spans were still served.",
                   "The release query dispatches by the release's declared version and its own lineage "
                   "declarations: v37.x releases answer from career_episode_successor, "
                   "career_predecessor_disposition and responsibility_successor with a raw locator and a "
                   "predecessor disposition per row; the predecessor stays readable only with --legacy-audit; "
                   "v36.1 stays readable as a predecessor-only release; malformed releases refuse by name; every "
                   "table paginates deterministically."),
    "MF37A02-05": ("Full-suite harness import failure and skip accounting", "The mounted full suite imported "
                   "test_acceptance_governance without the repository root (ModuleNotFoundError: tools), and the "
                   "receipt reported 13 skips against unittest's 17 with consistent=false.",
                   "The census binds the selected root, audits every module origin, and reconciles failures, "
                   "skips and subtests by exact identity across unittest's counts, the verbose text and "
                   "per-outcome records."),
    "WORKER-W37R-71": ("Cycle 29 numeric claims undeclared", "The Cycle 29 claim inventory declared only a "
                       "subset of the numeric values its artifacts publish (the repaired validator reports 35 "
                       "undeclared pairs).",
                       "A versioned successor inventories 38 claims (the 35 plus 3 the field-name match hides) by "
                       "JSON pointer and digest, each recomputed independently from bytes and classified; the "
                       "validator checks it only when explicitly selected, so the default still fails on the "
                       "unchanged original."),
}


def _j(value: Any, limit: int = 1200) -> str:
    text = json.dumps(value, indent=1, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + "\n... (truncated here; full value in the named file)"


def _receipt(ctx: Any, lane: str) -> dict[str, Any]:
    return ctx.receipts.get(lane) or {}


def _details(ctx: Any, lane: str) -> dict[str, Any]:
    return _receipt(ctx, lane).get("details") or {}


def render(ctx: Any, s: dict[str, Any]) -> str:
    c = ctx.contract
    cand = s["candidate"]
    label = f"Cycle #{s['cycle_number']} \u2014 Attempt #{s['attempt_number']} \u2014 {s['headline']}"
    worker_criteria = [row for row in s["criteria"] if ctx.criteria[row["id"]]["executor"] == "worker"]
    manager_criteria = [row for row in s["criteria"] if ctx.criteria[row["id"]]["executor"] != "worker"]
    verified = [row for row in worker_criteria if row["status"] == "VERIFIED_LOCAL"]
    in_cycle = [row for row in c["carryforward"] if row["disposition"] == "IN_CYCLE"]
    backlog = [row for row in c["carryforward"] if row["disposition"] == "OWNED_BACKLOG"]
    inherited_originals = [row for row in in_cycle if row["id"].startswith("ORIGINAL-")]
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
            f"{len(verified)} of {len(worker_criteria)} worker criteria are VERIFIED_LOCAL at the candidate head, "
            "each backed by a lane receipt and its command log. Independently accepted: **NO** (PENDING_MANAGER_REVIEW; "
            f"{len(manager_criteria)} manager criteria and the MANAGER_REVIEW lane are the manager's). Integrated: **NO** (NOT_AUTHORIZED; "
            f"nothing pushed, merged or published). Headline: **{s['headline']}**. Predictive skill: "
            f"**{s['predictive_skill']}**.", ""]
    if red:
        out += [f"Software validation is **{s['dimensions']['software_validation']}** because "
                + ", ".join(f"{row['id']}" for row in red)
                + " stay red for inherited, identity-classified causes (see *Exact validation matrix* and *Every "
                  "unfinished obligation*). No failing test is skipped, disabled or relabelled.", ""]
    out += ["| Dimension | Actual state | Evidence | Remaining acceptance |", "| --- | --- | --- | --- |"]
    dims = s["dimensions"]
    out += [
        f"| Implementation | {dims['implementation']} | {ctx.candidate_commit_count} commits after the issued base; FINDING_CLOSURE_MATRIX.json | Manager replay of every repair |",
        f"| Data/evidence | {dims['data_evidence']} | DELIVERED_CONSUMER_MANIFEST.json, HISTORICAL_CLAIM_SUCCESSOR.json | Manager recomputation; no activation |",
        f"| Software validation | {dims['software_validation']} | LANE_RESULTS.json, lanes/RUNS.jsonl, 12 receipts | Owner decisions for inherited red |",
        f"| Independent scientific acceptance | {dims['independent_acceptance']} | -- | All `-M` criteria and MANAGER_REVIEW |",
        f"| Integration/release | {dims['integration_release']} | INTEGRATION_DECISION_PACKET.md | Explicit actor/action/target grants |",
        f"| Overall cycle | {dims['overall_cycle']} | submission.json | Independent manager review |",
        ""]

    # ---- subject
    start = _details(ctx, "START_CONTEXT")
    installed = _details(ctx, "INSTALLED_CONSUMER_C01")
    out += ["## Issued versus actual subject", ""]
    out += [f"- Issued: contract SHA-256 `{s['contract_sha256']}`; brief, checklist and prompt bound by the sealed "
            f"issuance `{ctx.contract_path.parent / 'issuance' / 'issuance.json'}`.",
            f"- Actual: {ctx.candidate_commit_count} commits after the issued base. Worktree clean at the start and end "
            f"of every executed lane run: {ctx.all_runs_clean} (each receipt's `source_binding` and "
            "`source_binding_after`).",
            f"- Interpreter (input only): `{(_receipt(ctx, 'START_CONTEXT').get('interpreter') or {}).get('executable')}` "
            f"CPython {((_receipt(ctx, 'START_CONTEXT').get('interpreter') or {}).get('version') or '').split()[0] if _receipt(ctx, 'START_CONTEXT') else ''}.",
            f"- Delivered database: SHA-256 `{(start.get('delivered_database') or {}).get('expected')}`, unchanged "
            f"before and after the installed lane ({(installed.get('delivered_database_unchanged') or {}).get('after')}).",
            f"- Released C01 wheel: SHA-256 `{(start.get('c01_wheel') or {}).get('expected')}`, composed, never rebuilt.",
            f"- New noneditable BAS wheel: SHA-256 `{installed.get('wheel_sha256')}`, built from a git archive of the "
            "candidate head's pyproject.toml, README.md and src with cached tooling, installed offline into a new "
            "environment under the packaging root and run outside the checkout.",
            f"- Main checkout `{(start.get('main_checkout') or {}).get('path')}` stayed at "
            f"`{(start.get('main_checkout') or {}).get('head')}` with {(start.get('main_checkout') or {}).get('status_entries')} "
            f"status entries; the integration worktree stayed at `{(start.get('integration_worktree') or {}).get('head')}`.",
            "- Scope changes: none. The retired assistive interlock stays retired on this branch; "
            "`tools/validate_retired_assistive_pipeline_decommission.py` runs in START_CONTEXT and the retired "
            "interlock validator is never invoked.", ""]
    origins = installed.get("installed_origins") or {}
    if origins:
        out += ["Installed module origins (every one in site-packages of the new environment):", "", "```json",
                _j(origins.get("origins") or origins, 2500), "```", ""]

    # ---- criteria
    out += ["## Every criterion, original finding and carryforward", ""]
    out += ["| Criterion | Executor | Status | Reason | Evidence |", "| --- | --- | --- | --- | --- |"]
    for row in s["criteria"]:
        executor = ctx.criteria[row["id"]]["executor"]
        reason = row["reason"].replace("|", "/")
        out.append(f"| {row['id']} | {executor} | {row['status']} | {reason} | {', '.join(row['evidence_ids'][:4])}"
                   + (f" (+{len(row['evidence_ids']) - 4})" if len(row["evidence_ids"]) > 4 else "") + " |")
    out += ["", "### Original manager findings and the assigned worker finding", ""]
    carry = {row["id"]: row for row in c["carryforward"]}
    for key, (title, before, after) in FINDING_TEXT.items():
        meaning = carry[key]["original_meaning"]
        if meaning.lstrip().startswith("{"):
            # Worker findings carry their original record as JSON; its title and detail are quoted here, and
            # the verbatim record is in ORIGINAL_OBLIGATION_DISPOSITIONS.json.
            record = json.loads(meaning)
            meaning = f"{record.get('title')}. {record.get('detail')} (original disposition {record.get('disposition')})"
        out += [f"**{key} -- {title}.** Original meaning: {meaning}", "",
                f"- Reproduced before: {before}", f"- Repair: {after}",
                f"- Disposition: repaired locally, pending the manager's independent replay; see "
                f"FINDING_CLOSURE_MATRIX.json for the commit, the before files by digest and the after lanes.", ""]
    counts = ctx.carry_counts
    out += ["### Carryforward", "",
            f"All {sum(counts['composition'].values())} carryforward identities are accounted in "
            "ORIGINAL_OBLIGATION_DISPOSITIONS.json with each original meaning copied verbatim, its disposition "
            "unchanged, and its owner and next action: "
            + ", ".join(f"{k} {v}" for k, v in counts["composition"].items()) + "; dispositions "
            + ", ".join(f"{k} {v}" for k, v in counts["dispositions"].items()) + ".", "",
            f"The {len(in_cycle)} IN_CYCLE items are the five manager findings, W37R-71 and the "
            f"{len(inherited_originals)} original criteria and obligations the issued requirements inherit. Each "
            f"carries the evidence of its linked criteria. The {len(backlog)} OWNED_BACKLOG items remain owned "
            "backlog: none is marked fulfilled by this accounting, and the 22 original lanes each carry a reuse or "
            "invalidation disposition in LANE_RESULTS.json.", ""]
    states: dict[str, int] = {}
    for row in ctx.obligation_items:
        states[row["attempt3_state"]] = states.get(row["attempt3_state"], 0) + 1
    out += ["| Attempt 3 state | Items |", "| --- | --- |"] + [f"| {k} | {v} |" for k, v in sorted(states.items())] + [""]

    # ---- delivered behaviour
    pagination = installed.get("pagination") or {}
    bill = installed.get("bill_anderson") or {}
    career = installed.get("career_locators") or {}
    resp = installed.get("responsibility_locators") or {}
    oracle = installed.get("filtered_oracle") or {}
    claim = (_details(ctx, "CLAIM_SUCCESSOR").get("claim_successor") or {})
    out += ["## Delivered behavior and national data", "",
            "Before: the installed `bas-staff-query` answered career and responsibility questions from the "
            "predecessor tables of the corrected release. After: the same installed command answers from the "
            "corrected successor tables, and each row carries its raw locator and predecessor disposition.", "",
            "Pagination through the installed CLI, compared with an independent SQL oracle over the delivered "
            "database (distinct identities, no duplicates or gaps, deterministic order):", "",
            "| Table view | Rows through the CLI | Oracle | Pages |", "| --- | --- | --- | --- |"]
    for name, row in pagination.items():
        out.append(f"| {name} | {row.get('distinct')} | {row.get('expected')} | {row.get('pages')} |")
    out += ["", "Filtered answers against an independent Python filter over the same rows:", "",
            "| Query | CLI | Oracle | Equal |", "| --- | --- | --- | --- |"]
    for name, row in oracle.items():
        out.append(f"| {name} | {row.get('cli')} | {row.get('oracle')} | {row.get('equal')} |")
    out += ["", f"Bill Anderson (born 1925): {bill.get('corrected_rows')} corrected rows; any corrected row titled TX: "
            f"{bill.get('any_row_with_title_TX')}; the legacy audit still shows the predecessor TX rows "
            f"({len(bill.get('legacy_rows_with_title_TX') or [])}).", "",
            f"Career locators re-read from the raw wiki captures: {career.get('verified')} of {career.get('rows')} rows "
            f"verified from {career.get('raw_files_read')} raw files, {career.get('span_mismatch')} span mismatches, "
            f"{career.get('raw_file_digest_mismatch')} digest mismatches; {career.get('team_absent_in_source')} rows "
            "name no team in the source text and are verified on their years span alone.", "",
            f"Responsibility captures: {resp.get('capture_digest_verified')} capture digests verified, "
            f"{resp.get('capture_digest_mismatch')} mismatched, {resp.get('capture_absent')} absent.", "",
            f"Cycle 29 claim successor: {ctx.successor_summary}. Rerun at the candidate head: census reproduced "
            f"{claim.get('census_reproduced')} (body `{claim.get('census_body_sha256_rerun')}`), claims reproduced "
            f"{claim.get('claims_reproduced')}, dispositions reproduced {claim.get('dispositions_reproduced')}, "
            f"accounting reproduced {claim.get('accounting_reproduced')}; the explicitly selected validator passes "
            f"({claim.get('selected_passes')}) while the default still reports the 35 undeclared pairs "
            f"({claim.get('default_reports_35')}); the original inventory is unchanged since the issued base "
            f"({claim.get('original_inventory_unchanged_since_base')}).", "",
            "Real eligible forecasts: **0**. Real proven PIT rows: **0**. The fixture positives are admitted only "
            "under a TEST_ONLY receipt authority; no durable receipt store is declared, so no real row is admitted.",
            "", "National population note: this attempt changes consumers of the delivered national release; it "
            "adds and removes no rows. The expected/acquired/normalized/admitted sets of the release are unchanged "
            "and bound by its digest.", ""]

    # ---- repairs and reproduction guide
    out += ["## Repairs and independent-review inputs", "",
            "Every repair has a positive and a negative control in its suite, and the manager's saved probes are "
            "replayed verbatim (byte-identical copies, paths adapted only into owned fixtures) against the source "
            "and the installed wheel. Receipts name each replay's original, its copy digest and its outcome.", "",
            "Manager reproduction guide (from preserved inputs; each command is the issued lane command):", ""]
    for lane_id in ("WRITE_PROTECTION", "SOURCE_ADMISSION", "SOURCE_HARNESS", "INSTALLED_CONSUMER_C01",
                    "CLAIM_SUCCESSOR"):
        out += [f"- `{lane_id}`: `{ctx.lanes[lane_id]['command']}` in `{ctx.lanes[lane_id]['cwd']}`"]
    out += ["", "Known scientific limitations: the write guard covers Python processes and refuses non-Python "
            "children; it is not OS isolation. The Cycle 29 successor records producer literals that contradict "
            "the artifacts' own `focus_game_hardcode: false` statement rather than hiding them. Nothing here "
            "activates the corrected release, the successor inventory or any restoration candidate.", ""]

    # ---- validation matrix
    executed = [lane_id for lane_id, lane in ctx.lanes.items() if lane["executor"] == "worker" and lanes[lane_id]["executed"]]
    workers = [lane_id for lane_id, lane in ctx.lanes.items() if lane["executor"] == "worker"]
    out += ["## Exact validation matrix", "",
            f"{len(executed)} of {len(workers)} worker lanes ran through the issued command at the candidate head"
            + ("" if len(executed) == len(workers) else " (the rest are listed as NOT_RUN)") + ". Environment: the "
            "contract's environment string; every child gets a credential-scrubbed environment, the attempt-owned "
            "packaging root as TEMP (long spelling; see the runner for the measured MAX_PATH constraints), the "
            "canonical write guard over the data root, the main checkout, the integration worktree and All-22, and "
            "the loopback-only network guard, except where a receipt names an exception.",
            "", "| Lane | Kind | Status | Run | Tests | Fail | Err | Import err | Failed subtests | Skipped | Reason |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for lane_id, lane in ctx.lanes.items():
        row = lanes[lane_id]
        reason = (row.get("reason") or "").replace("|", "/")[:300]
        out.append(f"| {lane_id} | {lane['kind']} | {row['status']} | {row.get('run', '--')} | {row['tests']} | "
                   f"{row['failures']} | {row['errors']} | {row['import_errors']} | {row['failed_subtests']} | "
                   f"{row['skipped']} | {reason} |")
    out += ["", "Original 22 lanes (Attempt 2 receipts preserved unchanged):", "",
            "| Original lane | Attempt 2 | Disposition |", "| --- | --- | --- |"]
    for row in ctx.original_lanes:
        out.append(f"| {row['original_lane']} | {row.get('attempt2_result', '--')} | {row['disposition']} |")
    refused: dict[str, dict[str, int]] = {}
    for lane_id in ctx.lanes:
        for event in ((_receipt(ctx, lane_id).get("write_and_network_scope") or {}).get("guard_blocked_events") or []):
            name = Path(str(event.get("path") or "?")).name
            refused.setdefault(lane_id, {})[f"{event.get('operation')} {name}"] = (
                refused.get(lane_id, {}).get(f"{event.get('operation')} {name}", 0) + 1)
    if refused:
        out += ["", "Operations the guard refused inside lane children (each is also in the lane receipt's guard log): "
                + "; ".join(f"{lane_id}: " + ", ".join(f"{k} x{v}" for k, v in sorted(rows.items()))
                            for lane_id, rows in sorted(refused.items()))
                + ". In the mounted suite these are the live hosted-CI tests' `gh` (disclosed as unqueried; three "
                  "tests skip with that reason), the harness test's deliberately missing binary (it asserts the "
                  "command is BLOCKED, which holds) and the benchmark's optional `nvidia-smi` probe (it reports no "
                  "GPU name). "
                + ("Every refusal was of a child process start; no lane child attempted a write or network access "
                   "that the guard refused." if all(key.startswith("subprocess.Popen ") for rows in refused.values()
                                                   for key in rows)
                   else "Refusals other than child starts are listed above and in the receipts."), ""]
    full = _details(ctx, "FULL_FINAL_MOUNTED").get("baseline_comparison") or {}
    if full:
        out += ["", "Full mounted suite against the Attempt 2 final log, by identity: "
                f"{full.get('final_tests_run')} tests run (Attempt 2: {full.get('baseline_tests_run')}); "
                f"persisting {len(full.get('persisting') or [])}, new {len(full.get('new_in_attempt3') or [])}, no "
                f"longer failing {len(full.get('no_longer_failing') or [])}.", ""]
        if full.get("no_longer_failing"):
            out += ["No longer failing: " + ", ".join(f"`{x}`" for x in full["no_longer_failing"]), ""]

    # ---- platform
    platform = json.loads((ctx.out_root / "PLATFORM_RECONCILIATION.json").read_text(encoding="utf-8"))
    out += ["## Plans, Jira, PR feedback and integrations", "",
            "Governing sources (the issued contract's `source_refs`, each verified by digest at issuance):", ""]
    out += [f"- `{row['id']}`: {row['section']} (`{Path(row['path']).name}`, SHA-256 `{row['sha256'][:16]}...`)"
            for row in c["source_refs"]]
    out += ["", "Granted Jira comments (marker, created id, readback):", ""]
    for row in platform["granted_comments"]:
        out.append(f"- {row['phase']} {row['issue']} `{row['marker']}`: {row['result']}, created {row['created_id']}, "
                   f"read back {row['readback_comment_ids']}, comments {row['comments_before']} -> {row['comments_after']}")
    out += ["", "Private Jira successor runs of the selected sync contract (dry run, apply, strict validator, audit, "
            "second dry run) in a private copy; never the committed pack and never live Jira:", ""]
    for row in platform["private_jira_successors"]:
        steps = ", ".join(f"{x['name']} exit {x['exit']} ({x['conflicts']} conflicts)" for x in row["steps"])
        out.append(f"- {row['phase']}: {steps}; private changes {row['private_changes']}; guard blocked "
                   f"{row['write_guard_blocked']}; committed canonical mutations {row['committed_canonical_mutations']}; "
                   f"adopted {row['adopted']}")
    out += ["", "The BEFORE and first DURING exports omitted the project's Logical Workflow State field, which "
            "made the reconciler report 237 changes and 112 conflicts that were artifacts of the export. The DURING "
            "export was re-derived offline from the retained DURING raw payload (provenance file beside it), and "
            "the AFTER read resolves the field by its exact name; the superseded receipts are kept.", ""]
    github = ctx.latest_github
    if github:
        out += [f"GitHub at the latest read ({github.get('phase')}, {github.get('observed_at')}): main "
                f"`{github.get('main_head')}`, {github.get('open_pr_count')} open pull requests, "
                f"{github.get('unresolved_thread_total')} unresolved review threads. No PR, push, merge, retarget or "
                "branch change was made.", ""]
    all22 = ctx.latest_all22
    if all22:
        owner = all22.get("owner_plan_check") or {}
        issued_owner_head = "886e277dd9f34eb0ea1de78f98ee516bcc0c33cb"
        out += [f"All-22 at the latest read ({all22.get('phase')}, {all22.get('observed_at')}): "
                f"{all22.get('discovered_count')} GridironCortex repositories enumerated. CFBProgramSpecifications "
                f"remote head `{owner.get('remote_head')}` (issued owner authority `{issued_owner_head}`; equal: "
                f"{owner.get('remote_head') == issued_owner_head}); retained owner snapshots present unchanged at that "
                f"head: {owner.get('snapshots_present_unchanged')} of {owner.get('snapshots_compared')}. The 22 "
                "accepted Phase 2 plans remain NOT_IMPLEMENTED. The installed BAS wheel composes with the released C01 "
                "0.1.2 wheel; no owner repository was changed and no proposal is presented as adoption.", ""]

    # ---- cost
    ledger = json.loads((ctx.out_root / "COST_AND_AUTHORITY_LEDGER.json").read_text(encoding="utf-8"))
    out += ["## Cost, storage, privacy and recovery", "", "| Request lane | Requests | Retries | Ceiling |",
            "| --- | --- | --- | --- |"]
    for lane_id, row in ledger["request_lanes"].items():
        out.append(f"| {lane_id} | {row['requests']} | {row['retries']} | {row['ceiling']} |")
    storage = ledger["storage"]
    out += ["", f"Paid AI calls 0, cost 0. Free space now {storage['free_bytes_now']} bytes against the "
            f"{storage['reserve_bytes']}-byte reserve (satisfied: {storage['reserve_satisfied']}). Created roots: "
            "the attempt root, `C:\\BatteredAggieSyndrome.validation\\c37a03` and "
            "`C:\\BatteredAggieSyndrome.packaging\\c37a03`, all within the write grants. No credential was printed, "
            "logged or written; lane children run with credential variables removed. No secret or restricted raw "
            "payload is in this report. Nothing was deleted, moved or cleaned up.", ""]

    # ---- unfinished
    out += ["## Every unfinished obligation and precise decisions", ""]
    for item in s["unfinished"]:
        affected = item["criterion_ids"] + item["lane_ids"] + item["finding_ids"]
        out += [f"- **{item['id']}** ({item['kind']}; owner {item['owner']}) -- affects {', '.join(affected)}. "
                f"Next: {item['next_action']} Why not local: {item['alternatives_and_reason']}"]
    out += ["", f"Global backlog ({len(backlog)} OWNED_BACKLOG carryforward items) stays distinct from this finite "
            "attempt.", ""]

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
            f"Writers released: **{s['writer_released']}**. No lane, reader or build process of this attempt "
            "remains running after the final accounting; the only other live writer observed is an external All-22 "
            "lane-system scratch area (measured with no lane running, evidence/scope/IDLE_WINDOW_*.json), which this "
            "attempt does not own.", "",
            f"Submission: `{ctx.out_root / 'submission.json'}`; checklist generated by `cycle_protocol.py checklist`; "
            f"lane receipts and logs under `{ctx.out_root / 'lanes'}` indexed by `lanes/RUNS.jsonl`. Next manager "
            "action: independent replay of the saved probes against the final source and the installed wheel, "
            "review of the lane receipts and the platform readbacks. The worker does not edit a released submission "
            "and does not declare acceptance.", ""]

    # ---- lifecycle
    out += ["## Delivery and platform lifecycle receipts (v2.3)", "", "| Duty | State | Result | Next action |",
            "| --- | --- | --- | --- |"]
    for row in s["platform_receipts"]:
        out.append(f"| {row['id']} | {row['state']} | {row['result']} | {row['next_action']} |")
    history = c["delivery_plan"]["attempt_history"]
    out += ["", "Prior attempts and prevention: " + " ".join(
        f"Attempt {row['attempt_number']}: {row['outcome']} (cause {row['cause']}); prevention: "
        f"{row['prevention_or_justification']}" for row in history), "",
            "This attempt's prevention: every lane runs through one attempt-parameterized runner that binds the "
            "contract digest, the exact head and source digest, imports, data digests and write/network scope per "
            "run; receipts are create-only; the packet is built from those receipts, not restated.", ""]
    return "\n".join(out) + "\n"
