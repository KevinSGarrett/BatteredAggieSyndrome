"""Independent artifact/JSONL/code claim discovery.

Claims are identified by artifact + exact pointer/row identity + field +
population. Bare field names are not identity. Unreadable evidence fails.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from aggie_analytics.cycle30.hashing import sha256_json

CLAIM_FIELDS = (
    "claim_id",
    "artifact_path",
    "pointer",
    "row_identity",
    "field",
    "population",
    "value_class",
    "formula",
    "numerator",
    "denominator",
    "source_identities",
    "temporal_authority",
    "producer",
    "validator",
    "independent_reference",
    "dependencies",
    "trust_class",
)

NUMERIC_SUFFIXES = ("_count", "_rows", "_row_count", "_n", "_bytes")
STATUS_FIELDS = {
    "scientific_status",
    "row_verdict",
    "trust_class",
    "trust_classification",
    "classification",
    "state",
    "matrix_state",
    "evidence_class",
    "artifact_type",
    "artifact_class",
    "row_class",
    "evidence_type",
}
AUTHORITY_KEY_MARKERS = {
    "proven_pit_training_rows",
    "cycle30_kernel_trust_usable",
    "cycle29_kernel_trust_usable",
    "current_fitted_forecast_trust_recovered",
    "project_wide_scientific_trust_recovered",
    "scientific_trust_recovered",
    "unmapped_count",
    "all_cycle_trust_recovered",
    "primary_kernel_objective",
    "N",
    "attempted",
    "row_count",
}
SKIP_DISCOVERY_NAMES = {
    "CYCLE30_CLAIM_INVENTORY.json",
    "CYCLE30_MATERIALIZATION_MANIFEST.json",
    "CYCLE30_PREFLIGHT_AND_PRESERVATION.json",
}

CONTAINMENT = "CONTAINMENT"
SCIENCE = "SCIENCE"


class ClaimError(ValueError):
    """Raised when a claim cannot be inventoried."""


def require_mapped(claim: Mapping[str, Any]) -> None:
    missing = [field for field in CLAIM_FIELDS if field not in claim]
    if missing:
        raise ClaimError(f"unmapped authority-bearing claim fields: {missing}")


def claim_identity(claim: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(claim.get("artifact_path") or ""),
        str(claim.get("pointer") or ""),
        str(claim.get("row_identity") or ""),
        str(claim.get("field") or ""),
    )


def _value_class(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "null"
    return type(value).__name__


def _is_authority_key(key: str, value: Any) -> bool:
    if key in AUTHORITY_KEY_MARKERS or key in STATUS_FIELDS:
        return True
    if any(key.endswith(suffix) for suffix in NUMERIC_SUFFIXES):
        return isinstance(value, (int, float, bool)) or value is None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        lowered = str(key).lower()
        if any(
            token in lowered
            for token in (
                "count",
                "row",
                "edge",
                "opponent",
                "game",
                "byte",
                "score",
                "metric",
            )
        ) or lowered in {"n", "w"}:
            return True
    if isinstance(value, str) and value.upper() in {
        "VERIFIED",
        "PASS",
        "PROVEN",
        "PROVEN_PIT_TRAINING_ROW",
        "COMPLETE",
        "NATIONAL_ACQUISITION_ATTEMPTED_WITH_EXPLICIT_GAPS",
    }:
        return True
    return False


def _walk_json(
    payload: Any,
    pointer: str,
    found: list[dict[str, Any]],
    *,
    artifact: str,
) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            child = f"{pointer}/{key}" if pointer else f"/{key}"
            if _is_authority_key(str(key), value):
                found.append(
                    {
                        "artifact_path": artifact,
                        "pointer": child,
                        "row_identity": "",
                        "field": str(key),
                        "value": value,
                        "value_class": _value_class(value),
                        "population": artifact,
                    }
                )
            _walk_json(payload=value, pointer=child, found=found, artifact=artifact)
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            child = f"{pointer}/{index}"
            _walk_json(payload=item, pointer=child, found=found, artifact=artifact)


def _jsonl_row_identity(row: Mapping[str, Any], index: int) -> str:
    for key in (
        "canonical_game_id",
        "claim_id",
        "program_id",
        "predecessor_record_id",
        "record_id",
        "contest_id",
        "ncaa_contest_id",
        "object_id",
    ):
        if row.get(key) not in {None, ""}:
            return f"{key}={row[key]}"
    return f"line={index}"


def discover_authority_claims(
    art_dir: Path,
    declared: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Enumerate actual artifact/JSONL closure independently of declarations."""

    if not art_dir.exists():
        raise ClaimError(f"claim discovery directory missing: {art_dir}")
    discovered: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    files = sorted(
        path
        for path in art_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl"}
    )
    if not files:
        raise ClaimError("claim discovery produced no readable artifacts")
    for path in files:
        if path.name in SKIP_DISCOVERY_NAMES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ClaimError(f"unreadable evidence {path.name}: {exc}") from exc
        if path.suffix.lower() == ".jsonl":
            for index, line in enumerate(text.splitlines()):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ClaimError(
                        f"unreadable JSONL {path.name} line {index}: {exc}"
                    ) from exc
                if not isinstance(row, dict):
                    raise ClaimError(f"JSONL {path.name} line {index} is not an object")
                row_id = _jsonl_row_identity(row, index)
                for key, value in row.items():
                    if not _is_authority_key(str(key), value):
                        continue
                    pointer = f"/rows/{row_id}/{key}"
                    ident = (path.name, pointer, row_id, str(key))
                    if ident in seen:
                        raise ClaimError(f"duplicate claim pointer {ident}")
                    seen.add(ident)
                    discovered.append(
                        {
                            "artifact_path": path.name,
                            "pointer": pointer,
                            "row_identity": row_id,
                            "field": str(key),
                            "value": value,
                            "value_class": _value_class(value),
                            "population": path.name,
                        }
                    )
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ClaimError(f"unreadable JSON {path.name}: {exc}") from exc
        found: list[dict[str, Any]] = []
        _walk_json(payload, "", found, artifact=path.name)
        for item in found:
            ident = (
                item["artifact_path"],
                item["pointer"],
                item["row_identity"],
                item["field"],
            )
            if ident in seen:
                raise ClaimError(f"duplicate claim pointer {ident}")
            seen.add(ident)
            discovered.append(item)
    if not discovered:
        raise ClaimError("claim discovery produced no authority-bearing fields")
    declared = declared or []
    declared_idents = {claim_identity(row) for row in declared}
    if declared:
        for claim in declared:
            require_mapped(claim)
        for item in discovered:
            ident = (
                item["artifact_path"],
                item["pointer"],
                item["row_identity"],
                item["field"],
            )
            # Bare field name is not identity: same field on a different artifact
            # remains unmapped unless the exact pointer is declared.
            if ident not in declared_idents and not any(
                str(row.get("artifact_path")) == item["artifact_path"]
                and str(row.get("pointer")) == item["pointer"]
                and str(row.get("field")) == item["field"]
                for row in declared
            ):
                item["unmapped"] = True
            else:
                item["unmapped"] = False
    return discovered


def inventory_claims(
    declared: Sequence[Mapping[str, Any]],
    discovered: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if discovered is declared:
        raise ClaimError("discovered claims cannot be the producer's declared list")
    for claim in declared:
        require_mapped(claim)
    declared_idents = {claim_identity(row) for row in declared}
    if len(declared_idents) != len(declared):
        raise ClaimError("duplicate declared claim identities")
    unmapped = []
    for claim in discovered:
        ident = claim_identity(claim)
        field_only_match = any(
            str(row.get("field")) == ident[3]
            and str(row.get("artifact_path")) != ident[0]
            for row in declared
        )
        if ident not in declared_idents:
            # Wrong-artifact same-name matches are unmapped, not identity.
            unmapped.append({**dict(claim), "field_only_collision": field_only_match})
    if unmapped:
        raise ClaimError(
            f"unmapped numeric/status claims: {len(unmapped)}; gate fails closed"
        )
    return {
        "declared_count": len(declared),
        "discovered_count": len(discovered),
        "unmapped_count": 0,
        "inventory_identity": sha256_json([dict(row) for row in declared]),
        "all_cycle_project_wide_trust": False,
        "producer_cannot_write_unmapped_count": True,
    }


def reject_empty_science_pass(
    *,
    mode: str,
    producer_modules: Sequence[Path],
    reference_modules: Sequence[Path],
    bound_row_files: Sequence[Path],
    claimed_row_count: int,
) -> None:
    if mode != SCIENCE:
        return
    if not producer_modules:
        raise ClaimError("empty producer directory cannot pass scientific independence")
    if not reference_modules:
        raise ClaimError(
            "empty reference directory cannot pass scientific independence"
        )
    if claimed_row_count and not bound_row_files:
        raise ClaimError("missing external row file cannot establish scientific PASS")
    for path in bound_row_files:
        if not Path(path).is_file():
            raise ClaimError(f"bound scientific row file missing: {path}")
        if Path(path).stat().st_size == 0 and claimed_row_count:
            raise ClaimError("empty bound row file cannot support a nonzero claim")


def reject_vacuous_row_count(path: Path, claimed_rows: int) -> int:
    if claimed_rows < 0:
        raise ClaimError("negative row counts are invalid")
    if not path.is_file():
        if claimed_rows:
            raise ClaimError(
                f"claimed {claimed_rows} rows against missing file {path.name}"
            )
        return 0
    count = 0
    with path.open("rb") as handle:
        for line in handle:
            if line.strip():
                count += 1
    if count == 0 and claimed_rows not in {0}:
        raise ClaimError(f"claimed {claimed_rows} rows against empty file {path.name}")
    if count != claimed_rows:
        raise ClaimError(
            f"claimed {claimed_rows} rows disagrees with opened count {count}"
        )
    return count
