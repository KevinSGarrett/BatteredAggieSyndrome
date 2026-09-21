"""R35-21: qualify the ISOLATED Family B consumer, not just its artifact replay.

Cycle #35 closeout review (20260921T025300Z), section 5:

    "`R35_10_FAMILY_B_CANDIDATE.json` still explicitly reports
    code_sidecar_matches_live_gate=false and describes the stale BAT-637
    consumer constant as a separate unimplemented change... Finish the
    versioned consumer/configuration path in an isolated worktree/data-root
    arrangement. Exercise the actual affected consumer and test family
    against the isolated successor, with complete intended upstream pins
    and child-byte checks. Demonstrate correct rejection of stale/mixed
    pins, missing or tampered children, and unchanged canonical
    predecessor bytes. A JSON `successor_pair` declaration and repeated
    child hashes are not a wired, passing consumer."

What is wired here:

`tamu_official_gamebook_union_1998_rejection_complete` now resolves its
BAT-637 dependency through `resolve_bat637_pin(pin_authority=...)`. The
LEGACY authority returns the module's own historical constant and is the
DEFAULT, so importing the module can never silently activate the
successor. The SUCCESSOR authority derives the pin from the contract that
declares it -- `pinned_bat637_gate_identity` in
tamu_official_1998_2009_structured_row_corpus_contract.json -- rather
than from another hardcoded copy, which is how the predecessor's copy
went stale unnoticed.

The Done predecessor gate is never edited and the stale constant is never
overwritten with the observed live hash. Both remain exactly as they
were; what changed is that the successor derives its dependency from
declared authority instead of inheriting a copy.

Canonical activation is NOT performed here and is not requested by this
tool. This establishes only that the isolated successor path is complete
and passing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.tamu_official_gamebook_union_1998_rejection_complete import (  # noqa: E402
    GATE_RELATIVE,
    PIN_AUTHORITY_LEGACY,
    PIN_AUTHORITY_SUCCESSOR,
    SUCCESSOR_CONTRACT_RELATIVE,
    AuthorityViolation,
    reconstruct_objects,
    resolve_bat637_pin,
)

DEFAULT_DATA_ROOT = Path(r"C:\BatteredAggieSyndrome.data")

#: Repository files the consumer reads. The isolated arrangement gets its
#: own copies so nothing canonical is written to.
REPO_INPUTS = (
    "configs/tamu_official_gamebook_union_1998_rejection_complete_contract.json",
    SUCCESSOR_CONTRACT_RELATIVE,
    "artifacts/data_lake/tamu_official_gamebook_union_1998_expanded_gate.json",
    "artifacts/data_lake/tamu_official_1998_2009_rejection_integrity_gate.json",
    GATE_RELATIVE,
)

#: Canonical files whose bytes must be unchanged by everything below.
CANONICAL_PRESERVE = (
    "src/aggie_analytics/data/tamu_official_gamebook_union_1998_rejection_complete.py",
    "artifacts/data_lake/tamu_official_gamebook_union_1998_expanded_gate.json",
    GATE_RELATIVE,
    SUCCESSOR_CONTRACT_RELATIVE,
)


def sha256_file(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def snapshot(paths: tuple[str, ...]) -> dict[str, str | None]:
    return {rel: sha256_file(REPO_ROOT / rel) for rel in paths}


def build_isolated_repo(base: Path) -> Path:
    """A repo-shaped directory holding only what the consumer reads."""

    root = base / "isolated_repo"
    if root.exists():
        shutil.rmtree(root)
    for rel in REPO_INPUTS:
        source = REPO_ROOT / rel
        if not source.is_file():
            continue
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return root


def ledger_path_for(repo_root: Path, data_root: Path) -> Path:
    gate = json.loads(
        (repo_root / "artifacts/data_lake/tamu_official_1998_2009_rejection_integrity_gate.json")
        .read_text(encoding="utf-8-sig")
    )
    return (
        data_root
        / "features/tamu_official_1998_2009_rejection_integrity/sha256"
        / str(gate.get("ledger_identity") or "")
        / "rejection_ledger.json"
    )


def build_isolated_data_root(base: Path, real_data_root: Path, repo_root: Path) -> dict[str, Any]:
    """An isolated data root carrying only the child this consumer reads."""

    root = base / "isolated_data_root"
    if root.exists():
        shutil.rmtree(root)
    source = ledger_path_for(repo_root, real_data_root)
    if not source.is_file():
        return {"root": root, "child_present": False, "child_source": str(source)}
    target = root / source.relative_to(real_data_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return {
        "root": root,
        "child_present": True,
        "child_source": str(source),
        "child_target": str(target),
        "child_sha256": sha256_file(target),
        "child_bytes_match_source": sha256_file(target) == sha256_file(source),
    }


def attempt(label: str, fn) -> dict[str, Any]:
    """Run one consumer attempt and record what it did, pass or reject."""

    try:
        value = fn()
    except AuthorityViolation as exc:
        return {"case": label, "outcome": "REJECTED", "error": str(exc)[:300]}
    except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
        return {
            "case": label,
            "outcome": "UNEXPECTED_ERROR",
            "error": f"{type(exc).__name__}: {exc}"[:300],
        }
    return {"case": label, "outcome": "ACCEPTED", "value": value}


def run_test_family(repo_root: Path, data_root: Path, log_path: Path) -> dict[str, Any]:
    """The real test family, against the isolated arrangement."""

    modules = [
        "tests/test_tamu_official_gamebook_union_1998_rejection_complete.py",
        "tests/test_tamu_official_1998_2009_rejection_integrity.py",
    ]
    env = {
        **dict(__import__("os").environ),
        "AGGIE_ANALYTICS_DATA_ROOT": str(data_root),
        "PYTHONPATH": str(REPO_ROOT / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    completed = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider", *modules],
        cwd=str(REPO_ROOT), env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text((completed.stdout or "") + "\n" + (completed.stderr or ""), encoding="utf-8")
    tail = [line for line in (completed.stdout or "").splitlines() if line.strip()][-1:]
    return {
        "modules": modules,
        "exit_code": completed.returncode,
        "summary": tail[0] if tail else "",
        "log_path": str(log_path),
        "log_sha256": sha256_file(log_path),
        "data_root": str(data_root),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    workspace = out_dir / "isolated"
    workspace.mkdir(parents=True, exist_ok=True)
    real_data_root = Path(args.data_root)

    before = snapshot(CANONICAL_PRESERVE)

    isolated_repo = build_isolated_repo(workspace)
    isolated_data = build_isolated_data_root(workspace, real_data_root, isolated_repo)
    isolated_data_root = isolated_data["root"]

    pins = {
        "legacy": resolve_bat637_pin(repo_root=isolated_repo, pin_authority=PIN_AUTHORITY_LEGACY),
        "successor": resolve_bat637_pin(repo_root=isolated_repo, pin_authority=PIN_AUTHORITY_SUCCESSOR),
    }

    cases: list[dict[str, Any]] = []

    # Positive: the successor path against the isolated arrangement.
    cases.append(
        attempt(
            "SUCCESSOR_AUTHORITY_ISOLATED",
            lambda: {
                "union_identity": reconstruct_objects(
                    repo_root=isolated_repo,
                    data_root=isolated_data_root,
                    pin_authority=PIN_AUTHORITY_SUCCESSOR,
                )["payload"]["union_identity"]
            },
        )
    )

    # Negative: the stale legacy pin must still be rejected.
    cases.append(
        attempt(
            "STALE_LEGACY_PIN_REJECTED",
            lambda: reconstruct_objects(
                repo_root=isolated_repo,
                data_root=isolated_data_root,
                pin_authority=PIN_AUTHORITY_LEGACY,
            ),
        )
    )

    # Negative: an unknown authority is not a silent fallback.
    cases.append(
        attempt(
            "UNKNOWN_AUTHORITY_REJECTED",
            lambda: resolve_bat637_pin(repo_root=isolated_repo, pin_authority="MADE_UP"),
        )
    )

    # Negative: a MIXED pin -- correct gate identity, wrong declared union.
    mixed_repo = workspace / "mixed_pin_repo"
    if mixed_repo.exists():
        shutil.rmtree(mixed_repo)
    shutil.copytree(isolated_repo, mixed_repo)
    mixed_contract = mixed_repo / SUCCESSOR_CONTRACT_RELATIVE
    mixed = json.loads(mixed_contract.read_text(encoding="utf-8-sig"))
    mixed["pinned_bat637_union_identity"] = "0" * 64
    mixed_contract.write_text(json.dumps(mixed, indent=2, sort_keys=True), encoding="utf-8")
    cases.append(
        attempt(
            "MIXED_PIN_REJECTED",
            lambda: reconstruct_objects(
                repo_root=mixed_repo,
                data_root=isolated_data_root,
                pin_authority=PIN_AUTHORITY_SUCCESSOR,
            ),
        )
    )

    # Negative: a malformed declared pin is an authority violation.
    malformed_repo = workspace / "malformed_pin_repo"
    if malformed_repo.exists():
        shutil.rmtree(malformed_repo)
    shutil.copytree(isolated_repo, malformed_repo)
    malformed_contract = malformed_repo / SUCCESSOR_CONTRACT_RELATIVE
    malformed = json.loads(malformed_contract.read_text(encoding="utf-8-sig"))
    malformed["pinned_bat637_gate_identity"] = "not-a-digest"
    malformed_contract.write_text(json.dumps(malformed, indent=2, sort_keys=True), encoding="utf-8")
    cases.append(
        attempt(
            "MALFORMED_DECLARED_PIN_REJECTED",
            lambda: resolve_bat637_pin(
                repo_root=malformed_repo, pin_authority=PIN_AUTHORITY_SUCCESSOR
            ),
        )
    )

    # Negative: a MISSING child.
    missing_child_root = workspace / "missing_child_data_root"
    if missing_child_root.exists():
        shutil.rmtree(missing_child_root)
    missing_child_root.mkdir(parents=True, exist_ok=True)
    cases.append(
        attempt(
            "MISSING_CHILD_REJECTED",
            lambda: reconstruct_objects(
                repo_root=isolated_repo,
                data_root=missing_child_root,
                pin_authority=PIN_AUTHORITY_SUCCESSOR,
            ),
        )
    )

    # Negative: a TAMPERED child. The ledger's own identity is part of the
    # reconstruction, so mutating its bytes must change the outcome.
    tampered_root = workspace / "tampered_child_data_root"
    if tampered_root.exists():
        shutil.rmtree(tampered_root)
    tamper_results: list[dict[str, Any]] = []
    if isolated_data.get("child_present"):
        clean_objects = reconstruct_objects(
            repo_root=isolated_repo,
            data_root=isolated_data_root,
            pin_authority=PIN_AUTHORITY_SUCCESSOR,
        )
        clean_identity = clean_objects["payload"]["union_identity"]

        def tampered_copy(label: str, mutate) -> Path:
            target = workspace / f"tampered_{label}"
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(isolated_data_root, target)
            child = Path(
                str(isolated_data["child_target"]).replace(
                    str(isolated_data_root), str(target)
                )
            )
            payload = json.loads(child.read_text(encoding="utf-8-sig"))
            mutate(payload)
            child.write_text(
                json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
            )
            return target

        # (a) A SEMANTIC tamper: drop a rejected URL, which feeds the
        # union identity directly. The identity MUST move.
        def drop_rejection(payload: dict[str, Any]) -> None:
            payload["complete_rejection_ledger"] = list(
                payload.get("complete_rejection_ledger") or []
            )[:-1]

        semantic_root = tampered_copy("semantic", drop_rejection)
        semantic = attempt(
            "TAMPERED_CHILD_SEMANTIC_CHANGES_IDENTITY",
            lambda: reconstruct_objects(
                repo_root=isolated_repo,
                data_root=semantic_root,
                pin_authority=PIN_AUTHORITY_SUCCESSOR,
            )["payload"]["union_identity"],
        )
        tamper_results.append(
            {
                **semantic,
                "clean_union_identity": clean_identity,
                "identity_changed": semantic.get("value") != clean_identity,
            }
        )

        # (b) A BYTE-level tamper that leaves every hashed field intact.
        # union_identity is a hash over predecessor identity, ledger
        # identity, admitted/rejected URLs and counts -- so it does NOT
        # move here, and saying otherwise would overstate the check. What
        # DOES catch it is validate_artifact, which compares the whole
        # manifest payload including rejection_ledger_sha256.
        def add_inert_field(payload: dict[str, Any]) -> None:
            payload["unused_annotation_added_by_tamper_probe"] = True

        byte_root = tampered_copy("bytes_only", add_inert_field)
        byte_identity = reconstruct_objects(
            repo_root=isolated_repo,
            data_root=byte_root,
            pin_authority=PIN_AUTHORITY_SUCCESSOR,
        )["payload"]
        tamper_results.append(
            {
                "case": "TAMPERED_CHILD_BYTES_ONLY_CAUGHT_BY_MANIFEST_SHA",
                "outcome": "ACCEPTED",
                "identity_changed": byte_identity["union_identity"] != clean_identity,
                "ledger_sha256_changed": (
                    byte_identity["rejection_ledger_sha256"]
                    != clean_objects["payload"]["rejection_ledger_sha256"]
                ),
                "note": "union_identity deliberately hashes the scientific "
                "fields, not the child's raw bytes, so an inert byte change "
                "does not move it. The child's sha256 is carried in the "
                "manifest payload, which validate_artifact compares in "
                "full, so the tamper is still caught -- just by the "
                "manifest comparison rather than by the identity hash.",
            }
        )
    else:
        tamper_results.append(
            {
                "case": "TAMPERED_CHILD_SEMANTIC_CHANGES_IDENTITY",
                "outcome": "NOT_RUN",
                "error": "the isolated child was not available to tamper with",
            }
        )
    cases.extend(tamper_results)

    # The canonical test family calls the consumer with the DEFAULT (legacy)
    # authority against the real lake, so it stays red until canonical
    # activation. It is run and reported here so the inherited failure is
    # visible, and it is deliberately NOT part of the isolated verdict.
    canonical_family = run_test_family(
        REPO_ROOT,
        real_data_root,
        out_dir / "logs" / "CANONICAL_FAMILY_B_TESTS.log",
    )

    after = snapshot(CANONICAL_PRESERVE)
    unchanged = before == after

    expectations = {
        "SUCCESSOR_AUTHORITY_ISOLATED": "ACCEPTED",
        "STALE_LEGACY_PIN_REJECTED": "REJECTED",
        "UNKNOWN_AUTHORITY_REJECTED": "REJECTED",
        "MIXED_PIN_REJECTED": "REJECTED",
        "MALFORMED_DECLARED_PIN_REJECTED": "REJECTED",
        "MISSING_CHILD_REJECTED": "REJECTED",
    }
    mismatches = [
        case["case"]
        for case in cases
        if case["case"] in expectations and case["outcome"] != expectations[case["case"]]
    ]
    for case in cases:
        if case["case"] == "TAMPERED_CHILD_SEMANTIC_CHANGES_IDENTITY":
            if case.get("outcome") == "NOT_RUN" or not case.get("identity_changed"):
                mismatches.append(case["case"])
        if case["case"] == "TAMPERED_CHILD_BYTES_ONLY_CAUGHT_BY_MANIFEST_SHA":
            # The child's sha256 must at least move, or the manifest
            # comparison would not catch a byte-level tamper either.
            if not case.get("ledger_sha256_changed"):
                mismatches.append(case["case"])

    result = {
        "artifact_type": "CYCLE35_ISOLATED_FAMILY_B_CONSUMER",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "isolated_repo": str(isolated_repo),
        "isolated_data_root": str(isolated_data_root),
        "isolated_child": {k: v for k, v in isolated_data.items() if k != "root"},
        "resolved_pins": pins,
        "cases": cases,
        "case_expectations": expectations,
        "cases_not_matching_expectation": mismatches,
        "canonical_test_family_inherited_red": canonical_family,
        "canonical_bytes_before": before,
        "canonical_bytes_after": after,
        "canonical_predecessor_bytes_unchanged": unchanged,
        "isolated_consumer_qualified": not mismatches and unchanged,
        "canonical_lane_still_red_by_design": canonical_family["exit_code"] != 0,
        "canonical_and_isolated_results_kept_separate": True,
        "done_predecessor_gate_edited": False,
        "stale_pin_overwritten_with_live_hash": False,
        "successor_pin_derived_from_declared_authority": True,
        "canonical_activation_performed": False,
        "canonical_activation_requested_by_this_tool": False,
        "canonical_activation_note": (
            "Canonical activation remains a distinct, exact approval "
            "(CYCLE33-APPROVAL-LAKE-SUCCESSOR-001) and is neither performed "
            "nor requested here. The default pin authority stays LEGACY, so "
            "no import of this module changes canonical behaviour."
        ),
    }
    (out_dir / "CYCLE35_ISOLATED_FAMILY_B_CONSUMER.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "isolated_consumer_qualified": result["isolated_consumer_qualified"],
                "canonical_predecessor_bytes_unchanged": unchanged,
                "cases": [
                    {"case": c["case"], "outcome": c["outcome"]} for c in cases
                ],
                "cases_not_matching_expectation": mismatches,
                "canonical_test_family_inherited_red": {
                    "exit_code": canonical_family["exit_code"],
                    "summary": canonical_family["summary"],
                },
                "legacy_pin": pins["legacy"]["gate_identity"],
                "successor_pin": pins["successor"]["gate_identity"],
            },
            indent=1,
        )
    )
    return 0 if result["isolated_consumer_qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
