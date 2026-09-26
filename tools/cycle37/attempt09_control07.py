r"""Cycle #37 — Attempt #9 — retain and rebind the qualified, inert CONTROL-07 proposal (R37A09-03-A/B).

    attempt09_control07.py retain   --out-root <attempt 9 evidence root>
    attempt09_control07.py validate --out-root <attempt 9 evidence root> [--receipt R --markdown M --patch P]
                                    [--candidate <revision>]

The proposal was qualified offline by the Attempt 7 manager (21 independent cases) and that qualification was carried
by the Attempt 8 manager under verified unchanged dependencies and the current candidate
(``CONTROL07_INDEPENDENT_REVIEW.json``, 19 cases re-run there, ``reused_not_reexecuted``); TP37-A09-03 says: retain its
bytes and rebind the final candidate, do not repeat unchanged proof. This tool:

* ``retain`` copies the Attempt 8 retained proposed bytes (``attempt08\evidence\control07\proposed``, themselves the
  Attempt 7 qualified bytes) byte for byte, create-only, into ``<out-root>\evidence\control07\proposed`` -- outside
  every checkout, never executed as hosted authority -- and proves every file's SHA-256 against the Attempt 8 copy and
  the Attempt 7 original;
* ``validate`` runs the preserved offline qualification (``attempt07_control07``, unchanged) rebound to the Attempt 9
  identity, roots and subjects -- main, this repair head and the final candidate -- so the receipt binds the exact
  heads it was run at (this is the worker's own matrix re-run at new heads, which the lane needs to bind the final
  candidate; it is not a second independent review); it proves the regenerated patch is byte-identical to the
  qualified patch (``fab1911e...``), and records the issued Attempt 8 proposal document, its validation receipt and
  the manager's Attempt 8 independent review and integration decision by digest.

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

CYCLE_NUMBER, ATTEMPT_NUMBER = 37, 9
LABEL = "Cycle #37 — Attempt #9 — IN_PROGRESS_LOCAL_WORK_REMAINS"
VALIDATION_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a09")
ATTEMPT7_ROOT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle37\attempt07")
ATTEMPT8_ROOT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle37\attempt08")
ATTEMPT7_PROPOSED = ATTEMPT7_ROOT / "evidence" / "control07" / "proposed"
ATTEMPT8_PROPOSED = ATTEMPT8_ROOT / "evidence" / "control07" / "proposed"
QUALIFIED_PATCH_SHA256 = "fab1911ef3e2de173bdfb12ca30921f1688b8375cb354bbcce0387f50a2b7630"
ATTEMPT8_PATCH = ATTEMPT8_ROOT / "evidence" / "control07" / "CONTROL07_PROPOSAL.patch"
ATTEMPT8_DOCUMENT = ATTEMPT8_ROOT / "CONTROL07_PROPOSAL.md"
ATTEMPT8_DOCUMENT_SHA256 = "fef4da28e52bc8dc45d12b0a64545f46e6cad9b2b773fb2c054b60daa28599e3"
ATTEMPT8_VALIDATION = ATTEMPT8_ROOT / "CONTROL07_PROPOSAL_VALIDATION.json"
MANAGER_REVIEW = Path(r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle37\attempt08\review-20260926T151153Z"
                      r"\CONTROL07_INDEPENDENT_REVIEW.json")
MANAGER_REVIEW_SHA256 = "e31cbe4841f7840a526504d32d7919ade65959be6fe3f68088f7b518cb5bd34e"
INTEGRATION_DECISION = MANAGER_REVIEW.parent / "INTEGRATION_AUTHORITY_DECISION.md"
INTEGRATION_DECISION_SHA256 = "4d6893ac1789d15180e6de07ba78e51d5a4959077d67c91e117387c5c2f12304"
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
    """Copy the Attempt 8 retained bytes, create-only, and prove each against the Attempt 8 and Attempt 7 files."""

    target = out_root / "evidence" / "control07" / "proposed"
    if target.exists():
        raise SystemExit(f"{target} exists; the retained proposal is copied once")
    for source in sorted(p for p in ATTEMPT8_PROPOSED.rglob("*") if p.is_file()):
        destination = target / source.relative_to(ATTEMPT8_PROPOSED)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as reader, destination.open("xb") as writer:
            shutil.copyfileobj(reader, writer)
    retained, attempt8, attempt7 = _files(target), _files(ATTEMPT8_PROPOSED), _files(ATTEMPT7_PROPOSED)
    if not retained or retained != attempt8 or retained != attempt7:
        raise SystemExit(f"the retained proposal is not byte-identical to the Attempt 8 and 7 copies: {retained}")
    return {"source": str(ATTEMPT8_PROPOSED), "target": str(target), "files": retained, "byte_identical": True}


def _retention(out_root: Path, document: dict[str, Any]) -> dict[str, Any]:
    files = _files(out_root / "evidence" / "control07" / "proposed")
    patch = document.get("patch") or {}
    review = json.loads(MANAGER_REVIEW.read_text(encoding="utf-8"))
    attempt8 = json.loads(ATTEMPT8_VALIDATION.read_text(encoding="utf-8"))
    return {
        "proposed_bytes_identical_to_attempt8_and_attempt7": files == _files(ATTEMPT8_PROPOSED) == _files(ATTEMPT7_PROPOSED),
        "proposed_files": files,
        "patch_identical_to_the_qualified_patch": patch.get("sha256") == QUALIFIED_PATCH_SHA256
        and sha256_file(ATTEMPT8_PATCH) == QUALIFIED_PATCH_SHA256,
        "attempt8_patch": {"path": str(ATTEMPT8_PATCH), "sha256": sha256_file(ATTEMPT8_PATCH)},
        "attempt8_document": {"path": str(ATTEMPT8_DOCUMENT), "sha256": sha256_file(ATTEMPT8_DOCUMENT),
                              "expected_sha256": ATTEMPT8_DOCUMENT_SHA256,
                              "as_issued": sha256_file(ATTEMPT8_DOCUMENT) == ATTEMPT8_DOCUMENT_SHA256},
        "attempt8_validation": {"path": str(ATTEMPT8_VALIDATION), "sha256": sha256_file(ATTEMPT8_VALIDATION),
                                "result": attempt8.get("result"), "subjects": attempt8.get("subjects")},
        "manager_independent_review": {
            "path": str(MANAGER_REVIEW), "sha256": sha256_file(MANAGER_REVIEW), "expected_sha256": MANAGER_REVIEW_SHA256,
            "summary": {"state": review.get("state"), "all_expected": review.get("all_expected"),
                        "cases": review.get("cases"), "runs": review.get("runs"), "scope": review.get("scope"),
                        "owner_decision": review.get("owner_decision"),
                        "reused_not_reexecuted": review.get("reused_not_reexecuted"),
                        "candidate_head": review.get("candidate_head")},
            "reviewed_checker_sha256": review.get("checker_sha256"),
            "reviewed_workflow_sha256": review.get("workflow_sha256"),
            "retained_bytes_are_the_reviewed_bytes": (
                files.get(a7c.CHECKER) == review.get("checker_sha256")
                and files.get(a7c.WORKFLOW) == review.get("workflow_sha256"))},
        "integration_authority_decision": {"path": str(INTEGRATION_DECISION), "sha256": sha256_file(INTEGRATION_DECISION),
                                           "expected_sha256": INTEGRATION_DECISION_SHA256},
        "control_change_protocol": {"path": str(CONTROL_AUTHORITY), "sha256": sha256_file(CONTROL_AUTHORITY),
                                    "expected_sha256": CONTROL_AUTHORITY_SHA256},
        "rebinding": ("The retained proposal was re-run through the worker's offline matrix at the Attempt 9 subjects in "
                      "this receipt, only to bind the final candidate; its bytes and patch are the qualified ones. The "
                      "proof's other dependencies -- main's six control surfaces, the committed CONTROL-07 protocol and "
                      "the repository's evaluator -- are unchanged by Attempt 9 (neither repair touches them), so the "
                      "managers' independent offline cases apply to these bytes; this receipt is not a second independent "
                      "review and adopts nothing."),
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
                "attempt9_retention": _retention(root, document)}
    retention = document["attempt9_retention"]
    document["checks"] = {**document["checks"],
                          "proposed_bytes_identical_to_attempt8_and_attempt7":
                              retention["proposed_bytes_identical_to_attempt8_and_attempt7"],
                          "patch_identical_to_the_qualified_patch": retention["patch_identical_to_the_qualified_patch"],
                          "attempt8_proposal_document_is_the_issued_bytes": retention["attempt8_document"]["as_issued"],
                          "manager_review_is_the_issued_bytes":
                              retention["manager_independent_review"]["sha256"] == MANAGER_REVIEW_SHA256,
                          "retained_bytes_are_the_manager_reviewed_bytes":
                              retention["manager_independent_review"]["retained_bytes_are_the_reviewed_bytes"],
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
    text = text.replace(old, "Internal IDs: CYCLE-37 / ATTEMPT-09-20260926. Requirement R37A09-03 (TP37-A09-03).")
    header = "### Authority"
    retained = "\n".join([
        "### Retained from Attempts 7 and 8, rebound here (not redesigned)", "",
        "The proposed bytes are the qualified bytes, copied byte for byte from the Attempt 8 retention (identical to it and "
        f"to the Attempt 7 original: {retention['proposed_bytes_identical_to_attempt8_and_attempt7']}); the regenerated "
        f"patch is byte-identical to the qualified patch `{QUALIFIED_PATCH_SHA256}` "
        f"({retention['patch_identical_to_the_qualified_patch']}). The issued Attempt 8 proposal document "
        f"`{ATTEMPT8_DOCUMENT}` (SHA-256 `{retention['attempt8_document']['sha256']}`) and its validation receipt stay "
        "unchanged as the record this one rebinds; the Attempt 8 manager's independent review "
        f"`{MANAGER_REVIEW.name}` (SHA-256 `{retention['manager_independent_review']['sha256']}`) carried the "
        "qualification of these exact bytes, and its `INTEGRATION_AUTHORITY_DECISION.md` "
        f"(SHA-256 `{retention['integration_authority_decision']['sha256']}`) is the concrete decision subject. This "
        "receipt re-runs the worker's offline matrix only to bind the Attempt 9 repair and final candidate heads; it is "
        "not a second independent review, and it adopts nothing.", "", header])
    text = text.replace(header, retained, 1)
    with markdown.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print(json.dumps({"result": document["result"], "checks": document["checks"],
                      "current_green": document["characterization"]["current_checkers_green_on"]}, indent=2))
    return 0 if document["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
