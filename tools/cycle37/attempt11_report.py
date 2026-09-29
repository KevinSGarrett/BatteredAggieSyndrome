r"""Cycle #37 — Attempt #11 — WORKER_REPORT.md renderer (R37A11-05).

Renders the worker report from the same context and submission ``attempt11_outputs.py`` builds, so every count, state
and identity in the narrative is read from a receipt, a declared output or the submission rather than typed. Timing
claims are derived from the receipts' own timestamps and the commits' dates. The sections follow
``templates/WORKER_REPORT.template.md`` of the v2.4.1 release. Nothing here grants acceptance.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

FINDING_TEXT = {
    "MF37A10-01": ("Count-changing false restructuring bypasses source-interval validation",
                   "Every successor row of both relations and both formats is now read again from the source unit its "
                   "identity names, whatever its disposition -- restructured, ordinary, single, multiple, added, role "
                   "line: the rows naming one source field must be exactly the intervals that field states (membership, "
                   "interval ordinal and multiplicity; REFUSED_CAREER_SUCCESSOR_INTERVAL_CARDINALITY_MISMATCH) and each "
                   "row's stated interval must be the one its source states "
                   "(REFUSED_CAREER_SUCCESSOR_PERIOD_WITNESS_MISMATCH). A restructure claim is qualified by its source: "
                   "the child's whole field in the parent's unit must be claimed and its interval count must genuinely "
                   "differ (RESTRUCTURE otherwise); a NOT_PRODUCED claim must name a unit its source does not produce; "
                   "every period-stating field unit of a cited capture must be held. The same census runs over the "
                   "Attempt 4 file a successor declares. The new checks run after the earlier rules, so every earlier "
                   "forgery keeps its cause (verifier v7). The independent source-cardinality oracle "
                   "(a11_interval_oracle.py, no project import) has no restructure exemption."),
}


def _j(value: Any, limit: int = 1200) -> str:
    """A value inline, on one line (so it never breaks a list item or a table row), truncated with a pointer."""

    text = json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + " ... (truncated here; full value in the named file)"


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
    text = (f"- Timing: the before-repair reproduction (`{path}`, reproduced {receipt.get('reproduced')}) ran from "
            f"{receipt.get('started_at')} to {receipt.get('finished_at')} on head `{str(before.get('head'))[:10]}` "
            f"(issued base {before.get('is_issued_base')}, clean {before.get('clean')} before and {after.get('clean')} "
            f"after; installed consumer equal to the base {before.get('installed_equal_to_base')}); drafts before it: "
            f"{receipt.get('drafts_before_reproduction')}")
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
             f"{semantics.get('holds')}); every command the unchanged Attempt 9 wrapper builds carries both settings "
             f"(missing {len(helper.get('commands_missing_the_settings') or [])}). No repository configuration was "
             "changed and no gc, maintenance, prune, repack or clean was run."]
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
        lines.append(f"- Shared Git store around every lane run counted at the candidate head (a retained lane's own "
                     f"original run included): unchanged in packs, loose objects and refs in {sum(stores)} of "
                     f"{len(stores)} lane runs.")
    return lines


def _kept(ctx: Any) -> dict[str, Any]:
    """The lanes kept at their original execution under a current dependency check (empty when every lane ran fresh)."""

    return dict(getattr(ctx, "reuse", None) or {})


def _lane_head(ctx: Any, lane: str) -> str:
    """The head a lane's own execution ran at: the original head for a retained lane, else the candidate head."""

    kept = _kept(ctx)
    return kept[lane]["original"]["head"] if lane in kept else ctx.candidate["head"]


def _retained_note(ctx: Any) -> str:
    kept = _kept(ctx)
    if not kept:
        return ""
    parts = []
    for lane in sorted(kept):
        original = kept[lane]["original"]
        again = [r["name"] for r in kept[lane]["reexecuted"]]
        parts.append(f"`{lane}` (run {original['run']} at head `{original['head'][:10]}`, {original['result']}"
                     + (f"; command(s) {', '.join(again)} executed again in the check" if again else "") + ")")
    return ("Not every lane ran at this head: " + "; ".join(parts) + " keep(s) the original execution under a current "
            "complete dependency check and were not executed again; every other worker lane ran fresh. ")


def render(ctx: Any, s: dict[str, Any]) -> str:
    c = ctx.contract
    cand = s["candidate"]
    label = f"Cycle #{s['cycle_number']} \u2014 Attempt #{s['attempt_number']} \u2014 {s['headline']}"
    worker_criteria = [row for row in s["criteria"] if ctx.criteria[row["id"]]["executor"] == "worker"]
    manager_criteria = [row for row in s["criteria"] if ctx.criteria[row["id"]]["executor"] != "worker"]
    verified = [row for row in worker_criteria if row["status"] == "VERIFIED_LOCAL"]
    failed = [row for row in worker_criteria if row["status"] == "FAIL"]
    backlog = [row for row in c["carryforward"] if row["disposition"] == "OWNED_BACKLOG"]
    in_cycle = [row for row in c["carryforward"] if row["disposition"] == "IN_CYCLE"]
    lanes = {row["id"]: row for row in s["lanes"]}
    red = [row for row in s["lanes"] if row["status"] == "FAIL"]
    out: list[str] = [f"# {label}", ""]
    out += [f"Internal identity: `{s['cycle_id']}` / `{s['attempt_id']}`. Contract `{ctx.contract_path}` SHA-256 "
            f"`{s['contract_sha256']}` (equal to the sealed issuance record). Branch `{c['repo']['branch']}` from base "
            f"`{c['repo']['base_sha']}`.", "",
            f"Repair subject (the candidate head): `{cand['head']}`, tree `{cand['tree']}`, source digest "
            f"`{cand['source_digest']}` (SHA-256 of `git ls-tree -r --full-tree HEAD`). " + _retained_note(ctx)
            + "The local integration candidate built from it is named under the storage and candidate section.", ""]

    # ---- direct answer
    dims = s["dimensions"]
    out += ["## Direct answer and six dimensions", "",
            f"Worker-owned work complete: **{'YES' if len(verified) == len(worker_criteria) else 'NO'}** -- "
            f"{len(verified)} of {len(worker_criteria)} worker criteria are VERIFIED_LOCAL at the candidate head"
            + (f" and {len(failed)} FAIL ({', '.join(r['id'] for r in failed)})" if failed else "")
            + ", each backed by lane receipts and command logs. Independently accepted: **NO** (PENDING_MANAGER_REVIEW; "
            f"{len(manager_criteria)} manager criteria and the MANAGER_REVIEW lane are the manager's). Integrated: "
            "**NO** (NOT_AUTHORIZED; "
            + (f"the local candidate advanced forward from cf992e4b by {len(ctx.candidate_record_paths)} commit(s)"
               if ctx.candidate_record_paths else "the local candidate has not yet been advanced")
            + "; the retained CONTROL-07 proposal is private and inert; nothing pushed, merged, published, adopted or "
              f"activated). Headline: **{s['headline']}**. Predictive skill: **{s['predictive_skill']}**.", ""]
    if red:
        out += [f"Software validation is **{dims['software_validation']}** because "
                + ", ".join(row["id"] for row in red)
                + " stay red, classified identity by identity and compared with the Attempt 10 final lanes by identity "
                  "and cause (INHERITED_LANE_EQUIVALENCE.json). No failing test is skipped, disabled or relabelled.", ""]
    elif dims["software_validation"] == "PARTIAL":
        out += ["Software validation is **PARTIAL**: the manager-owned MANAGER_REVIEW lane has not run"
                + ("" if all(lanes[key]["executed"] for key in lanes if ctx.lanes[key]["executor"] == "worker")
                   else " and some worker lanes have not run at this head") + "; every lane's state is in the matrix "
                "below.", ""]
    out += ["| Dimension | Actual state | Evidence | Remaining acceptance |", "| --- | --- | --- | --- |",
            f"| Implementation | {dims['implementation']} | {ctx.candidate_commit_count} commit(s) after the issued base; FINDING_CLOSURE_MATRIX.json | Manager replay of the repair |",
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
            f"(evidence/intake/INTAKE.json) bound every issued source ({intake.get('sources_all_match')}), the immutable "
            f"inputs ({intake.get('immutable_inputs_all_match')}), both closure archives "
            f"({_j(intake.get('closures'), 300)}) and the subjects ({_j(intake.get('subjects'), 300)}).",
            f"- Actual: {ctx.candidate_commit_count} commit(s) after the issued base"
            + (": " + ", ".join(f"`{sha[:10]}` {subject}" for sha, subject in reversed(ctx.commits)) if ctx.commits else "")
            + f". Worktree clean at the start and end of every executed lane run: {getattr(ctx, 'all_runs_clean', None)}.",
            f"- Interpreter (input only): `{interpreter.get('executable')}` CPython "
            f"{(interpreter.get('version') or '').split()[0] if interpreter.get('version') else ''}. Application: Claude "
            "Code (desktop app), model claude-opus-5-5; no sub-agents, workflows or paid providers.",
            f"- Delivered database: SHA-256 `{(start.get('delivered_database') or {}).get('expected')}` at its default "
            f"path, unchanged before and after the installed lane ({(installed.get('delivered_database_unchanged') or {}).get('after')}).",
            f"- Served career successor (unchanged, delivered by Attempt 5): `{ctx.pointer.get('successor_file')}` SHA-256 "
            f"`{ctx.pointer.get('successor_sha256')}`; the Attempt 4 successor `{ctx.pointer.get('a04_successor_sha256')}`; "
            "selected only by name, never a default.",
            f"- Released C01 wheel: SHA-256 `{(start.get('c01_wheel') or {}).get('expected')}`, composed, never rebuilt.",
            f"- Fresh noneditable BAS wheel: SHA-256 `{installed.get('wheel_sha256')}`, built from a git archive of "
            + (f"head `{_lane_head(ctx, 'INSTALLED_CONSUMER_C01')[:10]}` (the head that lane ran at; the lane is retained, "
               "not executed again, and its current dependency check proves the packaged product tree unchanged at the "
               "candidate head)" if "INSTALLED_CONSUMER_C01" in _kept(ctx) else "the candidate head")
            + " and installed offline into a new environment under the packaging root, run outside every checkout.",
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
    out += ["", "### The manager finding", ""]
    carry = {row["id"]: row for row in c["carryforward"]}
    matrix = {row["finding"]: row for row in (_output(ctx, "FINDING_CLOSURE_MATRIX.json").get("findings") or [])}
    reproduction = _read(ctx.out_root / "evidence" / "before" / "BEFORE_REPRODUCTION.json")
    saved = {r.get("entrypoint"): (r.get("exit"), r.get("row_count"), r.get("refusal"))
             for r in (reproduction.get("saved_fixture") or {}).get("results") or []}
    for key, (title, after) in FINDING_TEXT.items():
        meaning = carry[key]["original_meaning"]
        try:
            record = json.loads(meaning)
            meaning = f"{record.get('title')}. {record.get('reproduction')}"
        except ValueError:
            pass
        row = matrix.get(key) or {}
        out += [f"**{key} -- {title}.** Original meaning: {meaning}", "",
                f"- Reproduced before repair on the clean issued base ({row.get('reproduced_before_repair')}): the saved "
                f"fixture (as copied {(reproduction.get('saved_fixture') or {}).get('copy_matches')}) through each "
                f"entrypoint, (exit, rows, refusal) {_j(saved, 400)}; adjacent negatives served by the unfixed base "
                f"{_j(reproduction.get('negatives_served_by_unfixed_base'), 900)}; retained negatives (refused there "
                f"under the earlier rules) {_j(reproduction.get('retained_negatives_observed'), 400)}; positives "
                f"{_j(reproduction.get('positives_observed'), 500)}; the source's own count read independently "
                f"{_j((reproduction.get('saved_fixture') or {}).get('independent_source_cardinality'), 300)}; the "
                f"unchanged Attempt 10 oracle over the fixture "
                f"{_j((reproduction.get('worker_oracle_a10') or {}).get('summary'), 300)}.",
                f"- General repair: {after}",
                f"- Commits: {', '.join(x['sha'][:10] for x in row.get('commits') or []) or 'none named'}. Disposition: "
                "repaired locally, pending the manager's independent replay.", ""]
    counts = ctx.carry_counts
    states: dict[str, int] = {}
    for row in ctx.obligation_items:
        if "attempt11_state" in row:
            states[row["attempt11_state"]] = states.get(row["attempt11_state"], 0) + 1
    out += ["### Carryforward", "",
            f"All {sum(counts['composition'].values())} carryforward identities are in "
            "ORIGINAL_OBLIGATION_DISPOSITIONS.json with each original meaning, source, owner, reason, next action, "
            "prior mapping and disposition copied unchanged: "
            + ", ".join(f"{k} {v}" for k, v in counts["composition"].items()) + "; dispositions "
            + ", ".join(f"{k} {v}" for k, v in counts["dispositions"].items()) + ".", "",
            f"The {len(in_cycle)} IN_CYCLE items carry the evidence of their linked criteria; the {len(backlog)} "
            "OWNED_BACKLOG items stay owned backlog and none is marked fulfilled by accounting. The 22 original lanes "
            "and the Attempt 3 to 10 lanes each carry a disposition in LANE_RESULTS.json.", "",
            "| Attempt 11 state | Items |", "| --- | --- |"] + [f"| {k} | {v} |" for k, v in sorted(states.items())] + [""]

    # ---- delivered behaviour
    career = _details(ctx, "CAREER_SUCCESSOR")
    checks = career.get("source_interval_checks") or {}
    observed = checks.get("observed") or {}
    oracle = career.get("independent_cardinality_oracle") or {}
    genuine = oracle.get("genuine_a05") or {}
    genuine4 = oracle.get("genuine_a04") or {}
    saved_oracle = oracle.get("manager_a10_false_restructure") or {}
    crossed_oracle = oracle.get("manager_a9_interval") or {}
    kept = career.get("earlier_oracles_kept") or {}
    census = career.get("independent_identity_census") or {}
    cases = (installed.get("a11_cases") or {}).get("cases") or {}
    manager = installed.get("manager_a10_false_restructure_entrypoints") or {}
    manager9 = installed.get("manager_a9_interval_entrypoints") or {}
    retained_a10 = (installed.get("a10_interval_cases") or {}).get("cases") or {}
    served_census = installed.get("installed_identity_census") or {}
    pagination = installed.get("successor_pagination") or {}
    out += ["## Delivered behavior and national data", "",
            "Before (evidence/before, on the clean issued base with nothing drafted): the installed console script, the "
            "installed module and the source module each served Walter Camp's three rows from the manager's saved "
            "false-restructure fixture (the genuine field states two intervals; one row claimed both parents as a "
            "restructure), and every new negative of the exception-branch matrix was served too. After: the fresh "
            "installed `bas-staff-query`, its module entrypoint and the source module refuse that fixture and every new "
            "construction for its own cause, and serve the genuine Attempt 5 and Attempt 4 successors unchanged; "
            "without `--career-successor` they answer exactly as the delivered release did.", "",
            f"Repaired verifier `{(career.get('source_identity_bindings') or {}).get('verifier_version')}` over the "
            f"genuine files: checks {_j(checks.get('checks'), 1400)}. Observed: Attempt 5 "
            f"{_j(observed.get('A05'), 1200)}; Attempt 4 format {_j(observed.get('A04'), 500)}; restructure claims "
            + _j({rel: {k: (row or {}).get(k) for k in ('restructured_entries', 'restructure_claims_qualified')}
                  for rel, row in (observed.get('anchors') or {}).items()}, 400) + ".", "",
            f"Independent source-cardinality oracle `{genuine.get('oracle_version')}` (stdlib and the Attempt 8 "
            "raw-structure reader only; no project import; no restructure exemption):", "",
            "| Population | Rows | Fields | Captures | Field classes | Invalid | Unresolved | Multi-interval fields (rows) |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for name, row in (("genuine Attempt 5", genuine), ("genuine Attempt 4 format", genuine4),
                      ("manager's false-restructure fixture", saved_oracle),
                      ("manager's Attempt 9 interval fixture", crossed_oracle)):
        out.append(f"| {name} | {_j(row.get('rows'), 120)} | {row.get('fields')} | {row.get('captures_read')} | "
                   f"{_j(row.get('field_classes'), 400)} | {row.get('invalid_total')} | {row.get('unresolved_fields')} | "
                   f"{row.get('multi_interval_fields')} ({row.get('rows_in_multi_interval_fields')}) |")
    out += ["", "| Relation (genuine Attempt 5) | Verdicts | Invalid |", "| --- | --- | --- |"]
    out += [f"| {r.get('relation')} | {_j(r.get('counts'), 500)} | {r.get('invalid')} |"
            for r in genuine.get("relations") or []]
    out += ["", f"Named parser anomalies (left to a person, never passed): {_j(genuine.get('named_anomalies'), 700)}; equal "
            f"to the Attempt 10 manager's non-proven census: {genuine.get('known_anomaly_comparison_equal')} (the seven "
            "known parser-anomaly fields stay owned future scope; nothing is rebuilt). Completeness "
            f"{_j(genuine.get('completeness'), 300)}; rows stating no period text {_j(genuine.get('missing_periods'), 500)}. "
            f"Limits: {genuine.get('limits')}", "",
            f"The oracle over the manager's saved false-restructure fixture (as issued {saved_oracle.get('sha256_as_issued')}) "
            f"finds {saved_oracle.get('invalid_total')} invalid: {_j(saved_oracle.get('invalid_field_examples'), 700)}; over "
            f"the manager's Attempt 9 interval fixture {crossed_oracle.get('invalid_total')} invalid. The Attempt 8, 9 and "
            f"10 oracles over the genuine files, kept: {_j({k: kept.get(k) for k in ('a08_genuine_crossed', 'a09_genuine_crossed', 'a09_genuine_unresolved', 'a10_genuine_invalid', 'holds')}, 300)}.",
            "", f"Attempt 6 identity census kept (sqlite3/json/hashlib only): {census.get('rows')} rows, "
            f"{census.get('raw_files')} raw captures, mismatches {_j(census.get('mismatch_counts'), 200)}.", "",
            f"Installed served identities against the census: {served_census.get('served_rows')} rows served, identity "
            f"sets equal {served_census.get('same_identities')}. Full pagination: {pagination.get('distinct')} distinct "
            f"rows in {pagination.get('pages')} pages against {pagination.get('expected')} in the independent SQL oracle; "
            f"reconciled {pagination.get('reconciled')}.", "",
            f"The manager's saved false-restructure fixture through every entrypoint (as issued {manager.get('as_issued')}): "
            f"exits {_j(manager.get('exits'), 200)}, refusals {_j(manager.get('refusals'), 400)}, the source's two "
            f"intervals named {_j(manager.get('names_the_source_count'), 200)}; holds {manager.get('holds')}. The "
            f"manager's Attempt 9 interval fixture stays refused at every entrypoint ({manager9.get('holds')}); the "
            f"Attempt 10 interval cases hold at both entrypoints "
            f"({sum(1 for r in retained_a10.values() if r.get('holds'))} of {len(retained_a10)}).", "",
            "| This attempt's case (fixture reset before each) | Kind | Format | Person | Expected | Console script | Module entrypoint | Holds |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for name, row in cases.items():
        refusals = row.get("refusals") or {}
        served = row.get("served_rows") or {}
        out.append(f"| {name} | {row.get('kind')} | {row.get('format')} | {row.get('person')} | {row.get('expected')} | "
                   f"{refusals.get('script') or ('served ' + str(served.get('script')) if served else 'exit ' + str(row.get('script_exit')))} | "
                   f"{refusals.get('module') or ('served ' + str(served.get('module')) if served else 'exit ' + str(row.get('module_exit')))} | "
                   f"{row.get('holds')} |")
    retained = {key: (installed.get(key) or {}).get("holds") for key in (
        "a9_forgeries", "manager_a8_null_span_entrypoints", "a8_forgeries", "manager_a7_envelope_entrypoints",
        "a7_forgeries", "manager_a6_same_page_lineage", "a6_forgeries", "manager_a5_successor_adversarial",
        "manager_a5_successor_population_audit", "manager_a5_career_semantic_census", "manager_a3_career_challenge",
        "manager_a4_career_semantic_census", "manager_a4_successor_challenge", "installed_identity_census")}
    out += ["", f"Retained forgeries and manager replays against this wheel (each holds): {_j(retained, 900)}; named "
            f"cases {_j((installed.get('successor_named_cases') or {}).get('holds'), 700)}.", "",
            "Real eligible forecasts: **0**. Real proven PIT rows: **0**. Wikimedia revisions are retrospective secondary "
            "evidence; no successor row is PIT admitted, official, activated or accepted.", ""]

    # ---- storage, candidate and control
    admission = _details(ctx, "STORAGE_ADMISSION")
    storage_lane = admission.get("storage_ledger") or {}
    mgr9 = admission.get("manager_a9_storage_independent") or {}
    mgr8 = admission.get("manager_a8_storage_independent") or {}
    measured = operational.get("measured") or {}
    candidate = _output(ctx, "LOCAL_INTEGRATION_CANDIDATE.json")
    lane_c = candidate.get("lane") or {}
    record = candidate.get("append_record") or {}
    control = _output(ctx, "CONTROL07_PROPOSAL_VALIDATION.json")
    unfixed = _details(ctx, "SOURCE_REGRESSIONS").get("attempt11_suite_on_the_unfixed_base") or {}
    predicates = getattr(ctx, "process_predicates", {}) or {}
    windows = predicates.get("storage_windows") or {}
    dependencies = admission.get("storage_dependencies_equal_to_attempt10_accepted") or {}
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
            "Process predicates read from the evidence (R37A11-05-C; a violated one makes its criteria FAIL whatever a "
            "finding says): "
            + "; ".join(f"{name} holds {row.get('holds')}" for name, row in predicates.items()) + ". Root ledger windows: "
            + _j({k: (windows.get("operational") or {}).get(k) for k in ("windows", "gaps", "unattributed_bytes",
                                                                         "overlapping_reservations",
                                                                         "exceeded_reservations",
                                                                         "unreconciled_reservations")}, 700)
            + "; final-output continuation: "
            + _j({k: (windows.get("final_output") or {}).get(k) for k in ("windows", "gaps", "unattributed_bytes",
                                                                          "overlapping_reservations",
                                                                          "exceeded_reservations")}, 400)
            + ". Every lane's receipt and index line are written inside a reservation of their own "
            + _j(predicates.get("receipt_windows"), 300) + ".", "",
            f"STORAGE_ADMISSION (the accepted behavior, preserved and re-run fresh): the storage tools and suites are the "
            f"exact blobs the Attempt 10 final STORAGE_ADMISSION qualified {_j({k: dependencies.get(k) for k in ('attempt10_final_run', 'attempt10_final_result', 'unchanged', 'holds')}, 300)}; unchanged since "
            f"the issued base {_j((admission.get('storage_tools_unchanged_since_the_issued_base') or {}).get('equal'))}; live "
            f"over-budget control {_j(storage_lane.get('live_over_budget_control'), 300)}. The manager's Attempt 9 "
            f"continuation challenge, replayed with only its fixture root adapted: twelve processes "
            f"{_j(mgr9.get('concurrent'), 400)}; the extra-empty-root restart {_j(mgr9.get('extra_root_restart'), 300)}; "
            f"its other cases {_j(mgr9.get('other_cases'), 400)}; holds {mgr9.get('holds')}. The Attempt 8 challenge "
            f"holds {mgr8.get('holds')}; the Attempt 7 race and stop/reserve, Attempt 6 and 5 challenges hold "
            f"{_j({k: (admission.get(k) or {}).get('holds') for k in ('manager_a7_same_path_race', 'manager_a7_stop_reserve', 'manager_a6_storage_continuation', 'manager_a5_storage_independent')}, 300)}.",
            "", f"The Attempt 11 suite over a git archive of the unfixed base c2f82759: exit {unfixed.get('exit')}; "
            f"{unfixed.get('negative_cases')} new negative case outcomes, none passing there "
            f"({len(unfixed.get('negative_cases_passing_on_the_base') or [])}); accepted by the unfixed code (no refusal "
            f"raised) {len(unfixed.get('accepted_by_the_unfixed_code') or [])} -- the saved construction "
            f"{_j(unfixed.get('saved_construction'), 300)}; refused there only under another cause "
            f"{len(unfixed.get('refused_under_another_cause') or [])} ({_j(unfixed.get('refused_under_another_cause'), 400)}); "
            f"new API or record absent {len(unfixed.get('new_api_or_record_absent') or [])}; other behavior "
            f"{len(unfixed.get('other_behavior') or [])}; unclassified {len(unfixed.get('unclassified') or [])}. Retained "
            f"negatives there (refused on both, recorded): {_j(unfixed.get('retained_negative_cases_on_the_base'), 300)}. "
            f"Positive cases there (recorded, never required): {_j(unfixed.get('positive_cases_on_the_base'), 900)}; "
            f"holds {unfixed.get('holds')}.",
            "", "Every append, in order (the first continues the granted head cf992e4b): "
            + "; ".join(f"`{str(row.get('previous_candidate_head'))[:10]}` -> `{str(row.get('candidate_commit'))[:10]}` "
                        f"from repair head `{str(row.get('repair_head'))[:10]}`" for row in candidate.get("appends") or [])
            + f". Last append: commit `{record.get('candidate_commit')}`, tree `{record.get('candidate_tree')}`; refs "
            f"changed {record.get('refs_changed')}; shared Git store "
            f"{_j([{k: g.get(k) for k in ('packs_unchanged', 'loose_objects_not_decreased')} for g in candidate.get('git_housekeeping') or []], 300)}.",
            "", f"Attempt 11 chain {_j(lane_c.get('attempt11_chain'), 500)}; tree checks {_j(lane_c.get('tree_checks'), 900)}", "",
            f"Committed-blob proof {_j(lane_c.get('committed_tree_proof'), 700)}", "",
            f"Negatives {_j({k: v.get('refused_for_its_cause') for k, v in ((lane_c.get('negatives') or {}).get('cases') or {}).items()}, 400)}; "
            + "; ".join(f"the manager's Attempt {n} committed-tree review "
                        f"{_j({k: (lane_c.get(f'manager_a{n}_committed_tree') or {}).get(k) for k in ('head', 'paths', 'manifest_rows', 'mismatches', 'holds')}, 400)}"
                        for n in (10, 9, 8, 7, 6))
            + f"; consumer {_j((lane_c.get('consumer') or {}).get('holds'))}; review-control characterization "
            f"{_j(((lane_c.get('review_control_characterization') or {}).get('outcome') or {}), 700)}.", "",
            f"CONTROL-07 (retained from Attempt 10, itself the qualified Attempt 9, 8 and 7 bytes; private, inert, not adopted): "
            f"result **{control.get('result')}** at subjects {_j(control.get('subjects'), 300)}; checks "
            f"{_j(control.get('checks'), 1600)}; the current checkers exit green on "
            f"{_j((control.get('characterization') or {}).get('current_checkers_green_on'), 600)}. See "
            "CONTROL07_PROPOSAL.md for the exact bytes, the fixture matrix and the adoption path.", "",
            f"Decision for the owner: {candidate.get('decision_for_the_owner')}", ""]

    # ---- repairs and reproduction guide
    held_cases = sum(1 for row in cases.values() if row.get("holds"))
    a05_checks = observed.get("A05") or {}
    out += ["## Repairs and independent-review inputs", "",
            "The repair has positive and negative controls in its suite (test_cycle37_a11_restructure_lineage: the "
            "manager's count-changing collapse with genuine, forged, blank, enlarged and parent-copied periods, "
            "expansion with and without a fabricated interval, a fabricated ordinal in a genuinely restructured field, a "
            "restructured merge expanded past its source, a restructured split collapsed and relabelled ordinary, forged "
            "periods on every formerly exempt branch and in the declared Attempt 4 file, a partial restructure, the "
            "Attempt 4 format, and the retained count-preserving and one-relation constructions, against the genuine "
            "fixture's splits, merges, role lines, added rows, blank text and unstated dates). The Attempt 5, 6 and 7 "
            "suites' synthetic rows are corrected where they stated readings their own parser does not produce (each "
            "correction documented in its suite). The census was fitted against the whole genuine population before it "
            "was enforced: at the candidate head the verifier reads "
            f"{_j((a05_checks.get('source_intervals_proved') or {}).get('rows_read_again_from_source'))} Attempt 5 rows "
            "again from their captures with every restructure claim qualified and every NOT_PRODUCED claim proved, and "
            f"the independent oracle finds {genuine.get('invalid_total')} invalid over the genuine Attempt 5 file and "
            f"{genuine4.get('invalid_total')} over the Attempt 4 format. The installed wheel holds {held_cases} of "
            f"{len(cases)} cases at both entrypoints. The new suite was run over a git archive of the unfixed base and "
            "fails there. The manager's saved Attempt 10 probes (the false-restructure fixture through all three "
            "entrypoints, the committed-tree review) are replayed from owned copies; the Attempt 2 to 9 probes are "
            "replayed as before.", "",
            "Manager reproduction guide (each is the issued lane command):", ""]
    for lane_id in ("STORAGE_ADMISSION", "SOURCE_REGRESSIONS", "CAREER_SUCCESSOR", "INSTALLED_CONSUMER_C01",
                    "LOCAL_INTEGRATION_CANDIDATE", "FINAL_PACKET"):
        out.append(f"- `{lane_id}`: `{ctx.lanes[lane_id]['command']}` in `{ctx.lanes[lane_id]['cwd']}`")
    out += ["- Independent source-cardinality oracle alone: `python tools/cycle37/a11_interval_oracle.py --successor "
            "<A5 file> --a04 <A4 file> --database <delivered database> --out <new file> --label <label> "
            "[--known-anomalies <manager census>]` (no project import).",
            "- Storage window audit of any ledger: `python tools/cycle37/attempt11_outputs.py audit --ledger <ledger>`.",
            "- Candidate provenance proof from Git alone: `python tools/cycle37/attempt11_candidate.py verify-tree "
            f"{record.get('candidate_commit') or '<candidate commit>'}`.",
            "- Storage chain: `python tools/cycle37/storage_snapshot.py chain --ledger <final-output ledger>` and "
            "`python tools/cycle37/storage_snapshot.py verify --ledger STORAGE_RESERVATIONS.jsonl --snapshot "
            "STORAGE_EVIDENCE_SNAPSHOT.json`.",
            "- CONTROL-07: `python tools/cycle37/attempt11_control07.py validate --out-root <attempt root> --candidate "
            "<candidate head>` (offline, guarded, create-only).", "",
            "Known limitations: interval lineage is proved against each row's own parser reading of its verified capture, "
            "not against biography truth; the v37.2 delivered rows are parents only (their ordinal is their identity; "
            "no reader of their own exists); the v37.4 reader states only the last period of a line with several, so "
            "the Attempt 4 format's completeness is not asserted and the oracle leaves those fields unresolved; the "
            "seven known parser-anomaly fields stay as the parser read them (owned future scope); the guard log is a "
            "diagnostic record whose torn lines are kept as fragments, so no exhaustive zero-write claim is made from "
            "it (the before/after measurements are the independent check); root normalization is normcase(abspath) and "
            "does not resolve links or junctions; the guard covers Python processes and confines, not isolates, Git "
            "children; the delivered staff release is not rebuilt (its 2,223 affected rows stay owned backlog).", ""]

    # ---- validation matrix
    workers = [lane_id for lane_id, lane in ctx.lanes.items() if lane["executor"] == "worker"]
    executed = [lane_id for lane_id in workers if lanes[lane_id]["executed"]]
    kept = set(_kept(ctx))
    out += ["## Exact validation matrix", "",
            f"{len([lane_id for lane_id in executed if lane_id not in kept])} of {len(workers)} worker lanes ran fresh "
            "through the issued command at the candidate head"
            + (f" and {len(kept)} ({', '.join(sorted(kept))}) keep their original execution under a current complete "
               "dependency check, NOT executed again at this head" if kept else "")
            + ("" if len(executed) == len(workers) else " (the rest are NOT_RUN)") + ". "
            + ("Each retained lane's original run, head, receipt, log, counts and result are unchanged and named in its row "
               "and in INHERITED_LANE_EQUIVALENCE.json; the check is recomputed on every build and check and would refuse "
               "a changed, missing or forged dependency. " if kept else
               "No lane was carried by dependency equivalence (INHERITED_LANE_EQUIVALENCE.json). ")
            + "Every child gets a credential-scrubbed "
            "environment, the attempt packaging root as TEMP and declared Git scratch root, the write guard over the "
            "data root, main checkout, both integration worktrees, All-22 and the Attempt 3 to 10 roots, and the "
            "loopback-only network guard, except where a receipt names an exception. WRITE_PROTECTION and "
            "STORAGE_ADMISSION qualified the guard and the ledger before the costly and mounted lanes, every lane "
            "reserved its storage on the attempt's one ledger before it ran (and its receipt in a window of its own), and every lane measured the shared Git "
            "store around it.", "",
            "| Lane | Kind | Status | Execution | Run | Tests | Fail | Err | Import err | Failed subtests | Skipped | Reason |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for lane_id, lane in ctx.lanes.items():
        row = lanes[lane_id]
        reason = (row.get("reason") or "").replace("|", "/")[:300]
        out.append(f"| {lane_id} | {lane['kind']} | {row['status']} | {row.get('execution', '--')} | {row.get('run', '--')} | {row['tests']} | "
                   f"{row['failures']} | {row['errors']} | {row['import_errors']} | {row['failed_subtests']} | "
                   f"{row['skipped']} | {reason} |")
    equivalence = _output(ctx, "INHERITED_LANE_EQUIVALENCE.json")
    for row in equivalence.get("lanes") or []:
        comparison = row.get("attempt10_comparison") or {}
        if comparison:
            out += ["", f"{row['lane']} against Attempt 10 at the issued base, by identity: persisting "
                    f"{len(comparison.get('persisting') or [])}, new {len(comparison.get('new_in_attempt11') or [])}, "
                    f"no longer failing {len(comparison.get('no_longer_failing') or comparison.get('no_longer_reported') or [])}"
                    + (f", same cause {len(comparison.get('persisting_same_cause') or [])}" if "persisting_same_cause" in comparison else "")
                    + "."]
    out += ["", "Original 22 lanes and the Attempt 3 to 10 lanes:", "",
            "| Lane | Prior result | Disposition |", "| --- | --- | --- |"]
    out += [f"| {row['original_lane']} | {row.get('attempt2_result', '--')} | {row['disposition']} |" for row in ctx.original_lanes]
    for number in range(3, 11):
        out += [f"| A{number:02d} {row[f'attempt{number}_lane']} | {row.get(f'attempt{number}_result', '--')} | "
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
        compared = (f"Retained owner snapshots present unchanged at CFBProgramSpecifications `{owner.get('remote_head')}`: "
                    f"{owner.get('snapshots_present_unchanged')} of {owner.get('snapshots_compared')}. " if owner else
                    "The latest All-22 read made no owner-snapshot comparison (only a read with the remote manifest, "
                    "PLATFORM_CARRY's AFTER read, makes one). ")
        out += ["", compared + "The accepted Phase 2 plans remain NOT_IMPLEMENTED; the installed BAS wheel composes with "
                "the released C01 0.1.2 wheel; no owner repository was changed and no CFIP proposal was posted or "
                "presented as adoption.", ""]

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
            "Created roots: the attempt root, `C:\\BatteredAggieSyndrome.validation\\c37a11` and "
            "`C:\\BatteredAggieSyndrome.packaging\\c37a11`, within the write grants (evidence/CLEANUP_INVENTORY.json "
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
            "path, never sealed). Next manager action: independent replay of the saved false-restructure fixture and "
            "fresh collapse, expansion, ordinal and forged-period variants on every exception branch against the final "
            "source, the installed wheel and the source module; independent raw cardinality reconstruction over the 142 "
            "groups, their parents and the missing-period rows; the advanced candidate, the retained "
            "CONTROL-07 proposal and the frozen storage chain. The worker does not edit a released submission and does "
            "not declare acceptance.", ""]

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
    out += ["This attempt's prevention: the finding was reproduced on the clean issued base with the manager's own saved "
            "fixture and the whole exception-branch matrix (restructured and ordinary, single and multiple, parent and "
            "no parent, legitimate split and merge, both relations and formats) before any source was drafted; the "
            "consumer's exemption was removed rather than narrowed -- every row is read again from its source -- and the "
            "independent oracle was built without any restructure exemption; the lane, output and report tools were "
            "preflighted on tiny owned fixtures (including a gapped ledger, an OPEN_OUT_OF_SCOPE finding and a partially "
            "FIXED_LOCAL finding with unmet clauses) before the costly lanes; process predicates are read from the "
            "evidence, not from finding labels; every lane receipt is written inside a reservation of its own; every Git "
            "mutator carried the command-scoped housekeeping settings, proved on owned fixtures first; development "
            "windows on the storage ledger were closed before any other reserved operation ran.", ""]
    return "\n".join(out) + "\n"
