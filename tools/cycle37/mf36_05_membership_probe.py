r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

Reproduce MF36-05 against a chosen source tree, through the real prover.

MF36-05: "Membership proof ignores multiplicity and request authenticity. A
duplicate/reordered observed population and an invalid request identity
produce PROVED. Set equality is not declared exact row reproduction and a
cache filename is not an authenticated acquisition receipt."

Three probe families, each with a positive control beside it, because a
prover that refuses everything is not repaired:

* multiplicity -- a derivative whose rows are the transform's rows with one
  identifier repeated;
* order -- the transform's rows reversed, which no transformation in the
  table produces;
* request authenticity -- a receipt carrying a request identity that
  recomputes to nothing, and one carrying none at all.

A fourth family separates what a cache filename can attest from what a
declared attempt can, which MF36-05 names and which is a distinction rather
than a defect.

The probe imports the prover from ``--src`` and refuses to run if the import
did not bind there, so the same instrument measures the predecessor and the
repaired head.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


class _bas_atomic:  # U37-11: atomic writes once this tool has imported the package itself
    @staticmethod
    def _module():
        import sys as _bas_sys

        if "aggie_analytics" not in _bas_sys.modules:
            return None  # never bind the package from another tree before the tool does
        try:
            from aggie_analytics import atomic_io
        except ImportError:
            return None
        return atomic_io

    @classmethod
    def write_text(cls, path, *args, **kwargs):
        module = cls._module()
        return module.write_text(path, *args, **kwargs) if module else path.write_text(*args, **kwargs)

    @classmethod
    def write_bytes(cls, path, *args, **kwargs):
        module = cls._module()
        return module.write_bytes(path, *args, **kwargs) if module else path.write_bytes(*args, **kwargs)

    @classmethod
    def open_write(cls, path, *args, **kwargs):
        module = cls._module()
        return module.open_write(path, *args, **kwargs) if module else path.open(*args, **kwargs)


sys.dont_write_bytecode = True

ENDPOINT = "/teams"

#: The rows every probe starts from: three source rows, two of which the
#: declared transform keeps, in source order.
PAYLOAD = [
    {"id": 1, "classification": "fbs"},
    {"id": 2, "classification": "fcs"},
    {"id": 3, "classification": "iii"},
]
EXPECTED = ["1", "2"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()

    src = Path(args.src).resolve()
    sys.path.insert(0, str(src / "src"))
    for name in [m for m in sys.modules if m.startswith("aggie_analytics")]:
        del sys.modules[name]

    from aggie_analytics.cycle36 import membership_lineage as lineage

    origin = Path(lineage.__file__).resolve()
    if src not in origin.parents:
        raise SystemExit(f"import binding failed: membership_lineage -> {origin}")

    holder = tempfile.TemporaryDirectory()
    payload_path = Path(holder.name) / "payload.json"
    raw = json.dumps(PAYLOAD).encode("utf-8")
    _bas_atomic.write_bytes(payload_path, raw)
    digest = hashlib.sha256(raw).hexdigest()

    def canonical(value: Any) -> str:
        return hashlib.sha256(
            json.dumps(
                value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest()

    def authentic_identity(parameters: dict[str, Any]) -> str:
        """The identity the Cycle #30 ledger's cache-hit branch writes."""

        return canonical({"path": ENDPOINT, "parameters": parameters})

    has_basis = "identity_basis" in getattr(
        lineage.Receipt, "__dataclass_fields__", {}
    )

    def receipt(
        year: int,
        *,
        request_identity: str | None = "AUTHENTIC",
        basis: str | None = None,
        http_status: Any = 200,
        retrieved: str | None = "2026-09-09T18:08:43Z",
    ) -> Any:
        parameters = {"year": year}
        identity = (
            authentic_identity(parameters)
            if request_identity == "AUTHENTIC"
            else request_identity
        )
        fields: dict[str, Any] = dict(
            endpoint=ENDPOINT,
            parameters=parameters,
            declared_digest=digest,
            request_identity=identity,
            cached_path=str(payload_path),
            actual_digest=digest,
            retrieved_at_utc=retrieved,
            http_status=http_status,
            payload_rows=len(PAYLOAD),
        )
        if basis is not None and has_basis:
            fields["identity_basis"] = basis
        return lineage.Receipt(**fields)

    result: dict[str, Any] = {
        "label": args.label,
        "cycle_number": 37,
        "attempt_number": 2,
        "state": "ACTUAL_STATE",
        "requirement": "R37-04",
        "finding": "MF36-05",
        "source_tree": str(src),
        "lineage_module": str(origin),
        "lineage_version": getattr(lineage, "LINEAGE_VERSION", None),
        "receipt_carries_identity_basis": has_basis,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "probes": {},
    }

    def record(name: str, fn: Callable[[], Any], *, expectation: str) -> None:
        try:
            value = fn()
        except BaseException as error:  # noqa: BLE001 - a raise is an outcome
            result["probes"][name] = {
                "outcome": "RAISED",
                "error_type": type(error).__name__,
                "error": str(error)[:300],
                "expectation": expectation,
                "honours_expectation": expectation == "REFUSED",
            }
            return
        state = str(value.get("state"))
        proved = state.startswith("PROVED")
        result["probes"][name] = {
            "outcome": "PROVED" if proved else "REFUSED",
            "state": state,
            "bound_year": value.get("bound_year"),
            "expectation": expectation,
            "honours_expectation": proved if expectation == "PROVED" else not proved,
            "why": str(value.get("why") or "")[:400],
        }

    prove = lineage.prove_lineage
    transform = "TEAMS_FBS_FCS_V1"

    # ------------------------------------------------- positive controls
    record(
        "positive_exact_reproduction",
        lambda: prove(list(EXPECTED), [receipt(2026)], transform),
        expectation="PROVED",
    )
    record(
        "positive_same_year_twice",
        lambda: prove(list(EXPECTED), [receipt(2026), receipt(2026)], transform),
        expectation="PROVED",
    )

    # -------------------------------------------------------- multiplicity
    record(
        "duplicated_row_in_the_file",
        lambda: prove(["1", "1", "2"], [receipt(2026)], transform),
        expectation="REFUSED",
    )
    record(
        "every_row_duplicated",
        lambda: prove(["1", "2", "1", "2"], [receipt(2026)], transform),
        expectation="REFUSED",
    )

    # --------------------------------------------------------------- order
    record(
        "rows_reversed",
        lambda: prove(list(reversed(EXPECTED)), [receipt(2026)], transform),
        expectation="REFUSED",
    )

    # ------------------------------------------------ request authenticity
    record(
        "identity_is_an_arbitrary_string",
        lambda: prove(
            list(EXPECTED), [receipt(2026, request_identity="request-2026")], transform
        ),
        expectation="REFUSED",
    )
    record(
        "identity_is_a_plausible_digest_of_nothing",
        lambda: prove(
            list(EXPECTED), [receipt(2026, request_identity="f" * 64)], transform
        ),
        expectation="REFUSED",
    )
    record(
        "identity_belongs_to_a_different_year",
        lambda: prove(
            list(EXPECTED),
            [receipt(2026, request_identity=authentic_identity({"year": 2019}))],
            transform,
        ),
        expectation="REFUSED",
    )
    record(
        "identity_absent",
        lambda: prove(
            list(EXPECTED), [receipt(2026, request_identity=None)], transform
        ),
        expectation="REFUSED",
    )

    # ------------------------------------------ acquisition attestation
    record(
        "cache_filename_only",
        lambda: prove(
            list(EXPECTED),
            [
                receipt(
                    2026,
                    basis="RECONSTRUCTED_FROM_CACHE_FILENAME",
                    http_status=None,
                    retrieved=None,
                )
            ],
            transform,
        ),
        expectation="PROVED",
    )
    record(
        "declared_attempt_that_failed",
        lambda: prove(list(EXPECTED), [receipt(2026, http_status=500)], transform),
        expectation="PROVED",
    )

    probes = result["probes"]
    negatives = [name for name, row in probes.items() if row["expectation"] == "REFUSED"]
    positives = [name for name, row in probes.items() if row["expectation"] == "PROVED"]
    result["summary"] = {
        "negative_controls": len(negatives),
        "negative_controls_refused": sum(
            1 for name in negatives if probes[name].get("honours_expectation")
        ),
        "negative_controls_still_proved": sorted(
            name for name in negatives if not probes[name].get("honours_expectation")
        ),
        "positive_controls": len(positives),
        "positive_controls_proved": sum(
            1 for name in positives if probes[name].get("honours_expectation")
        ),
        "positive_controls_broken": sorted(
            name for name in positives if not probes[name].get("honours_expectation")
        ),
    }
    result["repaired"] = (
        not result["summary"]["negative_controls_still_proved"]
        and not result["summary"]["positive_controls_broken"]
    )
    # An attested and an unattested proof must be distinguishable, or the
    # third part of MF36-05 is unaddressed even when nothing is over-admitted.
    result["attestation_is_distinguishable"] = probes.get(
        "positive_exact_reproduction", {}
    ).get("state") != probes.get("cache_filename_only", {}).get("state")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(out, 
        json.dumps(result, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    holder.cleanup()

    summary = result["summary"]
    print("label                      :", args.label)
    print("lineage version            :", result["lineage_version"])
    print(
        "negative controls refused  :",
        f"{summary['negative_controls_refused']}/{summary['negative_controls']}",
    )
    print("still proved               :", summary["negative_controls_still_proved"] or "none")
    print(
        "positive controls proved   :",
        f"{summary['positive_controls_proved']}/{summary['positive_controls']}",
    )
    print("attestation distinguishable:", result["attestation_is_distinguishable"])
    print("repaired                   :", result["repaired"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
