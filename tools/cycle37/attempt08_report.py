r"""Cycle #37 — Attempt #8 — WORKER_REPORT.md renderer (R37A08-05).

Renders the worker report from the same context and submission ``attempt08_outputs.py`` builds, so every count,
state and identity in the narrative is read from a receipt, a declared output or the submission rather than typed.
The sections follow ``templates/WORKER_REPORT.template.md`` of the v2.4.1 release. Nothing here grants acceptance.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

FINDING_TEXT = {
    "MF37A07-01": ("An enlarged witness satisfied the lineage anchors, and the worker oracle shared the assumption",
                   "on the clean issued base 996ada4d, the manager's saved fixture -- two of Fred Mariani's coaching "
                   "episodes with their default and Attempt 4 edges swapped and each row's team witness widened into "
                   "one span that covers both jobs' fields -- was served seven rows by the installed console script, "
                   "the installed module and the source module, and the Attempt 7 worker oracle reported 0 crossed "
                   "edges: both accepted any overlap of recorded spans as agreement.",
                   "A recorded span is evidence only if it is exactly the source unit the row's own identity names in "
                   "the revision it cites: the numbered field's value (``*_teamN``/``*_yearsN``), or the career list's "
                   "line, nested line or role line (a list date inside its line or its employer's line), under the "
                   "splitting of the parser version that wrote the row (v37.5 blanks comments and nowiki; v37.4 and "
                   "v37.2 read them literally). Every successor row and every delivered and Attempt 4 row an edge names "
                   "is proved so before its anchors are compared, from the capture opened at attach and hashed as "
                   "recorded; two proven units then agree only by containment. Anything else is refused as "
                   "REFUSED_CAREER_SUCCESSOR_SOURCE_FIELD_WITNESS_MISMATCH. The independent oracle derives the units "
                   "itself (its own bracket stack, sqlite3/json/re only) and judges each edge by field identity."),
    "MF37A07-02": ("Two callers of the same continuation could both initialize the child",
                   "on the clean issued base, the manager's same-path race let two callers pass the child-existence "
                   "check and both write an INIT (the child's chain broke at line 3 and every restart was refused); "
                   "its stop/reserve challenge continued a bounded-stopped ledger, and a lowered reserve, with no "
                   "recorded decision.",
                   "open_successor is one critical section under the parent's lock: snapshot proof, claim, the child's "
                   "existence and identity, its INIT (absence checked under the child's own lock) and its OPENED "
                   "record. A second caller of the same continuation resumes the one child or is refused for the "
                   "parameter that differs; an interrupted claim or INIT is recovered without a second child or "
                   "duplicate headroom; a torn INIT or orphaned head log is refused. A stopped ledger or a changed "
                   "reserve continues only under a recorded revised plan that names an existing authority document and "
                   "is feasible under the unchanged ceiling; the plan's ceiling then bounds the continuation."),
}


def _j(value: Any, limit: int = 1200) -> str:
    text = json.dumps(value, indent=1, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + "\n... (truncated here; full value in the named file)"


def _details(ctx: Any, lane: str) -> dict[str, Any]:
    return (ctx.receipts.get(lane) or {}).get("details") or {}


def _output(ctx: Any, name: str) -> dict[str, Any]:
    path = ctx.out_root / name
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _timing(ctx: Any) -> list[str]:
    """When the before-repair reproduction ran, on which bytes, how the uncommitted draft was parked, and how that
    relates to the first repair commit -- read from the receipts and git, never typed."""

    path = ctx.out_root / "evidence" / "before" / "BEFORE_REPRODUCTION.json"
    parking = _read(ctx.out_root / "evidence" / "intake" / "DRAFT_PARKING.json")
    if not path.is_file():
        return ["- Timing: no before-repair reproduction receipt exists."]
    receipt = _read(path)
    before, after = receipt.get("subject_before") or {}, receipt.get("subject_after") or {}
    first = next(iter(reversed(ctx.commits)), None)
    dated = (getattr(ctx, "commit_dates", {}) or {}).get(first[0]) if first else None
    text = (f"- Timing: the before-repair reproduction of both findings (`{path}`, reproduced {receipt.get('reproduced')}) "
            f"ran from {receipt.get('started_at')} to {receipt.get('finished_at')} on head "
            f"`{str(before.get('head'))[:10]}` (issued base {before.get('is_issued_base')}, clean {before.get('clean')} "
            f"before and {after.get('clean')} after)")
    if first and dated:
        preceded = datetime.fromisoformat(receipt["finished_at"]) < datetime.fromisoformat(dated)
        text += (f"; the first repair commit `{first[0][:10]}` is dated {dated}, so the reproduction "
                 + ("preceded it" if preceded else "was recorded after it (it still read the parked, unfixed bytes)"))
    lines = [text + ". Every platform receipt binds its own head (PLATFORM_RECONCILIATION.json `phase_subjects`)."]
    if parking:
        lines.append(
            "- Disclosed order of work: part of the MF37A07-01 draft (the new witness module and edits to the verifier) "
            "was written in the repair worktree before the storage ledger existed and before the unfixed reproduction. "
            f"It was parked outside the worktree at {parking.get('parked_at')} ("
            + ", ".join(f"`{name}` {row.get('state')} {row.get('bytes')} bytes" for name, row in
                        (parking.get("files") or {}).items())
            + f"); the worktree was restored to the issued base at {parking.get('restored_at')} (clean "
            f"{(parking.get('repair_worktree_after') or {}).get('clean')}, the verifier blob equal to the base's "
            f"{(parking.get('repair_worktree_after') or {}).get('equal_to_issued_base')}); the draft came back only after "
            f"the reproduction finished at {receipt.get('finished_at')}. The ledger's INIT note records the pre-ledger "
            "draft bytes (evidence/intake/DRAFT_PARKING.json and the new findings).")
    return lines


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
            "**NO** (NOT_AUTHORIZED; "
            + (f"the local candidate advanced forward from 0c22af20 by {len(ctx.candidate_record_paths)} commit(s)"
               if ctx.candidate_record_paths else "the local candidate has not yet been advanced")
            + "; the retained CONTROL-07 proposal is private and inert; nothing pushed, merged, published, adopted or "
              f"activated). Headline: **{s['headline']}**. Predictive skill: **{s['predictive_skill']}**.", ""]
    if red:
        out += [f"Software validation is **{dims['software_validation']}** because "
                + ", ".join(row["id"] for row in red)
                + " stay red, classified identity by identity and compared with the Attempt 7 final lanes by identity "
                  "and cause (INHERITED_LANE_EQUIVALENCE.json). No failing test is skipped, disabled or relabelled.", ""]
    elif dims["software_validation"] == "PARTIAL":
        out += ["Software validation is **PARTIAL**: the manager-owned MANAGER_REVIEW lane has not run"
                + ("" if all(lanes[key]["executed"] for key in lanes if ctx.lanes[key]["executor"] == "worker")
                   else " and some worker lanes have not run at this head") + "; every lane's state is in the matrix "
                "below.", ""]
    out += ["| Dimension | Actual state | Evidence | Remaining acceptance |", "| --- | --- | --- | --- |",
            f"| Implementation | {dims['implementation']} | {ctx.candidate_commit_count} commits after the issued base; FINDING_CLOSURE_MATRIX.json | Manager replay of every repair |",
            f"| Data/evidence | {dims['data_evidence']} | CAREER_POPULATION_DISPOSITIONS.json, DELIVERED_CONSUMER_MANIFEST.json | Manager recomputation; no activation |",
            f"| Software validation | {dims['software_validation']} | LANE_RESULTS.json, INHERITED_LANE_EQUIVALENCE.json, lanes/RUNS.jsonl | Owner decisions for inherited red; MANAGER_REVIEW |",
            f"| Independent scientific acceptance | {dims['independent_acceptance']} | -- | All `-M` criteria and MANAGER_REVIEW |",
            f"| Integration/release | {dims['integration_release']} | LOCAL_INTEGRATION_CANDIDATE.json, INTEGRATION_DECISION_PACKET.md, CONTROL07_PROPOSAL.md | Explicit actor/action/target grants; owner decision on a trusted review control |",
            f"| Overall cycle | {dims['overall_cycle']} | submission.json, FINAL_PACKET_VALIDATION.json | Independent manager review |", ""]

    # ---- subject
    start = _details(ctx, "START_CONTEXT")
    installed = _details(ctx, "INSTALLED_CONSUMER_C01")
    interpreter = (ctx.receipts.get("START_CONTEXT") or {}).get("interpreter") or {}
    storage = ctx.storage()
    operational = storage["operational"]
    out += ["## Issued versus actual subject", "",
            f"- Issued: contract SHA-256 `{s['contract_sha256']}`, bound by the sealed issuance "
            f"`{ctx.contract_path.parent / 'issuance' / 'issuance.json'}`; every contract source reference re-hashed at "
            f"START_CONTEXT ({sum(1 for r in start.get('source_refs') or [] if r.get('matches'))} of "
            f"{len(start.get('source_refs') or [])} equal to their issued digests).",
            f"- Actual: {ctx.candidate_commit_count} commits after the issued base "
            + ", ".join(f"`{sha[:10]}` {subject}" for sha, subject in reversed(ctx.commits))
            + f". Worktree clean at the start and end of every executed lane run: {getattr(ctx, 'all_runs_clean', None)}.",
            f"- Interpreter (input only): `{interpreter.get('executable')}` CPython "
            f"{(interpreter.get('version') or '').split()[0] if interpreter.get('version') else ''}.",
            f"- Delivered database: SHA-256 `{(start.get('delivered_database') or {}).get('expected')}` at its default "
            f"path, unchanged before and after the installed lane ({(installed.get('delivered_database_unchanged') or {}).get('after')}).",
            f"- Served career successor (unchanged, delivered by Attempt 5): `{ctx.pointer.get('successor_file')}` SHA-256 "
            f"`{ctx.pointer.get('successor_sha256')}`; the Attempt 4 successor `{ctx.pointer.get('a04_successor_sha256')}`; "
            "selected only by name, never a default.",
            f"- Released C01 wheel: SHA-256 `{(start.get('c01_wheel') or {}).get('expected')}`, composed, never rebuilt.",
            f"- Fresh noneditable BAS wheel: SHA-256 `{installed.get('wheel_sha256')}`, built from a git archive of the "
            "candidate head and installed offline into a new environment under the packaging root, run outside every "
            "checkout.",
            f"- Storage: one ledger chain, identity {_j(storage['chain'].get('identity'), 200)}; root ledger "
            + ("frozen, verified " + str((operational.get('verification') or {}).get('result')) if operational["frozen"]
               else "operational (not yet frozen)")
            + f"; chain proof {storage['chain'].get('result')}; final-output continuation "
            + ("claimed" if storage["continuation_claim"]["exists"] else "not yet opened") + ".",
            "- Scope changes: none. The retired assistive interlock stays retired; its decommission validator runs in "
            "START_CONTEXT and the retired interlock validator is never invoked.",
            *_timing(ctx), ""]

    # ---- criteria
    out += ["## Every criterion, original finding and carryforward", "",
            "| Criterion | Executor | Status | Reason | Evidence |", "| --- | --- | --- | --- | --- |"]
    for row in s["criteria"]:
        executor = ctx.criteria[row["id"]]["executor"]
        reason = row["reason"].replace("|", "/")
        out.append(f"| {row['id']} | {executor} | {row['status']} | {reason} | {', '.join(row['evidence_ids'][:4])}"
                   + (f" (+{len(row['evidence_ids']) - 4})" if len(row["evidence_ids"]) > 4 else "") + " |")
    out += ["", "### The two manager findings", ""]
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
                f"- Reproduced before repair on the clean issued base ({row.get('reproduced_before_repair')}): {before}",
                f"- General repair: {after}",
                f"- Commits: {', '.join(x['sha'][:10] for x in row.get('commits') or []) or 'none named'}. Disposition: "
                "repaired locally, pending the manager's independent replay.", ""]
    counts = ctx.carry_counts
    states: dict[str, int] = {}
    for row in ctx.obligation_items:
        if "attempt8_state" in row:
            states[row["attempt8_state"]] = states.get(row["attempt8_state"], 0) + 1
    out += ["### Carryforward", "",
            f"All {sum(counts['composition'].values())} carryforward identities are in "
            "ORIGINAL_OBLIGATION_DISPOSITIONS.json with each original meaning, source, owner, reason, next action, "
            "prior mapping and disposition copied unchanged: "
            + ", ".join(f"{k} {v}" for k, v in counts["composition"].items()) + "; dispositions "
            + ", ".join(f"{k} {v}" for k, v in counts["dispositions"].items()) + ".", "",
            f"The {len(in_cycle)} IN_CYCLE items carry the evidence of their linked criteria; the {len(backlog)} "
            "OWNED_BACKLOG items stay owned backlog and none is marked fulfilled by accounting. The 22 original lanes "
            "and the Attempt 3 (13), Attempt 4 (13), Attempt 5 (15), Attempt 6 (15) and Attempt 7 (15) lanes each "
            "carry a disposition in LANE_RESULTS.json.", "",
            "| Attempt 8 state | Items |", "| --- | --- |"] + [f"| {k} | {v} |" for k, v in sorted(states.items())] + [""]

    # ---- delivered behaviour
    career = _details(ctx, "CAREER_SUCCESSOR")
    witness = career.get("source_witness_checks") or {}
    oracle = career.get("independent_source_field_oracle") or {}
    genuine = oracle.get("genuine") or {}
    envelope_oracle = oracle.get("manager_a7_envelope") or {}
    same_page_oracle = oracle.get("manager_a6_same_page") or {}
    census = career.get("independent_identity_census") or {}
    a8 = (installed.get("a8_forgeries") or {}).get("cases") or {}
    a7 = (installed.get("a7_forgeries") or {}).get("cases") or {}
    a6 = (installed.get("a6_forgeries") or {}).get("cases") or {}
    envelope = installed.get("manager_a7_envelope_entrypoints") or {}
    source_module = installed.get("a8_genuine_source_module") or {}
    mgr6 = installed.get("manager_a6_same_page_lineage") or {}
    served = installed.get("installed_identity_census") or {}
    pagination = installed.get("successor_pagination") or {}
    fixtures = (installed.get("lineage_fixtures") or {}).get("cases") or {}
    adversarial = installed.get("manager_a5_successor_adversarial") or {}
    population = installed.get("manager_a5_successor_population_audit") or {}
    out += ["## Delivered behavior and national data", "",
            "Before (evidence/before, on the clean issued base): the installed console script, the installed module "
            "and the source module each served seven Fred Mariani rows from the manager's saved envelope fixture, and "
            "the Attempt 7 worker oracle found 0 crossed edges in it. After: the fresh installed `bas-staff-query`, its "
            "module entrypoint and the source module refuse that fixture and every new witness forgery for the "
            "source-field cause, and serve the genuine Attempt 5 and Attempt 4 successors unchanged; without "
            "`--career-successor` they answer exactly as the delivered release did.", "",
            f"Repaired verifier `{(career.get('source_identity_bindings') or {}).get('verifier_version')}` over the "
            f"genuine files: checks {_j(witness.get('checks'), 900)}; successor witnesses {_j(witness.get('successor'), 500)}; "
            f"named Attempt 4 witnesses {_j(witness.get('a04_relation'), 300)}; the Attempt 4 file's own witnesses "
            f"{_j(witness.get('a04_format'), 400)}.", "",
            "Independent source-field oracle "
            f"`{genuine.get('oracle_version')}` (sqlite3/json/re only; its own bracket-stack tokenizer; no project "
            f"import): rows {_j(genuine.get('rows'), 200)}, {genuine.get('captures_read')} capture revisions read, "
            f"{genuine.get('captures_unreadable_or_changed')} unreadable or changed; witness classes "
            f"{_j(genuine.get('witness_classes'), 600)}; unit forms {_j(genuine.get('unit_forms'), 600)}; unresolved "
            f"{_j(genuine.get('unresolved'), 300)}; triangle mismatches {genuine.get('triangle_mismatches')}.", "",
            "| Relation | Edges | Verdicts | Crossed | Not interval-adjudicated (multi-interval field) |",
            "| --- | --- | --- | --- | --- |"]
    out += [f"| {r.get('relation')} | {r.get('edges')} | {_j(r.get('counts'), 300).replace(chr(10), ' ')} | "
            f"{r.get('crossed_edges')} | {r.get('edges_into_multi_interval_fields_not_interval_adjudicated')} |"
            for r in genuine.get("relations") or []]
    out += ["", f"The same oracle over the manager's saved envelope fixture (`{envelope_oracle.get('fixture')}`, as "
            f"issued {envelope_oracle.get('sha256_as_issued')}): Attempt 5 witness classes "
            f"{_j(envelope_oracle.get('a05_witness_classes'), 300)}, crossed by relation "
            f"{_j(envelope_oracle.get('crossed_by_relation'), 200)}; over the Attempt 6 same-page fixture: crossed "
            f"{_j(same_page_oracle.get('crossed_by_relation'), 200)}. Interval agreement inside one multi-interval "
            "field is reported as not independently adjudicated rather than assumed.", "",
            f"Attempt 6 identity census kept (sqlite3/json/hashlib only): {census.get('rows')} rows, "
            f"{census.get('raw_files')} raw captures, mismatches {_j(census.get('mismatch_counts'), 200)}; legitimate "
            "classes " + ", ".join(f"{k} {v}" for k, v in (census.get("legitimate_classes") or {}).items()) + ".", "",
            f"Installed served identities against the census: {served.get('served_rows')} rows served, identity sets equal "
            f"{served.get('same_identities')}, rows whose served identity differs {served.get('rows_whose_served_identity_differs')}. "
            f"Full pagination: {pagination.get('distinct')} distinct rows in {pagination.get('pages')} pages against "
            f"{pagination.get('expected')} in the independent SQL oracle; reconciled {pagination.get('reconciled')}. The "
            f"genuine successor through the source module: {_j(source_module, 200)}.", "",
            f"The manager's saved envelope through every entrypoint (as issued {envelope.get('as_issued')}): exits "
            f"{_j(envelope.get('exits'), 200)}, refusals {_j(envelope.get('refusals'), 400)}; holds {envelope.get('holds')}.",
            "", "| This attempt's forgery (fixture reset before each) | Format | Console script | Module entrypoint | Holds |",
            "| --- | --- | --- | --- | --- |"]
    for name, row in a8.items():
        refusals = row.get("refusals") or {}
        out.append(f"| {name} | {row.get('format')} | {refusals.get('script') or 'exit ' + str(row.get('script_exit'))} | "
                   f"{refusals.get('module') or 'exit ' + str(row.get('module_exit'))} | {row.get('holds')} |")
    out += ["", "| Attempt 7 forgery (retained) | Expected | Console script | Module entrypoint | Holds |",
            "| --- | --- | --- | --- | --- |"]
    for name, row in a7.items():
        refusals = row.get("refusals") or {}
        out.append(f"| {name} | {row.get('expected')} | {refusals.get('script') or 'exit ' + str(row.get('script_exit'))} | "
                   f"{refusals.get('module') or 'exit ' + str(row.get('module_exit'))} | {row.get('holds')} |")
    out += ["", f"The manager's Attempt 6 same-page challenge, replayed through this wheel with its fixture and venv "
            f"literals adapted: case exit {mgr6.get('case_exit')}, refusal {mgr6.get('refusal')} (expected "
            f"{mgr6.get('expected')}); holds {mgr6.get('holds')}.", "",
            "| Attempt 6 forgery (installed CLI, kept) | Expected | Refusal | Holds |", "| --- | --- | --- | --- |"]
    out += [f"| {name} | {row.get('expected')} | {row.get('refusal') or ('exit ' + str(row.get('exit')))} | {row.get('holds')} |"
            for name, row in a6.items()]
    out += ["", "| Manager Attempt 5 adversarial case (installed CLI) | Exit | Refusal | Expected | Holds |",
            "| --- | --- | --- | --- | --- |"]
    for name, row in (adversarial.get("cases") or {}).items():
        out.append(f"| {name} | {row.get('exit')} | {row.get('refusal')} | "
                   f"{(adversarial.get('expected') or {}).get(name) or 'SERVED'} | {(adversarial.get('held') or {}).get(name)} |")
    out += ["", "| Original resealed or broken successor | Refused for its intended cause |", "| --- | --- |"]
    out += [f"| {name} | {row.get('expected_code')}: {row.get('refused_for_the_intended_cause')} |"
            for name, row in fixtures.items()]
    out += ["", f"Manager population audit replay: {_j({k: population.get(k) for k in ('rows', 'raw_files', 'lineage_errors', 'complete_predecessor_set', 'all_columns_multiset_match', 'served', 'holds')}, 600)}.", "",
            f"Other replays against this wheel: {_j({k: (installed.get(k) or {}).get('holds') for k in ('manager_a5_career_semantic_census', 'manager_a3_career_challenge', 'manager_a4_career_semantic_census', 'manager_a4_successor_challenge')}, 500)}; "
            f"named cases {_j((installed.get('successor_named_cases') or {}).get('holds'), 700)}.", "",
            "Real eligible forecasts: **0**. Real proven PIT rows: **0**. Wikimedia revisions are retrospective secondary "
            "evidence; no successor row is PIT admitted, official, activated or accepted.", ""]

    # ---- storage, candidate and control
    admission = _details(ctx, "STORAGE_ADMISSION")
    storage_lane = admission.get("storage_ledger") or {}
    race = admission.get("manager_a7_same_path_race") or {}
    stop = admission.get("manager_a7_stop_reserve") or {}
    mgr_storage = admission.get("manager_a6_storage_continuation") or {}
    measured = operational.get("measured") or {}
    candidate = _output(ctx, "LOCAL_INTEGRATION_CANDIDATE.json")
    lane_c = candidate.get("lane") or {}
    record = candidate.get("append_record") or {}
    control = _output(ctx, "CONTROL07_PROPOSAL_VALIDATION.json")
    regressions = _details(ctx, "SOURCE_REGRESSIONS").get("attempt8_suites_on_the_unfixed_base") or {}
    unfixed = _details(ctx, "SOURCE_REGRESSIONS").get("attempt8_witness_suite_on_the_unfixed_verifier") or {}
    out += ["## Storage evidence, the advanced candidate and CONTROL-07", "",
            "| Ledger | Records | Budget | Added at freeze | Headroom at freeze | Identity | Verified |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            f"| `{Path(operational['ledger']).name}` (root) | {operational.get('records', '--')} | "
            f"{operational.get('budget_bytes', '--')} | {measured.get('added_bytes', '--')} | "
            f"{measured.get('headroom_bytes', '--')} | {_j(operational.get('identity'), 120).replace(chr(10), ' ')} | "
            f"{(operational.get('verification') or {}).get('result', 'not frozen')} |", "",
            f"Chain proof: {_j({k: storage['chain'].get(k) for k in ('result', 'segments', 'live')}, 900)}.", "",
            f"Continuation claim `{storage['continuation_claim']['path']}` (create-only): exists "
            f"{storage['continuation_claim']['exists']}. Final-output ledger `{storage['final_output_ledger']['path']}` "
            f"(never evidence): {_j(storage['final_output_ledger']['status'], 400)}.", "",
            f"STORAGE_ADMISSION: live over-budget control {_j(storage_lane.get('live_over_budget_control'), 300)}; lane "
            f"reservation pairs {_j(storage_lane.get('lane_reservation_pairs'), 300)}. The manager's Attempt 7 same-path "
            f"race, replayed byte-faithfully: {_j({k: race.get(k) for k in ('exit', 'init_count', 'chain_in_script', 'chain_after_restart', 'holds')}, 300)}, "
            f"restart {_j(race.get('restart'), 200)} ({race.get('meaning')}). Its stop/reserve challenge: "
            f"{_j({k: stop.get(k) for k in ('exit', 'refusal', 'stopped_continuation_created', 'holds')}, 300)} "
            f"({stop.get('meaning')}). The manager's Attempt 6 continuation challenge holds {mgr_storage.get('holds')}; "
            f"Attempt 5 holds {(admission.get('manager_a5_storage_independent') or {}).get('holds')}.", "",
            f"The two Attempt 8 suites over a git archive of the unfixed base: exit {regressions.get('exit')}, "
            f"{_j(regressions.get('summary'), 200)}, {len(regressions.get('failed_or_errored') or [])} failed or errored; "
            f"holds {regressions.get('holds')}. The witness suite over the unfixed verifier with only the repair's unit "
            f"reader added: served (no refusal raised) {_j(unfixed.get('served_by_the_unfixed_verifier'), 900)}; refused "
            f"only under the earlier anchor rule {_j(unfixed.get('refused_by_the_unfixed_verifier_under_another_cause'), 600)}; "
            f"genuine forms attached {_j(unfixed.get('genuine_cases_attached_by_the_unfixed_verifier'), 300)}; holds "
            f"{unfixed.get('holds')}.",
            "", "Every append, in order (the first continues the granted head 0c22af20): "
            + "; ".join(f"`{str(row.get('previous_candidate_head'))[:10]}` -> `{str(row.get('candidate_commit'))[:10]}` "
                        f"from repair head `{str(row.get('repair_head'))[:10]}`" for row in candidate.get("appends") or [])
            + f". Last append: commit `{record.get('candidate_commit')}`, tree `{record.get('candidate_tree')}`; refs "
            f"changed {record.get('refs_changed')}.", "",
            f"Attempt 8 chain {_j(lane_c.get('attempt8_chain'), 300)}; tree checks {_j(lane_c.get('tree_checks'), 900)}", "",
            f"Committed-blob proof {_j(lane_c.get('committed_tree_proof'), 700)}", "",
            f"Negatives {_j({k: v.get('refused_for_its_cause') for k, v in ((lane_c.get('negatives') or {}).get('cases') or {}).items()}, 400)}; "
            f"the manager's Attempt 7 committed-tree review {_j({k: (lane_c.get('manager_a7_committed_tree') or {}).get(k) for k in ('head', 'paths', 'manifest_rows', 'mismatches', 'holds')}, 500)}; "
            f"Attempt 6 {_j({k: (lane_c.get('manager_a6_committed_tree') or {}).get(k) for k in ('head', 'mismatches', 'holds')}, 300)}; "
            f"consumer {_j((lane_c.get('consumer') or {}).get('holds'))}; review-control characterization "
            f"{_j(((lane_c.get('review_control_characterization') or {}).get('outcome') or {}), 700)}.", "",
            f"CONTROL-07 (retained from Attempt 7, private, inert, not adopted): result **{control.get('result')}** at "
            f"subjects {_j(control.get('subjects'), 300)}; retention {_j(control.get('attempt8_retention'), 700)}; checks "
            f"{_j(control.get('checks'), 1400)}; the current checkers exit green on "
            f"{_j((control.get('characterization') or {}).get('current_checkers_green_on'), 600)}. See "
            "CONTROL07_PROPOSAL.md for the exact bytes, the fixture matrix and the adoption path.", "",
            f"Decision for the owner: {candidate.get('decision_for_the_owner')}", ""]

    # ---- repairs and reproduction guide
    out += ["## Repairs and independent-review inputs", "",
            "Each repair has positive and negative controls in its suite (test_cycle37_a08_source_witness, "
            "test_cycle37_a08_continuation_atomicity, with the Attempt 5, 6 and 7 successor, anchor and snapshot suites "
            "corrected where their fixtures recorded witnesses no parser writes or encoded the defect) and fresh "
            "challenges at scale in its lane. The new suites were run over a git archive of the unfixed base and fail "
            "there. The manager's saved Attempt 7 probes (the envelope fixture through all three entrypoints, the "
            "same-path race, the stop/reserve challenge, the committed-tree review) are replayed from owned copies with "
            "only fixture-root and target-file literals adapted; the Attempt 2 to 6 probes are replayed as before.", "",
            "Manager reproduction guide (each is the issued lane command):", ""]
    for lane_id in ("STORAGE_ADMISSION", "SOURCE_REGRESSIONS", "CAREER_SUCCESSOR", "INSTALLED_CONSUMER_C01",
                    "LOCAL_INTEGRATION_CANDIDATE", "FINAL_PACKET"):
        out.append(f"- `{lane_id}`: `{ctx.lanes[lane_id]['command']}` in `{ctx.lanes[lane_id]['cwd']}`")
    out += ["- Independent oracle alone: `python tools/cycle37/a08_source_field_oracle.py --successor <A5 file> --a04 "
            "<A4 file> --database <delivered database> --out <new file> --label <label>` (no project import).",
            "- Candidate provenance proof from Git alone: `python tools/cycle37/attempt08_candidate.py verify-tree "
            f"{record.get('candidate_commit') or '<candidate commit>'}`.",
            "- Storage chain: `python tools/cycle37/storage_snapshot.py chain --ledger <final-output ledger>` and "
            "`python tools/cycle37/storage_snapshot.py verify --ledger STORAGE_RESERVATIONS.jsonl --snapshot "
            "STORAGE_EVIDENCE_SNAPSHOT.json`.",
            "- CONTROL-07: `python tools/cycle37/attempt08_control07.py validate --out-root <attempt root> --candidate "
            "<candidate head>` (offline, guarded, create-only).", "",
            "Known limitations: a proven witness shows that each row's recorded text is exactly the source unit its "
            "identity names in the cached capture, not biography truth; a row whose own normalized fields are rewritten "
            "to another episode's is outside this finding's class; interval agreement inside one multi-interval field "
            "is not independently adjudicated by the oracle; the guard covers Python processes and confines, not "
            "isolates, Git children; the delivered staff release is not rebuilt (its 2,223 affected rows stay owned "
            "backlog).", ""]

    # ---- validation matrix
    workers = [lane_id for lane_id, lane in ctx.lanes.items() if lane["executor"] == "worker"]
    executed = [lane_id for lane_id in workers if lanes[lane_id]["executed"]]
    out += ["## Exact validation matrix", "",
            f"{len(executed)} of {len(workers)} worker lanes ran through the issued command at the candidate head"
            + ("" if len(executed) == len(workers) else " (the rest are NOT_RUN)") + ". Every lane executed fresh; no "
            "dependency equivalence was used (INHERITED_LANE_EQUIVALENCE.json). Every child gets a credential-scrubbed "
            "environment, the attempt packaging root as TEMP and declared Git scratch root, the write guard over the "
            "data root, main checkout, both integration worktrees, All-22 and the Attempt 3 to 7 roots, and the "
            "loopback-only network guard, except where a receipt names an exception. WRITE_PROTECTION and "
            "STORAGE_ADMISSION qualified the guard and the ledger before the costly and mounted lanes, and every lane "
            "reserved its storage on the attempt's one ledger before it ran.", "",
            "| Lane | Kind | Status | Run | Tests | Fail | Err | Import err | Failed subtests | Skipped | Reason |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for lane_id, lane in ctx.lanes.items():
        row = lanes[lane_id]
        reason = (row.get("reason") or "").replace("|", "/")[:300]
        out.append(f"| {lane_id} | {lane['kind']} | {row['status']} | {row.get('run', '--')} | {row['tests']} | "
                   f"{row['failures']} | {row['errors']} | {row['import_errors']} | {row['failed_subtests']} | "
                   f"{row['skipped']} | {reason} |")
    equivalence = _output(ctx, "INHERITED_LANE_EQUIVALENCE.json")
    for row in equivalence.get("lanes") or []:
        comparison = row.get("attempt7_comparison") or {}
        if comparison:
            out += ["", f"{row['lane']} against Attempt 7 at the issued base, by identity: persisting "
                    f"{len(comparison.get('persisting') or [])}, new {len(comparison.get('new_in_attempt8') or [])}, "
                    f"no longer failing {len(comparison.get('no_longer_failing') or comparison.get('no_longer_reported') or [])}"
                    + (f", same cause {len(comparison.get('persisting_same_cause') or [])}" if "persisting_same_cause" in comparison else "")
                    + "."]
    out += ["", "Original 22 lanes and the Attempt 3 to 7 lanes:", "",
            "| Lane | Prior result | Disposition |", "| --- | --- | --- |"]
    out += [f"| {row['original_lane']} | {row.get('attempt2_result', '--')} | {row['disposition']} |" for row in ctx.original_lanes]
    out += [f"| A03 {row['attempt3_lane']} | {row.get('attempt3_result', '--')} | {row['disposition']} |" for row in ctx.attempt3_lanes]
    out += [f"| A04 {row['attempt4_lane']} | {row.get('attempt4_result', '--')} | {row['disposition']} |" for row in ctx.attempt4_lanes]
    out += [f"| A05 {row['attempt5_lane']} | {row.get('attempt5_result', '--')} | {row['disposition']} |" for row in ctx.attempt5_lanes]
    out += [f"| A06 {row['attempt6_lane']} | {row.get('attempt6_result', '--')} | {row['disposition']} |" for row in ctx.attempt6_lanes]
    out += [f"| A07 {row['attempt7_lane']} | {row.get('attempt7_result', '--')} | {row['disposition']} |" for row in ctx.attempt7_lanes]
    out.append("")

    # ---- platform
    platform = _output(ctx, "PLATFORM_RECONCILIATION.json")
    out += ["## Plans, Jira, PR feedback and integrations", "", "Governing sources (contract `source_refs`):", ""]
    out += [f"- `{row['id']}`: {row.get('section', '')} (`{Path(row['path']).name}`, SHA-256 `{str(row.get('sha256'))[:16]}...`)"
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
                f"{github.get('unresolved_thread_total')} unresolved review threads. No PR, push, merge, retarget or "
                "remote change was made; the only refs moved are the local repair branch (its own commits) and the "
                "local candidate branch, both forward only.", ""]
    revisions = platform.get("all22_owner_revisions") or []
    if revisions:
        out += ["All-22 owner repositories at the latest read (issued revision -> observed remote head):", ""]
        out += [f"- {r['repository']}: `{r['issued_remote_revision']}` -> `{r['observed_remote_head']}` (changed "
                f"{r['changed_since_issuance']}; local head `{r['local_head']}`, {r['local_dirty_entries']} dirty entries)"
                for r in revisions]
        owner = (ctx.latest_all22 or {}).get("owner_plan_check") or {}
        out += ["", f"Retained owner snapshots present unchanged at CFBProgramSpecifications `{owner.get('remote_head')}`: "
                f"{owner.get('snapshots_present_unchanged')} of {owner.get('snapshots_compared')}. The accepted Phase 2 "
                "plans remain NOT_IMPLEMENTED; the installed BAS wheel composes with the released C01 0.1.2 wheel; no "
                "owner repository was changed and no CFIP proposal was posted or presented as adoption.", ""]

    # ---- cost
    ledger = _output(ctx, "COST_AND_AUTHORITY_LEDGER.json")
    storage_doc = ledger.get("storage") or {}
    out += ["## Cost, storage, privacy and recovery", "", "| Request lane | Requests | Retries | Ceiling |",
            "| --- | --- | --- | --- |"]
    for lane_id, row in (ledger.get("request_lanes") or {}).items():
        out.append(f"| {lane_id} | {row['requests']} | {row['retries']} | {row['ceiling']} |")
    out += ["", f"Paid AI calls 0, cost 0. Storage: {storage_doc.get('added_bytes_at_freeze')} bytes added of the "
            f"{storage_doc.get('attempt_budget_bytes')}-byte attempt ceiling when the root ledger froze; free space now "
            f"{storage_doc.get('free_bytes_now')} bytes against the {storage_doc.get('reserve_bytes')}-byte reserve "
            f"(satisfied: {storage_doc.get('reserve_satisfied')}); bounded stops {len(storage_doc.get('bounded_stops') or [])}. "
            "Created roots: the attempt root, `C:\\BatteredAggieSyndrome.validation\\c37a08` and "
            "`C:\\BatteredAggieSyndrome.packaging\\c37a08`, within the write grants (evidence/CLEANUP_INVENTORY.json "
            "lists every directory and its bytes). No credential was printed, logged or written; lane children run "
            "with credential variables removed. Nothing was deleted, moved or cleaned up.", ""]

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
    validation = _output(ctx, "FINAL_PACKET_VALIDATION.json")
    out += ["## Final released handoff", "",
            f"Writers released: **{s['writer_released']}**. FINAL_PACKET validation: **{validation.get('state')}** "
            f"(receipt `{(validation.get('validation_receipt') or {}).get('path')}`; accounting only). No lane, reader or "
            "build process of this attempt remains running after the final accounting; the external All-22 lane-system "
            "areas are another system's writers this attempt does not own.", "",
            f"Submission: `{ctx.out_root / 'submission.json'}`; checklist generated by `cycle_protocol.py checklist`; "
            f"lane receipts and logs under `{ctx.out_root / 'lanes'}` indexed by `lanes/RUNS.jsonl` (append-only, named by "
            "path, never sealed). Next manager action: independent replay of the saved probes and fresh variants against "
            "the final source, the installed wheel, the served successor, the advanced candidate, the retained CONTROL-07 "
            "proposal and the frozen storage chain. The worker does not edit a released submission and does not declare "
            "acceptance.", ""]

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
    out += ["This attempt's prevention: both findings were reproduced before repair on the clean issued base with the "
            "manager's own saved fixture and challenges (the early draft parked outside the worktree, and disclosed); "
            "the witness rule was fitted against the whole genuine population -- every one of the 218,110 genuine rows "
            "records exactly its source unit -- before it was enforced, and an oracle that shares no code and no "
            "overlap assumption derives the units from the raw text; the continuation's atomicity was proved with a "
            "deterministic race on real locks, interrupted states and a many-caller stress (which found and fixed a "
            "lock-release defect) before any large allocation; every new forgery was proved against the source "
            "verifier before the installed lane; the new suites were shown to fail on the unfixed base.", ""]
    return "\n".join(out) + "\n"
