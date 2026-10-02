r"""Cycle #37 — Attempt #10 — retain and rebind the qualified, inert CONTROL-07 proposal (R37A10-03-A/B).

    attempt10_control07.py retain   --out-root <attempt 10 evidence root>
    attempt10_control07.py validate --out-root <attempt 10 evidence root> [--receipt R --markdown M --patch P]
                                    [--candidate <revision>]

The proposal was qualified offline by the Attempt 7 manager (21 independent cases); the Attempt 8 and Attempt 9 managers
carried that qualification under verified unchanged dependencies and re-qualified it at each final candidate (the
Attempt 9 manager's ``CONTROL07_INDEPENDENT_REVIEW.json`` binds the final ``514d74dc`` receipt and retains the Attempt 7
review). TP37-A10-03 says: retain its bytes and rebind the final candidate; rerun affected cases only if the proposal
or its authority changes -- neither did. This tool:

* ``retain`` copies the Attempt 9 retained proposed bytes (``attempt09\evidence\control07\proposed``, themselves the
  Attempt 8 and Attempt 7 qualified bytes) byte for byte, create-only, into ``<out-root>\evidence\control07\proposed``
  -- outside every checkout, never executed as hosted authority -- and proves every file's SHA-256 against the Attempt
  9, 8 and 7 copies;
* ``validate`` runs the preserved offline qualification (``attempt07_control07``, unchanged) rebound to the Attempt 10
  identity, roots and subjects -- main, this repair head and the final candidate -- so the receipt binds the exact
  heads it was run at (the worker's own matrix re-run at new heads, which the lane needs to bind the final candidate;
  not a second independent review); it proves the regenerated patch is byte-identical to the qualified patch
  (``fab1911e...``), and records the issued Attempt 9 proposal document, its validation receipt, the Attempt 9 manager's
  independent review (and the Attempt 7 review it retains) and the Attempt 9 integration decision by digest.

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

CYCLE_NUMBER, ATTEMPT_NUMBER = 37, 10
LABEL = "Cycle #37 — Attempt #10 — IN_PROGRESS_LOCAL_WORK_REMAINS"
VALIDATION_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a10")
OPS = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle37")
ATTEMPT7_PROPOSED = OPS / "attempt07" / "evidence" / "control07" / "proposed"
ATTEMPT8_PROPOSED = OPS / "attempt08" / "evidence" / "control07" / "proposed"
ATTEMPT9_ROOT = OPS / "attempt09"
ATTEMPT9_PROPOSED = ATTEMPT9_ROOT / "evidence" / "control07" / "proposed"
QUALIFIED_PATCH_SHA256 = "fab1911ef3e2de173bdfb12ca30921f1688b8375cb354bbcce0387f50a2b7630"
ATTEMPT9_PATCH = ATTEMPT9_ROOT / "evidence" / "control07" / "CONTROL07_PROPOSAL.patch"
ATTEMPT9_DOCUMENT = ATTEMPT9_ROOT / "CONTROL07_PROPOSAL.md"
ATTEMPT9_DOCUMENT_SHA256 = "43b408b44895656c8ea0344efa95b3ea02d7e437a1f04e740f1ce2f000bcb90a"
ATTEMPT9_VALIDATION = ATTEMPT9_ROOT / "CONTROL07_PROPOSAL_VALIDATION.json"
MANAGER_REVIEW = Path(r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle37\attempt09\review-20260927T224734Z"
                      r"\CONTROL07_INDEPENDENT_REVIEW.json")
MANAGER_REVIEW_SHA256 = "ded5fe8672d7e5e6a41f9f533d58f37d098170cd6c8715866129583b35be709f"
INTEGRATION_DECISION = MANAGER_REVIEW.parent / "INTEGRATION_AUTHORITY_DECISION.md"
INTEGRATION_DECISION_SHA256 = "6b9dadfc5f89d9facbb06d9c77bd39f087c2155c9e112b8d460228462d4680d9"
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


def retain(out_root: Path) -> dict[str, Any]:
    """Copy the Attempt 9 retained bytes, create-only, and prove each against the Attempt 9, 8 and 7 files."""

    target = out_root / "evidence" / "control07" / "proposed"
    if target.exists():
        raise SystemExit(f"{target} exists; the retained proposal is copied once")
    for source in sorted(p for p in ATTEMPT9_PROPOSED.rglob("*") if p.is_file()):
        destination = target / source.relative_to(ATTEMPT9_PROPOSED)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as reader, destination.open("xb") as writer:
            shutil.copyfileobj(reader, writer)
    retained = _files(target)
    if not retained or not retained == _files(ATTEMPT9_PROPOSED) == _files(ATTEMPT8_PROPOSED) == _files(ATTEMPT7_PROPOSED):
        raise SystemExit(f"the retained proposal is not byte-identical to the Attempt 9, 8 and 7 copies: {retained}")
    return {"source": str(ATTEMPT9_PROPOSED), "target": str(target), "files": retained, "byte_identical": True}


def _retention(out_root: Path, document: dict[str, Any]) -> dict[str, Any]:
    files = _files(out_root / "evidence" / "control07" / "proposed")
    patch = document.get("patch") or {}
    review = json.loads(MANAGER_REVIEW.read_text(encoding="utf-8"))
    retained_review_path = Path(str(review.get("retained_independent_review") or ""))
    retained_review = (json.loads(retained_review_path.read_text(encoding="utf-8"))
                       if retained_review_path.is_file() else {})
    attempt9 = json.loads(ATTEMPT9_VALIDATION.read_text(encoding="utf-8"))
    qualification = review.get("final_qualification") or {}
    return {
        "proposed_bytes_identical_to_attempt9_8_and_7": (
            files == _files(ATTEMPT9_PROPOSED) == _files(ATTEMPT8_PROPOSED) == _files(ATTEMPT7_PROPOSED)),
        "proposed_files": files,
        "patch_identical_to_the_qualified_patch": patch.get("sha256") == QUALIFIED_PATCH_SHA256
        and sha256_file(ATTEMPT9_PATCH) == QUALIFIED_PATCH_SHA256,
        "attempt9_patch": {"path": str(ATTEMPT9_PATCH), "sha256": sha256_file(ATTEMPT9_PATCH)},
        "attempt9_document": {"path": str(ATTEMPT9_DOCUMENT), "sha256": sha256_file(ATTEMPT9_DOCUMENT),
                              "expected_sha256": ATTEMPT9_DOCUMENT_SHA256,
                              "as_issued": sha256_file(ATTEMPT9_DOCUMENT) == ATTEMPT9_DOCUMENT_SHA256},
        "attempt9_validation": {"path": str(ATTEMPT9_VALIDATION), "sha256": sha256_file(ATTEMPT9_VALIDATION),
                                "result": attempt9.get("result"), "subjects": attempt9.get("subjects")},
        "manager_independent_review": {
            "path": str(MANAGER_REVIEW), "sha256": sha256_file(MANAGER_REVIEW), "expected_sha256": MANAGER_REVIEW_SHA256,
            "summary": {"current_receipt": review.get("current_receipt"),
                        "final_qualification_holds": qualification.get("holds"),
                        "final_qualification_checks_all_true": all((qualification.get("checks") or {"none": False}).values()),
                        "correction": review.get("correction")},
            "retained_independent_review": {
                "path": str(retained_review_path), "sha256": sha256_file(retained_review_path)
                if retained_review_path.is_file() else None,
                "expected_sha256": review.get("retained_independent_review_sha256"),
                "all_expected": retained_review.get("all_expected"), "cases": len(retained_review.get("cases") or []),
                "reviewed_checker_sha256": retained_review.get("checker_sha256"),
                "reviewed_workflow_sha256": retained_review.get("workflow_sha256")},
            "retained_bytes_are_the_reviewed_bytes": (
                bool(retained_review) and retained_review_path.is_file()
                and sha256_file(retained_review_path) == review.get("retained_independent_review_sha256")
                and files.get(a7c.CHECKER) == retained_review.get("checker_sha256")
                and files.get(a7c.WORKFLOW) == retained_review.get("workflow_sha256"))},
        "integration_authority_decision": {"path": str(INTEGRATION_DECISION), "sha256": sha256_file(INTEGRATION_DECISION),
                                           "expected_sha256": INTEGRATION_DECISION_SHA256},
        "control_change_protocol": {"path": str(CONTROL_AUTHORITY), "sha256": sha256_file(CONTROL_AUTHORITY),
                                    "expected_sha256": CONTROL_AUTHORITY_SHA256},
        "rebinding": ("The retained proposal was re-run through the worker's offline matrix at the Attempt 10 subjects "
                      "in this receipt, only to bind the final candidate; its bytes and patch are the qualified ones. The "
                      "proof's other dependencies -- main's six control surfaces, the committed CONTROL-07 protocol and "
                      "the repository's evaluator -- are unchanged by Attempt 10 (the interval repair touches none of "
                      "them), so the managers' independent offline cases apply to these bytes; this receipt is not a "
                      "second independent review and adopts nothing."),
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
                "attempt10_retention": _retention(root, document)}
    retention = document["attempt10_retention"]
    document["checks"] = {**document["checks"],
                          "proposed_bytes_identical_to_attempt9_8_and_7":
                              retention["proposed_bytes_identical_to_attempt9_8_and_7"],
                          "patch_identical_to_the_qualified_patch": retention["patch_identical_to_the_qualified_patch"],
                          "attempt9_proposal_document_is_the_issued_bytes": retention["attempt9_document"]["as_issued"],
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
    text = text.replace(old, "Internal IDs: CYCLE-37 / ATTEMPT-10-20260927. Requirement R37A10-03 (TP37-A10-03).")
    header = "### Authority"
    retained = "\n".join([
        "### Retained from Attempts 7, 8 and 9, rebound here (not redesigned)", "",
        "The proposed bytes are the qualified bytes, copied byte for byte from the Attempt 9 retention (identical to it and "
        f"to the Attempt 8 and 7 copies: {retention['proposed_bytes_identical_to_attempt9_8_and_7']}); the regenerated "
        f"patch is byte-identical to the qualified patch `{QUALIFIED_PATCH_SHA256}` "
        f"({retention['patch_identical_to_the_qualified_patch']}). The issued Attempt 9 proposal document "
        f"`{ATTEMPT9_DOCUMENT}` (SHA-256 `{retention['attempt9_document']['sha256']}`) and its validation receipt stay "
        "unchanged as the record this one rebinds; the Attempt 9 manager's independent review "
        f"`{MANAGER_REVIEW.name}` (SHA-256 `{retention['manager_independent_review']['sha256']}`) re-qualified these exact "
        "bytes at the Attempt 9 final candidate and retains the Attempt 7 manager's independent case review, and its "
        f"`INTEGRATION_AUTHORITY_DECISION.md` (SHA-256 `{retention['integration_authority_decision']['sha256']}`) is the "
        "concrete decision subject. This receipt re-runs the worker's offline matrix only to bind the Attempt 10 repair "
        "and final candidate heads; it is not a second independent review, and it adopts nothing.", "", header])
    text = text.replace(header, retained, 1)
    with markdown.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print(json.dumps({"result": document["result"], "checks": document["checks"],
                      "current_green": document["characterization"]["current_checkers_green_on"]}, indent=2))
    return 0 if document["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
