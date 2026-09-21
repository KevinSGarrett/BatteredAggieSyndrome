"""Rejection-complete immutable union-integrity successor built from BAT-637 + Phase 1 ledger."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.data.ncaa_contest_reconciliation import sha256_file, stable_hash
from aggie_analytics.data.tamu_official_historical_boxscores import AuthorityViolation
from aggie_analytics.validation.artifact_binding import compute_identity

SCHEMA_VERSION = "aggie.data.tamu_official_gamebook_union_1998_rejection_complete.v1"
VALIDATION_CONTRACT_VERSION = SCHEMA_VERSION
CONTRACT_RELATIVE = "configs/tamu_official_gamebook_union_1998_rejection_complete_contract.json"
GATE_RELATIVE = "artifacts/data_lake/tamu_official_gamebook_union_1998_rejection_complete_gate.json"
CONTRACT_ID = "BAT-649-TAMU-OFFICIAL-1998-UNION-REJECTION-COMPLETE-V1"
DECISION_UNIT = "POST-TASK-SRC014-1998-2009-REJECTION-INTEGRITY-001"
JIRA_KEY = "BAT-649"
SOURCE_ID = "SRC-014"
PASS_CLASSIFICATION = "TAMU_OFFICIAL_GAMEBOOK_UNION_1998_REJECTION_COMPLETE_CANDIDATE_ONLY"
PASS_RESULT = "PASS_IMMUTABLE_REJECTION_COMPLETE_UNION_SUCCESSOR"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
#: The BAT-637 gate identity this consumer was originally pinned to. It
#: predates BAT-649 and no longer equals the live gate. It keeps its
#: historical name and value: a Done predecessor's recorded pin is not
#: edited, and it is not "corrected" by pasting the observed live hash
#: over it, which would destroy the evidence that the two ever differed.
PINNED_BAT637_GATE_IDENTITY = "c1d2220943342e02bd55efdac6bf3a4992f5fcd4a00059e94cc21ea56581db4a"
LEGACY_BAT637_GATE_IDENTITY = PINNED_BAT637_GATE_IDENTITY

#: The contract that DECLARES the successor's BAT-637 dependency. The
#: successor pin is derived from this declared authority at run time
#: rather than restated as another hardcoded constant -- restating it is
#: what let the predecessor's copy go stale unnoticed.
SUCCESSOR_CONTRACT_RELATIVE = (
    "configs/tamu_official_1998_2009_structured_row_corpus_contract.json"
)
SUCCESSOR_CONTRACT_PIN_FIELD = "pinned_bat637_gate_identity"
SUCCESSOR_CONTRACT_UNION_FIELD = "pinned_bat637_union_identity"

#: Which dependency version a caller is asking for. LEGACY reproduces the
#: canonical predecessor exactly, including its disagreement with the live
#: gate; SUCCESSOR derives the pin from declared contract authority. The
#: default stays LEGACY so importing this module can never silently
#: activate the successor: activation is a separate explicit approval, not
#: a side effect of a code change.
PIN_AUTHORITY_LEGACY = "LEGACY_MODULE_CONSTANT"
PIN_AUTHORITY_SUCCESSOR = "DECLARED_CONTRACT_AUTHORITY"

UNION_MANIFEST_NAME = "union_manifest.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _counts(gate637: Mapping[str, Any], ledger: Mapping[str, Any]) -> dict[str, int]:
    prior = dict(gate637.get("counts") or {})
    out = dict(prior)
    out["union_captured_games"] = int(prior.get("union_captured_games") or 0)
    out["union_target_games"] = int(prior.get("union_target_games") or out["union_captured_games"])
    out["rejected_urls_complete"] = int(ledger.get("complete_rejection_count") or 0)
    out["unmatched_rejected"] = int(ledger.get("active_rejection_count") or len(ledger.get("active_rejections") or []))
    out["ncaa_contest_ids_created"] = 0
    return out


def resolve_bat637_pin(
    *, repo_root: Path, pin_authority: str = PIN_AUTHORITY_LEGACY
) -> dict[str, Any]:
    """The BAT-637 gate identity this run requires, and where it came from.

    LEGACY returns the module's own historical constant. SUCCESSOR reads
    the contract that declares the dependency. A contract declaring no pin,
    or a malformed one, is an authority violation rather than a silent
    fallback to the stale value.
    """

    if pin_authority == PIN_AUTHORITY_LEGACY:
        return {
            "gate_identity": LEGACY_BAT637_GATE_IDENTITY,
            "pin_authority": PIN_AUTHORITY_LEGACY,
            "declared_by": "module constant PINNED_BAT637_GATE_IDENTITY",
            "union_identity": None,
        }
    if pin_authority != PIN_AUTHORITY_SUCCESSOR:
        raise AuthorityViolation(f"unknown BAT-637 pin authority: {pin_authority}")

    contract_path = repo_root / SUCCESSOR_CONTRACT_RELATIVE
    if not contract_path.is_file():
        raise AuthorityViolation(
            f"declared BAT-637 authority contract is absent: {contract_path}"
        )
    declared_contract = load_json(contract_path)
    declared = str(declared_contract.get(SUCCESSOR_CONTRACT_PIN_FIELD) or "")
    if len(declared) != 64 or any(ch not in "0123456789abcdef" for ch in declared):
        raise AuthorityViolation(
            "declared BAT-637 gate identity missing or malformed in "
            f"{SUCCESSOR_CONTRACT_RELATIVE}"
        )
    return {
        "gate_identity": declared,
        "pin_authority": PIN_AUTHORITY_SUCCESSOR,
        "declared_by": f"{SUCCESSOR_CONTRACT_RELATIVE}:{SUCCESSOR_CONTRACT_PIN_FIELD}",
        "union_identity": str(
            declared_contract.get(SUCCESSOR_CONTRACT_UNION_FIELD) or ""
        )
        or None,
    }


def reconstruct_objects(
    *,
    repo_root: Path,
    data_root: Path,
    pin_authority: str = PIN_AUTHORITY_LEGACY,
) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    gate637 = load_json(repo_root / "artifacts/data_lake/tamu_official_gamebook_union_1998_expanded_gate.json")
    resolved_pin = resolve_bat637_pin(repo_root=repo_root, pin_authority=pin_authority)
    required_pin = resolved_pin["gate_identity"]
    observed_pin = str(gate637.get("gate_identity") or "")
    if observed_pin != required_pin:
        raise AuthorityViolation(
            "BAT-637 gate identity drifted: the live gate is "
            f"{observed_pin or '<absent>'} but the {resolved_pin['pin_authority']} "
            f"pin requires {required_pin} (declared by {resolved_pin['declared_by']})"
        )
    # A successor run must also agree with the declared union identity when
    # the contract states one, so a gate matching on one field while
    # disagreeing on the other cannot pass as a consistent dependency.
    declared_union = resolved_pin.get("union_identity")
    if declared_union and str(gate637.get("union_identity") or "") != declared_union:
        raise AuthorityViolation(
            "BAT-637 union identity does not match the declared successor "
            f"dependency {declared_union}"
        )
    rejection_gate = load_json(repo_root / "artifacts/data_lake/tamu_official_1998_2009_rejection_integrity_gate.json")
    rejection_gate_identity = str(rejection_gate.get("gate_identity") or "")
    rejection_ledger_identity = str(rejection_gate.get("ledger_identity") or "")
    if not rejection_gate_identity:
        raise AuthorityViolation("rejection-integrity gate identity missing")
    if not rejection_ledger_identity:
        raise AuthorityViolation("rejection ledger identity missing")
    ledger_path = (
        data_root
        / "features/tamu_official_1998_2009_rejection_integrity/sha256"
        / rejection_ledger_identity
        / "rejection_ledger.json"
    )
    if not ledger_path.is_file():
        raise AuthorityViolation("external rejection ledger missing")
    ledger = load_json(ledger_path)
    if ledger.get("ledger_identity") != rejection_ledger_identity:
        raise AuthorityViolation("external rejection ledger drifted")
    games = list(gate637.get("enriched_official_games") or [])
    counts = _counts(gate637, ledger)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "predecessor_union_identity": str(gate637.get("union_identity") or ""),
        "predecessor_gate_identity": required_pin,
        "rejection_integrity_gate_identity": rejection_gate_identity,
        "rejection_ledger_identity": rejection_ledger_identity,
        "rejection_ledger_sha256": sha256_file(ledger_path),
        "enriched_official_games": games,
        "complete_rejection_ledger": list(ledger.get("complete_rejection_ledger") or []),
        "admitted_row_gap_urls": list(ledger.get("admitted_row_gap_urls") or []),
        "counts": counts,
        "protected_lane": PROTECTED_LANE,
        "authority": {
            "availability_established": False,
            "historical_known_at_established": False,
            "ncaa_contest_ids_created": 0,
            "participation_as_availability": False,
        },
    }
    payload["union_identity"] = stable_hash(
        {
            "predecessor_union_identity": payload["predecessor_union_identity"],
            "rejection_ledger_identity": payload["rejection_ledger_identity"],
            "admitted_urls": [str(item.get("url") or "") for item in games],
            "rejected_urls": [str(item.get("url") or "") for item in payload["complete_rejection_ledger"]],
            "counts": counts,
        }
    )
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "TAMU_OFFICIAL_GAMEBOOK_UNION_1998_REJECTION_COMPLETE_GATE",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "decision_unit": DECISION_UNIT,
        "jira_key": JIRA_KEY,
        "source_id": SOURCE_ID,
        "disposition": "NEW_IMMUTABLE_REJECTION_COMPLETE_UNION_SUCCESSOR",
        "validation_contract_version": VALIDATION_CONTRACT_VERSION,
        "predecessor_union_identity": payload["predecessor_union_identity"],
        "predecessor_gate_identity": required_pin,
        "rejection_integrity_gate_identity": rejection_gate_identity,
        "rejection_ledger_identity": rejection_ledger_identity,
        "union_identity": payload["union_identity"],
        "counts": counts,
        "admitted_row_gap_urls": payload["admitted_row_gap_urls"],
        "protected_lane": PROTECTED_LANE,
        "upstream_identities": {
            "bat637_gate_identity": required_pin,
            "rejection_integrity_gate_identity": rejection_gate_identity,
            "rejection_ledger_identity": rejection_ledger_identity,
        },
    }
    gate["gate_identity"] = compute_identity(gate, "gate_identity")
    payload["gate_identity"] = gate["gate_identity"]
    root = data_root / contract["payloads"]["union_root"] / payload["union_identity"]
    return {"contract": contract, "payload": payload, "gate": gate, "manifest_path": root / UNION_MANIFEST_NAME}


def materialize_union(
    *,
    repo_root: Path,
    data_root: Path,
    pin_authority: str = PIN_AUTHORITY_LEGACY,
) -> dict[str, Any]:
    objects = reconstruct_objects(
        repo_root=repo_root, data_root=data_root, pin_authority=pin_authority
    )
    write_json(objects["manifest_path"], objects["payload"])
    write_json(repo_root / GATE_RELATIVE, objects["gate"])
    return {
        "gate_identity": objects["gate"]["gate_identity"],
        "union_identity": objects["payload"]["union_identity"],
        "manifest_path": str(objects["manifest_path"]),
    }


def validate_artifact(
    *,
    repo_root: Path,
    data_root: Path,
    gate: Mapping[str, Any] | None = None,
    pin_authority: str = PIN_AUTHORITY_LEGACY,
) -> dict[str, Any]:
    committed = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    expected = reconstruct_objects(
        repo_root=repo_root, data_root=data_root, pin_authority=pin_authority
    )
    if committed != expected["gate"]:
        raise AuthorityViolation("committed rejection-complete union gate does not match independent reconstruction")
    if committed.get("gate_identity") != compute_identity(committed, "gate_identity"):
        raise AuthorityViolation("gate identity does not recompute")
    if not expected["manifest_path"].is_file():
        raise AuthorityViolation("external rejection-complete union manifest missing")
    if load_json(expected["manifest_path"]) != expected["payload"]:
        raise AuthorityViolation("external rejection-complete union manifest mismatch")
    return {"result": "PASS", "gate_identity": committed["gate_identity"], "union_identity": committed["union_identity"]}


def default_data_root() -> Path:
    return Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
