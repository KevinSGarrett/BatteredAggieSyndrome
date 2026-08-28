"""Score frozen 2026 shadow forecasts against official finals, or report their absence.

The scorer is deliberately separate from the producer. It reads the published
forecast gate, loads the frozen forecast payload by hash, and only then looks for
an official-final payload. It refuses an outcome observed before its forecast was
frozen or before kickoff, it scores nothing but official finals, and it has no
code path that could tune or promote a candidate.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.national_foundation_reconciliation import (  # noqa: E402
    binding_identity,
    sha256_file,
)
from aggie_analytics.data.prospective_shadow_cohort import iso_utc, parse_utc  # noqa: E402
from aggie_analytics.modeling.prospective_shadow_forecasts import (  # noqa: E402
    CONTRACT_RELATIVE,
    GATE_RELATIVE,
    SCORING_GATE_RELATIVE,
    build_scoring_gate,
    load_contract,
    load_official_finals,
    score_forecasts,
)


def write_json(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", type=Path, required=True)
    result.add_argument("--data-root", type=Path, required=True)
    result.add_argument(
        "--official-finals",
        type=Path,
        default=None,
        help="optional JSONL payload of official finals; absent means none exist yet",
    )
    result.add_argument("--issued-at-utc", required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    contract = load_contract(repo_root)
    gate = json.loads((repo_root / GATE_RELATIVE).read_text(encoding="utf-8-sig"))
    manifest_path = data_root / gate["manifest"]["relative_path"]
    if sha256_file(manifest_path) != gate["manifest"]["sha256"]:
        raise ValueError("forecast manifest hash drifted; refusing to score")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    entry = next(
        item
        for item in manifest["payloads"]
        if item["role"] == "PROSPECTIVE_2026_SHADOW_FORECAST_ROWS"
    )
    payload_path = data_root / entry["relative_path"]
    if sha256_file(payload_path) != entry["sha256"]:
        raise ValueError("frozen forecast payload hash drifted; refusing to score")
    forecasts = [
        json.loads(line)
        for line in payload_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    finals = load_official_finals(args.official_finals)
    scoring = score_forecasts(contract=contract, forecasts=forecasts, finals=finals)
    scoring_gate = build_scoring_gate(
        contract=contract,
        contract_sha256=sha256_file(repo_root / CONTRACT_RELATIVE),
        forecast_gate=gate,
        scoring=scoring,
        official_final_source=(
            str(args.official_finals) if args.official_finals else "NO_OFFICIAL_FINAL_PAYLOAD_SUPPLIED"
        ),
    )
    scoring_gate = {
        **scoring_gate,
        "scored_at_utc": iso_utc(parse_utc(args.issued_at_utc)),
        "producer": {"python": sys.version.split()[0], "platform": platform.platform()},
    }
    scoring_gate["gate_identity"] = binding_identity(scoring_gate, "gate_identity")
    write_json(repo_root / SCORING_GATE_RELATIVE, scoring_gate)
    print(
        json.dumps(
            {
                "result": scoring_gate["result"],
                "frozen_forecast_count": scoring_gate["frozen_forecast_count"],
                "official_final_count": scoring_gate["official_final_count"],
                "state_counts": scoring_gate["state_counts"],
                "metrics": scoring_gate["metrics"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
