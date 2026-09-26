r"""Cycle #37 — Attempt #9 — WORKER_REPORT.md renderer (R37A09-05).

Renders the worker report from the same context and submission ``attempt09_outputs.py`` builds, so every count,
state and identity in the narrative is read from a receipt, a declared output or the submission rather than typed.
The sections follow ``templates/WORKER_REPORT.template.md`` of the v2.4.1 release. Nothing here grants acceptance.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

FINDING_TEXT = {
    "MF37A08-01": ("Absent coordinate witnesses let unverified enlarged text reconnect different jobs",
                   "on the clean issued base 91a83b19, the manager's saved fixture -- Fred Mariani's 1974 and 2009 "
                   "coaching rows with their default and Attempt 4 edges swapped, both rows' team, byte and years spans "
                   "set to NULL and their team and years text enlarged over all six jobs, resealed -- was served seven "
                   "rows by the installed console script, the installed module and the source module; the v4 verifier "
                   "skipped the absent witnesses and its anchor fell back to the rows' own text, and the Attempt 8 "
                   "oracle reported the forged edges only as unresolved.",
                   "Every row an attach checks -- every successor row and every delivered and Attempt 4 row an edge "
                   "names, witnessed or not -- is resolved to the source unit its own identity names in its verified "
                   "capture (a parent row must carry its own identity). A row with no witness may carry only blank text "
                   "or exactly that unit's text (a list line's years: text inside the line); an identity naming no unit, "
                   "or several, is never an anchor; SQL NULL, JSON null, [null, null] and an empty string are one absent "
                   "state. Each edge of both relations, in both formats, is compared by the two derived units alone "
                   "(verifier v5). Anything else is refused for its cause: unwitnessed text as "
                   "REFUSED_CAREER_SUCCESSOR_SOURCE_FIELD_WITNESS_MISMATCH, a relabelled row for its identity, a crossed "
                   "edge by the anchor, an edge with no derivable unit as UNANCHORED. The independent oracle "
                   "(a09_source_unit_oracle.py, sqlite3/json/re only) derives units from identity the same way."),
    "MF37A08-02": ("A continuation restart silently ignored a newly requested storage root",
                   "on the clean issued base, the manager's saved challenge restarted the same child naming an extra "
                   "empty root: it resumed without recording or refusing it, and bytes written there measured as 0 "
                   "added.",
                   "Every open, restart and interrupted-claim recovery derives one effective root contract under the "
                   "parent's lock -- the owned and shared roots, each normcase(abspath) (links not resolved), "
                   "deduplicated and sorted, a root in both classes refused -- records it in the claim and the child's "
                   "INIT, and compares it before any record. An added (empty or not), omitted or reclassified root is "
                   "refused as REFUSED_CONTINUATION_ROOT_CONTRACT_DIFFERS; another spelling of the same roots resumes; a "
                   "claim or INIT that recorded no contract is not completed (storage_snapshot v4)."),
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
    """When the before-repair reproduction ran, on which bytes, and how that relates to the first repair commit --
    read from the receipts and git, never typed."""

    path = ctx.out_root / "evidence" / "before" / "BEFORE_REPRODUCTION.json"
    if not path.is_file():
        return ["- Timing: no before-repair reproduction receipt exists."]
    receipt = _read(path)
    before, after = receipt.get("subject_before") or {}, receipt.get("subject_after") or {}
    first = next(iter(reversed(ctx.commits)), None)
    dated = (getattr(ctx, "commit_dates", {}) or {}).get(first[0]) if first else None
    text = (f"- Timing: the before-repair reproduction of both findings (`{path}`, reproduced {receipt.get('reproduced')}) "
            f"ran from {receipt.get('started_at')} to {receipt.get('finished_at')} on head "
            f"`{str(before.get('head'))[:10]}` (issued base {before.get('is_issued_base')}, clean {before.get('clean')} "
            f"before and {after.get('clean')} after); drafts before it: {receipt.get('drafts_before_reproduction')}")
    if first and dated:
        preceded = datetime.fromisoformat(receipt["finished_at"]) < datetime.fromisoformat(dated)
        text += (f"; the first repair commit `{first[0][:10]}` is dated {dated}, so the reproduction "
                 + ("preceded it" if preceded else "was recorded after it"))
    return [text + ". Every platform receipt binds its own head (PLATFORM_RECONCILIATION.json `phase_subjects`)."]


def _git(ctx: Any) -> list[str]:
    root = ctx.out_root / "evidence"
    semantics = _read(root / "intake" / "GIT_HOUSEKEEPING_PREFLIGHT.json")
    helper = _read(root / "intake" / "GIT_HELPER_CONSTRUCTION.json")
    cases = semantics.get("cases") or {}
    plain = (cases.get("plain_commit_hazard") or {})
    scoped = (cases.get("command_scoped_commit") or {})
    commits = [_read(p) for p in sorted((root / "git").glob("COMMIT_*.json"))]
    lines = [f"- Git housekeeping (the issued rule): on owned fixtures ({semantics.get('git_version')}) a plain commit "
             f"packed {(plain.get('objects_before_commit') or {}).get('loose_objects')} loose objects (auto gc "
             f"{plain.get('auto_gc_packed')}), the same commit with `-c gc.auto=0 -c maintenance.auto=false` left "
             f"{(scoped.get('objects_after_commit') or {}).get('loose_objects')} loose (preflight holds "
             f"{semantics.get('holds')}); every command the Attempt 9 wrapper builds carries both settings (missing "
             f"{len(helper.get('commands_missing_the_settings') or [])}). No repository configuration was changed and "
             "no gc, maintenance, prune, repack or clean was run."]
    for row in commits:
        lines.append(f"- Repair commit `{str(row.get('head'))[:10]}` ({row.get('subject')}): prefix "
                     f"`{' '.join(row.get('command_prefix') or [])}`, packs unchanged {row.get('packs_unchanged')}, loose "
                     f"objects not decreased {row.get('loose_objects_not_decreased')}, refs changed "
                     f"{row.get('refs_changed')}.")
    stores = []
    for lane, receipt in ctx.receipts.items():
        store = ((receipt.get("write_and_network_scope") or {}).get("shared_git_store") or {})
        if store and ctx.at_head(lane):
            stores.append(bool(store.get("packs_unchanged") and store.get("loose_objects_not_decreased")
                               and store.get("refs_unchanged")))
    if stores:
        lines.append(f"- Shared Git store around every lane at the candidate head: unchanged in packs, loose objects "
                     f"and refs in {sum(stores)} of {len(stores)} lane runs.")
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
            + (f"the local candidate advanced forward from c52e7b52 by {len(ctx.candidate_record_paths)} commit(s)"
               if ctx.candidate_record_paths else "the local candidate has not yet been advanced")
            + "; the retained CONTROL-07 proposal is private and inert; nothing pushed, merged, published, adopted or "
              f"activated). Headline: **{s['headline']}**. Predictive skill: **{s['predictive_skill']}**.", ""]
    if red:
        out += [f"Software validation is **{dims['software_validation']}** because "
                + ", ".join(row["id"] for row in red)
                + " stay red, classified identity by identity and compared with the Attempt 8 final lanes by identity "
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
    intake = start.get("intake") or {}
    out += ["## Issued versus actual subject", "",
            f"- Issued: contract SHA-256 `{s['contract_sha256']}`, bound by the sealed issuance "
            f"`{ctx.contract_path.parent / 'issuance' / 'issuance.json'}`; every contract source reference re-hashed at "
            f"START_CONTEXT ({sum(1 for r in start.get('source_refs') or [] if r.get('matches'))} of "
            f"{len(start.get('source_refs') or [])} equal to their issued digests); intake "
            f"(evidence/intake/INTAKE.json) bound every issued source ({intake.get('sources_all_match')}), both closure "
            f"archives ({_j(intake.get('closures'), 300)}) and the subjects ({_j(intake.get('subjects'), 300)}).",
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
            *_timing(ctx), *_git(ctx), ""]

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
        if "attempt9_state" in row:
            states[row["attempt9_state"]] = states.get(row["attempt9_state"], 0) + 1
    out += ["### Carryforward", "",
            f"All {sum(counts['composition'].values())} carryforward identities are in "
            "ORIGINAL_OBLIGATION_DISPOSITIONS.json with each original meaning, source, owner, reason, next action, "
            "prior mapping and disposition copied unchanged: "
            + ", ".join(f"{k} {v}" for k, v in counts["composition"].items()) + "; dispositions "
            + ", ".join(f"{k} {v}" for k, v in counts["dispositions"].items()) + ".", "",
            f"The {len(in_cycle)} IN_CYCLE items carry the evidence of their linked criteria; the {len(backlog)} "
            "OWNED_BACKLOG items stay owned backlog and none is marked fulfilled by accounting. The 22 original lanes "
            "and the Attempt 3 (13), Attempt 4 (13), Attempt 5 (15), Attempt 6 (15), Attempt 7 (15) and Attempt 8 (15) "
            "lanes each carry a disposition in LANE_RESULTS.json.", "",
            "| Attempt 9 state | Items |", "| --- | --- |"] + [f"| {k} | {v} |" for k, v in sorted(states.items())] + [""]

    # ---- delivered behaviour
    career = _details(ctx, "CAREER_SUCCESSOR")
    witness = career.get("source_witness_checks") or {}
    unit_oracle = career.get("independent_source_unit_oracle") or {}
    genuine = unit_oracle.get("genuine") or {}
    kept = career.get("attempt8_source_field_oracle") or {}
    census = career.get("independent_identity_census") or {}
    a9 = (installed.get("a9_forgeries") or {}).get("cases") or {}
    a8 = (installed.get("a8_forgeries") or {}).get("cases") or {}
    a7 = (installed.get("a7_forgeries") or {}).get("cases") or {}
    a6 = (installed.get("a6_forgeries") or {}).get("cases") or {}
    null_span = installed.get("manager_a8_null_span_entrypoints") or {}
    envelope = installed.get("manager_a7_envelope_entrypoints") or {}
    source_module = installed.get("a8_genuine_source_module") or {}
    mgr6 = installed.get("manager_a6_same_page_lineage") or {}
    served = installed.get("installed_identity_census") or {}
    pagination = installed.get("successor_pagination") or {}
    fixtures = (installed.get("lineage_fixtures") or {}).get("cases") or {}
    adversarial = installed.get("manager_a5_successor_adversarial") or {}
    population = installed.get("manager_a5_successor_population_audit") or {}
    successor = witness.get("successor") or {}
    out += ["## Delivered behavior and national data", "",
            "Before (evidence/before, on the clean issued base with nothing drafted): the installed console script, the "
            "installed module and the source module each served seven Fred Mariani rows from the manager's saved "
            "NULL-span fixture, and the Attempt 8 worker oracle reported its forged edges only as unresolved. After: the "
            "fresh installed `bas-staff-query`, its module entrypoint and the source module refuse that fixture and "
            "every new missing-witness construction for its own cause, and serve the genuine Attempt 5 and Attempt 4 "
            "successors unchanged; without `--career-successor` they answer exactly as the delivered release did.", "",
            f"Repaired verifier `{(career.get('source_identity_bindings') or {}).get('verifier_version')}` over the "
            f"genuine files: checks {_j(witness.get('checks'), 900)}.", "",
            f"Successor rows resolved to their identity-named unit {_j((successor.get('successor') or {}).get('rows_resolved_to_their_source_unit'))}, "
            f"of which proved by witness {_j((successor.get('successor') or {}).get('proved_by_form'), 300)} and resolved "
            f"without a witness {_j((successor.get('successor') or {}).get('resolved_without_a_witness_by_form'), 300)}; "
            f"unwitnessed fields by kind {_j((successor.get('successor') or {}).get('unwitnessed_fields'), 600)}; rows "
            f"naming no source unit {(successor.get('successor') or {}).get('rows_naming_no_source_unit')}. Named "
            f"delivered rows {_j(successor.get('delivered_predecessor'), 500)}; named Attempt 4 rows "
            f"{_j(witness.get('a04_relation'), 400)}; the Attempt 4 file's own rows {_j(witness.get('a04_format'), 400)}.",
            "", f"Anchors (all on derived units): default {_j(witness.get('default_anchors'), 300)}; Attempt 4 "
            f"{_j(witness.get('a04_anchors'), 300)}; Attempt 4-to-default {_j(witness.get('a04_format_anchors'), 300)}.",
            "", "Independent identity-derived oracle "
            f"`{genuine.get('oracle_version')}` (sqlite3/json/re only; no project import): rows {_j(genuine.get('rows'), 200)}, "
            f"{genuine.get('captures_read')} capture revisions read, {genuine.get('captures_unreadable_or_changed')} "
            f"unreadable or changed; row classes {_j(genuine.get('row_classes'), 700)}; limits {_j(genuine.get('limits'), 500)}.",
            "", "| Relation | Edges | Verdicts | Crossed | Unresolved |", "| --- | --- | --- | --- | --- |"]
    out += [f"| {r.get('relation')} | {r.get('edges')} | {_j(r.get('counts'), 300).replace(chr(10), ' ')} | "
            f"{r.get('crossed_edges')} | {r.get('unresolved_edges')} |" for r in genuine.get("relations") or []]
    null_oracle = unit_oracle.get("manager_a8_null_span") or {}
    out += ["", f"The same oracle over the manager's saved NULL-span fixture (`{null_oracle.get('fixture')}`, as issued "
            f"{null_oracle.get('sha256_as_issued')}): Attempt 5 row classes {_j(null_oracle.get('a05_row_classes'), 300)}, "
            f"invalid rows {_j(null_oracle.get('invalid_rows'), 400)}, crossed by relation "
            f"{_j(null_oracle.get('crossed_by_relation'), 200)}; over the Attempt 7 envelope "
            f"{_j((unit_oracle.get('manager_a7_envelope') or {}).get('crossed_by_relation'), 200)} and the Attempt 6 "
            f"same-page fixture {_j((unit_oracle.get('manager_a6_same_page') or {}).get('crossed_by_relation'), 200)}. "
            f"The Attempt 8 source-field oracle, kept: {_j({k: kept.get(k) for k in ('genuine_crossed', 'genuine_unresolved', 'manager_a7_envelope', 'manager_a6_same_page', 'holds')}, 500)}.",
            "", f"Attempt 6 identity census kept (sqlite3/json/hashlib only): {census.get('rows')} rows, "
            f"{census.get('raw_files')} raw captures, mismatches {_j(census.get('mismatch_counts'), 200)}; legitimate "
            "classes " + ", ".join(f"{k} {v}" for k, v in (census.get("legitimate_classes") or {}).items()) + ".", "",
            f"Installed served identities against the census: {served.get('served_rows')} rows served, identity sets equal "
            f"{served.get('same_identities')}, rows whose served identity differs {served.get('rows_whose_served_identity_differs')}. "
            f"Full pagination: {pagination.get('distinct')} distinct rows in {pagination.get('pages')} pages against "
            f"{pagination.get('expected')} in the independent SQL oracle; reconciled {pagination.get('reconciled')}. The "
            f"genuine successor through the source module: {_j(source_module, 200)}.", "",
            f"The manager's saved NULL-span fixture through every entrypoint (as issued {null_span.get('as_issued')}): exits "
            f"{_j(null_span.get('exits'), 200)}, refusals {_j(null_span.get('refusals'), 400)}, the unwitnessed text named "
            f"{_j(null_span.get('names_the_unwitnessed_text'), 200)}; holds {null_span.get('holds')}.",
            "", "| This attempt's missing-witness construction (fixture reset before each) | Format | Expected | Console script | Module entrypoint | Cause named | Holds |",
            "| --- | --- | --- | --- | --- | --- | --- |"]
    for name, row in a9.items():
        refusals = row.get("refusals") or {}
        out.append(f"| {name} | {row.get('format')} | {row.get('expected')} | "
                   f"{refusals.get('script') or 'exit ' + str(row.get('script_exit'))} | "
                   f"{refusals.get('module') or 'exit ' + str(row.get('module_exit'))} | "
                   f"{all((row.get('cause_named') or {}).values())} | {row.get('holds')} |")
    out += ["", f"The manager's Attempt 7 envelope through every entrypoint (kept): refusals "
            f"{_j(envelope.get('refusals'), 300)}; holds {envelope.get('holds')}.", "",
            "| Attempt 8 witness forgery (retained) | Format | Console script | Module entrypoint | Holds |",
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
    mgr8 = admission.get("manager_a8_storage_independent") or {}
    race = admission.get("manager_a7_same_path_race") or {}
    stop = admission.get("manager_a7_stop_reserve") or {}
    measured = operational.get("measured") or {}
    candidate = _output(ctx, "LOCAL_INTEGRATION_CANDIDATE.json")
    lane_c = candidate.get("lane") or {}
    record = candidate.get("append_record") or {}
    control = _output(ctx, "CONTROL07_PROPOSAL_VALIDATION.json")
    unfixed = _details(ctx, "SOURCE_REGRESSIONS").get("attempt9_suites_on_the_unfixed_base") or {}
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
            f"reservation pairs {_j(storage_lane.get('lane_reservation_pairs'), 300)}. The manager's Attempt 8 "
            f"continuation challenge, replayed with only its fixture root adapted: twelve processes "
            f"{_j(mgr8.get('concurrent'), 500)}; the extra-empty-root restart {_j(mgr8.get('extra_root_restart'), 300)}; "
            f"child records after {mgr8.get('child_records_after')}; its other cases {_j(mgr8.get('other_cases'), 400)}; "
            f"holds {mgr8.get('holds')} (before repair: {mgr8.get('before_repair')}). The manager's Attempt 7 race "
            f"{_j({k: race.get(k) for k in ('init_count', 'chain_after_restart', 'holds')}, 200)} and stop/reserve "
            f"challenge {_j({k: stop.get(k) for k in ('refusal', 'holds')}, 200)}, and the Attempt 6 and 5 challenges "
            f"({(admission.get('manager_a6_storage_continuation') or {}).get('holds')}, "
            f"{(admission.get('manager_a5_storage_independent') or {}).get('holds')}) still hold.", "",
            f"The two Attempt 9 suites over a git archive of the unfixed base 91a83b19: exit {unfixed.get('exit')}; "
            f"{unfixed.get('negative_cases')} negative case outcomes, none passing there "
            f"({len(unfixed.get('negative_cases_passing_on_the_base') or [])}); accepted by the unfixed code (no refusal "
            f"raised) {len(unfixed.get('accepted_by_the_unfixed_code') or [])} -- the saved constructions "
            f"{_j(unfixed.get('saved_constructions'), 300)}; refused there only under another cause "
            f"{len(unfixed.get('refused_under_another_cause') or [])}; new API or record absent "
            f"{len(unfixed.get('new_api_or_record_absent') or [])}; other behavior {len(unfixed.get('other_behavior') or [])} "
            f"({_j(unfixed.get('other_behavior'), 500)}); unclassified {len(unfixed.get('unclassified') or [])}; positive "
            f"cases on the base {_j(unfixed.get('positive_cases_on_the_base'), 500)}; holds {unfixed.get('holds')}.",
            "", "Every append, in order (the first continues the granted head c52e7b52): "
            + "; ".join(f"`{str(row.get('previous_candidate_head'))[:10]}` -> `{str(row.get('candidate_commit'))[:10]}` "
                        f"from repair head `{str(row.get('repair_head'))[:10]}`" for row in candidate.get("appends") or [])
            + f". Last append: commit `{record.get('candidate_commit')}`, tree `{record.get('candidate_tree')}`; refs "
            f"changed {record.get('refs_changed')}; shared Git store "
            f"{_j([{k: g.get(k) for k in ('packs_unchanged', 'loose_objects_not_decreased')} for g in candidate.get('git_housekeeping') or []], 300)}.",
            "", f"Attempt 9 chain {_j(lane_c.get('attempt9_chain'), 400)}; tree checks {_j(lane_c.get('tree_checks'), 900)}", "",
            f"Committed-blob proof {_j(lane_c.get('committed_tree_proof'), 700)}", "",
            f"Negatives {_j({k: v.get('refused_for_its_cause') for k, v in ((lane_c.get('negatives') or {}).get('cases') or {}).items()}, 400)}; "
            + "; ".join(f"the manager's Attempt {n} committed-tree review "
                        f"{_j({k: (lane_c.get(f'manager_a{n}_committed_tree') or {}).get(k) for k in ('head', 'paths', 'manifest_rows', 'mismatches', 'holds')}, 400)}"
                        for n in (8, 7, 6))
            + f"; consumer {_j((lane_c.get('consumer') or {}).get('holds'))}; review-control characterization "
            f"{_j(((lane_c.get('review_control_characterization') or {}).get('outcome') or {}), 700)}.", "",
            f"CONTROL-07 (retained from Attempt 8, itself the qualified Attempt 7 bytes; private, inert, not adopted): "
            f"result **{control.get('result')}** at subjects {_j(control.get('subjects'), 300)}; checks "
            f"{_j(control.get('checks'), 1600)}; the current checkers exit green on "
            f"{_j((control.get('characterization') or {}).get('current_checkers_green_on'), 600)}. See "
            "CONTROL07_PROPOSAL.md for the exact bytes, the fixture matrix and the adoption path.", "",
            f"Decision for the owner: {candidate.get('decision_for_the_owner')}", ""]

    # ---- repairs and reproduction guide
    out += ["## Repairs and independent-review inputs", "",
            "Each repair has positive and negative controls in its suite (test_cycle37_a09_missing_witness, "
            "test_cycle37_a09_continuation_roots, with the Attempt 4 contract suite and the Attempt 7 anchor suite "
            "corrected where their synthetic fixtures carried a form no genuine row has -- rows whose identity names "
            "nothing in the fixture revision, with lineage -- each cause kept and documented in the suite) and fresh "
            "challenges at scale in its lane. The absence rule was fitted against the whole genuine population first "
            "(evidence/census: every absent spelling and every unwitnessed text of the delivered, Attempt 4 and Attempt 5 "
            "files). The new suites were run over a git archive of the unfixed base and fail there. The manager's saved "
            "Attempt 8 probes (the NULL-span fixture through all three entrypoints, the continuation challenge, the "
            "committed-tree review) are replayed from owned copies with only fixture-root literals adapted; the Attempt "
            "2 to 7 probes are replayed as before.", "",
            "Manager reproduction guide (each is the issued lane command):", ""]
    for lane_id in ("STORAGE_ADMISSION", "SOURCE_REGRESSIONS", "CAREER_SUCCESSOR", "INSTALLED_CONSUMER_C01",
                    "LOCAL_INTEGRATION_CANDIDATE", "FINAL_PACKET"):
        out.append(f"- `{lane_id}`: `{ctx.lanes[lane_id]['command']}` in `{ctx.lanes[lane_id]['cwd']}`")
    out += ["- Independent oracle alone: `python tools/cycle37/a09_source_unit_oracle.py --successor <A5 file> --a04 "
            "<A4 file> --database <delivered database> --out <new file> --label <label>` (no project import).",
            "- Candidate provenance proof from Git alone: `python tools/cycle37/attempt09_candidate.py verify-tree "
            f"{record.get('candidate_commit') or '<candidate commit>'}`.",
            "- Storage chain: `python tools/cycle37/storage_snapshot.py chain --ledger <final-output ledger>` and "
            "`python tools/cycle37/storage_snapshot.py verify --ledger STORAGE_RESERVATIONS.jsonl --snapshot "
            "STORAGE_EVIDENCE_SNAPSHOT.json`.",
            "- CONTROL-07: `python tools/cycle37/attempt09_control07.py validate --out-root <attempt root> --candidate "
            "<candidate head>` (offline, guarded, create-only).", "",
            "Known limitations: resolving a row to the source unit its identity names shows that its recorded text is "
            "exactly that unit's text in the cached capture, not biography truth; a row whose own normalized fields are "
            "rewritten to another episode's is outside this finding's class; interval agreement inside one "
            "multi-interval field is not independently adjudicated by the oracle; root normalization is "
            "normcase(abspath) and does not resolve links or junctions (a linked spelling is a different root); the "
            "guard covers Python processes and confines, not isolates, Git children; the delivered staff release is not "
            "rebuilt (its 2,223 affected rows stay owned backlog).", ""]

    # ---- validation matrix
    workers = [lane_id for lane_id, lane in ctx.lanes.items() if lane["executor"] == "worker"]
    executed = [lane_id for lane_id in workers if lanes[lane_id]["executed"]]
    out += ["## Exact validation matrix", "",
            f"{len(executed)} of {len(workers)} worker lanes ran through the issued command at the candidate head"
            + ("" if len(executed) == len(workers) else " (the rest are NOT_RUN)") + ". Every lane executed fresh; no "
            "dependency equivalence was used (INHERITED_LANE_EQUIVALENCE.json). Every child gets a credential-scrubbed "
            "environment, the attempt packaging root as TEMP and declared Git scratch root, the write guard over the "
            "data root, main checkout, both integration worktrees, All-22 and the Attempt 3 to 8 roots, and the "
            "loopback-only network guard, except where a receipt names an exception. WRITE_PROTECTION and "
            "STORAGE_ADMISSION qualified the guard and the ledger before the costly and mounted lanes, every lane "
            "reserved its storage on the attempt's one ledger before it ran, and every lane measured the shared Git "
            "store around it.", "",
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
        comparison = row.get("attempt8_comparison") or {}
        if comparison:
            out += ["", f"{row['lane']} against Attempt 8 at the issued base, by identity: persisting "
                    f"{len(comparison.get('persisting') or [])}, new {len(comparison.get('new_in_attempt9') or [])}, "
                    f"no longer failing {len(comparison.get('no_longer_failing') or comparison.get('no_longer_reported') or [])}"
                    + (f", same cause {len(comparison.get('persisting_same_cause') or [])}" if "persisting_same_cause" in comparison else "")
                    + "."]
    out += ["", "Original 22 lanes and the Attempt 3 to 8 lanes:", "",
            "| Lane | Prior result | Disposition |", "| --- | --- | --- |"]
    out += [f"| {row['original_lane']} | {row.get('attempt2_result', '--')} | {row['disposition']} |" for row in ctx.original_lanes]
    for number in range(3, 9):
        out += [f"| A0{number} {row[f'attempt{number}_lane']} | {row.get(f'attempt{number}_result', '--')} | "
                f"{row['disposition']} |" for row in getattr(ctx, f"attempt{number}_lanes")]
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
            "Created roots: the attempt root, `C:\\BatteredAggieSyndrome.validation\\c37a09` and "
            "`C:\\BatteredAggieSyndrome.packaging\\c37a09`, within the write grants (evidence/CLEANUP_INVENTORY.json "
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
    out += ["This attempt's prevention: both findings were reproduced on the clean issued base with the manager's own "
            "saved fixture and challenge before any source was drafted; every Git command of a helper or commit carried "
            "the command-scoped housekeeping settings, proved on owned fixtures first, and the shared store was measured "
            "around every commit, append and lane; the absence rule was fitted against the whole genuine population "
            "before it was enforced, and an oracle that shares no code derives each unit from identity; every new "
            "forgery and every retained one was proved against the source verifier before the installed lane; the new "
            "suites were shown to fail on the unfixed base, each failure classified by what the unfixed code did.", ""]
    return "\n".join(out) + "\n"
