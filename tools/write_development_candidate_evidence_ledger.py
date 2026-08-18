from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.experimentation.development_candidate_evidence_ledger import (  # noqa: E402
    materialize,
    validate_artifact,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Materialize the identity-bound development candidate evidence ledger."
    )
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    written = materialize(repo_root)
    validated = validate_artifact(repo_root=repo_root)
    print(json.dumps({**written, "validation": validated["result"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
