"""CLI for the normalized latest-head review gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.governance.normalized_review_gate import (  # noqa: E402
    evaluate_latest_head_checks,
)


def load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", type=Path, required=True)
    args = parser.parse_args(argv)
    payload = load_payload(args.payload)
    result = evaluate_latest_head_checks(
        head_sha=str(payload.get("head_sha") or ""),
        checks=list(payload.get("checks") or []),
        required_names=tuple(
            payload.get("required_names") or ("codex-review", "codecov/patch")
        ),
    )
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
