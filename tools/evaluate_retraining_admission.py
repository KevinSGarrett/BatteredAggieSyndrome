from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.repo_root.resolve() / "src"))
    from aggie_analytics.validation.retraining_admission import canonical_json, decide, validate_decision

    request = json.loads(args.request.read_text(encoding="utf-8"))
    decision = decide(request)
    failures = validate_decision(decision)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(decision) + b"\n")
    print(json.dumps({"result": "PASS" if not failures else "FAIL", "action": decision["action"], "decision_identity": decision["decision_identity"], "output": str(args.output.resolve()), "failures": failures}, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
