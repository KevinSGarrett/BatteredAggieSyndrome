"""Validate cross-output scientific coherence without producer helpers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.scientific_reference.coherence import (  # noqa: E402
    pair_normalize,
)


def validate_rows(rows: list[dict]) -> list[str]:
    findings: list[str] = []
    for index, row in enumerate(rows):
        result = pair_normalize(
            float(row["home_win_probability"]),
            float(row["away_win_probability"]),
            float(row["expected_margin_home"]),
            float(row["expected_margin_away"]),
        )
        if not result["coherent"]:
            findings.append(f"CROSS_OUTPUT_INCOHERENT:{index}:{result['abstain_reason']}")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", required=False)
    args = parser.parse_args(argv)
    findings: list[str] = []
    if args.payload:
        payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
        findings = validate_rows(payload.get("rows") or [])
    print(
        json.dumps(
            {
                "validator": "cross_output_coherence",
                "result": "PASS" if not findings else "FAIL",
                "findings": findings,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
