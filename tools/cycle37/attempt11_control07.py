r"""Cycle #37 — Attempt #11 — retain and rebind the qualified, inert CONTROL-07 proposal (R37A11-03-A/B).

    attempt11_control07.py retain   --out-root <attempt 11 evidence root>
    attempt11_control07.py validate --out-root <attempt 11 evidence root> [--receipt R --markdown M --patch P]
                                    [--candidate <revision>]

The proposal was qualified offline by the Attempt 7 manager (21 independent cases); the Attempt 8, 9 and 10 managers
carried that qualification under verified unchanged dependencies and re-qualified it at each final candidate (the
Attempt 10 manager's ``CONTROL07_INDEPENDENT_REVIEW.json`` binds the final ``cf992e4b`` receipt and retains the Attempt
9 review, which retains the Attempt 7 case review). TP37-A11-03 says: retain its bytes and rebind the final candidate;
rerun affected cases only if the proposal or its authority changes -- neither did. This tool:

* ``retain`` copies the Attempt 10 retained proposed bytes (``attempt10\evidence\control07\proposed``, themselves the
  Attempt 9, 8 and 7 qualified bytes) byte for byte, create-only, into ``<out-root>\evidence\control07\proposed`` --
  outside every checkout, never executed as hosted authority -- and proves every file's SHA-256 against the Attempt 10,
  9, 8 and 7 copies;
* ``validate`` runs the preserved offline qualification (``attempt07_control07``, unchanged) rebound to the Attempt 11
  identity, roots and subjects -- main, this repair head and the final candidate -- so the receipt binds the exact
  heads it was run at (the worker's own matrix re-run at new heads, which the lane needs to bind the final candidate;
  not a second independent review); it proves the regenerated patch is byte-identical to the qualified patch
  (``fab1911e...``), and records the issued Attempt 10 proposal document, its validation receipt, the Attempt 10
  manager's independent review (and the chain of reviews it retains, down to the Attempt 7 case review) and the
  Attempt 10 integration decision by digest.

The Attempt 10 manager noted that the top-level Attempt 10 proposal described an intermediate candidate head while its
final lane re-qualified the final one. This receipt names the candidate it was run at; the handoff copy is written
only at the final candidate.

A synthetic approval is TEST_ONLY; nothing here is a review receipt, an approval, an adoption or a publication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import attempt07_control07 as a7c  # noqa: E402  (the preserved Attempt 7 qualification)

CYCLE_NUMBER, ATTEMPT_NUMBER = 37, 11
LABEL = "Cycle #37 — Attempt #11 — IN_PROGRESS_LOCAL_WORK_REMAINS"
VALIDATION_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a11")
OPS = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle37")
ATTEMPT7_PROPOSED = OPS / "attempt07" / "evidence" / "control07" / "proposed"
ATTEMPT8_PROPOSED = OPS / "attempt08" / "evidence" / "control07" / "proposed"
ATTEMPT9_PROPOSED = OPS / "attempt09" / "evidence" / "control07" / "proposed"
ATTEMPT10_ROOT = OPS / "attempt10"
ATTEMPT10_PROPOSED = ATTEMPT10_ROOT / "evidence" / "control07" / "proposed"
QUALIFIED_PATCH_SHA256 = "fab1911ef3e2de173bdfb12ca30921f1688b8375cb354bbcce0387f50a2b7630"
ATTEMPT10_PATCH = ATTEMPT10_ROOT / "evidence" / "control07" / "CONTROL07_PROPOSAL.patch"
ATTEMPT10_DOCUMENT = ATTEMPT10_ROOT / "CONTROL07_PROPOSAL.md"
ATTEMPT10_DOCUMENT_SHA256 = "da5a946065cff320fb826df9a740d6d551fe99f93b4402ec5d9a735f45dced04"
ATTEMPT10_VALIDATION = ATTEMPT10_ROOT / "CONTROL07_PROPOSAL_VALIDATION.json"
ATTEMPT10_VALIDATION_SHA256 = "ad0ec97812bfdff7e8e8aa278918cbbd9aeeb24182c1b6ac7126ffc0774b750a"
MANAGER_REVIEW = Path(r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle37\attempt10\review-20260928T174921Z"
                      r"\CONTROL07_INDEPENDENT_REVIEW.json")
MANAGER_REVIEW_SHA256 = "2d1e63297d1f158913e648ebc25a3f50a6966c5e767c1b9f0ae78375b0b7ea2c"
INTEGRATION_DECISION = MANAGER_REVIEW.parent / "INTEGRATION_AUTHORITY_DECISION.md"
INTEGRATION_DECISION_SHA256 = "b97dc3e22bed1bfe956a091f68f5e5b2e4e35c5a6264ffc5b6822c2b8dac690a"
CONTROL_AUTHORITY = Path(r"C:\BatteredAggieSyndrome.worktrees\cycle37-rework\artifacts\scientific_integrity\cycle27"
                         r"\CYCLE27_TRUSTED_CONTROL_CHANGE_PROTOCOL.json")
CONTROL_AUTHORITY_SHA256 = "b76f6d02b07430dd9a1865d417090588e4142f87ed348cdd0cfd90533ec29831"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rebind() -> None:
    a7c.CYCLE_NUMBER, a7c.ATTEMPT_NUMBER, a7c.LABEL = CYCLE_NUMBER, ATTEMPT_NUMBER, LABEL
    a7c.VALIDATION_ROOT = VALIDATION_ROOT


def _files(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): sha256_file(p) for p in sorted(root.rglob("*")) if p.is_file()}


def _prior_copies_equal(files: dict[str, str]) -> bool:
    return bool(files) and (files == _files(ATTEMPT10_PROPOSED) == _files(ATTEMPT9_PROPOSED)
                            == _files(ATTEMPT8_PROPOSED) == _files(ATTEMPT7_PROPOSED))


def retain(out_root: Path) -> dict[str, Any]:
    """Copy the Attempt 10 retained bytes, create-only, and prove each against the Attempt 10, 9, 8 and 7 files."""

    target = out_root / "evidence" / "control07" / "proposed"
    if target.exists():
        raise SystemExit(f"{target} exists; the retained proposal is copied once")
    for source in sorted(p for p in ATTEMPT10_PROPOSED.rglob("*") if p.is_file()):
        destination = target / source.relative_to(ATTEMPT10_PROPOSED)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as reader, destination.open("xb") as writer:
            shutil.copyfileobj(reader, writer)
    retained = _files(target)
    if not _prior_copies_equal(retained):
        raise SystemExit(f"the retained proposal is not byte-identical to the Attempt 10, 9, 8 and 7 copies: {retained}")
    return {"source": str(ATTEMPT10_PROPOSED), "target": str(target), "files": retained, "byte_identical": True}


def _review_chain(review: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Follow each manager review's ``retained_independent_review`` (each digest checked against the one naming it)
    down to the review that holds the independent cases."""

    chain: list[dict[str, Any]] = []
    current = review
    for _ in range(6):
        path = Path(str(current.get("retained_independent_review") or ""))
        expected = current.get("retained_independent_review_sha256")
        if not path.is_file():
            chain.append({"path": str(path), "present": False, "expected_sha256": expected})
            return chain, {}
        actual = sha256_file(path)
        document = json.loads(path.read_text(encoding="utf-8"))
        chain.append({"path": str(path), "present": True, "sha256": actual, "expected_sha256": expected,
                      "as_named": actual == expected, "holds_cases": bool(document.get("cases"))})
        if document.get("cases"):
            return chain, document
        current = document
    return chain, {}


def _retention(out_root: Path, document: dict[str, Any]) -> dict[str, Any]:
    files = _files(out_root / "evidence" / "control07" / "proposed")
    patch = document.get("patch") or {}
    review = json.loads(MANAGER_REVIEW.read_text(encoding="utf-8"))
    chain, case_review = _review_chain(review)
    attempt10 = json.loads(ATTEMPT10_VALIDATION.read_text(encoding="utf-8"))
    qualification = review.get("final_qualification") or {}
    return {
        "proposed_bytes_identical_to_attempt10_9_8_and_7": _prior_copies_equal(files),
        "proposed_files": files,
        "patch_identical_to_the_qualified_patch": patch.get("sha256") == QUALIFIED_PATCH_SHA256
        and sha256_file(ATTEMPT10_PATCH) == QUALIFIED_PATCH_SHA256,
        "attempt10_patch": {"path": str(ATTEMPT10_PATCH), "sha256": sha256_file(ATTEMPT10_PATCH)},
        "attempt10_document": {"path": str(ATTEMPT10_DOCUMENT), "sha256": sha256_file(ATTEMPT10_DOCUMENT),
                               "expected_sha256": ATTEMPT10_DOCUMENT_SHA256,
                               "as_issued": sha256_file(ATTEMPT10_DOCUMENT) == ATTEMPT10_DOCUMENT_SHA256},
        "attempt10_validation": {"path": str(ATTEMPT10_VALIDATION), "sha256": sha256_file(ATTEMPT10_VALIDATION),
                                 "expected_sha256": ATTEMPT10_VALIDATION_SHA256,
                                 "as_issued": sha256_file(ATTEMPT10_VALIDATION) == ATTEMPT10_VALIDATION_SHA256,
                                 "result": attempt10.get("result"), "subjects": attempt10.get("subjects")},
        "manager_independent_review": {
            "path": str(MANAGER_REVIEW), "sha256": sha256_file(MANAGER_REVIEW), "expected_sha256": MANAGER_REVIEW_SHA256,
            "summary": {"current_receipt": review.get("current_receipt"),
                        "final_qualification_holds": qualification.get("holds"),
                        "final_qualification_checks_all_true": all((qualification.get("checks") or {"none": False}).values()),
                        "compatibility": review.get("compatibility"), "correction": review.get("correction")},
            "retained_review_chain": chain,
            "case_review": {"all_expected": case_review.get("all_expected"), "cases": len(case_review.get("cases") or []),
                            "reviewed_checker_sha256": case_review.get("checker_sha256"),
                            "reviewed_workflow_sha256": case_review.get("workflow_sha256")},
            "retained_bytes_are_the_reviewed_bytes": (
                bool(case_review) and all(row.get("as_named") for row in chain)
                and files.get(a7c.CHECKER) == case_review.get("checker_sha256")
                and files.get(a7c.WORKFLOW) == case_review.get("workflow_sha256"))},
        "integration_authority_decision": {"path": str(INTEGRATION_DECISION), "sha256": sha256_file(INTEGRATION_DECISION),
                                           "expected_sha256": INTEGRATION_DECISION_SHA256},
        "control_change_protocol": {"path": str(CONTROL_AUTHORITY), "sha256": sha256_file(CONTROL_AUTHORITY),
                                    "expected_sha256": CONTROL_AUTHORITY_SHA256},
        "rebinding": ("The retained proposal was re-run through the worker's offline matrix at the Attempt 11 subjects "
                      "in this receipt, only to bind the final candidate; its bytes and patch are the qualified ones. The "
                      "proof's other dependencies -- main's six control surfaces, the committed CONTROL-07 protocol and "
                      "the repository's evaluator -- are unchanged by Attempt 11 (the restructure-lineage repair touches "
                      "none of them), so the managers' independent offline cases apply to these bytes; this receipt is "
                      "not a second independent review and adopts nothing."),
    }


def main(argv: list[str] | None = None) -> int:
    rebind()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    kept = sub.add_parser("retain")
    kept.add_argument("--out-root", type=Path, required=True)
    checked = sub.add_parser("validate")
    checked.add_argument("--out-root", type=Path, required=True)
    checked.add_argument("--receipt", type=Path, default=None)
    checked.add_argument("--markdown", type=Path, default=None)
    checked.add_argument("--patch", type=Path, default=None)
    checked.add_argument("--candidate", default=None)
    args = parser.parse_args(argv)
    root = args.out_root.resolve()
    if args.mode == "retain":
        print(json.dumps(retain(root), indent=2))
        return 0
    receipt = (args.receipt or root / "CONTROL07_PROPOSAL_VALIDATION.json").resolve()
    markdown = (args.markdown or root / "CONTROL07_PROPOSAL.md").resolve()
    patch = (args.patch or root / "evidence" / "control07" / "CONTROL07_PROPOSAL.patch").resolve()
    if markdown.exists() or receipt.exists():
        raise SystemExit(f"{markdown} or {receipt} exists; the proposal document and receipt are written once")
    matrix = receipt.with_name(receipt.stem + "_OFFLINE_MATRIX.json")
    document = a7c.validate(root / "evidence" / "control07" / "proposed", matrix, patch, args.candidate)
    document = {**document, "label": f"{LABEL} (CONTROL-07 private proposal: retained, rebound, not adopted)",
                "offline_matrix_receipt": {"path": str(matrix), "sha256": sha256_file(matrix)},
                "attempt11_retention": _retention(root, document)}
    retention = document["attempt11_retention"]
    document["checks"] = {**document["checks"],
                          "proposed_bytes_identical_to_attempt10_9_8_and_7":
                              retention["proposed_bytes_identical_to_attempt10_9_8_and_7"],
                          "patch_identical_to_the_qualified_patch": retention["patch_identical_to_the_qualified_patch"],
                          "attempt10_proposal_document_is_the_issued_bytes": retention["attempt10_document"]["as_issued"],
                          "attempt10_validation_is_the_issued_bytes": retention["attempt10_validation"]["as_issued"],
                          "manager_review_is_the_issued_bytes":
                              retention["manager_independent_review"]["sha256"] == MANAGER_REVIEW_SHA256,
                          "retained_bytes_are_the_manager_reviewed_bytes":
                              retention["manager_independent_review"]["retained_bytes_are_the_reviewed_bytes"],
                          "integration_decision_is_the_issued_bytes":
                              retention["integration_authority_decision"]["sha256"] == INTEGRATION_DECISION_SHA256,
                          "control_change_protocol_is_the_issued_bytes":
                              retention["control_change_protocol"]["sha256"] == CONTROL_AUTHORITY_SHA256}
    document["result"] = "PASS" if all(document["checks"].values()) else "FAIL"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    with receipt.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, indent=2, ensure_ascii=False, default=str) + "\n")
    text = a7c.render_markdown(document, receipt)
    old = "Internal IDs: CYCLE-37 / ATTEMPT-07-20260925. Requirement R37A07-03 (TP37-A07-03)."
    if old not in text:
        raise SystemExit("the preserved proposal renderer changed; refusing to relabel it")
    text = text.replace(old, "Internal IDs: CYCLE-37 / ATTEMPT-11-20260928. Requirement R37A11-03 (TP37-A11-03).")
    header = "### Authority"
    retained = "\n".join([
        "### Retained from Attempts 7 to 10, rebound here (not redesigned)", "",
        "The proposed bytes are the qualified bytes, copied byte for byte from the Attempt 10 retention (identical to it "
        f"and to the Attempt 9, 8 and 7 copies: {retention['proposed_bytes_identical_to_attempt10_9_8_and_7']}); the "
        f"regenerated patch is byte-identical to the qualified patch `{QUALIFIED_PATCH_SHA256}` "
        f"({retention['patch_identical_to_the_qualified_patch']}). The issued Attempt 10 proposal document "
        f"`{ATTEMPT10_DOCUMENT}` (SHA-256 `{retention['attempt10_document']['sha256']}`) and its validation receipt stay "
        "unchanged as the record this one rebinds; the Attempt 10 manager's independent review "
        f"`{MANAGER_REVIEW.name}` (SHA-256 `{retention['manager_independent_review']['sha256']}`) re-qualified these exact "
        "bytes at the Attempt 10 final candidate and retains the Attempt 9 review, which retains the Attempt 7 manager's "
        "independent case review; its "
        f"`INTEGRATION_AUTHORITY_DECISION.md` (SHA-256 `{retention['integration_authority_decision']['sha256']}`) is the "
        "concrete decision subject. This receipt re-runs the worker's offline matrix only to bind the Attempt 11 repair "
        f"and the candidate head it was run at (`{args.candidate}`); it is not a second independent review, and it "
        "adopts nothing.", "", header])
    text = text.replace(header, retained, 1)
    with markdown.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print(json.dumps({"result": document["result"], "checks": document["checks"],
                      "current_green": document["characterization"]["current_checkers_green_on"]}, indent=2))
    return 0 if document["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
