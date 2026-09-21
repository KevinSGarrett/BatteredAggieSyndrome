"""R35-31 (Cycle #35 continuation, 20260921T055921Z), section 5.

"Qualify the exact Family B successor requested for activation. The current
qualification still exercises ledger 1b79..., while the request names
d486.... Complete the isolated successor chain and actual-validator negative
tests without activating canonical routing."

Both halves of that were right.

THE WRONG LEDGER. R35-21 picks its isolated child with `ledger_path_for`,
which reads `ledger_identity` out of the COMMITTED gate -- 1b79f1ba... That
file is the PREDECESSOR: its own `ledger_identity` field says 1b79f1ba and
it carries no `supersessions` key at all. The successor is what the
reconstruction produces from it: the same ledger plus 23 supersession rows,
whose identity is d48698ab..., and the module's own `reconstruct_objects`
already returns `ledger_path` pointing at

    features/.../sha256/d48698abe2d94286.../rejection_ledger.json

which does not exist anywhere on disk. So the mounted failure "ledger
d48698ab vs committed 1b79f1ba" is not a drift to be reconciled. It is the
successor never having been materialized. Qualifying the predecessor and
then requesting activation of the successor asks an owner to approve an
artifact nothing has exercised.

THE NEGATIVE CONTROLS DID NOT REJECT. R35-21's tamper probes call
`reconstruct_objects`, which computes hashes and raises nothing, so both
recorded ACCEPTED -- one of them with a note explaining that
`validate_artifact` is what would really catch it. That note is correct and
it is also the admission: the check that catches the tamper was never run.
Here every negative control calls the real `validate_artifact`, and a case
PASSES ONLY IF THE VALIDATOR RAISES. A case that does not raise is recorded
as DID_NOT_REJECT and fails the qualification.

That change is what makes the inert-byte tamper meaningful. The union
identity deliberately hashes scientific fields rather than raw bytes, so it
does not move -- but `validate_artifact` compares the stored payload to the
reconstruction in full, so the added field is caught. R35-21 could only say
so; this runs it.

WHAT THIS DOES NOT DO. Nothing is written outside the isolated workspace.
`materialize` is called against the ISOLATED repo and data root, never the
mounted lake, so the canonical rejection-ledger tree gains no d48698ab
directory and the committed gate keeps its 1b79f1ba pin. Canonical bytes
are hashed before and after and compared. Activation remains
CYCLE33-APPROVAL-LAKE-SUCCESSOR-001, an owner decision this tool neither
performs nor requests, and the mounted Family B lane stays FAIL, which is
the correct state for an unactivated successor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_1998_2009_rejection_integrity import (  # noqa: E402
    CONTRACT_RELATIVE,
    GATE_RELATIVE,
    AuthorityViolation,
    load_json,
    materialize,
    reconstruct_objects,
    validate_artifact,
)
from aggie_analytics.validation.artifact_binding import compute_identity  # noqa: E402

DEFAULT_DATA_ROOT = Path(r"C:\BatteredAggieSyndrome.data")

#: Short on purpose. The isolated child lands under
#: features/<45 chars>/sha256/<64 hex>/rejection_ledger.json, and a
#: workspace under ops/cycle35/runs/<stamp>_implementation/... would push
#: that past Windows MAX_PATH and fail as a spurious "missing payload".
DEFAULT_WORKSPACE = Path(r"C:\bas35q")

APPROVAL_ID = "CYCLE33-APPROVAL-LAKE-SUCCESSOR-001"

#: The successor named in the activation request. Written here so a run
#: against a lake that reconstructs something else is reported as a
#: mismatch rather than quietly qualifying a different artifact.
REQUESTED_SUCCESSOR_LEDGER_IDENTITY = (
    "d48698abe2d94286c9b1f2688273a0050662e3a4e62347dac11ea353b9681aa1"
)
COMMITTED_PREDECESSOR_LEDGER_IDENTITY = (
    "1b79f1bac9883e93fca9a6154493cf646059986fdc8bff4491ddbc8715631574"
)

#: Hashed before and after to prove the mounted lake and the committed gate
#: are untouched by anything below.
CANONICAL_PRESERVE = (
    "artifacts/data_lake/tamu_official_1998_2009_rejection_integrity_gate.json",
    "artifacts/data_lake/tamu_official_gamebook_union_1996_expanded_gate.json",
    "configs/tamu_official_1998_2009_rejection_integrity_contract.json",
)

#: What the reconstruction reads out of the data root. Copied into the
#: isolated root so the successor can be materialized without the mounted
#: lake being writable at all.
UNION_FEATURE = "features/tamu_official_gamebook_union_1996_expanded/sha256"
CORPUS_FEATURE = (
    "features/tamu_official_1998_2009_structured_row_corpus/sha256"
    "/0ff650b1b691299d2b14fd252b8b938a9afe1d02cfd1eefdcd4d53bde2947ca8"
)


def sha256_bytes(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def snapshot(repo_root: Path, data_root: Path) -> dict[str, str | None]:
    out = {rel: sha256_bytes(repo_root / rel) for rel in CANONICAL_PRESERVE}
    out["MOUNTED_SUCCESSOR_CHILD_MUST_NOT_EXIST"] = sha256_bytes(
        data_root
        / "features/tamu_official_1998_2009_rejection_integrity/sha256"
        / REQUESTED_SUCCESSOR_LEDGER_IDENTITY
        / "rejection_ledger.json"
    )
    return out


def build_isolated_repo(workspace: Path, repo_root: Path) -> Path:
    """A repo copy carrying only the declarations the module reads."""

    root = workspace / "repo"
    if root.exists():
        shutil.rmtree(root)
    for rel in ("configs", "artifacts/data_lake"):
        source = repo_root / rel
        if not source.is_dir():
            continue
        for path in source.rglob("*.json"):
            target = root / path.relative_to(repo_root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    return root


def build_isolated_data_root(
    workspace: Path, repo_root: Path, data_root: Path
) -> dict[str, Any]:
    """The reconstruction's inputs, copied out of the mounted lake.

    The successor child is NOT copied, because it does not exist. It is
    what this qualification produces.
    """

    root = workspace / "data"
    if root.exists():
        shutil.rmtree(root)

    union_gate = load_json(
        repo_root / "artifacts/data_lake/tamu_official_gamebook_union_1996_expanded_gate.json"
    )
    union_identity = str(union_gate.get("union_identity") or "")
    copied: list[str] = []
    for rel in (f"{UNION_FEATURE}/{union_identity}", CORPUS_FEATURE):
        source = data_root / rel
        if not source.is_dir():
            continue
        shutil.copytree(source, root / rel)
        copied.append(rel)
    return {"root": root, "copied": copied, "union_identity": union_identity}


def expect_rejection(label: str, fn: Callable[[], Any]) -> dict[str, Any]:
    """A negative control passes ONLY when the real validator raises.

    Anything else -- a clean return, or an unrelated crash -- is recorded
    as a failure to reject. A probe that computes a different number is not
    a rejection, and this is the distinction the previous harness lost.
    """

    try:
        value = fn()
    except AuthorityViolation as error:
        return {"case": label, "outcome": "REJECTED", "raised": str(error)}
    except Exception as error:  # noqa: BLE001 - reported, never swallowed
        return {
            "case": label,
            "outcome": "DID_NOT_REJECT",
            "detail": f"{type(error).__name__}: {error}",
            "note": "The validator did not refuse this; something else broke.",
        }
    return {
        "case": label,
        "outcome": "DID_NOT_REJECT",
        "returned": str(value)[:200],
        "note": "The validator accepted a case declared as a negative control.",
    }


def expect_pass(label: str, fn: Callable[[], Any]) -> dict[str, Any]:
    try:
        return {"case": label, "outcome": "ACCEPTED", "value": fn()}
    except Exception as error:  # noqa: BLE001
        return {
            "case": label,
            "outcome": "REJECTED",
            "raised": f"{type(error).__name__}: {error}",
        }


def tampered_child(
    workspace: Path, data_root: Path, label: str, mutate: Callable[[dict[str, Any]], None]
) -> Path:
    """A full copy of the isolated data root with the child mutated."""

    target = workspace / f"t_{label}"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(data_root, target)
    child = next(
        (target / "features/tamu_official_1998_2009_rejection_integrity/sha256").rglob(
            "rejection_ledger.json"
        )
    )
    payload = json.loads(child.read_text(encoding="utf-8-sig"))
    mutate(payload)
    child.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Qualify the EXACT Family B successor, in isolation."
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    args = parser.parse_args()

    workspace: Path = args.workspace
    workspace.mkdir(parents=True, exist_ok=True)
    before = snapshot(REPO_ROOT, args.data_root)

    isolated_repo = build_isolated_repo(workspace, REPO_ROOT)
    isolated = build_isolated_data_root(workspace, REPO_ROOT, args.data_root)
    isolated_data = isolated["root"]

    # Which ledger does this actually exercise? Answered before anything is
    # qualified, so the artifact can never name one and exercise another.
    reconstructed = reconstruct_objects(repo_root=isolated_repo, data_root=isolated_data)
    exercised = str(reconstructed["payload"]["ledger_identity"])
    committed_gate = load_json(REPO_ROOT / GATE_RELATIVE)
    identity_binding = {
        "ledger_identity_exercised": exercised,
        "requested_for_activation": REQUESTED_SUCCESSOR_LEDGER_IDENTITY,
        "exercises_the_requested_successor": exercised
        == REQUESTED_SUCCESSOR_LEDGER_IDENTITY,
        "committed_gate_pins": str(committed_gate.get("ledger_identity") or ""),
        "committed_pin_is_the_predecessor": str(committed_gate.get("ledger_identity") or "")
        == COMMITTED_PREDECESSOR_LEDGER_IDENTITY,
        "successor_child_existed_before_this_run": before[
            "MOUNTED_SUCCESSOR_CHILD_MUST_NOT_EXIST"
        ]
        is not None,
        "supersession_rows": len(reconstructed["payload"].get("supersessions") or []),
    }

    cases: list[dict[str, Any]] = []

    # Positive: materialize the successor into the ISOLATED pair, then run
    # the real validator against it.
    materialized = materialize(repo_root=isolated_repo, data_root=isolated_data)
    cases.append(
        expect_pass(
            "SUCCESSOR_VALIDATES_IN_ISOLATION",
            lambda: validate_artifact(repo_root=isolated_repo, data_root=isolated_data),
        )
    )

    # Replay: materializing and validating twice must give one answer.
    second = materialize(repo_root=isolated_repo, data_root=isolated_data)
    cases.append(
        expect_pass(
            "SUCCESSOR_VALIDATES_ON_REPLAY",
            lambda: validate_artifact(repo_root=isolated_repo, data_root=isolated_data),
        )
    )
    replay = {
        "first": materialized,
        "second": second,
        "identical": materialized == second,
    }

    # ---- negative controls, every one through the real validator --------

    # The committed predecessor gate against the successor reconstruction.
    # This is the mounted failure itself, reproduced deliberately.
    cases.append(
        expect_rejection(
            "COMMITTED_PREDECESSOR_GATE_REJECTED",
            lambda: validate_artifact(
                repo_root=isolated_repo, data_root=isolated_data, gate=committed_gate
            ),
        )
    )

    # A gate whose stated identity does not recompute.
    forged = dict(load_json(isolated_repo / GATE_RELATIVE))
    forged["gate_identity"] = "0" * 64
    cases.append(
        expect_rejection(
            "GATE_IDENTITY_DOES_NOT_RECOMPUTE_REJECTED",
            lambda: validate_artifact(
                repo_root=isolated_repo, data_root=isolated_data, gate=forged
            ),
        )
    )

    # A gate that recomputes cleanly but states a different ledger: an
    # internally consistent forgery, which the reconstruction comparison
    # must still refuse.
    relabelled = dict(load_json(isolated_repo / GATE_RELATIVE))
    relabelled["ledger_identity"] = COMMITTED_PREDECESSOR_LEDGER_IDENTITY
    relabelled["gate_identity"] = compute_identity(relabelled, "gate_identity")
    cases.append(
        expect_rejection(
            "SELF_CONSISTENT_GATE_NAMING_ANOTHER_LEDGER_REJECTED",
            lambda: validate_artifact(
                repo_root=isolated_repo, data_root=isolated_data, gate=relabelled
            ),
        )
    )

    # The child removed entirely.
    missing = workspace / "t_missing"
    if missing.exists():
        shutil.rmtree(missing)
    shutil.copytree(isolated_data, missing)
    for stale in (
        missing / "features/tamu_official_1998_2009_rejection_integrity"
    ).rglob("rejection_ledger.json"):
        stale.unlink()
    cases.append(
        expect_rejection(
            "MISSING_CHILD_REJECTED",
            lambda: validate_artifact(repo_root=isolated_repo, data_root=missing),
        )
    )

    # A SEMANTIC tamper: drop a rejected URL.
    def drop_rejection(payload: dict[str, Any]) -> None:
        payload["complete_rejection_ledger"] = list(
            payload.get("complete_rejection_ledger") or []
        )[:-1]

    semantic = tampered_child(workspace, isolated_data, "semantic", drop_rejection)
    cases.append(
        expect_rejection(
            "TAMPERED_CHILD_SEMANTIC_REJECTED",
            lambda: validate_artifact(repo_root=isolated_repo, data_root=semantic),
        )
    )

    # An INERT byte tamper. The identity hash does not move -- and the
    # validator still refuses, because it compares the whole payload. This
    # is the case the previous harness could only describe.
    def add_inert_field(payload: dict[str, Any]) -> None:
        payload["unused_annotation_added_by_tamper_probe"] = True

    inert = tampered_child(workspace, isolated_data, "inert", add_inert_field)
    inert_identity_moved = (
        reconstruct_objects(repo_root=isolated_repo, data_root=inert)["payload"][
            "ledger_identity"
        ]
        != exercised
    )
    cases.append(
        {
            **expect_rejection(
                "TAMPERED_CHILD_INERT_BYTES_REJECTED",
                lambda: validate_artifact(repo_root=isolated_repo, data_root=inert),
            ),
            "identity_hash_moved": inert_identity_moved,
            "note": "The identity hashes scientific fields, so an inert field "
            "does not move it. validate_artifact compares the stored payload "
            "to the reconstruction in full, so the tamper is refused anyway. "
            "R35-21 asserted this in prose without running it.",
        }
    )

    # A tamper that rewrites the child's own stated identity to match.
    def relabel_child(payload: dict[str, Any]) -> None:
        payload["ledger_identity"] = COMMITTED_PREDECESSOR_LEDGER_IDENTITY

    relabelled_child = tampered_child(workspace, isolated_data, "relabel", relabel_child)
    cases.append(
        expect_rejection(
            "TAMPERED_CHILD_RELABELLED_IDENTITY_REJECTED",
            lambda: validate_artifact(
                repo_root=isolated_repo, data_root=relabelled_child
            ),
        )
    )

    after = snapshot(REPO_ROOT, args.data_root)

    negatives = [c for c in cases if c["case"].endswith("_REJECTED")]
    positives = [c for c in cases if not c["case"].endswith("_REJECTED")]
    did_not_reject = [c for c in negatives if c["outcome"] != "REJECTED"]
    positives_failed = [c for c in positives if c["outcome"] != "ACCEPTED"]

    qualified = (
        identity_binding["exercises_the_requested_successor"]
        and not did_not_reject
        and not positives_failed
        and replay["identical"]
        and before == after
    )

    result: dict[str, Any] = {
        "artifact_type": "CYCLE35_FAMILY_B_SUCCESSOR_QUALIFICATION",
        "successor_qualified_in_isolation": qualified,
        "identity_binding": identity_binding,
        "cases": cases,
        "negative_controls_declared": len(negatives),
        "negative_controls_that_rejected": len(negatives) - len(did_not_reject),
        "negative_controls_that_did_not_reject": did_not_reject,
        "every_negative_control_ran_the_real_validator": True,
        "replay": replay,
        "canonical_bytes_before": before,
        "canonical_bytes_after": after,
        "canonical_predecessor_bytes_unchanged": before == after,
        "canonical_activation_performed": False,
        "canonical_activation_requested_by_this_tool": False,
        "canonical_activation_state": "NOT_AUTHORIZED_SEPARATE_OWNER_DECISION",
        "approval_required_for_activation": APPROVAL_ID,
        "mounted_family_b_lane": (
            "Remains FAIL, which is the correct state for a successor that "
            "has not been activated. Qualifying a candidate in isolation is "
            "local work; writing it into the canonical lake is not."
        ),
        "what_qualified_means_here": (
            "The exact successor named for activation was materialized into "
            "an isolated root and accepted by the real validator, twice, "
            "while every declared negative control was refused by that same "
            "validator. It does not mean the successor is installed, "
            "approved, or scientifically accepted."
        ),
        "isolated_repo": str(isolated_repo),
        "isolated_data_root": str(isolated_data),
        "inputs_copied_from_the_mounted_lake": isolated["copied"],
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "CYCLE35_FAMILY_B_SUCCESSOR_QUALIFICATION.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2, sort_keys=True))
    print("\ncases:")
    for case in cases:
        print(f"  {case['outcome']:15} {case['case']}")
    return 0 if qualified else 1


if __name__ == "__main__":
    raise SystemExit(main())
