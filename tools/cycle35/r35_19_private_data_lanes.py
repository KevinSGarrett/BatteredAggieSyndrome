"""R35-19: execute the private-data readiness lanes, including the
partial and corrupt roots the packet had left NOT_RUN.

Cycle #35 closeout review (20260921T025300Z), section 1: "The current
packet marks PRIVATE_DATA_PARTIAL_ROOT and DETERMINISTIC_RELEASE_REPLAY as
NOT_RUN. Both are required local validation work. Implement the
partial/corrupt-root fixtures..."

`aggie_analytics.experimentation.walk_forward.private_payload_state`
distinguishes six distinct facts about the world -- no root, a root that
exists but is empty, a missing manifest, an unreadable manifest, a
manifest with only some payloads present, and every payload present. Each
must be observed against a real root rather than asserted.

The fixtures are built from the REAL mounted manifest so the partial case
is a genuine subset of the real declared payload set, not an invented
shape that happens to satisfy the code. No fixture ever copies a private
payload's bytes: the partial root links only the payload names that are
meant to be present and points the rest at paths that genuinely do not
exist, so nothing private leaves the lake.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.experimentation.walk_forward import (  # noqa: E402
    MANIFEST_RELATIVE,
    PAYLOAD_STATE_CORRUPT,
    PAYLOAD_STATE_EMPTY,
    PAYLOAD_STATE_MANIFEST_MISSING,
    PAYLOAD_STATE_MOUNTED,
    PAYLOAD_STATE_NO_ROOT,
    PAYLOAD_STATE_PARTIAL,
    REQUIRED_PAYLOADS,
    private_payload_state,
)

DEFAULT_DATA_ROOT = Path(r"C:\BatteredAggieSyndrome.data")


def observe_with_repo_root(root: Path | None, repo_root: Path) -> dict[str, Any]:
    state = private_payload_state(root, repo_root)
    return {
        "state": state["state"],
        "data_root": state.get("data_root"),
        "manifest_path": state.get("manifest_path"),
        "present_payloads": state.get("present_payloads"),
        "missing_payloads": state.get("missing_payloads"),
        "rebuild_possible": state.get("rebuild_possible"),
    }


def observe(root: Path | None) -> dict[str, Any]:
    state = private_payload_state(root, REPO_ROOT)
    return {
        "state": state["state"],
        "data_root": state.get("data_root"),
        "manifest_path": state.get("manifest_path"),
        "present_payloads": state.get("present_payloads"),
        "missing_payloads": state.get("missing_payloads"),
        "rebuild_possible": state.get("rebuild_possible"),
    }


def build_empty_root(base: Path) -> Path:
    root = base / "empty_root"
    root.mkdir(parents=True, exist_ok=True)
    return root


def build_manifest_missing_root(base: Path) -> Path:
    """A root with content but no manifest -- distinct from an empty one."""

    root = base / "manifest_missing_root"
    (root / "unrelated").mkdir(parents=True, exist_ok=True)
    (root / "unrelated" / "note.txt").write_text("not a manifest", encoding="utf-8")
    return root


def build_corrupt_root(base: Path, real_manifest: Path) -> Path:
    """A manifest that exists but cannot be parsed."""

    root = base / "corrupt_root"
    target = root / MANIFEST_RELATIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('{"payloads": [ this is not valid json', encoding="utf-8")
    return root


def build_partial_root(base: Path, real_manifest: Path, keep: int = 1) -> dict[str, Any]:
    """A manifest declaring the real payload set with only some present.

    Payload bytes are never copied. The payloads that are meant to be
    PRESENT are written as tiny placeholder files at the manifest's own
    declared relative paths; the rest keep their declared paths and are
    simply absent. That reproduces PAYLOADS_PARTIALLY_PRESENT exactly --
    the state is decided by resolving each declared path, not by the
    payload's contents.
    """

    root = base / "partial_root"
    manifest = json.loads(real_manifest.read_text(encoding="utf-8"))
    declared = [
        row for row in (manifest.get("payloads") or []) if str(row.get("name")) in REQUIRED_PAYLOADS
    ]
    present_names = [str(row.get("name")) for row in declared[:keep]]

    rewritten = []
    for row in manifest.get("payloads") or []:
        name = str(row.get("name"))
        new_row = dict(row)
        # Re-point every declared payload INSIDE the fixture root so the
        # fixture can never resolve back to a real private payload.
        new_row["path"] = f"payloads/{name}"
        rewritten.append(new_row)
    manifest["payloads"] = rewritten

    target = root / MANIFEST_RELATIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    payload_dir = root / "payloads"
    payload_dir.mkdir(parents=True, exist_ok=True)
    for name in present_names:
        (payload_dir / name).write_bytes(b"placeholder-not-real-payload-bytes")

    return {
        "root": root,
        "declared_required_payloads": sorted(REQUIRED_PAYLOADS),
        "placed_present": sorted(present_names),
        "intentionally_absent": sorted(set(REQUIRED_PAYLOADS) - set(present_names)),
        "payload_bytes_copied_from_the_lake": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument(
        "--fixture-dir",
        default="",
        help="Where to build the synthetic roots. Defaults to a fixtures/ "
        "directory inside --out-dir so they are inspectable afterwards.",
    )
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fixtures = Path(args.fixture_dir) if args.fixture_dir else out_dir / "fixtures"
    if fixtures.exists():
        shutil.rmtree(fixtures)
    fixtures.mkdir(parents=True, exist_ok=True)

    real_root = Path(args.data_root)
    real_manifest = real_root / MANIFEST_RELATIVE

    lanes: list[dict[str, Any]] = []

    # resolve_data_root walks a CANDIDATE LIST -- explicit, then the
    # AGGIE_ANALYTICS_DATA_ROOT env var, then
    # configs/external_storage_policy.json -- and skips any candidate that
    # is not a directory. So an explicit nonexistent path alone does NOT
    # produce NO_DATA_ROOT on this host: it falls through to the
    # policy-configured root, which is the real lake. That is correct
    # behaviour, and observing it required neutralising every candidate
    # rather than assuming the first one decides.
    policy_free_root = fixtures / "repo_without_storage_policy"
    (policy_free_root / "configs").mkdir(parents=True, exist_ok=True)
    lanes.append(
        {
            "lane": "PRIVATE_DATA_NO_ROOT",
            "expected_state": PAYLOAD_STATE_NO_ROOT,
            "observed": {
                **observe_with_repo_root(
                    Path("Z:/definitely/not/mounted"), policy_free_root
                )
            },
            "detail": "No candidate resolves: an absent explicit path, no "
            "AGGIE_ANALYTICS_DATA_ROOT in the environment, and a repo root "
            "carrying no external_storage_policy.json. This is the hosted-"
            "runner shape.",
            "candidate_sources_neutralised": [
                "explicit path (absent)",
                "AGGIE_ANALYTICS_DATA_ROOT (unset in this process)",
                "configs/external_storage_policy.json (absent in the probe root)",
            ],
        }
    )
    lanes.append(
        {
            "lane": "PRIVATE_DATA_EMPTY_ROOT",
            "expected_state": PAYLOAD_STATE_EMPTY,
            "observed": observe(build_empty_root(fixtures)),
            "detail": "A directory exists and is empty. Directory presence is "
            "not data availability.",
        }
    )
    lanes.append(
        {
            "lane": "PRIVATE_DATA_MANIFEST_MISSING_ROOT",
            "expected_state": PAYLOAD_STATE_MANIFEST_MISSING,
            "observed": observe(build_manifest_missing_root(fixtures)),
            "detail": "A root holding unrelated content but no manifest. "
            "Distinct from an empty root.",
        }
    )
    lanes.append(
        {
            "lane": "PRIVATE_DATA_CORRUPT_ROOT",
            "expected_state": PAYLOAD_STATE_CORRUPT,
            "observed": observe(build_corrupt_root(fixtures, real_manifest)),
            "detail": "A manifest that exists but cannot be parsed. An "
            "unreadable manifest must not read as an absent one.",
        }
    )

    if real_manifest.is_file():
        partial = build_partial_root(fixtures, real_manifest)
        lanes.append(
            {
                "lane": "PRIVATE_DATA_PARTIAL_ROOT",
                "expected_state": PAYLOAD_STATE_PARTIAL,
                "observed": observe(partial["root"]),
                "fixture": {
                    key: value for key, value in partial.items() if key != "root"
                },
                "detail": "A manifest declaring the real required payload set "
                "with only some payloads resolvable. Built from the real "
                "manifest so the subset is genuine; no private payload bytes "
                "are copied.",
            }
        )
        lanes.append(
            {
                "lane": "PRIVATE_DATA_MOUNTED",
                "expected_state": PAYLOAD_STATE_MOUNTED,
                "observed": observe(real_root),
                "detail": "The real mounted lake. The rebuild stays mandatory "
                "in this state.",
            }
        )
    else:
        lanes.append(
            {
                "lane": "PRIVATE_DATA_PARTIAL_ROOT",
                "expected_state": PAYLOAD_STATE_PARTIAL,
                "observed": None,
                "detail": f"NOT RUN: the real manifest is absent at "
                f"{real_manifest}, so a genuine partial subset of it cannot "
                "be constructed.",
            }
        )

    for lane in lanes:
        observed = lane.get("observed") or {}
        lane["matches_expected"] = observed.get("state") == lane["expected_state"]

    result = {
        "artifact_type": "CYCLE35_PRIVATE_DATA_LANE_RESULTS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "real_data_root": str(real_root),
        "real_manifest_present": real_manifest.is_file(),
        "real_manifest_sha256": hashlib.sha256(real_manifest.read_bytes()).hexdigest()
        if real_manifest.is_file()
        else None,
        "fixture_directory": str(fixtures),
        "lanes": lanes,
        "lane_count": len(lanes),
        "lanes_matching_expected": sum(1 for lane in lanes if lane["matches_expected"]),
        "lanes_not_matching": [
            lane["lane"] for lane in lanes if not lane["matches_expected"]
        ],
        "no_private_payload_bytes_were_copied": True,
        "directory_presence_is_not_data_availability": True,
    }
    (out_dir / "CYCLE35_PRIVATE_DATA_LANE_RESULTS.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "lanes": [
                    {
                        "lane": lane["lane"],
                        "expected": lane["expected_state"],
                        "observed": (lane.get("observed") or {}).get("state"),
                        "match": lane["matches_expected"],
                    }
                    for lane in lanes
                ],
                "lanes_not_matching": result["lanes_not_matching"],
            },
            indent=1,
        )
    )
    return 0 if not result["lanes_not_matching"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
