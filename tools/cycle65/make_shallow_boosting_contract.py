r"""Generate, check or pin the national frozen shallow-tree comparison contract (BAT-736, Cycle #65 TP65-A01).

``python -B tools/cycle65/make_shallow_boosting_contract.py --parent-database <accepted C56 sqlite>
--expect-parent-sha256 <issued SHA-256> --frozen-at <YYYY-MM-DDTHH:MM:SSZ> --write`` writes
``configs/national_shallow_boosting_comparison_2016_2023_contract.json`` from the module's frozen rules and the exact
parent alone (its pin: byte count, SHA-256, identities, schema, contract, record counts, total decompressed bytes and
model digests; and the expected key inventory of every table derived from its witness collections; no fit, no estimate
and no score recomputation) and regenerates the generated anchors block of
``src/aggie_analytics/retrospective_baseline/boosting_comparison.py`` from that contract.

``--check`` regenerates both in memory (the frozen-at time read from the committed contract) and exits 1 unless the
committed contract bytes and the module's anchors equal them (and, once a profile is pinned, the gate equals it).

``--profile <build receipt>`` pins BOOSTING_PROFILE from the first authorized canonical build's receipt (its content and
database identities, database SHA-256 and bytes, row and table counts and every table's lines digest) and writes the
same profile into the gate artifact ``artifacts/data_lake/national_shallow_boosting_comparison_2016_2023_gate.json``;
the contract and anchors stay byte-identical and the receipt must name the pinned contract. Nothing here reads or writes
canonical data of the new release.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.retrospective_baseline import boosting_build as bb  # noqa: E402
from aggie_analytics.retrospective_baseline import boosting_comparison as bc  # noqa: E402

MODULE = ROOT / "src" / "aggie_analytics" / "retrospective_baseline" / "boosting_comparison.py"
CONTRACT = ROOT / bc.CONTRACT_REL
GATE = ROOT / "artifacts" / "data_lake" / "national_shallow_boosting_comparison_2016_2023_gate.json"
GATE_SCHEMA = "BAS-SHALLOW-BOOSTING-COMPARISON-GATE-1"
BEGIN = "# ---- BEGIN GENERATED ANCHORS (tools/cycle65/make_shallow_boosting_contract.py; never hand edited) ----"
END = "# ---- END GENERATED ANCHORS ----"
PROFILE_KEYS = ("content_identity", "database_identity", "database_sha256", "database_bytes", "contract_sha256",
                "rules_sha256", "row_counts", "table_counts", "lines_sha256")


def _literal(value: Any) -> str:
    text = json.dumps(value, indent=1, sort_keys=True, ensure_ascii=True)
    if "'''" in text or text.endswith("\\"):
        raise SystemExit("the generated JSON cannot be embedded as a raw triple-quoted literal")
    return "json.loads(r'''" + text + "''')"


def anchors_block(anchors: dict[str, Any], profile: dict[str, Any] | None) -> str:
    lines = [BEGIN,
             "#: The pinned authority of the reader: the committed contract SHA-256, the exact accepted C56 parent "
             "(bytes, SHA-256,",
             "#: identities, witness counts and digests) and the expected key inventory generated from that parent "
             "before any fit.",
             f"ANCHORS: dict[str, Any] = {_literal(anchors)}",
             "#: The canonical profile of the first authorized build (None until that build is pinned by --profile).",
             "BOOSTING_PROFILE: dict[str, Any] | None = " + ("None" if profile is None else _literal(profile)),
             END]
    return "\n".join(lines) + "\n"


def replace_block(text: str, block: str) -> str:
    start, end = text.index(BEGIN), text.index(END)
    return text[:start] + block + text[end + len(END) + 1:]


def contract_anchors(contract: dict[str, Any], contract_sha256: str) -> dict[str, Any]:
    return {"contract_id": contract["contract_id"], "contract_sha256": contract_sha256,
            **{key: contract[key] for key in bb.ANCHOR_KEYS}}


def gate_bytes(anchors: dict[str, Any], profile: dict[str, Any]) -> bytes:
    """The gate artifact of a pinned release: the identities and counts of the canonical profile (never values)."""
    doc = {"schema": GATE_SCHEMA, "population": bc.POPULATION, "contract_id": anchors["contract_id"],
           "contract_sha256": anchors["contract_sha256"], "profile": profile, "labels": bc.LABELS,
           "parent": {"database_identity": anchors["parent"]["database_identity"],
                      "sqlite_sha256": anchors["parent"]["sqlite_sha256"]},
           "state": "CREATE_ONLY_RELEASE_PINNED_RETROSPECTIVE_RESEARCH_UNTRUSTED_SHADOW_PIT_NOT_ADMITTED",
           "statement": "The first authorized canonical build's content and database identities, database SHA-256 and "
                        "bytes, row and table counts and lines digests, pinned after that build; the release (with "
                        "its embedded byte-exact C56 parent) stays in the private data root outside Git; no record "
                        "value, PIT admission, forecast, skill, champion or activation."}
    return (json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--parent-database", type=Path)
    parser.add_argument("--expect-parent-sha256")
    parser.add_argument("--frozen-at")
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    parser.add_argument("--module", type=Path, default=MODULE)
    parser.add_argument("--gate", type=Path, default=GATE)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--profile", type=Path)
    args = parser.parse_args(argv)
    module_text = args.module.read_text(encoding="utf-8")
    if args.profile is not None:
        raw = args.contract.read_bytes()
        contract = json.loads(raw.decode("utf-8"))
        receipt = json.loads(args.profile.read_text(encoding="utf-8"))
        anchors = contract_anchors(contract, bc.sha256_bytes(raw))
        if receipt.get("contract_sha256") != anchors["contract_sha256"] or \
                receipt.get("state") not in ("MATERIALIZED", "ALREADY_PRESENT_IDENTICAL") or \
                receipt.get("rules_sha256") != bc.rules_sha256() or \
                not (receipt.get("reader_check") or {}).get("verified"):
            raise SystemExit("the receipt is not a verified build of the committed contract and rules")
        profile = {key: receipt[key] for key in PROFILE_KEYS}
        args.module.write_text(replace_block(module_text, anchors_block(anchors, profile)), encoding="utf-8",
                               newline="\n")
        args.gate.parent.mkdir(parents=True, exist_ok=True)
        args.gate.write_bytes(gate_bytes(anchors, profile))
        print(json.dumps({"profile_pinned": profile["database_identity"], "contract_sha256": anchors["contract_sha256"]},
                         indent=1))
        return 0
    if not args.parent_database or not args.expect_parent_sha256:
        parser.error("--parent-database and --expect-parent-sha256 are required to generate or check the contract")
    frozen = args.frozen_at
    if args.check and frozen is None:
        frozen = json.loads(args.contract.read_text(encoding="utf-8"))["frozen_at_utc"]
    if frozen is None:
        parser.error("--frozen-at is required with --write")
    try:
        contract = bb.make_contract(args.parent_database, frozen, expect_parent_sha256=args.expect_parent_sha256)
    except bb.BuildRefused as exc:
        print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
        return 2
    data = bb.contract_bytes(contract)
    anchors = contract_anchors(contract, bc.sha256_bytes(data))
    current_profile = bc.BOOSTING_PROFILE if args.module.resolve() == MODULE.resolve() else None
    block = anchors_block(anchors, current_profile)
    if args.check:
        committed = args.contract.read_bytes() if args.contract.is_file() else b""
        same_contract = committed == data
        start, end = module_text.index(BEGIN), module_text.index(END)
        same_anchors = module_text[start:end + len(END) + 1] == block
        same_gate = current_profile is None or (args.gate.is_file() and
                                                args.gate.read_bytes() == gate_bytes(anchors, current_profile))
        print(json.dumps({"contract_equal": same_contract, "anchors_equal": same_anchors, "gate_equal": same_gate,
                          "contract_sha256": anchors["contract_sha256"]}, indent=1))
        return 0 if same_contract and same_anchors and same_gate else 1
    args.contract.parent.mkdir(parents=True, exist_ok=True)
    args.contract.write_bytes(data)
    args.module.write_text(replace_block(module_text, block), encoding="utf-8", newline="\n")
    print(json.dumps({"contract": str(args.contract), "contract_sha256": anchors["contract_sha256"],
                      "counts": contract["expected"]["counts"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
