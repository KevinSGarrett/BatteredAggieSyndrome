"""R36-12: reproduce the composed Family B successor in a NEW isolated root.

MR35R-10. The manager advanced this from "blocked" to "qualified in
isolation": upstream ledger ``d48698ab`` / gate ``2dcb3368`` composed with
downstream union ``ab170b25`` / gate ``f343e4e3``, both rejecting byte and
semantic tampering. The new unit is the **composition**, not another check of
the predecessor consumer on its own.

This tool reproduces that independently in a directory that must not already
exist, expands the negative controls well beyond the manager's two, and
reconstructs the scientific identities rather than copying them from the
manager's JSON. Every identity the manager published is asserted against what
this run derives; a mismatch is a finding, never something to overwrite.

Canonical files are not touched. The default stays LEGACY. Nothing here
activates anything: the activation and rollback scope is written out for a
human decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.workspace.paths import (  # noqa: E402
    require_free_bytes,
    resolve_seed,
)
from aggie_analytics import atomic_io as _bas_atomic
from aggie_analytics.data import (  # noqa: E402
    tamu_official_1998_2009_rejection_integrity as upstream,
)
from aggie_analytics.data import (  # noqa: E402
    tamu_official_gamebook_union_1998_rejection_complete as downstream,
)

#: The composed qualification seed is a DECLARED INPUT, not scratch that
#: happens to still exist on one machine. It used to be the literal
#: path "C:\bas35q" -- a Cycle 35 qualification directory created as
#: disposable that silently became a prerequisite, so it could neither be
#: cleaned up nor reproduced anywhere else. It now resolves through an
#: explicit --seed / BAS_FAMILY_B_SEED location which must declare the
#: contract below before a single byte is read.
SEED_CONTRACT_ID = "CYCLE35-FAMILY-B-COMPOSED-SEED-V1"
SEED_REQUIRED_ENTRIES = ("repo", "data")

#: Identities the manager published. This run must derive the same ones.
EXPECTED = {
    "upstream_ledger_identity": "d48698abe2d94286c9b1f2688273a0050662e3a4e62347dac11ea353b9681aa1",
    "upstream_gate_identity": "2dcb3368fc8865efaacab570584fe810150ce4b015bac3016d54052a1b0bb835",
    "downstream_union_identity": "ab170b25b4478f7b36e4d150d3eca874efc910b76a4854768a07182e7004526a",
    "downstream_gate_identity": "f343e4e327d3991ae9cf048c149b679b3de9f08ea270eb32fbafc23f1dc4b93f",
}

APPROVAL_ID = "CYCLE33-APPROVAL-LAKE-SUCCESSOR-001"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def attempt(name: str, call: Callable[[], Any]) -> dict[str, Any]:
    try:
        value = call()
        return {"control": name, "outcome": "ACCEPTED", "value": _small(value)}
    except Exception as error:  # noqa: BLE001 - the rejection IS the result
        return {
            "control": name,
            "outcome": "REJECTED",
            "exception": type(error).__name__,
            "message": str(error)[:400],
        }


def _small(value: Any) -> Any:
    text = json.dumps(value, default=str)
    return json.loads(text) if len(text) < 4000 else {"truncated": len(text)}


def _seed_tree_bytes(seed: Path) -> int:
    return sum(p.stat().st_size for p in seed.rglob("*") if p.is_file())


def prepare(isolated: Path, worktree: Path, seed: Path) -> dict[str, Any]:
    if isolated.exists():
        raise RuntimeError(
            f"refuse to overwrite an existing isolated root: {isolated}"
        )
    # The copy below is what the 2026-09 volume exhaustion broke. A copy
    # that cannot fit is refused here rather than failing part-way and
    # leaving a half-populated root that reads as a qualification failure.
    require_free_bytes(isolated.parent, _seed_tree_bytes(seed))
    shutil.copytree(seed / "repo", isolated / "repo")
    shutil.copytree(seed / "data", isolated / "data")
    copied = []
    for relative in (
        downstream.CONTRACT_RELATIVE,
        downstream.GATE_RELATIVE,
        downstream.SUCCESSOR_CONTRACT_RELATIVE,
        "artifacts/data_lake/tamu_official_gamebook_union_1998_expanded_gate.json",
    ):
        destination = isolated / "repo" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(worktree / relative, destination)
        copied.append(
            {"relative": relative, "sha256": sha256_file(destination)}
        )
    return {"seed": str(seed), "copied_from_worktree": copied}


def run(isolated: Path, worktree: Path, seed: Path) -> dict[str, Any]:
    layout = prepare(isolated, worktree, seed)
    repo = isolated / "repo"
    data = isolated / "data"
    kwargs = {"pin_authority": downstream.PIN_AUTHORITY_SUCCESSOR}

    upstream_positive = upstream.validate_artifact(repo_root=repo, data_root=data)
    materialized = downstream.materialize_union(repo_root=repo, data_root=data, **kwargs)
    downstream_positive = downstream.validate_artifact(
        repo_root=repo, data_root=data, **kwargs
    )
    objects = downstream.reconstruct_objects(repo_root=repo, data_root=data, **kwargs)

    derived = {
        "upstream_ledger_identity": objects["gate"].get("rejection_ledger_identity"),
        "upstream_gate_identity": (upstream_positive or {}).get("gate_identity"),
        "downstream_union_identity": (downstream_positive or {}).get("union_identity"),
        "downstream_gate_identity": (downstream_positive or {}).get("gate_identity"),
    }
    identity_agreement = {
        key: {
            "expected_from_manager": EXPECTED[key],
            "derived_here": derived.get(key),
            "agrees": derived.get(key) == EXPECTED[key],
        }
        for key in EXPECTED
    }

    ledger_path = (
        data
        / "features/tamu_official_1998_2009_rejection_integrity/sha256"
        / str(derived["upstream_ledger_identity"])
        / "rejection_ledger.json"
    )
    union_manifest = Path(str(materialized.get("manifest_path") or ""))
    original_ledger = ledger_path.read_bytes()
    original_union = union_manifest.read_bytes() if union_manifest.is_file() else None
    gate_path = repo / downstream.GATE_RELATIVE
    original_gate = gate_path.read_bytes()

    controls: list[dict[str, Any]] = []

    def both(label: str, must_reject: tuple[str, ...]) -> None:
        """Run both validators and record which of them was REQUIRED to fail.

        A control that tampers with a downstream-only file must be rejected
        downstream and legitimately passes upstream, because upstream never
        reads that file. Demanding both would turn a correct separation of
        concerns into a false finding, which is what a first version of this
        tool did.
        """

        controls.append(
            {
                "case": label,
                "must_reject": list(must_reject),
                "upstream": attempt(
                    "upstream", lambda: upstream.validate_artifact(repo_root=repo, data_root=data)
                ),
                "downstream": attempt(
                    "downstream",
                    lambda: downstream.validate_artifact(
                        repo_root=repo, data_root=data, **kwargs
                    ),
                ),
            }
        )

    def mutate_ledger(
        change: Callable[[dict[str, Any]], dict[str, Any]],
        label: str,
        must_reject: tuple[str, ...] = ("upstream", "downstream"),
    ) -> None:
        _bas_atomic.write_text(ledger_path, 
            json.dumps(change(json.loads(original_ledger))), encoding="utf-8"
        )
        both(label, must_reject)
        _bas_atomic.write_bytes(ledger_path, original_ledger)

    # -- the manager's two controls, reproduced -----------------------------
    mutate_ledger(lambda d: {**d, "cycle36_inert_marker": True}, "inert_byte_in_ledger")
    mutate_ledger(
        lambda d: {**d, "active_rejection_count": 999}, "semantic_field_in_ledger"
    )

    # -- controls this cycle adds -------------------------------------------
    mutate_ledger(lambda d: {k: v for k, v in d.items() if k != "active_rejection_count"},
                  "removed_semantic_field")
    mutate_ledger(lambda d: {}, "emptied_ledger_payload")

    missing = ledger_path.with_suffix(".missing")
    ledger_path.rename(missing)
    both("missing_ledger_payload", ("upstream", "downstream"))
    missing.rename(ledger_path)

    if original_union is not None:
        _bas_atomic.write_text(union_manifest, 
            json.dumps({**json.loads(original_union), "cycle36_marker": True}),
            encoding="utf-8",
        )
        # Downstream owns the union manifest; upstream never reads it.
        both("changed_child_union_manifest_bytes", ("downstream",))
        _bas_atomic.write_bytes(union_manifest, original_union)

    stale = json.loads(original_gate)
    stale_pin = dict(stale)
    stale_pin["rejection_ledger_identity"] = "0" * 64
    _bas_atomic.write_text(gate_path, json.dumps(stale_pin), encoding="utf-8")
    both("stale_pin_in_committed_gate", ("downstream",))
    _bas_atomic.write_bytes(gate_path, original_gate)

    mixed = dict(stale)
    mixed["union_identity"] = EXPECTED["upstream_gate_identity"]
    _bas_atomic.write_text(gate_path, json.dumps(mixed), encoding="utf-8")
    both("mixed_predecessor_identities_in_gate", ("downstream",))
    _bas_atomic.write_bytes(gate_path, original_gate)

    # A coordinated recompute: change the payload AND the recorded digest so
    # the two agree with each other but not with the independent
    # reconstruction. This is the tampering a naive hash check misses.
    tampered = json.loads(original_ledger)
    tampered["active_rejection_count"] = 998
    _bas_atomic.write_text(ledger_path, json.dumps(tampered), encoding="utf-8")
    recomputed = hashlib.sha256(ledger_path.read_bytes()).hexdigest()
    coordinated = json.loads(original_gate)
    coordinated["rejection_ledger_identity"] = recomputed
    _bas_atomic.write_text(gate_path, json.dumps(coordinated), encoding="utf-8")
    both("coordinated_recomputed_identity", ("upstream", "downstream"))
    _bas_atomic.write_bytes(gate_path, original_gate)
    _bas_atomic.write_bytes(ledger_path, original_ledger)

    controls.append(
        {
            "case": "wrong_root_canonical_data_with_isolated_repo",
            "must_reject": ["downstream"],
            "downstream": attempt(
                "downstream",
                lambda: downstream.validate_artifact(
                    repo_root=repo,
                    data_root=Path(r"C:\BatteredAggieSyndrome.data"),
                    **kwargs,
                ),
            ),
        }
    )
    controls.append(
        {
            "case": "wrong_pin_authority",
            "must_reject": ["downstream"],
            "downstream": attempt(
                "downstream",
                lambda: downstream.validate_artifact(
                    repo_root=repo,
                    data_root=data,
                    pin_authority="SOMETHING_ELSE",
                ),
            ),
        }
    )

    restored_upstream = attempt(
        "upstream", lambda: upstream.validate_artifact(repo_root=repo, data_root=data)
    )
    restored_downstream = attempt(
        "downstream",
        lambda: downstream.validate_artifact(repo_root=repo, data_root=data, **kwargs),
    )

    for case in controls:
        required = case.get("must_reject") or ["upstream", "downstream"]
        case["required_rejections_observed"] = all(
            (case.get(side) or {}).get("outcome") == "REJECTED" for side in required
        )
        case["unrequired_sides_accepted"] = [
            side
            for side in ("upstream", "downstream")
            if side in case
            and side not in required
            and (case.get(side) or {}).get("outcome") == "ACCEPTED"
        ]
    rejected = [case for case in controls if case["required_rejections_observed"]]
    unexpected_accepts = [
        case for case in controls if not case["required_rejections_observed"]
    ]

    return {
        "artifact_type": "CYCLE36_FAMILY_B_COMPOSED_QUALIFICATION",
        "generated_at_utc": utc_now(),
        "classification": "INDEPENDENT_INTEGRATION_PROBE_NOT_SCIENTIFIC_ACCEPTANCE",
        "isolated_root": str(isolated),
        "layout": layout,
        "module_digests": {
            "upstream": sha256_file(Path(upstream.__file__)),
            "downstream": sha256_file(Path(downstream.__file__)),
        },
        "upstream_positive": _small(upstream_positive),
        "downstream_materialized": _small(materialized),
        "downstream_positive": _small(downstream_positive),
        "identity_agreement": identity_agreement,
        "all_published_identities_reproduced": all(
            row["agrees"] for row in identity_agreement.values()
        ),
        "negative_controls": controls,
        "negative_controls_total": len(controls),
        "negative_controls_rejected": len(rejected),
        "unexpected_accepts": [case["case"] for case in unexpected_accepts],
        "restored_upstream": restored_upstream,
        "restored_downstream": restored_downstream,
        "restored_after_every_control": (
            restored_upstream["outcome"] == "ACCEPTED"
            and restored_downstream["outcome"] == "ACCEPTED"
        ),
        "canonical_activation": False,
        "hold_release": False,
        "default_remains": "LEGACY",
        "activation_request": {
            "approval_id": APPROVAL_ID,
            "state": "REQUESTED_NOT_GRANTED",
            "exact_scope": [
                "Set the Family B consumer default from LEGACY to the composed "
                "successor for the two named artifacts only.",
                "Bind upstream ledger "
                f"{EXPECTED['upstream_ledger_identity']} with gate "
                f"{EXPECTED['upstream_gate_identity']}.",
                "Bind downstream union "
                f"{EXPECTED['downstream_union_identity']} with gate "
                f"{EXPECTED['downstream_gate_identity']}.",
            ],
            "affected_consumers": [
                "aggie_analytics.data.tamu_official_1998_2009_rejection_integrity",
                "aggie_analytics.data.tamu_official_gamebook_union_1998_rejection_complete",
                "the canonical mounted validation lane that currently reports FAIL",
            ],
            "reversion_scope": [
                "Restore the LEGACY default; the predecessor ledgers, pins, "
                "gates and lake bytes are untouched by this qualification and "
                "need no restoration.",
                "No canonical file was written, so rollback is a configuration "
                "change rather than a data repair.",
            ],
            "who_decides": "The user or a separately authorised release authority.",
            "what_this_evidence_does_not_show": (
                "Isolated qualification shows the composed consumers accept "
                "correct inputs and reject tampered ones. It is not an "
                "independent reconstruction of every scientific calculation "
                "inside them, and the canonical mounted lane honestly remains "
                "FAIL while the successor is not activated."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--isolated-root", type=Path, required=True)
    parser.add_argument("--worktree", type=Path, default=ROOT)
    parser.add_argument(
        "--seed",
        type=Path,
        default=None,
        help=(
            "Directory holding the Cycle 35 composed qualification seed. "
            "It must contain a SEED_CONTRACT.json declaring "
            f"{SEED_CONTRACT_ID}. Falls back to BAS_FAMILY_B_SEED. There "
            "is deliberately no built-in default location."
        ),
    )
    parser.add_argument(
        "--seed-contract",
        type=Path,
        default=None,
        help=(
            "Path to the declared seed contract. Use this when the seed is a "
            "preserved directory that must not be written to; the contract "
            "then lives in the cycle evidence packet and pins the seed's "
            "entry digests."
        ),
    )
    args = parser.parse_args()
    try:
        seed, seed_contract = resolve_seed(
            SEED_CONTRACT_ID,
            explicit=args.seed,
            required_entries=SEED_REQUIRED_ENTRIES,
            contract_path=args.seed_contract,
        )
        artifact = run(args.isolated_root, args.worktree, seed)
        artifact["seed_contract"] = seed_contract
    except Exception as error:  # noqa: BLE001 - the failure is the evidence
        artifact = {
            "artifact_type": "CYCLE36_FAMILY_B_COMPOSED_QUALIFICATION",
            "generated_at_utc": utc_now(),
            "state": "QUALIFICATION_FAILED",
            "exception": type(error).__name__,
            "message": str(error)[:800],
            "traceback_tail": traceback.format_exc()[-1500:],
            "canonical_activation": False,
            "hold_release": False,
            "seed_requested": None if args.seed is None else str(args.seed),
            "seed_contract_id": SEED_CONTRACT_ID,
        }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(args.out_dir / "CYCLE36_FAMILY_B_COMPOSED_QUALIFICATION.json", 
        json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                key: artifact.get(key)
                for key in (
                    "state",
                    "all_published_identities_reproduced",
                    "negative_controls_total",
                    "negative_controls_rejected",
                    "unexpected_accepts",
                    "restored_after_every_control",
                    "canonical_activation",
                    "default_remains",
                )
                if key in artifact
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
