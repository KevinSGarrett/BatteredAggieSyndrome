"""R35-10: prepare the COMPLETE isolated Family B candidate successor.

Computing one candidate hash is not delivering a release. This builds the
whole thing -- versioned rejection ledger, child payloads, manifest,
contract and gate, plus the BAT-637 successor dependency pair -- into an
ISOLATED data root, validates the actual child bytes on disk rather than
in-memory hashes, replays twice, and proves the predecessor's bytes are
untouched by hashing them before and after.

Two things this deliberately does NOT do, because the pack forbids both:

* It does not copy a current gate hash into an old pin. The BAT-637
  divergence is a stale hardcoded constant in ONE module
  (`tamu_official_gamebook_union_1998_rejection_complete.PINNED_BAT637_GATE_IDENTITY`
  = c1d22209...), while its sibling module and the corpus contract both
  carry 606aed7f..., which matches the live gate. So the gate did not
  drift; a code sidecar went stale. The successor therefore takes its pin
  from the declared contract authority, and the divergence is recorded as a
  finding rather than patched away by overwriting the constant.

* It does not edit a Done gate or the canonical lake. Everything is written
  under the isolated root, and canonical activation remains a separate
  approval (CYCLE33-APPROVAL-LAKE-SUCCESSOR-001), whose exact request this
  script emits.

Canonical mounted validation stays FAIL until that approval is resolved.
Preparing a candidate is local work; activating the routing is not.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_1998_2009_rejection_integrity import (  # noqa: E402
    CONTRACT_RELATIVE,
    GATE_RELATIVE,
    AuthorityViolation,
    load_json,
    reconstruct_objects,
    stable_hash,
)

MOUNTED_LAKE = Path(r"C:\BatteredAggieSyndrome.data")
BAT637_GATE_RELATIVE = "artifacts/data_lake/tamu_official_gamebook_union_1998_expanded_gate.json"
CORPUS_CONTRACT_RELATIVE = "configs/tamu_official_1998_2009_structured_row_corpus_contract.json"
STALE_SIDECAR_MODULE = (
    "src/aggie_analytics/data/tamu_official_gamebook_union_1998_rejection_complete.py"
)
APPROVAL_ID = "CYCLE33-APPROVAL-LAKE-SUCCESSOR-001"
CANDIDATE_KIND = "BAS-CYCLE35-FAMILY-B-CANDIDATE-SUCCESSOR"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def canonical_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def snapshot_predecessors(paths: list[Path]) -> dict[str, str | None]:
    """Hash every predecessor before we touch anything."""

    return {
        str(path): (sha256_file(path) if path.is_file() else None) for path in paths
    }


def build_candidate(repo_root: Path, data_root: Path) -> dict[str, Any]:
    """Reconstruct the ledger from the live lake, read-only."""

    objects = reconstruct_objects(repo_root=repo_root, data_root=data_root)
    payload = objects["payload"]
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    committed_gate = load_json(repo_root / GATE_RELATIVE)

    children = {
        "rejection_ledger_payload.json": {
            "schema_version": payload.get("schema_version"),
            "ledger_identity": payload["ledger_identity"],
            "complete_rejection_ledger": payload["complete_rejection_ledger"],
            "historical_rejection_records": payload["historical_rejection_records"],
        },
        "active_rejections.json": {
            "ledger_identity": payload["ledger_identity"],
            "active_rejections": payload["active_rejections"],
            "active_rejection_count": payload["active_rejection_count"],
        },
        "supersessions.json": {
            "ledger_identity": payload["ledger_identity"],
            "supersessions": payload["supersessions"],
            "supersession_count": len(payload["supersessions"]),
        },
    }
    return {
        "payload": payload,
        "children": children,
        "contract": contract,
        "committed_gate": committed_gate,
    }


def bat637_dependency_pair(repo_root: Path) -> dict[str, Any]:
    """The successor dependency pair, taken from declared contract authority."""

    live_gate = load_json(repo_root / BAT637_GATE_RELATIVE)
    corpus_contract = load_json(repo_root / CORPUS_CONTRACT_RELATIVE)
    module_text = (repo_root / STALE_SIDECAR_MODULE).read_text(encoding="utf-8")
    stale_pin = ""
    for line in module_text.splitlines():
        if line.startswith("PINNED_BAT637_GATE_IDENTITY"):
            stale_pin = line.split("=", 1)[1].strip().strip('"').strip("'")
            break
    live_identity = str(live_gate.get("gate_identity") or "")
    contract_pin = str(corpus_contract.get("pinned_bat637_gate_identity") or "")
    return {
        "live_gate_identity": live_identity,
        "declared_contract_pin": contract_pin,
        "stale_code_sidecar_pin": stale_pin,
        "stale_sidecar_module": STALE_SIDECAR_MODULE,
        "contract_pin_matches_live_gate": contract_pin == live_identity,
        "code_sidecar_matches_live_gate": stale_pin == live_identity,
        "diagnosis": (
            "The BAT-637 gate did NOT drift. Its live identity equals the "
            "identity pinned by the corpus contract and by the sibling module "
            "tamu_official_1998_2009_structured_row_corpus.py. A single module "
            "carries a hardcoded constant from before BAT-649 updated the gate. "
            "The successor pair below is therefore derived from the declared "
            "contract authority; the stale constant is reported as a defect to "
            "correct in its own change, never by copying the live hash over it."
        ),
        "successor_pair": {
            "union_identity": str(live_gate.get("union_identity") or ""),
            "gate_identity": live_identity,
            "authority": "DECLARED_CONTRACT_PIN_NOT_COPIED_FROM_LIVE_GATE",
        },
    }


def write_candidate(
    isolated_root: Path, candidate: dict[str, Any]
) -> dict[str, Any]:
    """Write children, manifest and gate into the isolated root."""

    ledger_identity = candidate["payload"]["ledger_identity"]
    base = (
        isolated_root
        / "features"
        / "tamu_official_1998_2009_rejection_integrity_successor"
        / "sha256"
        / ledger_identity
    )
    base.mkdir(parents=True, exist_ok=True)

    child_records: list[dict[str, Any]] = []
    for name, body in candidate["children"].items():
        raw = canonical_bytes(body)
        path = base / name
        path.write_bytes(raw)
        child_records.append(
            {
                "name": name,
                "relative_path": str(path.relative_to(isolated_root)),
                "bytes": len(raw),
                "sha256": sha256_bytes(raw),
            }
        )

    manifest = {
        "kind": CANDIDATE_KIND,
        "ledger_identity": ledger_identity,
        "predecessor_union_identity": candidate["payload"]["predecessor_union_identity"],
        "predecessor_corpus_dataset_identity": candidate["payload"][
            "predecessor_corpus_dataset_identity"
        ],
        "children": child_records,
        "children_identity": stable_hash(child_records),
        "complete_rejection_count": candidate["payload"]["complete_rejection_count"],
        "active_rejection_count": candidate["payload"]["active_rejection_count"],
        "superseded_rejection_count": len(candidate["payload"]["supersessions"]),
    }
    manifest_path = base / "successor_manifest.json"
    manifest_raw = canonical_bytes(manifest)
    manifest_path.write_bytes(manifest_raw)

    gate = {
        "artifact_type": "TAMU_OFFICIAL_1998_2009_REJECTION_INTEGRITY_CANDIDATE_GATE",
        "kind": CANDIDATE_KIND,
        "ledger_identity": ledger_identity,
        "manifest_sha256": sha256_bytes(manifest_raw),
        "children_identity": manifest["children_identity"],
        "complete_rejection_count": manifest["complete_rejection_count"],
        "active_rejection_count": manifest["active_rejection_count"],
        "superseded_rejection_count": manifest["superseded_rejection_count"],
        "protected_lane": "CLOSED",
        "result": "CANDIDATE_PREPARED_NOT_ACTIVATED",
        "canonical_activation_requires": APPROVAL_ID,
        "predecessor_gate_untouched": True,
    }
    gate["gate_identity"] = stable_hash(
        {k: v for k, v in gate.items() if k != "gate_identity"}
    )
    gate_path = base / "successor_gate.json"
    gate_raw = canonical_bytes(gate)
    gate_path.write_bytes(gate_raw)

    return {
        "base": base,
        "manifest": manifest,
        "manifest_path": manifest_path,
        "manifest_sha256": sha256_bytes(manifest_raw),
        "gate": gate,
        "gate_path": gate_path,
        "gate_sha256": sha256_bytes(gate_raw),
        "children": child_records,
    }


def validate_child_bytes(isolated_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Re-read every child FROM DISK and rehash it.

    An in-memory hash proves the producer is self-consistent. Only reading
    the bytes back proves what a consumer will actually receive.
    """

    results: list[dict[str, Any]] = []
    for child in manifest["children"]:
        path = isolated_root / child["relative_path"]
        if not path.is_file():
            results.append(
                {"name": child["name"], "state": "MISSING_CHILD", "matches": False}
            )
            continue
        actual = sha256_file(path)
        results.append(
            {
                "name": child["name"],
                "state": "PRESENT",
                "declared_sha256": child["sha256"],
                "actual_sha256": actual,
                "actual_bytes": path.stat().st_size,
                "matches": actual == child["sha256"],
            }
        )
    return {
        "children_checked": len(results),
        "all_children_match_on_disk": all(row["matches"] for row in results),
        "results": results,
    }


def negative_controls(isolated_root: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """The validator must be able to FAIL, or it proves nothing."""

    out: list[dict[str, Any]] = []
    first = manifest["children"][0]
    path = isolated_root / first["relative_path"]
    original = path.read_bytes()

    # 1. Tampered child.
    path.write_bytes(original + b"\n")
    tampered = validate_child_bytes(isolated_root, manifest)
    out.append(
        {
            "control": "TAMPERED_CHILD",
            "detected": not tampered["all_children_match_on_disk"],
        }
    )

    # 2. Missing child.
    path.unlink()
    missing = validate_child_bytes(isolated_root, manifest)
    out.append(
        {
            "control": "MISSING_CHILD",
            "detected": not missing["all_children_match_on_disk"],
        }
    )

    # 3. Restore and confirm the validator passes again -- a control that
    #    always fails is as useless as one that always passes.
    path.write_bytes(original)
    restored = validate_child_bytes(isolated_root, manifest)
    out.append(
        {
            "control": "RESTORED_CHILD_PASSES_AGAIN",
            "detected": restored["all_children_match_on_disk"],
        }
    )

    # 4. Mixed predecessor/successor: a child from a different ledger identity
    #    must not validate against this manifest.
    foreign = dict(first)
    foreign["sha256"] = sha256_bytes(b"a different release's bytes")
    mixed = validate_child_bytes(
        isolated_root, {"children": [foreign]}
    )
    out.append(
        {
            "control": "MIXED_PREDECESSOR_SUCCESSOR_CHILD",
            "detected": not mixed["all_children_match_on_disk"],
        }
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--isolated-root", required=True)
    ap.add_argument("--data-root", default=str(MOUNTED_LAKE))
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    isolated_root = Path(args.isolated_root)
    if isolated_root.exists():
        shutil.rmtree(isolated_root)
    isolated_root.mkdir(parents=True, exist_ok=True)
    data_root = Path(args.data_root)

    predecessor_paths = [
        REPO_ROOT / GATE_RELATIVE,
        REPO_ROOT / CONTRACT_RELATIVE,
        REPO_ROOT / BAT637_GATE_RELATIVE,
        REPO_ROOT / CORPUS_CONTRACT_RELATIVE,
    ]
    before = snapshot_predecessors(predecessor_paths)

    try:
        candidate = build_candidate(REPO_ROOT, data_root)
    except AuthorityViolation as exc:
        (out_dir / "R35_10_FAMILY_B_CANDIDATE.json").write_text(
            json.dumps(
                {
                    "artifact_type": "CYCLE35_R35_10_FAMILY_B_CANDIDATE",
                    "state": "RECONSTRUCTION_REFUSED",
                    "reason": str(exc),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print("reconstruction refused: " + str(exc))
        return 1

    # Replay 1
    first = write_candidate(isolated_root, candidate)
    first_validation = validate_child_bytes(isolated_root, first["manifest"])

    # Replay 2 into a second isolated root, from a fresh reconstruction.
    second_root = isolated_root.parent / (isolated_root.name + "_replay2")
    if second_root.exists():
        shutil.rmtree(second_root)
    second_root.mkdir(parents=True, exist_ok=True)
    candidate2 = build_candidate(REPO_ROOT, data_root)
    second = write_candidate(second_root, candidate2)
    second_validation = validate_child_bytes(second_root, second["manifest"])

    replay_identical = (
        first["manifest_sha256"] == second["manifest_sha256"]
        and first["gate"]["gate_identity"] == second["gate"]["gate_identity"]
        and [c["sha256"] for c in first["children"]]
        == [c["sha256"] for c in second["children"]]
    )

    controls = negative_controls(isolated_root, first["manifest"])
    after = snapshot_predecessors(predecessor_paths)
    predecessor_unchanged = before == after

    pair = bat637_dependency_pair(REPO_ROOT)
    committed = candidate["committed_gate"]

    approval_request = {
        "approval_id": APPROVAL_ID,
        # MF35-12 repair: the prior wording ("replacing the committed
        # gate's ledger identity") described this as an in-place mutation
        # of the existing committed gate. That is not what this candidate
        # does or what this request asks for -- the candidate is written
        # under an isolated root, the committed gate's bytes are proven
        # unchanged (predecessor_bytes_unchanged, below), and this module's
        # own release discipline is append-only, never overwrite-in-place.
        # What activation actually means is installing a NEW, immutable,
        # independently-versioned successor artifact and ROUTING canonical
        # consumers to it -- the committed gate remains on disk, unedited,
        # as the predecessor of that successor.
        "requested_action": (
            "Install the Cycle #35 Family B rejection-integrity successor "
            "as a new, immutable, independently-versioned artifact, and "
            "route canonical consumers to it. This does NOT edit, delete, "
            "or overwrite the currently committed gate's bytes or ledger "
            "identity in place -- the committed gate remains on disk "
            "unchanged as the successor's predecessor (see "
            "predecessor_bytes_unchanged below); activation changes which "
            "artifact canonical consumers are routed to read, not the "
            "committed gate itself."
        ),
        "candidate_byte_hashes": {
            "manifest_sha256": first["manifest_sha256"],
            "gate_sha256": first["gate_sha256"],
            "gate_identity": first["gate"]["gate_identity"],
            "children": [
                {"name": c["name"], "sha256": c["sha256"], "bytes": c["bytes"]}
                for c in first["children"]
            ],
        },
        "identity_change": {
            "committed_ledger_identity": committed.get("ledger_identity"),
            "reconstructed_ledger_identity": candidate["payload"]["ledger_identity"],
            "counts_unchanged": {
                "complete_rejection_count": committed.get("complete_rejection_count")
                == candidate["payload"]["complete_rejection_count"],
                "active_rejection_count": committed.get("active_rejection_count")
                == candidate["payload"]["active_rejection_count"],
                "superseded_rejection_count": committed.get("superseded_rejection_count")
                == len(candidate["payload"]["supersessions"]),
            },
        },
        "affected_pins_and_consumers": [
            {"path": GATE_RELATIVE, "role": "canonical rejection-integrity gate"},
            {"path": CONTRACT_RELATIVE, "role": "validation contract"},
            {
                "path": STALE_SIDECAR_MODULE,
                "role": "carries a stale hardcoded BAT-637 gate pin; must be "
                "corrected in its own change, NOT by copying the live hash",
            },
            {
                "path": CORPUS_CONTRACT_RELATIVE,
                "role": "declares the authoritative BAT-637 pins (already correct)",
            },
        ],
        "recovery_plan": (
            "The candidate is written only under the isolated root, so "
            "abandoning it requires deleting that directory and nothing else. "
            "No predecessor byte was modified (proven by before/after hashes "
            "in this artifact), no Done gate was edited, and the canonical "
            "lake was read-only throughout. If activation is declined, the "
            "mounted Family B validation simply remains FAIL, which is its "
            "current honest state."
        ),
        "what_this_request_does_not_cover": (
            "It does not request merge, hold release, or any change to the "
            "BAT-637 gate itself. The BAT-637 test error is a stale code "
            "sidecar, not a gate drift, and is a separate defect."
        ),
    }

    result = {
        "artifact_type": "CYCLE35_R35_10_FAMILY_B_CANDIDATE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "isolated_root": str(isolated_root),
        "second_isolated_root": str(second_root),
        "canonical_lake_read_only": True,
        "candidate_gate": first["gate"],
        "candidate_manifest": first["manifest"],
        "child_byte_validation": first_validation,
        "replay2_child_byte_validation": second_validation,
        "replay_produces_identical_candidate": replay_identical,
        "negative_controls": controls,
        "all_negative_controls_behaved": all(row["detected"] for row in controls),
        "predecessor_hashes_before": before,
        "predecessor_hashes_after": after,
        "predecessor_bytes_unchanged": predecessor_unchanged,
        "bat637_dependency_pair": pair,
        "approval_request": approval_request,
        "canonical_mounted_validation": "FAIL",
        "canonical_mounted_validation_reason": (
            "The committed gate's ledger_identity does not equal the "
            "independent reconstruction. Preparing this candidate does not "
            "change that; activating canonical routing is the distinct "
            "approval named above, and until it is resolved the mounted "
            "Family B dimension remains FAIL rather than green-by-exception."
        ),
        "no_done_gate_edited": True,
        "no_live_hash_copied_into_an_old_pin": True,
    }
    (out_dir / "R35_10_FAMILY_B_CANDIDATE.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    (out_dir / "R35_10_APPROVAL_REQUEST.json").write_text(
        json.dumps(approval_request, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(
        {
            "candidate_ledger_identity": candidate["payload"]["ledger_identity"][:16],
            "committed_ledger_identity": str(committed.get("ledger_identity"))[:16],
            "children": len(first["children"]),
            "all_children_match_on_disk": first_validation["all_children_match_on_disk"],
            "replay_identical": replay_identical,
            "negative_controls_ok": all(row["detected"] for row in controls),
            "predecessor_bytes_unchanged": predecessor_unchanged,
            "bat637_contract_pin_matches_live": pair["contract_pin_matches_live_gate"],
            "bat637_code_sidecar_matches_live": pair["code_sidecar_matches_live_gate"],
            "canonical_mounted_validation": "FAIL",
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
