from __future__ import annotations

import argparse
import json
import sys
sys.dont_write_bytecode = True
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.packaging import safe_extract, verify_prior_pair


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a prior cumulative/hydration pair before mutation.")
    parser.add_argument("--hydration", type=Path, required=True)
    parser.add_argument("--cumulative", type=Path, required=True)
    parser.add_argument("--expected-next-wave")
    parser.add_argument("--extract-to", type=Path)
    args = parser.parse_args()
    binding = verify_prior_pair(args.hydration, args.cumulative, args.expected_next_wave)
    if args.extract_to:
        safe_extract(args.cumulative, args.extract_to)
    print(json.dumps({
        "status": "PASS",
        "wave": binding["wave"],
        "next_wave": binding["next_wave"],
        "cumulative_sha256": binding["cumulative_zip_sha256"],
        "extracted_to": str(args.extract_to) if args.extract_to else None,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
