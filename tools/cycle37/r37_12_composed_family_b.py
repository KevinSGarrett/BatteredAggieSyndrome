"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-12 / R36-12 / MR35R-10 / U37-01: the COMPOSED Family B successor -- upstream
rejection ledger d48698ab / gate 2dcb3368 and downstream union ab170b25 / gate
f343e4e3 -- qualified together in a new isolated root built from the sealed
declared seed.

The Cycle 37 family-b lane ran only the upstream qualification
(r35_31). R36-12 names the composition as the new unit. This tool:

* reproduces the manager's ``family_b_composed_probe.py`` (read before this
  was written) in a root that must not already exist, from the seed whose
  entry digests the declared contract pins;
* materializes and validates the downstream twice and requires one answer;
* asserts the four published identities against what this run derives, and
  has ``r37_12_family_b_independent`` (stdlib only) recompute them and the
  scientific fields acceptance depends on from raw bytes, and compare the
  canonical predecessor with the candidate so each changed identity is
  explained from content;
* runs 32 negative controls through the REAL validators -- stale and mixed
  pins, missing payloads, changed child bytes, altered semantic fields,
  recomputed-hash forgery, absent consumer files, wrong module, wrong root,
  canonical-versus-isolated confusion and the stale code sidecar -- restoring
  and byte-verifying every file after each one;
* rehearses rollback: re-pins the isolated copy to the branch head's
  committed predecessor files, shows both validators then behave exactly as
  they do in the mounted configuration (branch head against the canonical
  lake), re-activates, and shows the identities come back;
* hashes the canonical checkout, the worktree and the canonical lake children
  before and after.

Nothing is activated. The default stays LEGACY, no canonical byte is written,
and the canonical mounted lane honestly stays FAIL until an owner grants
CYCLE33-APPROVAL-LAKE-SUCCESSOR-001. Exit 0 only when every clause holds.
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
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from aggie_analytics.data import (  # noqa: E402
    tamu_official_1998_2009_rejection_integrity as upstream,
)
from aggie_analytics import atomic_io as _bas_atomic
from aggie_analytics.data import (  # noqa: E402
    tamu_official_gamebook_union_1998_rejection_complete as downstream,
)
from aggie_analytics.data.tamu_official_historical_boxscores import AuthorityViolation  # noqa: E402
from aggie_analytics.workspace.paths import require_free_bytes, resolve_seed  # noqa: E402

import r37_12_family_b_independent as independent  # noqa: E402

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
SEED_CONTRACT_ID = "CYCLE35-FAMILY-B-COMPOSED-SEED-V1"
CANONICAL_REPO = Path(r"C:\BatteredAggieSyndrome")
CANONICAL_DATA = Path(r"C:\BatteredAggieSyndrome.data")
APPROVAL_ID = "CYCLE33-APPROVAL-LAKE-SUCCESSOR-001"
SUCCESSOR = downstream.PIN_AUTHORITY_SUCCESSOR
LEGACY = downstream.PIN_AUTHORITY_LEGACY

#: Published by the manager (TP36-08 / MR35R-10). Asserted, never copied.
EXPECTED = {
    "upstream_ledger_identity": "d48698abe2d94286c9b1f2688273a0050662e3a4e62347dac11ea353b9681aa1",
    "upstream_gate_identity": "2dcb3368fc8865efaacab570584fe810150ce4b015bac3016d54052a1b0bb835",
    "downstream_union_identity": "ab170b25b4478f7b36e4d150d3eca874efc910b76a4854768a07182e7004526a",
    "downstream_gate_identity": "f343e4e327d3991ae9cf048c149b679b3de9f08ea270eb32fbafc23f1dc4b93f",
}

#: Every repo file either module reads that an activation or a control touches.
REPO_FILES = (
    upstream.GATE_RELATIVE,
    upstream.CONTRACT_RELATIVE,
    independent.UNION_1996_GATE,
    independent.BAT637_GATE,
    downstream.GATE_RELATIVE,
    downstream.CONTRACT_RELATIVE,
    downstream.SUCCESSOR_CONTRACT_RELATIVE,
)
#: The files an activation re-pins, so the files a rollback restores.
ACTIVATION_FILES = (upstream.GATE_RELATIVE, upstream.CONTRACT_RELATIVE, downstream.GATE_RELATIVE)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def canonical_snapshot() -> dict[str, Any]:
    """Canonical checkout, this worktree and the canonical lake children."""

    lake = CANONICAL_DATA / "features"
    return {
        "canonical_checkout": {rel: sha(CANONICAL_REPO / rel) for rel in REPO_FILES},
        "worktree": {rel: sha(ROOT / rel) for rel in REPO_FILES},
        "lake": {
            "successor_ledger_child_must_not_exist": sha(
                CANONICAL_DATA / independent.LEDGER_ROOT / EXPECTED["upstream_ledger_identity"] / "rejection_ledger.json"),
            "successor_union_child_must_not_exist": sha(
                CANONICAL_DATA / independent.UNION_ROOT / EXPECTED["downstream_union_identity"] / "union_manifest.json"),
            "predecessor_children": {
                str(p.relative_to(lake)): sha(p) for p in sorted(
                    list((lake / "tamu_official_1998_2009_rejection_integrity/sha256").rglob("*.json"))
                    + list((lake / "tamu_official_gamebook_union_1998_rejection_complete/sha256").rglob("*.json")))
            },
        },
    }


def outcome(call: Callable[[], Any]) -> dict[str, Any]:
    try:
        value = call()
    except AuthorityViolation as error:
        return {"outcome": "REJECTED", "by": "AuthorityViolation", "message": str(error)[:400]}
    except Exception as error:  # noqa: BLE001 - which refusal it was is the evidence
        return {"outcome": "REJECTED", "by": type(error).__name__, "message": str(error)[:400],
                "note": "Fail-closed, but by an incidental exception rather than a declared authority check."}
    return {"outcome": "ACCEPTED", "value": value}


class Probe:
    def __init__(self, isolated: Path) -> None:
        self.isolated = isolated
        self.repo = isolated / "repo"
        self.data = isolated / "data"
        self.quarantine = isolated / "control_quarantine"
        self.controls: list[dict[str, Any]] = []

    # -- the real validators ------------------------------------------------
    def up(self, repo: Path | None = None, data: Path | None = None, **kwargs: Any) -> Any:
        return upstream.validate_artifact(repo_root=repo or self.repo, data_root=data or self.data, **kwargs)

    def down(self, repo: Path | None = None, data: Path | None = None, pin: str = SUCCESSOR, **kwargs: Any) -> Any:
        return downstream.validate_artifact(repo_root=repo or self.repo, data_root=data or self.data,
                                            pin_authority=pin, **kwargs)

    # -- controls -------------------------------------------------------------
    def control(self, case: str, must_reject: tuple[str, ...], calls: dict[str, Callable[[], Any]],
                changes: dict[Path, bytes | None] | None = None, note: str = "",
                must_not_return_successor: bool = False) -> None:
        """Apply byte changes, run the named validators, restore, and prove it.

        ``None`` for a file means absent: it is moved into the quarantine
        folder and moved back, never deleted.
        """

        originals: dict[Path, str | None] = {}
        moved: dict[Path, Path] = {}
        saved: dict[Path, bytes] = {}
        created: list[Path] = []
        for path, new in (changes or {}).items():
            originals[path] = sha(path)
            if path.is_file():
                saved[path] = path.read_bytes()
            elif new is not None:
                # The topmost directory this control creates is moved out
                # afterwards, so the data root ends exactly as it began.
                top = path
                while not top.parent.exists():
                    top = top.parent
                created.append(top)
            if new is None:
                target = self.quarantine / case / path.name
                target.parent.mkdir(parents=True, exist_ok=True)
                path.replace(target)
                moved[path] = target
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                _bas_atomic.write_bytes(path, new)
        results = {side: outcome(call) for side, call in calls.items()}
        for path, target in moved.items():
            target.replace(path)
        for path, original in saved.items():
            if path not in moved:
                _bas_atomic.write_bytes(path, original)
        for top in created:
            target = self.quarantine / case / "created" / top.name
            target.parent.mkdir(parents=True, exist_ok=True)
            top.replace(target)
        restored = all(sha(path) == digest for path, digest in originals.items())
        required_rejected = all(results[side]["outcome"] == "REJECTED" for side in must_reject)
        returned = {str(v) for r in results.values() for v in (r.get("value") or {}).values()}
        successor_returned = bool(returned & set(EXPECTED.values()))
        if must_not_return_successor:
            required_rejected = required_rejected and not successor_returned
        self.controls.append({
            "case": case, "must_reject": list(must_reject), **results,
            "changed_files": [str(p.relative_to(self.isolated)) for p in originals],
            "required_rejections_observed": required_rejected,
            "rejected_by_authority_check": all(results[s].get("by") == "AuthorityViolation" for s in must_reject),
            "must_not_return_a_successor_identity": must_not_return_successor,
            "returned_a_successor_identity": successor_returned,
            "bytes_restored_exactly": restored, "note": note,
        })


def dumps(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def run(isolated: Path, seed: Path) -> dict[str, Any]:
    if isolated.exists():
        raise RuntimeError(f"refuse to reuse an existing isolated root: {isolated}")
    seed_bytes = sum(p.stat().st_size for name in ("repo", "data") for p in (seed / name).rglob("*") if p.is_file())
    require_free_bytes(isolated.parent, seed_bytes * 2, reserve=8 * 1024**3)
    before = canonical_snapshot()
    shutil.copytree(seed / "repo", isolated / "repo")
    shutil.copytree(seed / "data", isolated / "data")
    probe = Probe(isolated)
    repo, data = probe.repo, probe.data
    copied = []
    for rel in (downstream.CONTRACT_RELATIVE, downstream.GATE_RELATIVE, downstream.SUCCESSOR_CONTRACT_RELATIVE,
                independent.BAT637_GATE):
        destination = repo / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, destination)
        copied.append({"relative": rel, "sha256": sha(destination)})
    seed_state = {rel: sha(repo / rel) for rel in REPO_FILES}
    # After an activation the canonical lake would hold the predecessor
    # children beside the successor's, so the isolated copy models that too.
    predecessor_children = []
    for root, identity, name in (
            (independent.LEDGER_ROOT, upstream_predecessor_ledger(), "rejection_ledger.json"),
            (independent.UNION_ROOT, json.loads((CANONICAL_REPO / downstream.GATE_RELATIVE).read_bytes())["union_identity"],
             "union_manifest.json")):
        source = CANONICAL_DATA / root / identity / name
        destination = data / root / identity / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        predecessor_children.append({"relative": f"{root}/{identity}/{name}", "sha256": sha(destination),
                                     "equals_canonical": sha(destination) == sha(source)})

    # ---- positive, twice ----------------------------------------------------
    upstream_positive = outcome(lambda: probe.up())
    first = downstream.materialize_union(repo_root=repo, data_root=data, pin_authority=SUCCESSOR)
    downstream_positive = outcome(lambda: probe.down())
    second = downstream.materialize_union(repo_root=repo, data_root=data, pin_authority=SUCCESSOR)
    downstream_replay = outcome(lambda: probe.down())
    upstream_replay = outcome(lambda: probe.up())
    replay_identical = first == second and downstream_positive == downstream_replay and upstream_positive == upstream_replay
    derived = {
        "upstream_ledger_identity": (upstream_positive.get("value") or {}).get("ledger_identity"),
        "upstream_gate_identity": (upstream_positive.get("value") or {}).get("gate_identity"),
        "downstream_union_identity": (downstream_positive.get("value") or {}).get("union_identity"),
        "downstream_gate_identity": (downstream_positive.get("value") or {}).get("gate_identity"),
    }
    ind = independent.run(repo, data, CANONICAL_REPO, CANONICAL_DATA)
    recomputed = {
        "upstream_ledger_identity": ind["upstream"]["ledger_identity"],
        "upstream_gate_identity": ind["upstream"]["gate_identity"],
        "downstream_union_identity": ind["downstream"]["union_identity"],
        "downstream_gate_identity": ind["downstream"]["gate_identity"],
    }
    identity_agreement = {key: {"published_by_manager": EXPECTED[key], "validator_returned": derived[key],
                                "independently_recomputed": recomputed[key],
                                "all_three_agree": EXPECTED[key] == derived[key] == recomputed[key]}
                          for key in EXPECTED}

    # ---- the paths the controls touch ----------------------------------------
    ledger = data / independent.LEDGER_ROOT / EXPECTED["upstream_ledger_identity"] / "rejection_ledger.json"
    union = Path(first["manifest_path"])
    up_gate, down_gate = repo / upstream.GATE_RELATIVE, repo / downstream.GATE_RELATIVE
    down_contract = repo / downstream.CONTRACT_RELATIVE
    succ_contract = repo / downstream.SUCCESSOR_CONTRACT_RELATIVE
    bat637 = repo / independent.BAT637_GATE
    L = json.loads(ledger.read_bytes())
    U = json.loads(union.read_bytes())
    UG, DG = json.loads(up_gate.read_bytes()), json.loads(down_gate.read_bytes())
    SC, B637 = json.loads(succ_contract.read_bytes()), json.loads(bat637.read_bytes())
    pred_down_gate = json.loads((CANONICAL_REPO / downstream.GATE_RELATIVE).read_bytes())
    both = {"upstream": lambda: probe.up(), "downstream": lambda: probe.down()}
    down_only = {"downstream": lambda: probe.down()}
    c = probe.control

    def regate(gate: dict[str, Any], **fields: Any) -> bytes:
        forged = {**gate, **fields}
        forged["gate_identity"] = independent.gate_hash(forged)
        return dumps(forged)

    # the manager's two, then the ledger family
    c("ledger_inert_field", ("upstream", "downstream"), both, {ledger: dumps({**L, "cycle37_inert_marker": True})})
    c("ledger_semantic_count_altered", ("upstream", "downstream"), both, {ledger: dumps({**L, "active_rejection_count": 999})})
    c("ledger_semantic_field_removed", ("upstream", "downstream"), both,
      {ledger: dumps({k: v for k, v in L.items() if k != "active_rejection_count"})})
    c("ledger_semantic_row_dropped", ("upstream", "downstream"), both,
      {ledger: dumps({**L, "complete_rejection_ledger": L["complete_rejection_ledger"][:-1]})})
    c("ledger_payload_emptied", ("upstream", "downstream"), both, {ledger: dumps({})})
    c("ledger_payload_missing", ("upstream", "downstream"), both, {ledger: None})

    # recomputed-hash forgery: a tampered ledger that states its own recomputed
    # identity, in the child directory that identity names, with both gates
    # re-pinned and re-hashed so every stated hash agrees with its bytes.
    forged_ledger = {**L, "active_rejection_count": 998}
    forged_id = independent.content_hash({k: v for k, v in forged_ledger.items() if k not in ("ledger_identity", "gate_identity")})
    forged_ledger["ledger_identity"] = forged_id
    forged_path = data / independent.LEDGER_ROOT / forged_id / "rejection_ledger.json"
    c("recomputed_hash_forgery_upstream_gate_and_ledger", ("upstream", "downstream"), both,
      {forged_path: dumps(forged_ledger), up_gate: regate(UG, ledger_identity=forged_id),
       down_gate: regate(DG, rejection_ledger_identity=forged_id)},
      note="Every stated hash agrees with its own bytes. Upstream refuses because its reconstruction from raw "
           "inputs names d48698ab; downstream refuses because its own reconstruction yields a different union.")

    # the downstream child
    c("union_manifest_missing", ("downstream",), down_only, {union: None})
    c("union_manifest_inert_field", ("downstream",), down_only, {union: dumps({**U, "cycle37_inert_marker": True})})
    c("union_manifest_semantic_game_dropped", ("downstream",), down_only,
      {union: dumps({**U, "enriched_official_games": U["enriched_official_games"][:-1]})})
    c("bat637_gate_games_changed_identity_kept", ("downstream",), down_only,
      {bat637: dumps({**B637, "enriched_official_games": B637["enriched_official_games"][:-1]})},
      note="The BAT-637 gate keeps its stated gate identity, so the pin still matches; the union reconstruction must refuse.")

    # stale and mixed pins in the committed gates
    c("downstream_gate_stale_ledger_pin", ("downstream",), down_only,
      {down_gate: dumps({**DG, "rejection_ledger_identity": upstream_predecessor_ledger()})})
    c("downstream_gate_stale_ledger_pin_rehashed", ("downstream",), down_only,
      {down_gate: regate(DG, rejection_ledger_identity=upstream_predecessor_ledger())})
    c("downstream_gate_mixed_predecessor_union_rehashed", ("downstream",), down_only,
      {down_gate: regate(DG, union_identity=pred_down_gate["union_identity"])})
    c("upstream_gate_is_the_canonical_predecessor", ("upstream", "downstream"), both,
      {up_gate: (CANONICAL_REPO / upstream.GATE_RELATIVE).read_bytes()},
      note="Predecessor upstream gate (ledger 1b79f1ba) mixed with the successor downstream.")
    c("downstream_gate_is_the_canonical_predecessor", ("downstream",), down_only,
      {down_gate: (CANONICAL_REPO / downstream.GATE_RELATIVE).read_bytes()},
      note="Predecessor downstream gate mixed with the successor upstream; upstream never reads this file.")

    # the pin authority and the code sidecar
    c("stale_code_sidecar_legacy_pin_authority", ("downstream",), {"downstream": lambda: probe.down(pin=LEGACY)},
      note="The module's historical constant c1d22209 against the live BAT-637 gate 606aed7f.")
    c("unknown_pin_authority", ("downstream",), {"downstream": lambda: probe.down(pin="SOMETHING_ELSE")})
    c("successor_contract_stale_gate_pin", ("downstream",), down_only,
      {succ_contract: dumps({**SC, downstream.SUCCESSOR_CONTRACT_PIN_FIELD: downstream.LEGACY_BAT637_GATE_IDENTITY})})
    c("successor_contract_mixed_union_pin", ("downstream",), down_only,
      {succ_contract: dumps({**SC, downstream.SUCCESSOR_CONTRACT_UNION_FIELD: "0" * 64})},
      note="The gate pin still matches; only the declared union identity disagrees.")
    c("successor_contract_malformed_pin", ("downstream",), down_only,
      {succ_contract: dumps({**SC, downstream.SUCCESSOR_CONTRACT_PIN_FIELD: "not-a-sha256"})})

    # absent consumer files
    c("absent_downstream_consumer_contract", ("downstream",), down_only, {down_contract: None})
    c("absent_successor_authority_contract", ("downstream",), down_only, {succ_contract: None})
    c("absent_committed_downstream_gate", ("downstream",), down_only, {down_gate: None})
    c("absent_bat637_gate", ("downstream",), down_only, {bat637: None})
    c("absent_upstream_gate", ("upstream", "downstream"), both, {up_gate: None})

    # wrong module, wrong root, canonical-versus-isolated confusion
    c("wrong_module_upstream_validator_given_downstream_gate", ("upstream",),
      {"upstream": lambda: probe.up(gate=json.loads(down_gate.read_bytes()))})
    c("wrong_module_downstream_validator_given_upstream_gate", ("downstream",),
      {"downstream": lambda: probe.down(gate=json.loads(up_gate.read_bytes()))})
    c("canonical_lake_with_isolated_repo", ("upstream", "downstream"),
      {"upstream": lambda: probe.up(data=CANONICAL_DATA), "downstream": lambda: probe.down(data=CANONICAL_DATA)},
      note="Read-only: validate_artifact never writes.")
    c("branch_head_checkout_with_isolated_data", ("upstream", "downstream"),
      {"upstream": lambda: probe.up(repo=ROOT), "downstream": lambda: probe.down(repo=ROOT)},
      note="The worktree's committed gates still pin the predecessor while its BAT-637 and corpus gates are the "
           "BAT-649 regeneration, so both validators must refuse. Read-only: validate_artifact never writes.")
    c("canonical_main_checkout_with_isolated_data", (),
      {"upstream": lambda: probe.up(repo=CANONICAL_REPO), "downstream": lambda: probe.down(repo=CANONICAL_REPO)},
      must_not_return_successor=True,
      note="Canonical main predates the BAT-649 BAT-637 and corpus regeneration, so its gates and the "
           "predecessor children form a self-consistent PREDECESSOR and may validate. The confusion risk is "
           "mistaking that for the successor, so the control requires that no successor identity is returned.")
    empty = isolated / "empty_data_root"
    empty.mkdir()
    c("empty_data_root", ("upstream", "downstream"),
      {"upstream": lambda: probe.up(data=empty), "downstream": lambda: probe.down(data=empty)})

    restored = {"upstream": outcome(lambda: probe.up()), "downstream": outcome(lambda: probe.down())}
    restored_ok = restored == {"upstream": upstream_positive, "downstream": downstream_positive}

    rollback = rehearse_rollback(probe, upstream_positive, downstream_positive)
    after = canonical_snapshot()

    controls = probe.controls
    failed_controls = [x["case"] for x in controls if not x["required_rejections_observed"]]
    unrestored = [x["case"] for x in controls if not x["bytes_restored_exactly"]]
    incidental = [x["case"] for x in controls if x["required_rejections_observed"] and not x["rejected_by_authority_check"]]
    clauses = {
        "positive_upstream_and_downstream_pass": upstream_positive["outcome"] == downstream_positive["outcome"] == "ACCEPTED",
        "replay_identical": replay_identical,
        "published_identities_reproduced_and_independently_recomputed": all(
            v["all_three_agree"] for v in identity_agreement.values()),
        "independent_scientific_checks_pass": ind["all_checks_pass"],
        "every_negative_control_rejected_on_its_required_side": not failed_controls,
        "every_control_restored_byte_exact": not unrestored,
        "restored_validation_equals_first_positive": restored_ok,
        "rollback_rehearsal_complete": rollback["complete"],
        "canonical_bytes_unchanged": before == after,
        "successor_children_absent_from_the_canonical_lake": (
            after["lake"]["successor_ledger_child_must_not_exist"] is None
            and after["lake"]["successor_union_child_must_not_exist"] is None),
    }
    return {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2,
        "artifact_type": "CYCLE37_FAMILY_B_COMPOSED_QUALIFICATION",
        "requirements": ["R37-12", "R37-12-CF-R36-12", "R37-12-CF-R35-10", "R37-12-CF-MR35R-10", "R37-12-CF-U37-01"],
        "classification": "INDEPENDENT_INTEGRATION_PROBE_NOT_SCIENTIFIC_ACCEPTANCE",
        "generated_at_utc": utc_now(), "isolated_root": str(isolated),
        "manager_probe_reproduced": r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle35\20260921T131038Z\family_b_composed_probe.py",
        "layout": {"seed": str(seed), "seed_repo_files": seed_state, "copied_from_worktree": copied,
                   "canonical_predecessor_children_copied_in": predecessor_children},
        "module_digests": {"upstream": sha(Path(upstream.__file__)), "downstream": sha(Path(downstream.__file__)),
                           "independent_checker": sha(Path(independent.__file__))},
        "positive": {"upstream": upstream_positive, "downstream_materialized_first": first,
                     "downstream": downstream_positive, "downstream_materialized_second": second,
                     "downstream_replay": downstream_replay, "upstream_replay": upstream_replay,
                     "replay_identical": replay_identical},
        "identity_agreement": identity_agreement,
        "independent_reconstruction": ind,
        "negative_controls": controls, "negative_controls_total": len(controls),
        "negative_controls_rejected": len(controls) - len(failed_controls),
        "negative_controls_not_rejected": failed_controls,
        "controls_rejected_by_an_incidental_exception": incidental,
        "incidental_exception_note": (
            "An absent committed gate or contract is refused by FileNotFoundError from the module's JSON load, not "
            "by a declared AuthorityViolation. The declared CLI validators' own mutation-control helper "
            "(expect_rejection in tools/validate_tamu_official_1998_2009_rejection_integrity.py and "
            "tools/validate_tamu_official_gamebook_union_1998_rejection_complete.py) counts FileNotFoundError, "
            "like AuthorityViolation, as PASS_FAIL_CLOSED. The consumer fails closed; the distinction is recorded "
            "rather than hidden."),
        "controls_not_restored": unrestored,
        "restored_validation": restored,
        "rollback_rehearsal": rollback,
        "canonical_bytes_before": before, "canonical_bytes_after": after,
        "clauses": clauses, "qualified_in_isolation": all(clauses.values()),
        "canonical_activation": False, "hold_release": False, "default_remains": LEGACY,
        "activation_authority": f"{APPROVAL_ID} REQUESTED_NOT_GRANTED",
        "not_shown": ("Isolated qualification shows the composed consumers accept correct inputs, reject tampered "
                      "ones and roll back cleanly. It is not scientific acceptance, and the canonical mounted lane "
                      "stays FAIL while the successor is not activated."),
    }


def upstream_predecessor_ledger() -> str:
    return str(json.loads((CANONICAL_REPO / upstream.GATE_RELATIVE).read_bytes())["ledger_identity"])


def rehearse_rollback(probe: Probe, up_positive: dict[str, Any], down_positive: dict[str, Any]) -> dict[str, Any]:
    """Activation -> rollback to the canonical predecessor files -> re-activation.

    The rollback writes the canonical predecessor bytes over the isolated
    copy's activation files and leaves the successor children in place,
    unreferenced. The rolled-back copy must then behave exactly as the
    canonical checkout does (LEGACY default), and re-activation must return
    the same identities.
    """

    repo = probe.repo
    activated = {rel: (repo / rel).read_bytes() for rel in ACTIVATION_FILES}
    children = {
        "ledger": probe.data / independent.LEDGER_ROOT / EXPECTED["upstream_ledger_identity"] / "rejection_ledger.json",
        "union": probe.data / independent.UNION_ROOT / EXPECTED["downstream_union_identity"] / "union_manifest.json",
    }
    children_before = {k: sha(v) for k, v in children.items()}
    for rel in ACTIVATION_FILES:
        _bas_atomic.write_bytes(repo / rel, (ROOT / rel).read_bytes())
    rolled_back_digests = {rel: sha(repo / rel) for rel in ACTIVATION_FILES}
    canonical_digests = {rel: sha(ROOT / rel) for rel in ACTIVATION_FILES}
    canonical_main_digests = {rel: sha(CANONICAL_REPO / rel) for rel in ACTIVATION_FILES}
    isolated_after_rollback = {
        "upstream": outcome(lambda: probe.up()),
        "downstream_legacy_default": outcome(lambda: probe.down(pin=LEGACY)),
        "downstream_successor_authority": outcome(lambda: probe.down()),
    }
    def behaviour(checkout: Path) -> dict[str, Any]:
        return {
            "upstream": outcome(lambda: upstream.validate_artifact(repo_root=checkout, data_root=CANONICAL_DATA)),
            "downstream_legacy_default": outcome(lambda: downstream.validate_artifact(
                repo_root=checkout, data_root=CANONICAL_DATA, pin_authority=LEGACY)),
            "downstream_successor_authority": outcome(lambda: downstream.validate_artifact(
                repo_root=checkout, data_root=CANONICAL_DATA, pin_authority=SUCCESSOR)),
        }

    # The mounted configuration is the branch head against the canonical lake.
    canonical_behaviour = behaviour(ROOT)
    canonical_main_behaviour = behaviour(CANONICAL_REPO)

    def shape(result: dict[str, Any]) -> tuple[Any, ...]:
        return result["outcome"], result.get("by"), result.get("message"), json.dumps(result.get("value"), sort_keys=True)

    same_behaviour = {k: shape(isolated_after_rollback[k]) == shape(canonical_behaviour[k]) for k in canonical_behaviour}
    for rel, payload in activated.items():
        _bas_atomic.write_bytes(repo / rel, payload)
    reactivated = {"upstream": outcome(lambda: probe.up()), "downstream": outcome(lambda: probe.down())}
    children_after = {k: sha(v) for k, v in children.items()}
    complete = (rolled_back_digests == canonical_digests and all(same_behaviour.values())
                and reactivated == {"upstream": up_positive, "downstream": down_positive}
                and children_before == children_after and None not in children_after.values())
    return {
        "activation_files": list(ACTIVATION_FILES),
        "rollback_source": "the branch head's committed predecessor files, which the approval request binds",
        "rolled_back_digests": rolled_back_digests, "predecessor_digests_at_branch_head": canonical_digests,
        "predecessor_digests_on_canonical_main": canonical_main_digests,
        "rollback_restores_the_exact_predecessor_bytes": rolled_back_digests == canonical_digests,
        "isolated_after_rollback": isolated_after_rollback,
        "mounted_behaviour_branch_head_with_canonical_lake": canonical_behaviour,
        "rolled_back_copy_behaves_like_the_mounted_configuration": same_behaviour,
        "canonical_main_behaviour_informative": canonical_main_behaviour,
        "canonical_main_note": ("Canonical main predates the BAT-649 regeneration of the BAT-637 and corpus gates, so "
                                "its own Family B files are a self-consistent predecessor. The mounted failure is a "
                                "property of the branch head against the lake, which is what a rollback returns to."),
        "successor_children_left_unreferenced_not_deleted": children_before == children_after,
        "reactivated": reactivated,
        "reactivation_returns_the_same_identities": reactivated == {"upstream": up_positive, "downstream": down_positive},
        "complete": complete,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--isolated-root", type=Path, required=True)
    parser.add_argument("--seed-contract", type=Path, required=True)
    parser.add_argument("--seed", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        seed, contract = resolve_seed(SEED_CONTRACT_ID, explicit=args.seed, required_entries=("repo", "data"),
                                      contract_path=args.seed_contract)
        artifact = run(args.isolated_root, seed)
        artifact["seed_contract"] = {"path": str(args.seed_contract), "sha256": sha(args.seed_contract),
                                     "entry_digests_verified": True, "contract": contract}
    except Exception as error:  # noqa: BLE001 - the failure is the evidence
        artifact = {"label": LABEL, "cycle_number": 37, "attempt_number": 2,
                    "artifact_type": "CYCLE37_FAMILY_B_COMPOSED_QUALIFICATION", "state": "QUALIFICATION_FAILED",
                    "exception": type(error).__name__, "message": str(error)[:800],
                    "traceback_tail": traceback.format_exc()[-2000:], "qualified_in_isolation": False,
                    "canonical_activation": False, "hold_release": False}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(args.out_dir / "CYCLE37_FAMILY_B_COMPOSED_QUALIFICATION.json", 
        json.dumps(artifact, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    summary = {k: artifact.get(k) for k in ("state", "qualified_in_isolation", "clauses", "negative_controls_total",
                                            "negative_controls_rejected", "negative_controls_not_rejected",
                                            "controls_rejected_by_an_incidental_exception", "controls_not_restored")}
    summary["identities"] = {k: v["all_three_agree"] for k, v in (artifact.get("identity_agreement") or {}).items()}
    summary["independent_failed_checks"] = (artifact.get("independent_reconstruction") or {}).get("failed_checks")
    print(json.dumps(summary, indent=1, default=str))
    return 0 if artifact.get("qualified_in_isolation") else 1


if __name__ == "__main__":
    sys.exit(main())
