r"""Cycle #37 — Attempt #7 — the private, inert CONTROL-07 proposal and its offline qualification (R37A07-03).

    attempt07_control07.py validate --out-root <attempt evidence root> [--candidate <revision>]

CONTROL-07 (R27-CODEX-MASKED-FAIL, P0): main's checker exits 0 on a schema-valid FAIL or BLOCKED report, main's
hosted workflow calls a paid provider on every pull request and runs the checker from the pull request's own merge
ref; the repair branch's checker fixes the verdicts, but its default workflow reports a green SKIPPED without any
review. Neither whole bundle is approved (the Attempt 6 manager's CONTROL_AUTHORITY_CHARACTERIZATION).

The proposal's bytes live only under ``<out-root>\evidence\control07\proposed`` (inert: never under a checkout, never
executed as hosted authority). This tool, offline and without credentials or network:

* binds the six control surfaces the committed protocol (``CYCLE27_TRUSTED_CONTROL_CHANGE_PROTOCOL.json``) names on
  main, the repair branch, the local candidate and the proposal, and writes the exact inert patch;
* characterizes each checker on one fixture matrix -- PASS, FAIL, BLOCKED, SKIPPED, missing, malformed, stale,
  wrong-artifact and unresolved-P1 reports, and for the proposal the review-authority cases (an eligible independent
  exact-head approval as a TEST_ONLY synthetic fixture, and denied self-approval, unapproved, dismissed, stale-head,
  changed-head, ineligible, later-changes-requested, missing, malformed-report, a changed control surface and a
  TEST_ONLY document offered as real) -- each run under the canonical write guard with non-loopback network denied;
* statically reads each workflow for provider calls, secrets, dispatch paths, where its checker comes from, and
  whether a green result can occur without an independent report;
* evaluates the change with the repository's own CONTROL-07 evaluator
  (``aggie_analytics.governance.trusted_control_change_protocol``): without a bootstrap receipt the change is refused;
* writes the create-only ``CONTROL07_PROPOSAL_VALIDATION.json`` and the generated ``CONTROL07_PROPOSAL.md``.

A synthetic approval is TEST_ONLY; nothing here is a review receipt, an approval, an adoption or a publication.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
WORKTREE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKTREE / "src"))

from aggie_analytics.governance import trusted_control_change_protocol as protocol_tool  # noqa: E402

CYCLE_NUMBER, ATTEMPT_NUMBER = 37, 7
LABEL = "Cycle #37 — Attempt #7 — IN_PROGRESS_LOCAL_WORK_REMAINS"
MAIN = "55e12a5aad3a7e843204fcba619c3cb3d3d6194d"
CANDIDATE_BRANCH = "codex/BAT-706-cycle37-qualified-integration"
PROTOCOL = "artifacts/scientific_integrity/cycle27/CYCLE27_TRUSTED_CONTROL_CHANGE_PROTOCOL.json"
PROTOCOL_SHA256 = "b76f6d02b07430dd9a1865d417090588e4142f87ed348cdd0cfd90533ec29831"
CHECKER = "tools/validate_codex_scientific_review.py"
WORKFLOW = ".github/workflows/codex-scientific-review.yml"
PAID = ".github/workflows/paid-scientific-review.yml"
SURFACES = protocol_tool.CONTROL_SURFACES
VALIDATION_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a07")
GUARD_DIR = WORKTREE / "tools" / "cycle37" / "canonical_write_guard"
GUARDED = (WORKTREE, Path(r"C:\BatteredAggieSyndrome.worktrees\cycle37-integration-review"),
           Path(r"C:\BatteredAggieSyndrome"), Path(r"C:\BatteredAggieSyndrome.data"))
MANAGER_CHARACTERIZATION = Path(r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle37\attempt06"
                                r"\review-20260925T205004Z\CONTROL_AUTHORITY_CHARACTERIZATION.json")
PR, AUTHOR, REVIEWER = 777, "implementation-author", "independent-reviewer"
BASE, HEAD, MERGE, OLD_HEAD = "b" * 40, "c" * 40, "d" * 40, "e" * 40
INVENTORY = ["src/aggie_analytics/cycle37/career_successor.py", "tests/test_cycle37_a07_source_anchor.py"]
INVARIANTS = ["pit_known_at", "target_game_exclusion", "current_opponent_binding", "game_grain_pair_coherence",
              "probability_margin_distribution_coherence", "immutable_forecasts", "protected_exposure",
              "report_artifact_agreement", "producer_validator_independence"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", "--no-optional-locks", "-C", str(WORKTREE), *args], capture_output=True, text=True,
                          encoding="utf-8", check=True).stdout.strip()


def blob(revision: str, path: str) -> bytes | None:
    listed = git("ls-tree", revision, path)
    if not listed:
        return None
    return subprocess.run(["git", "--no-optional-locks", "-C", str(WORKTREE), "cat-file", "blob", listed.split()[2]],
                          capture_output=True, check=True).stdout


def digest_inventory(items: list[str]) -> str:
    return sha256_bytes(json.dumps(sorted(items), separators=(",", ":")).encode("utf-8"))


def rule_identity() -> str:
    return (f".github/CODE_REVIEW_RULES.md sha256:{sha256_bytes(blob(MAIN, '.github/CODE_REVIEW_RULES.md'))};"
            f".cursor/BUGBOT.md sha256:{sha256_bytes(blob(MAIN, '.cursor/BUGBOT.md'))}")


# ------------------------------------------------------------------ the proposal's exact bytes


def surfaces(revision: str | None, proposed: Path) -> dict[str, dict[str, Any]]:
    rows = {}
    for path in SURFACES:
        if revision is None:
            file = proposed / path
            data = file.read_bytes() if file.is_file() else (blob(MAIN, path) if path not in (CHECKER, WORKFLOW, PAID)
                                                             else None)
            origin = "PROPOSED_FILE" if file.is_file() else ("MAIN_UNCHANGED" if data is not None else "ABSENT")
        else:
            data, origin = blob(revision, path), "GIT"
        rows[path] = {"sha256": sha256_bytes(data) if data is not None else None,
                      "bytes": len(data) if data is not None else 0, "present": data is not None, "origin": origin}
    return rows


def write_patch(proposed: Path, out: Path) -> dict[str, Any]:
    chunks = []
    for path in SURFACES:
        old = blob(MAIN, path)
        new = (proposed / path).read_bytes() if (proposed / path).is_file() else (None if path == PAID else old)
        if old == new:
            continue
        chunks.extend(difflib.unified_diff(
            (old or b"").decode("utf-8").splitlines(keepends=True), (new or b"").decode("utf-8").splitlines(keepends=True),
            fromfile=f"a/{path}" if old is not None else "/dev/null", tofile=f"b/{path}" if new is not None else "/dev/null"))
    text = "".join(chunks)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return {"path": str(out), "sha256": sha256_bytes(text.encode("utf-8")), "bytes": len(text.encode("utf-8"))}


# ------------------------------------------------------------------ fixtures


def report(**changes: Any) -> dict[str, Any]:
    document = {"pr_number": PR, "base_sha": BASE, "head_sha": HEAD, "reviewed_merge_sha": MERGE,
                "changed_file_inventory": INVENTORY, "changed_file_digest": digest_inventory(INVENTORY),
                "review_rule_identity": rule_identity(), "model": "independent-reviewer (no automated provider)",
                "reasoning_effort": "not-applicable", "findings_p0": [], "findings_p1": [], "findings_p2": [],
                "scientific_invariants_checked": INVARIANTS, "critical_files_not_reviewed": [],
                "limitations": ["synthetic TEST_ONLY fixture; not a review of any real pull request"], "verdict": "PASS"}
    document.update(changes)
    return document


def review(state: str = "APPROVED", *, login: str = REVIEWER, commit: str = HEAD, association: str = "COLLABORATOR",
           body: dict[str, Any] | str | None = None, at: str = "2026-09-25T12:00:00Z", number: int = 1) -> dict[str, Any]:
    payload = report() if body is None else body
    text = payload if isinstance(payload, str) else json.dumps(payload, indent=2)
    return {"id": number, "user": {"login": login}, "state": state, "commit_id": commit, "author_association": association,
            "submitted_at": at, "body": f"Independent scientific review.\n\nBAS-SCIENTIFIC-REVIEW-REPORT v1\n```json\n{text}\n```\n"}


def fixture_cases() -> dict[str, dict[str, Any]]:
    """Each case: the report file (for the current checkers), the reviews document (for the proposal), extra argv
    and the binding inventory; ``expected`` is the proposal's required outcome."""

    test_only = lambda *reviews: {"source": "TEST_ONLY_SYNTHETIC", "reviews": list(reviews)}  # noqa: E731
    return {
        "pass_eligible_independent_exact_head_TEST_ONLY": {"report": report(), "reviews": test_only(review()),
                                                           "flag": True, "expected": ("TEST_ONLY_PASS", 0)},
        "fail_verdict": {"report": report(verdict="FAIL", findings_p1=["P1 finding"]),
                         "reviews": test_only(review(body=report(verdict="FAIL", findings_p1=["P1 finding"]))),
                         "flag": True, "expected": ("FAIL", 1)},
        "blocked_verdict": {"report": report(verdict="BLOCKED"), "reviews": test_only(review(body=report(verdict="BLOCKED"))),
                            "flag": True, "expected": ("FAIL", 1)},
        "successful_skip_is_not_acceptance": {
            "report": report(verdict="SKIPPED_UNTIL_PAID_SCIENTIFIC_REVIEW_READY"),
            "reviews": test_only(review(body=report(verdict="SKIPPED_UNTIL_PAID_SCIENTIFIC_REVIEW_READY"))),
            "flag": True, "expected": ("FAIL", 1)},
        "pass_with_unresolved_p1": {"report": report(findings_p1=["open P1"]),
                                    "reviews": test_only(review(body=report(findings_p1=["open P1"]))),
                                    "flag": True, "expected": ("FAIL", 1)},
        "missing_report": {"report": None, "reviews": test_only(), "flag": True, "expected": ("FAIL", 1)},
        "malformed_report": {"report": "{not json", "reviews": test_only(review(body="{not json")), "flag": True,
                             "expected": ("FAIL", 1)},
        "stale_report_head": {"report": report(head_sha=OLD_HEAD),
                              "reviews": test_only(review(body=report(head_sha=OLD_HEAD))), "flag": True,
                              "expected": ("MALFORMED", 2)},
        "wrong_artifact_inventory": {"report": report(changed_file_inventory=["README.md"],
                                                      changed_file_digest=digest_inventory(["README.md"])),
                                     "reviews": test_only(review(body=report(
                                         changed_file_inventory=["README.md"],
                                         changed_file_digest=digest_inventory(["README.md"])))),
                                     "flag": True, "expected": ("MALFORMED", 2)},
        "self_approved": {"report": report(), "reviews": test_only(review(login=AUTHOR)), "flag": True,
                          "expected": ("FAIL", 1)},
        "unapproved_commented": {"report": report(), "reviews": test_only(review("COMMENTED")), "flag": True,
                                 "expected": ("FAIL", 1)},
        "approval_then_changes_requested": {"report": report(), "reviews": test_only(
            review(number=1), review("CHANGES_REQUESTED", at="2026-09-25T13:00:00Z", number=2)), "flag": True,
                                            "expected": ("FAIL", 1)},
        "dismissed_approval": {"report": report(), "reviews": test_only(review("DISMISSED")), "flag": True,
                               "expected": ("FAIL", 1)},
        "stale_head_approval": {"report": report(), "reviews": test_only(review(commit=OLD_HEAD)), "flag": True,
                                "expected": ("FAIL", 1)},
        "changed_head_after_approval": {"report": report(), "reviews": test_only(review()), "flag": True,
                                        "head": OLD_HEAD, "expected": ("FAIL", 1)},
        "ineligible_reviewer_association": {"report": report(), "reviews": test_only(review(association="CONTRIBUTOR")),
                                            "flag": True, "expected": ("FAIL", 1)},
        "approval_without_report": {"report": report(), "reviews": test_only(
            {**review(), "body": "LGTM"}), "flag": True, "expected": ("FAIL", 1)},
        "pr_changes_its_own_checker": {"report": report(changed_file_inventory=INVENTORY + [CHECKER],
                                                        changed_file_digest=digest_inventory(INVENTORY + [CHECKER])),
                                       "reviews": test_only(review(body=report(
                                           changed_file_inventory=INVENTORY + [CHECKER],
                                           changed_file_digest=digest_inventory(INVENTORY + [CHECKER])))),
                                       "inventory": INVENTORY + [CHECKER], "flag": True, "expected": ("FAIL", 1)},
        "test_only_offered_as_real": {"report": report(), "reviews": test_only(review()), "flag": False,
                                      "expected": ("FAIL", 1)},
        "reviews_input_missing": {"report": report(), "reviews": None, "flag": True, "expected": ("MALFORMED", 2)},
    }


def guarded_env(folder: Path, log: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "COMSPEC", "PATHEXT"}}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1", TEMP=str(folder), TMP=str(folder),
               PYTHONPATH=str(GUARD_DIR), BAS_NETWORK_GUARD="DENY_NON_LOOPBACK",
               BAS_CANONICAL_WRITE_GUARD=os.pathsep.join(str(p) for p in GUARDED if p.exists()),
               BAS_CANONICAL_WRITE_ALLOW=str(folder), BAS_CANONICAL_WRITE_GUARD_LOG=str(log))
    return env


def run_matrix(name: str, checker: Path, proposed_cli: bool, folder: Path) -> dict[str, Any]:
    """Every fixture through one checker, each in its own directory, guarded and offline."""

    results = {}
    log = folder / f"{name}.guard.jsonl"
    for case, spec in fixture_cases().items():
        where = folder / name / case
        where.mkdir(parents=True)
        binding = where / "binding.json"
        inventory = spec.get("inventory", INVENTORY)
        binding.write_text(json.dumps({"pr_number": PR, "base_sha": BASE, "head_sha": HEAD, "reviewed_merge_sha": MERGE,
                                       "changed_file_inventory": inventory,
                                       "changed_file_digest": digest_inventory(inventory)}), encoding="utf-8")
        head = spec.get("head", HEAD)
        common = ["--binding", str(binding), "--expected-pr", str(PR), "--expected-base", BASE, "--expected-head", head,
                  "--expected-merge", MERGE]
        if proposed_cli:
            reviews = where / "reviews.json"
            if spec["reviews"] is not None:
                reviews.write_text(json.dumps(spec["reviews"]), encoding="utf-8")
            argv = [sys.executable, "-B", str(checker), "--reviews", str(reviews), "--pr-author", AUTHOR, *common,
                    "--trusted-rule-identity", rule_identity()] + (["--allow-test-only-fixture"] if spec["flag"] else [])
        else:
            payload = where / "report.json"
            if spec["report"] is not None:
                payload.write_text(spec["report"] if isinstance(spec["report"], str) else json.dumps(spec["report"]),
                                   encoding="utf-8")
            argv = [sys.executable, "-B", str(checker), "--payload", str(payload), *common]
        run = subprocess.run(argv, cwd=str(where), env=guarded_env(where, log), capture_output=True, text=True,
                             encoding="utf-8", timeout=120)
        try:
            output = json.loads(run.stdout) if run.stdout.strip().startswith("{") else {}
        except ValueError:
            output = {}
        results[case] = {"exit": run.returncode, "result": output.get("result"), "findings": output.get("findings"),
                         "stderr_tail": run.stderr[-300:], "successful_check": run.returncode == 0}
        if proposed_cli:
            expected = spec["expected"]
            results[case]["expected"] = {"result": expected[0], "exit": expected[1]}
            results[case]["holds"] = (output.get("result"), run.returncode) == expected
    guard = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()] if log.is_file() else []
    return {"checker": str(checker), "checker_sha256": sha256_bytes(checker.read_bytes()), "cli": "proposed" if proposed_cli
            else "current", "cases": results, "guard_events": len(guard),
            "guard_blocked": [row for row in guard if row.get("event") == "BLOCKED"][:20]}


# ------------------------------------------------------------------ static workflow reading


def read_workflow(text: str | None) -> dict[str, Any]:
    if text is None:
        return {"present": False}
    lowered = text.lower()
    return {"present": True,
            "calls_paid_provider": any(t in lowered for t in ("openai/codex-action", "openai-api-key", "anthropic",
                                                               "api.openai.com")),
            "uses_secrets": "secrets." in lowered,
            "workflow_dispatch": "workflow_dispatch" in lowered,
            "checker_from_protected_base": bool(re.search(
                r'git show "\$\{?base_sha\}?:tools/validate_codex_scientific_review\.py"', lowered)),
            "checker_from_pull_request_tree": "python tools/validate_codex_scientific_review.py" in lowered,
            "green_without_independent_report": "skipped_until_paid_scientific_review_ready" in lowered,
            "passes_test_only_flag": "--allow-test-only-fixture" in lowered,
            "write_permissions": any(f"{k}: write" in lowered for k in ("pull-requests", "contents", "issues", "actions")),
            "posts_comments": "gh pr comment" in lowered,
            "required_context_job_codex_review": "\n  codex-review:" in text}


# ------------------------------------------------------------------ the validation


def validate(proposed: Path, out: Path, patch: Path, candidate: str | None) -> dict[str, Any]:
    if out.exists() or patch.exists():
        raise SystemExit(f"{out} or {patch} exists; the validation receipt and patch are written once")
    protocol_bytes = (WORKTREE / PROTOCOL).read_bytes()
    if sha256_bytes(protocol_bytes) != PROTOCOL_SHA256:
        raise SystemExit("the committed CONTROL-07 protocol is not the contract's exact bytes")
    protocol = json.loads(protocol_bytes.decode("utf-8"))
    repair = git("rev-parse", "HEAD")
    candidate = candidate or git("rev-parse", f"refs/heads/{CANDIDATE_BRANCH}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = VALIDATION_ROOT / "control07" / stamp
    folder.mkdir(parents=True)
    checkers = {}
    for name, revision in (("main", MAIN), ("repair", repair), ("candidate", candidate)):
        path = folder / f"{name}_checker.py"
        path.write_bytes(blob(revision, CHECKER))
        checkers[name] = run_matrix(name, path, False, folder)
    checkers["proposed"] = run_matrix("proposed", proposed / CHECKER, True, folder)
    bindings = {name: surfaces(rev, proposed) for name, rev in (("main", MAIN), ("repair", repair),
                                                               ("candidate", candidate))}
    bindings["proposed"] = surfaces(None, proposed)
    workflows = {name: {"codex-scientific-review.yml": read_workflow(
                            (blob(rev, WORKFLOW) or b"").decode("utf-8") if blob(rev, WORKFLOW) else None),
                        "paid-scientific-review.yml": read_workflow(
                            (blob(rev, PAID) or b"").decode("utf-8") if blob(rev, PAID) else None)}
                 for name, rev in (("main", MAIN), ("repair", repair), ("candidate", candidate))}
    workflows["proposed"] = {"codex-scientific-review.yml": read_workflow((proposed / WORKFLOW).read_text(encoding="utf-8")),
                             "paid-scientific-review.yml": read_workflow(None)}
    changed = [path for path in SURFACES if bindings["proposed"][path]["sha256"] != bindings["main"][path]["sha256"]]
    synthetic_receipt = {"bootstrap_approved": True, "independent_reviewer": REVIEWER, "author": AUTHOR,
                         "class": "TEST_ONLY_SYNTHETIC"}
    self_receipt = {"bootstrap_approved": True, "independent_reviewer": AUTHOR, "author": AUTHOR,
                    "class": "TEST_ONLY_SYNTHETIC"}
    evaluator = {
        "module": "aggie_analytics.governance.trusted_control_change_protocol",
        "module_sha256": sha256_bytes(Path(protocol_tool.__file__).read_bytes()),
        "change_without_receipt": protocol_tool.evaluate_changed_control_surfaces(protocol=protocol, changed_files=changed),
        "change_with_self_approval": protocol_tool.evaluate_changed_control_surfaces(
            protocol=protocol, changed_files=changed, approval_receipt=self_receipt),
        "change_with_TEST_ONLY_independent_receipt": protocol_tool.evaluate_changed_control_surfaces(
            protocol=protocol, changed_files=changed, approval_receipt=synthetic_receipt),
        "pass_report_under_unapproved_protocol": protocol_tool.evaluate_review_payload_acceptance(report(),
                                                                                                protocol=protocol),
        "fail_report": protocol_tool.evaluate_review_payload_acceptance(report(verdict="FAIL"), protocol=protocol),
    }
    proposal = checkers["proposed"]["cases"]
    current_green = {name: sorted(case for case, row in checkers[name]["cases"].items() if row["successful_check"])
                     for name in ("main", "repair", "candidate")}
    checks = {
        "every_proposed_case_holds": all(row["holds"] for row in proposal.values()),
        "only_the_TEST_ONLY_fixture_is_green": [c for c, r in proposal.items() if r["successful_check"]]
        == ["pass_eligible_independent_exact_head_TEST_ONLY"],
        "no_proposed_result_is_a_real_PASS": all(r["result"] != "PASS" for r in proposal.values()),
        "proposed_workflow_calls_no_provider_and_uses_no_secret": not workflows["proposed"]["codex-scientific-review.yml"]
        ["calls_paid_provider"] and not workflows["proposed"]["codex-scientific-review.yml"]["uses_secrets"],
        "proposed_workflow_takes_its_checker_from_the_protected_base":
            workflows["proposed"]["codex-scientific-review.yml"]["checker_from_protected_base"]
            and not workflows["proposed"]["codex-scientific-review.yml"]["checker_from_pull_request_tree"],
        "proposed_workflow_has_no_dispatch_no_write_no_comment_no_test_flag": not any(
            workflows["proposed"]["codex-scientific-review.yml"][k] for k in ("workflow_dispatch", "write_permissions",
                                                                             "posts_comments", "passes_test_only_flag")),
        "proposed_workflow_keeps_the_required_context": workflows["proposed"]["codex-scientific-review.yml"]
        ["required_context_job_codex_review"],
        "paid_workflow_absent_in_proposal": not bindings["proposed"][PAID]["present"],
        "rules_prompt_schema_unchanged_from_main": all(
            bindings["proposed"][p]["sha256"] == bindings["main"][p]["sha256"] for p in SURFACES if p not in (CHECKER, WORKFLOW)),
        "candidate_keeps_main_controls": all(bindings["candidate"][p] == bindings["main"][p] for p in SURFACES),
        "change_refused_without_bootstrap_receipt": not evaluator["change_without_receipt"]["ok"],
        "change_refused_under_self_approval": not evaluator["change_with_self_approval"]["ok"],
        "pass_report_refused_while_the_protocol_is_unapproved": not evaluator["pass_report_under_unapproved_protocol"]["ok"],
        "no_guard_blocked_event": all(not checkers[n]["guard_blocked"] for n in checkers),
        "active_controls_unchanged_in_both_worktrees": all(
            not subprocess.run(["git", "--no-optional-locks", "-C", str(tree), "status", "--porcelain", "--", *SURFACES],
                               capture_output=True, text=True).stdout.strip() for tree in GUARDED[:2]),
    }
    document = {
        "label": f"{LABEL} (CONTROL-07 private proposal: offline qualification, not adoption)",
        "cycle_number": CYCLE_NUMBER, "attempt_number": ATTEMPT_NUMBER, "observed_at": utc_now(),
        "control": "CONTROL-07 / R27-CODEX-MASKED-FAIL (P0)",
        "authority": {"protocol": {"path": PROTOCOL, "sha256": PROTOCOL_SHA256,
                                   "bootstrap_status": protocol.get("bootstrap_status"),
                                   "authorized_future_checker_change_path": protocol.get(
                                       "authorized_future_checker_change_path"),
                                   "acceptance_requires": protocol.get("acceptance_requires")},
                      "manager_characterization": {"path": str(MANAGER_CHARACTERIZATION),
                                                   "sha256": sha256_bytes(MANAGER_CHARACTERIZATION.read_bytes()),
                                                   "decision": json.loads(MANAGER_CHARACTERIZATION.read_text(
                                                       encoding="utf-8")).get("decision")}},
        "subjects": {"main": MAIN, "repair": repair, "candidate": candidate},
        "bindings": bindings, "changed_surfaces_in_proposal": changed,
        "proposed_root": str(proposed), "patch": write_patch(proposed, patch),
        "characterization": {"current_checkers_green_on": current_green, "workflows": workflows},
        "checker_runs": checkers, "protocol_evaluator": evaluator, "checks": checks,
        "result": "PASS" if all(checks.values()) else "FAIL",
        "scratch": str(folder),
        "meaning": ("An offline qualification of an inert proposal. The only green proposed case is a synthetic "
                    "TEST_ONLY approval, which is not a review receipt. Adoption needs the eligible independent "
                    "reviewer's bootstrap receipt and separate publication authority; nothing here grants either."),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, indent=2, ensure_ascii=False, default=str) + "\n")
    return document


def render_markdown(document: dict[str, Any], receipt: Path) -> str:
    """CONTROL07_PROPOSAL.md, generated from the validation receipt so every number is the receipt's."""

    b = document["bindings"]
    rows = ["| Control surface | Main | Repair branch | Candidate | Proposal |", "| --- | --- | --- | --- | --- |"]
    for path in SURFACES:
        cell = lambda name: (b[name][path]["sha256"] or "absent")[:16]  # noqa: E731
        rows.append(f"| `{path}` | {cell('main')} | {cell('repair')} | {cell('candidate')} | {cell('proposed')} |")
    cases = document["checker_runs"]
    table = ["| Case | Main | Repair | Candidate | Proposal (result, exit) | Proposal holds |",
             "| --- | --- | --- | --- | --- | --- |"]
    for case, row in cases["proposed"]["cases"].items():
        table.append(f"| {case} | {cases['main']['cases'][case]['exit']} | {cases['repair']['cases'][case]['exit']} | "
                     f"{cases['candidate']['cases'][case]['exit']} | {row['result']}, {row['exit']} | {row['holds']} |")
    wf = document["characterization"]["workflows"]
    workflow_rows = ["| Subject | Paid provider | Secrets | Dispatch | Checker source | Green without a report |",
                     "| --- | --- | --- | --- | --- | --- |"]
    for name in ("main", "repair", "candidate", "proposed"):
        for file, row in wf[name].items():
            if not row.get("present"):
                workflow_rows.append(f"| {name} `{file}` | absent | | | | |")
                continue
            source = ("protected base" if row["checker_from_protected_base"] else
                      "pull-request tree" if row["checker_from_pull_request_tree"] else "none")
            workflow_rows.append(f"| {name} `{file}` | {row['calls_paid_provider']} | {row['uses_secrets']} | "
                                 f"{row['workflow_dispatch']} | {source} | {row['green_without_independent_report']} |")
    evaluator = document["protocol_evaluator"]
    return "\n".join([
        f"# {LABEL}", "",
        "## CONTROL-07 private proposal: a no-paid, fail-closed scientific-review gate (inert; not adopted)", "",
        f"Internal IDs: CYCLE-37 / ATTEMPT-07-20260925. Requirement R37A07-03 (TP37-A07-03). Control: "
        f"{document['control']}. Validation receipt `{receipt}` (result **{document['result']}**). Proposed bytes: "
        f"`{document['proposed_root']}`; inert patch `{document['patch']['path']}` (SHA-256 "
        f"`{document['patch']['sha256']}`). Subjects: main `{document['subjects']['main']}`, repair "
        f"`{document['subjects']['repair']}`, candidate `{document['subjects']['candidate']}`.", "",
        "This proposal changes no active control, runs no workflow, calls no provider and contains no approval. The "
        "only green proposed case is a synthetic TEST_ONLY approval, which is not a review receipt.", "",
        "### Authority", "",
        f"The committed protocol `{PROTOCOL}` (SHA-256 `{PROTOCOL_SHA256}`) is `PREPARATION_NOT_APPROVED`: a control "
        "change needs an independent reviewer separate from its author and a named bootstrap approval receipt, and "
        "the hosted workflow must take its checker from the protected base. The Attempt 6 manager's characterization "
        "(`CONTROL_AUTHORITY_CHARACTERIZATION.json`) approved neither existing bundle. The repository's own evaluator "
        f"(`{evaluator['module']}`) refuses this change without a receipt ({evaluator['change_without_receipt']['findings']}) "
        f"and under self-approval ({evaluator['change_with_self_approval']['findings']}), and refuses even a PASS report "
        f"while the protocol is unapproved ({evaluator['pass_report_under_unapproved_protocol']['findings']}).", "",
        "### The six control surfaces (SHA-256 prefixes)", "", *rows, "",
        "The proposal changes exactly the checker and the hosted workflow; the paid workflow stays absent (as on main); "
        "the rules, prompt and schema keep main's bytes.", "",
        "### Current behavior (characterized before proposing) and the proposal, offline", "",
        "Exit 0 is a successful check. Main's checker is green on a FAIL, BLOCKED or SKIPPED report; the repair "
        "checker refuses those verdicts; neither asks who reviewed. The proposal is green only for the synthetic "
        "TEST_ONLY eligible independent exact-head approval, and only when the fixture flag the workflow never passes "
        "is given.", "", *table, "", *workflow_rows, "",
        "### What the proposal does", "",
        "* The hosted job keeps the required context name `codex-review`, has read-only permissions, uses no secret "
        "and no model, and has no dispatch or comment step.",
        "* It takes the checker and the review-rule identity from the pull request's protected base "
        "(`git show \"${BASE_SHA}:...\"`), never from the pull request's tree.",
        "* It reads the pull request's reviews through the read-only token. The checker admits a report only when the "
        "latest review at the exact head by an eligible independent reviewer (not the author; a collaborator, member or "
        "owner) is APPROVED and carries the report after the marker `BAS-SCIENTIFIC-REVIEW-REPORT v1`; the report must "
        "be PASS with the exact pull request, base, head, merge, inventory and rule identity and no unresolved P0/P1.",
        "* Everything else fails: no review, FAIL/BLOCKED/SKIPPED or unknown verdicts, stale, dismissed, unapproved, "
        "self-approved or ineligible reviews, a later change request, a report absent from the approval, a malformed "
        "report, a changed inventory, and a pull request that changes a control surface.", "",
        "### Bootstrap and publication prerequisites (exact; none granted by this attempt)", "",
        "1. **Publication authority** (owner): an explicit grant to push a control-change branch holding exactly this "
        "patch and to open one pull request against `main`.",
        "2. **Eligible independent GitHub review** (the protocol's `GitHub independent required reviewer`): a "
        "collaborator with write access who is neither the change's author nor its last pusher approves the exact "
        "head, with the report block, satisfying `required_approving_review_count: 1`, `require_last_push_approval` "
        "and `dismiss_stale_reviews`.",
        "3. **Named bootstrap receipt** (owner): the adoption pull request cannot pass its own gate -- main's checker "
        "does not know `--reviews` and the proposal refuses a pull request that changes its own checker -- so the owner "
        "records a one-time decision naming the pull request, its exact head and tree, this receipt's SHA-256 and the "
        "reviewer's review id, and the exact admission route (for example removing `codex-review` from the required "
        "contexts for that single merge, with admins still enforced, and restoring it immediately). This is the "
        "`requires_named_bootstrap_approval_receipt` step; no worker, manager statement or fixture can supply it.",
        "4. **Protocol successor** (after adoption): a reviewed follow-up recording the adopted bindings and "
        "`bootstrap_status: APPROVED` with that receipt. The current protocol trusts a model identity "
        "(`gpt-5.3-codex`/`low`) and a prompt hash that is the repair branch's, not main's; under a no-paid gate the "
        "trust anchor is the reviewer's authority, which that successor must state (an owner decision).", "",
        "### Adoption, rollback and verification actions", "",
        "* **Adopt** (only after 1-3): apply the patch, open the pull request, collect the eligible review, record the "
        "bootstrap receipt, merge through the authorized route, restore every required context, read back main's "
        "protection and the merged bytes.",
        "* **Rollback**: revert the adoption commit (main's checker `214d1cde...` and workflow `74496c14...` return), "
        "restore protection if it was changed, read both back.",
        "* **Verify on the merged main**: test pull requests with no review, a self-approval, a FAIL report, a stale "
        "approval, a change to the checker, and one eligible PASS approval: only the last is green; the run logs show "
        "no provider call and no secret.", "",
        "### Remaining limits", "",
        "Offline behavior is proved on synthetic fixtures; hosted behavior, GitHub's association and last-push rules and "
        "the bootstrap route are not exercised here. The two candidate control compatibility errors remain visible "
        "until an authorized adoption. This document is a proposal, not an approval, adoption or publication.", ""])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    checked = sub.add_parser("validate")
    checked.add_argument("--out-root", type=Path, required=True, help="the attempt evidence root (proposal inputs)")
    checked.add_argument("--receipt", type=Path, default=None, help="default <out-root>/CONTROL07_PROPOSAL_VALIDATION.json")
    checked.add_argument("--markdown", type=Path, default=None, help="default <out-root>/CONTROL07_PROPOSAL.md")
    checked.add_argument("--patch", type=Path, default=None,
                         help="default <out-root>/evidence/control07/CONTROL07_PROPOSAL.patch")
    checked.add_argument("--candidate", default=None)
    args = parser.parse_args(argv)
    root = args.out_root.resolve()
    receipt = (args.receipt or root / "CONTROL07_PROPOSAL_VALIDATION.json").resolve()
    markdown = (args.markdown or root / "CONTROL07_PROPOSAL.md").resolve()
    patch = (args.patch or root / "evidence" / "control07" / "CONTROL07_PROPOSAL.patch").resolve()
    if markdown.exists():
        raise SystemExit(f"{markdown} exists; the proposal document is written once")
    document = validate(root / "evidence" / "control07" / "proposed", receipt, patch, args.candidate)
    with markdown.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(render_markdown(document, receipt))
    print(json.dumps({"result": document["result"], "checks": document["checks"],
                      "current_green": document["characterization"]["current_checkers_green_on"]}, indent=2))
    return 0 if document["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
