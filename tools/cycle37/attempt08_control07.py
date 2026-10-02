r"""Cycle #37 — Attempt #8 — retain and rebind the qualified, inert CONTROL-07 proposal (R37A08-03-A/B).

    attempt08_control07.py retain   --out-root <attempt 8 evidence root>
    attempt08_control07.py validate --out-root <attempt 8 evidence root> [--receipt R --markdown M --patch P]
                                    [--candidate <revision>]

The Attempt 7 proposal was qualified offline by the Attempt 7 manager (21 independent cases,
``CONTROL07_INDEPENDENT_REVIEW.json``); Attempt 8 does not redesign it. This tool:

* ``retain`` copies the Attempt 7 proposed bytes (``attempt07\evidence\control07\proposed``) byte for byte, create-only,
  into ``<out-root>\evidence\control07\proposed`` -- outside every checkout, never executed as hosted authority -- and
  proves every file's SHA-256 against the Attempt 7 original;
* ``validate`` runs the preserved Attempt 7 offline qualification (``attempt07_control07``, unchanged) rebound to the
  Attempt 8 identity, roots and subjects -- main, this repair head and the final candidate -- so the receipt binds the
  exact heads it was run at; it then proves the regenerated patch is byte-identical to the qualified Attempt 7 patch
  (``fab1911e...``), records the retained Attempt 7 proposal document and validation receipt and the manager's
  independent review by digest, and writes ``CONTROL07_PROPOSAL_VALIDATION.json`` and ``CONTROL07_PROPOSAL.md``.

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

CYCLE_NUMBER, ATTEMPT_NUMBER = 37, 8
LABEL = "Cycle #37 — Attempt #8 — IN_PROGRESS_LOCAL_WORK_REMAINS"
VALIDATION_ROOT = Path(r"C:\BatteredAggieSyndrome.validation\c37a08")
ATTEMPT7_ROOT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle37\attempt07")
ATTEMPT7_PROPOSED = ATTEMPT7_ROOT / "evidence" / "control07" / "proposed"
ATTEMPT7_PATCH = ATTEMPT7_ROOT / "evidence" / "control07" / "CONTROL07_PROPOSAL.patch"
ATTEMPT7_PATCH_SHA256 = "fab1911ef3e2de173bdfb12ca30921f1688b8375cb354bbcce0387f50a2b7630"
ATTEMPT7_DOCUMENT = ATTEMPT7_ROOT / "CONTROL07_PROPOSAL.md"
ATTEMPT7_DOCUMENT_SHA256 = "d61e1266d4969c0577cb0d359804b12b1412686429b0ed2e8c71c987a43fa530"
ATTEMPT7_VALIDATION = ATTEMPT7_ROOT / "CONTROL07_PROPOSAL_VALIDATION.json"
MANAGER_REVIEW = Path(r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle37\attempt07\review-20260926T023810Z"
                      r"\CONTROL07_INDEPENDENT_REVIEW.json")
MANAGER_REVIEW_SHA256 = "da720f5bb3da928cfedf212987fa3029a9faa920d4a90c1cbcc5b86fdee5e4a4"
INTEGRATION_DECISION = MANAGER_REVIEW.parent / "INTEGRATION_AUTHORITY_DECISION.md"
INTEGRATION_DECISION_SHA256 = "c1b9c9be2935fcb1d541e5dcf7ced8c8d15be18d2408d50156bce82084f00968"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rebind() -> None:
    a7c.CYCLE_NUMBER, a7c.ATTEMPT_NUMBER, a7c.LABEL = CYCLE_NUMBER, ATTEMPT_NUMBER, LABEL
    a7c.VALIDATION_ROOT = VALIDATION_ROOT


def retain(out_root: Path) -> dict[str, Any]:
    """Copy the Attempt 7 proposed bytes, create-only, and prove each against its original."""

    target = out_root / "evidence" / "control07" / "proposed"
    if target.exists():
        raise SystemExit(f"{target} exists; the retained proposal is copied once")
    files = {}
    for source in sorted(p for p in ATTEMPT7_PROPOSED.rglob("*") if p.is_file()):
        relative = source.relative_to(ATTEMPT7_PROPOSED)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as reader, destination.open("xb") as writer:
            shutil.copyfileobj(reader, writer)
        files[relative.as_posix()] = {"attempt7_sha256": sha256_file(source), "retained_sha256": sha256_file(destination)}
    if not files or any(row["attempt7_sha256"] != row["retained_sha256"] for row in files.values()):
        raise SystemExit(f"the retained proposal is not byte-identical to the Attempt 7 original: {files}")
    return {"source": str(ATTEMPT7_PROPOSED), "target": str(target), "files": files, "byte_identical": True}


def _retention(out_root: Path, document: dict[str, Any]) -> dict[str, Any]:
    proposed = out_root / "evidence" / "control07" / "proposed"
    files = {p.relative_to(proposed).as_posix(): sha256_file(p) for p in sorted(proposed.rglob("*")) if p.is_file()}
    originals = {p.relative_to(ATTEMPT7_PROPOSED).as_posix(): sha256_file(p)
                 for p in sorted(ATTEMPT7_PROPOSED.rglob("*")) if p.is_file()}
    patch = document.get("patch") or {}
    review = json.loads(MANAGER_REVIEW.read_text(encoding="utf-8"))
    return {
        "proposed_bytes_identical_to_attempt7": files == originals, "proposed_files": files,
        "patch_identical_to_the_qualified_attempt7_patch": patch.get("sha256") == ATTEMPT7_PATCH_SHA256
        and sha256_file(ATTEMPT7_PATCH) == ATTEMPT7_PATCH_SHA256,
        "attempt7_patch": {"path": str(ATTEMPT7_PATCH), "sha256": sha256_file(ATTEMPT7_PATCH)},
        "attempt7_document": {"path": str(ATTEMPT7_DOCUMENT), "sha256": sha256_file(ATTEMPT7_DOCUMENT),
                              "expected_sha256": ATTEMPT7_DOCUMENT_SHA256},
        "attempt7_validation": {"path": str(ATTEMPT7_VALIDATION), "sha256": sha256_file(ATTEMPT7_VALIDATION),
                                "subjects": json.loads(ATTEMPT7_VALIDATION.read_text(encoding="utf-8")).get("subjects")},
        "manager_independent_review": {
            "path": str(MANAGER_REVIEW), "sha256": sha256_file(MANAGER_REVIEW), "expected_sha256": MANAGER_REVIEW_SHA256,
            "summary": {"state": review.get("state"), "all_expected": review.get("all_expected"),
                        "cases": len(review.get("cases") or []), "runs": len(review.get("runs") or []),
                        "scope": review.get("scope"), "owner_decision": review.get("owner_decision")},
            "reviewed_checker_sha256": review.get("checker_sha256"),
            "reviewed_workflow_sha256": review.get("workflow_sha256"),
            "retained_bytes_are_the_reviewed_bytes": (
                files.get(a7c.CHECKER) == review.get("checker_sha256")
                and files.get(a7c.WORKFLOW) == review.get("workflow_sha256"))},
        "integration_authority_decision": {"path": str(INTEGRATION_DECISION), "sha256": sha256_file(INTEGRATION_DECISION),
                                           "expected_sha256": INTEGRATION_DECISION_SHA256},
        "rebinding": ("The retained proposal was re-qualified offline at the Attempt 8 subjects in this receipt; its "
                      "bytes and patch are the qualified Attempt 7 ones. The proof's other dependencies -- main's six "
                      "control surfaces, the committed CONTROL-07 protocol and the repository's evaluator -- are "
                      "unchanged by Attempt 8, so the manager's 21 independent offline cases apply to these bytes; "
                      "this receipt re-runs the worker's own matrix at the new heads, it is not a second independent "
                      "review."),
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
    # The preserved qualification writes its own create-only matrix receipt beside the final one.
    matrix = receipt.with_name(receipt.stem + "_OFFLINE_MATRIX.json")
    document = a7c.validate(root / "evidence" / "control07" / "proposed", matrix, patch, args.candidate)
    document = {**document, "label": f"{LABEL} (CONTROL-07 private proposal: retained, rebound, not adopted)",
                "offline_matrix_receipt": {"path": str(matrix), "sha256": sha256_file(matrix)},
                "attempt8_retention": _retention(root, document)}
    retention = document["attempt8_retention"]
    document["checks"] = {**document["checks"],
                          "proposed_bytes_identical_to_attempt7": retention["proposed_bytes_identical_to_attempt7"],
                          "patch_identical_to_the_qualified_attempt7_patch":
                              retention["patch_identical_to_the_qualified_attempt7_patch"],
                          "manager_review_is_the_issued_bytes":
                              retention["manager_independent_review"]["sha256"] == MANAGER_REVIEW_SHA256,
                          "retained_bytes_are_the_manager_reviewed_bytes":
                              retention["manager_independent_review"]["retained_bytes_are_the_reviewed_bytes"]}
    document["result"] = "PASS" if all(document["checks"].values()) else "FAIL"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    with receipt.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, indent=2, ensure_ascii=False, default=str) + "\n")
    text = a7c.render_markdown(document, receipt)
    old = "Internal IDs: CYCLE-37 / ATTEMPT-07-20260925. Requirement R37A07-03 (TP37-A07-03)."
    if old not in text:
        raise SystemExit("the preserved proposal renderer changed; refusing to relabel it")
    text = text.replace(old, "Internal IDs: CYCLE-37 / ATTEMPT-08-20260926. Requirement R37A08-03 (TP37-A08-03).")
    header = "### Authority"
    retained = "\n".join([
        "### Retained from Attempt 7, rebound here (not redesigned)", "",
        f"The proposed bytes are the Attempt 7 qualified bytes, copied byte for byte "
        f"(identical: {retention['proposed_bytes_identical_to_attempt7']}); the regenerated patch is byte-identical to "
        f"the qualified Attempt 7 patch `{ATTEMPT7_PATCH_SHA256}` "
        f"({retention['patch_identical_to_the_qualified_attempt7_patch']}). The Attempt 7 proposal document "
        f"`{ATTEMPT7_DOCUMENT}` (SHA-256 `{retention['attempt7_document']['sha256']}`) and its validation receipt stay "
        f"unchanged as the original record; the manager's independent offline review `{MANAGER_REVIEW.name}` "
        f"(SHA-256 `{retention['manager_independent_review']['sha256']}`) qualified these bytes. This receipt re-runs "
        "the worker's offline matrix bound to the Attempt 8 repair and candidate heads; it is not a second independent "
        "review, and it adopts nothing.", "", header])
    text = text.replace(header, retained, 1)
    with markdown.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print(json.dumps({"result": document["result"], "checks": document["checks"],
                      "current_green": document["characterization"]["current_checkers_green_on"]}, indent=2))
    return 0 if document["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
