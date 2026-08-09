from __future__ import annotations

import argparse
import json
import sys
sys.dont_write_bytecode = True
from datetime import datetime, timezone
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.packaging import build_cumulative, build_hydration
from tools.repo_integrity import (
    scan_forbidden, scan_secrets, sha256_file, validate_manifest,
    validate_required_structure, write_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic cumulative and hydration ZIPs for the current wave.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--wave", required=True, help="Wave token such as W02")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--previous-cumulative", type=Path)
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    identity = repo / "governance/PROJECT_IDENTITY.yaml"
    current_wave = None
    for line in identity.read_text(encoding="utf-8").splitlines():
        if line.startswith("current_wave:"):
            current_wave = line.split(":", 1)[1].strip().strip("'\"")
            break
    if current_wave != args.wave:
        raise SystemExit(f"Refusing to package {args.wave}: repository current_wave is {current_wave}")
    if args.wave != "W01" and not args.previous_cumulative:
        raise SystemExit("A previous cumulative ZIP is required for Wave 02+ packaging")
    write_manifest(repo)
    findings = validate_required_structure(repo) + scan_forbidden(repo) + scan_secrets(repo) + validate_manifest(repo)
    if findings:
        for finding in findings:
            print(f"FAIL {finding.kind}: {finding.path}: {finding.detail}")
        raise SystemExit("Repository validation failed before packaging")
    out = args.output_dir.resolve(); out.mkdir(parents=True, exist_ok=True)
    cumulative = out / f"Aggie_Analytics_Engine_{args.wave}_CUMULATIVE.zip"
    hydration = out / f"Aggie_Analytics_Engine_{args.wave}_HYDRATION.zip"
    cumulative_sha, file_count, fingerprint = build_cumulative(repo, cumulative)
    previous_sha = sha256_file(args.previous_cumulative) if args.previous_cumulative else None
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    binding = build_hydration(repo, cumulative, hydration, previous_sha, stamp)
    result = {
        "cumulative": str(cumulative),
        "cumulative_sha256": cumulative_sha,
        "hydration": str(hydration),
        "hydration_sha256": sha256_file(hydration),
        "repository_file_count": file_count,
        "repository_tree_fingerprint": fingerprint,
        "binding": binding,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
