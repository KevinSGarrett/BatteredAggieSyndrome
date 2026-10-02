"""Build the national Division I population 2016-2025 (BAT-710, Cycle #38 TP38-A01-02..07).

``python -B tools/build_national_di_population_2016_2025.py --stage program-season|contest|query-db
--contract configs/national_di_population_2016_2025_contract.json --data-root <lake>
--output-canonical-root <lake>/canonical/national_di_population_2016_2025
--output-manifest-root <lake>/manifests/national_di_population_2016_2025 --issued-at-utc <ISO8601Z>
--receipt <evidence path> [--program-season-manifest <m1 run_manifest.json>] [--contest-manifest <m2 run_manifest.json>]``

The builder refuses to run without the contract, reads the lake read-only, and writes only new content-addressed
stage roots (an existing identity with identical bytes is verified, never rewritten) and, at the query-db stage, the
new successor gate files under artifacts/. The receipt is a new file written once.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data import national_di_population as population  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--stage", required=True, choices=population.STAGES)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--output-canonical-root", required=True, type=Path)
    parser.add_argument("--output-manifest-root", required=True, type=Path)
    parser.add_argument("--issued-at-utc", required=True)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--program-season-manifest", type=Path, default=None)
    parser.add_argument("--contest-manifest", type=Path, default=None)
    args = parser.parse_args(argv)
    started = time.time()
    receipt: dict = {"stage": args.stage, "contract": str(args.contract), "data_root": str(args.data_root),
                     "issued_at_utc": args.issued_at_utc, "argv": sys.argv[1:] if argv is None else list(argv)}
    try:
        population.parse_instant(args.issued_at_utc)
        contract, contract_sha256 = population.load_contract(args.contract)
        receipt["contract_sha256"] = contract_sha256
        common = {"contract": contract, "contract_sha256": contract_sha256,
                  "canonical_root": args.output_canonical_root, "manifest_root": args.output_manifest_root,
                  "issued_at_utc": args.issued_at_utc}
        if args.stage == "program-season":
            result = population.run_program_season_stage(data_root=args.data_root, repo_root=REPO_ROOT, **common)
        elif args.stage == "contest":
            if args.program_season_manifest is None:
                raise population.PopulationRefused("UPSTREAM_MANIFEST_MISSING", "--program-season-manifest is required")
            result = population.run_contest_stage(data_root=args.data_root,
                                                  program_season_manifest=args.program_season_manifest, **common)
        else:
            if args.contest_manifest is None:
                raise population.PopulationRefused("UPSTREAM_MANIFEST_MISSING", "--contest-manifest is required")
            result = population.run_query_db_stage(contest_manifest=args.contest_manifest, repo_root=REPO_ROOT, **common)
        result = {k: v for k, v in result.items() if k != "identity_document"}
        receipt.update(result="PASS", **result)
        code = 0
    except population.PopulationRefused as exc:
        receipt.update(result="REFUSED", refusal=exc.code, error=str(exc))
        code = 2
    receipt["seconds"] = round(time.time() - started, 3)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    with args.receipt.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(receipt, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    print(json.dumps({k: receipt.get(k) for k in ("stage", "result", "identity", "state", "refusal", "seconds")}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
