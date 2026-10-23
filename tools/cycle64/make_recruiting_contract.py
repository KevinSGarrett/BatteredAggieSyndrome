r"""Generate, check or pin the national recruiting evidence data contract (BAT-735, Cycle #64 TP64-A01).

``python -B tools/cycle64/make_recruiting_contract.py --data-root <data> --frozen-at <YYYY-MM-DDTHH:MM:SSZ> --write``
writes ``configs/national_recruiting_evidence_2010_2017_contract.json`` from the original sources (the module's frozen
rules, every pinned input and the source key universe: requested cells, captures and the observation keys of every
recruiting array; no person, program, value or time decision) and regenerates the generated anchors block of
``src/aggie_analytics/personnel_evidence/recruiting.py`` from that contract.

``--check`` regenerates both in memory (the frozen-at time read from the committed contract) and exits 1 unless the
committed contract bytes and the module's anchors equal them.

``--profile <build receipt>`` pins RECRUITING_PROFILE from the first authorized canonical build's receipt (its content
and database identities, database SHA-256 and bytes, row and table counts and every table's lines digest); the contract
and anchors stay byte-identical and the receipt must name the pinned contract. Nothing here reads or writes canonical
data.
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

from aggie_analytics.personnel_evidence import recruiting as rc  # noqa: E402
from aggie_analytics.personnel_evidence import recruiting_build as rb  # noqa: E402

MODULE = ROOT / "src" / "aggie_analytics" / "personnel_evidence" / "recruiting.py"
CONTRACT = ROOT / rc.CONTRACT_REL
BEGIN = "# ---- BEGIN GENERATED ANCHORS (tools/cycle64/make_recruiting_contract.py; never hand edited) ----"
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
             "#: The pinned authority of the reader: the committed contract SHA-256, every pinned input (locator, "
             "relative path,",
             "#: SHA-256, bytes) and the source key universe (requested cells, captures, per-season observation counts "
             "and key",
             "#: digests) generated from the original sources before any qualification; never hand edited.",
             f"ANCHORS: dict[str, Any] = {_literal(anchors)}",
             "#: The canonical profile of the first authorized build (None until that build is pinned by --profile).",
             "RECRUITING_PROFILE: dict[str, Any] | None = " + ("None" if profile is None else _literal(profile)),
             END]
    return "\n".join(lines) + "\n"


def replace_block(text: str, block: str) -> str:
    start, end = text.index(BEGIN), text.index(END)
    return text[:start] + block + text[end + len(END) + 1:]


def contract_anchors(contract: dict[str, Any], contract_sha256: str) -> dict[str, Any]:
    return {"contract_id": contract["contract_id"], "contract_sha256": contract_sha256,
            **{key: contract[key] for key in rb.ANCHOR_KEYS}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--frozen-at")
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    parser.add_argument("--module", type=Path, default=MODULE)
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
        anchors = contract_anchors(contract, rc.sha256_bytes(raw))
        if receipt.get("contract_sha256") != anchors["contract_sha256"] or \
                receipt.get("state") not in ("MATERIALIZED", "ALREADY_PRESENT_IDENTICAL") or \
                receipt.get("rules_sha256") != rc.rules_sha256() or \
                not (receipt.get("reader_check") or {}).get("verified"):
            raise SystemExit("the receipt is not a verified build of the committed contract and rules")
        profile = {key: receipt[key] for key in PROFILE_KEYS}
        new_text = replace_block(module_text, anchors_block(anchors, profile))
        args.module.write_text(new_text, encoding="utf-8", newline="\n")
        print(json.dumps({"profile_pinned": profile["database_identity"], "contract_sha256": anchors["contract_sha256"]},
                         indent=1))
        return 0
    if not args.data_root:
        parser.error("--data-root is required to generate or check the contract")
    frozen = args.frozen_at
    if args.check and frozen is None:
        frozen = json.loads(args.contract.read_text(encoding="utf-8"))["frozen_at_utc"]
    if frozen is None:
        parser.error("--frozen-at is required with --write")
    try:
        contract = rb.make_contract(args.data_root, args.repo_root, frozen)
    except (rc.RecruitingError, rb.BuildRefused) as exc:
        print(json.dumps({"refused": exc.code, "error": str(exc)}), file=sys.stderr)
        return 2
    data = rb.contract_bytes(contract)
    anchors = contract_anchors(contract, rc.sha256_bytes(data))
    current_profile = rc.RECRUITING_PROFILE if args.module.resolve() == MODULE.resolve() else None
    block = anchors_block(anchors, current_profile)
    if args.check:
        committed = args.contract.read_bytes() if args.contract.is_file() else b""
        same_contract = committed == data
        start, end = module_text.index(BEGIN), module_text.index(END)
        committed_block = module_text[start:end + len(END) + 1]
        same_anchors = committed_block == block
        print(json.dumps({"contract_equal": same_contract, "anchors_equal": same_anchors,
                          "contract_sha256": anchors["contract_sha256"]}, indent=1))
        return 0 if same_contract and same_anchors else 1
    args.contract.parent.mkdir(parents=True, exist_ok=True)
    args.contract.write_bytes(data)
    args.module.write_text(replace_block(module_text, block), encoding="utf-8", newline="\n")
    print(json.dumps({"contract": str(args.contract), "contract_sha256": anchors["contract_sha256"],
                      "counts": contract["expected"]["counts"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
