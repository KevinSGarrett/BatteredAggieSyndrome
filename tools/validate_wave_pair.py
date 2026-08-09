from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
sys.dont_write_bytecode = True
import tempfile
import zipfile
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.packaging import safe_extract, safe_zip_names, verify_prior_pair
from tools.repo_integrity import sha256_file, validate_manifest

REQUIRED_HYDRATION = {
    "HYDRATE_FIRST.md", "PROJECT_IDENTITY.yaml", "CURRENT_STATE.yaml", "WAVE_PLAN.md",
    "WAVE_LEDGER.md", "NEXT_WAVE.md", "REQUIREMENTS_INDEX.csv", "REQUIREMENTS_TRACEABILITY.csv",
    "DECISION_LEDGER.md", "ADR_INDEX.csv", "IMMUTABLE_RULES.md", "DO_NOT_DRIFT.md",
    "SOURCE_OF_TRUTH_MAP.md", "SUPERSEDED_DECISIONS.md", "CURRENT_BACKLOG.yaml",
    "OPPORTUNITY_BACKLOG.yaml", "OPEN_ISSUES.md", "RISKS.md", "ASSUMPTIONS.md",
    "ADAPTIVE_CHANGE_LOG.md", "ASSUMPTION_CHALLENGE_LOG.md", "WAVE_PLAN_REVISIONS.md",
    "ACCEPTANCE_STATUS.json", "CURRENT_TREE.txt", "PROJECT_FILE_MANIFEST.csv",
    "PROJECT_FILE_HASHES.sha256", "CHANGELOG_SINCE_WAVE_01.md", "PACK_BINDING.json",
    "HYDRATION_FILE_HASHES.sha256"
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a completed wave cumulative/hydration pair.")
    parser.add_argument("--cumulative", type=Path, required=True)
    parser.add_argument("--hydration", type=Path, required=True)
    parser.add_argument("--expected-wave", required=True)
    args = parser.parse_args()
    safe_zip_names(args.cumulative); safe_zip_names(args.hydration)
    with zipfile.ZipFile(args.hydration) as hz:
        names=set(hz.namelist())
        missing=sorted(REQUIRED_HYDRATION-names)
        if missing: raise SystemExit(f"FAIL hydration missing: {missing}")
        binding=json.loads(hz.read("PACK_BINDING.json"))
        if binding["wave"] != args.expected_wave: raise SystemExit("FAIL binding wave mismatch")
        if sha256_file(args.cumulative) != binding["cumulative_zip_sha256"]: raise SystemExit("FAIL cumulative binding hash")
        # validate hydration hash list
        listed={}
        for line in hz.read("HYDRATION_FILE_HASHES.sha256").decode().splitlines():
            if line.strip():
                h,n=line.split("  ",1); listed[n]=h
        for n,h in listed.items():
            if hashlib.sha256(hz.read(n)).hexdigest()!=h: raise SystemExit(f"FAIL hydration hash: {n}")
    with tempfile.TemporaryDirectory(prefix="aggie_pair_validate_") as td:
        safe_extract(args.cumulative, Path(td))
        roots=[p for p in Path(td).iterdir() if p.is_dir()]
        if len(roots)!=1: raise SystemExit("FAIL cumulative must contain one root directory")
        findings=validate_manifest(roots[0])
        if findings: raise SystemExit(f"FAIL cumulative manifest: {findings[:3]}")
    print(json.dumps({
        "status":"PASS",
        "wave":args.expected_wave,
        "cumulative_sha256":sha256_file(args.cumulative),
        "hydration_sha256":sha256_file(args.hydration),
        "hydration_required_files":len(REQUIRED_HYDRATION)
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
