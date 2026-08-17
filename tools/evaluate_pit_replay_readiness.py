from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.validation.pit_replay_readiness import (  # noqa: E402
    compute_artifact_identity,
    validate_readiness_artifact,
    write_readiness_artifact,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="BAT-401 PIT/replay readiness gate")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    output = args.output
    if output is None:
        output = repo_root / "artifacts" / "pit" / "PIT_REPLAY_READINESS.json"
    elif not output.is_absolute():
        output = repo_root / output
    if args.validate_only:
        payload = json.loads(output.read_text(encoding="utf-8"))
        validate_readiness_artifact(payload, repo_root)
        if payload.get("artifact_identity") != compute_artifact_identity(payload):
            raise SystemExit("artifact identity mismatch")
        print(f"PASS validate-only identity={payload['artifact_identity']} lane={payload['lane_decision']}")
        return 0
    payload = write_readiness_artifact(repo_root, output)
    print(
        json.dumps(
            {
                "issue_status": payload["issue_status"],
                "lane_decision": payload["lane_decision"],
                "artifact_identity": payload["artifact_identity"],
                "output": str(output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
