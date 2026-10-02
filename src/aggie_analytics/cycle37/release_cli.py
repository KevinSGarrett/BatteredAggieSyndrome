r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

The release-build command line, inside the package so a clean installed wheel
can build the release (R35-03: "clean isolated wheel builds this release from
receipts"). Run it as ``python -I -m aggie_analytics.cycle37.release_cli``;
tools/cycle37/build_corrected_release.py is a thin wrapper around it.

Build the corrected national release (R37-07) as a content-addressed
successor to the delivered Cycle 36 release, and prove the build is
deterministic by replaying it into a second root.

The predecessor is opened read-only and immutable and is never modified. Its
digest is checked against the one the manager recorded and every declared
source file is rehashed before a row is read; a tampered or missing input
fails the build closed.

Output goes under the attempt's own packaging root, addressed by the content
identity of its declared scientific tables so two honest replays land on the
same identity.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aggie_analytics.cycle37 import corrected_release
from aggie_analytics.cycle37.corrected_release import (
    CorrectedReleaseError,
    replay_and_compare,
)
from aggie_analytics import atomic_io as _bas_atomic

DEFAULT_PREDECESSOR = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle36\runs\20260921T200027Z"
    r"\implementation_output\release_c36_r1\CYCLE36_NATIONAL_RELEASE.sqlite"
)
DEFAULT_PREDECESSOR_SHA256 = (
    "beabfe4ddff771bd694dfd7370380380c25a63b640478c2f89bbf640b2044a77"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def builder_provenance() -> dict[str, Any]:
    """Which code actually built the release: file, interpreter, distribution, isolation."""

    try:
        distribution = importlib.metadata.distribution("aggie-analytics-engine")
        installed = {"name": distribution.metadata["Name"], "version": distribution.version,
                     "location": str(distribution.locate_file(""))}
    except importlib.metadata.PackageNotFoundError:
        installed = None
    return {
        "cli_module_file": str(Path(__file__).resolve()),
        "corrected_release_module_file": str(Path(corrected_release.__file__).resolve()),
        "executable": sys.executable,
        "isolated_mode": bool(sys.flags.isolated),
        "no_user_site": bool(sys.flags.no_user_site),
        "cwd": os.getcwd(),
        "pythonpath": os.environ.get("PYTHONPATH"),
        "installed_distribution": installed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predecessor", type=Path, default=DEFAULT_PREDECESSOR)
    parser.add_argument("--predecessor-sha256", default=DEFAULT_PREDECESSOR_SHA256)
    parser.add_argument("--crosswalk", type=Path, required=True)
    parser.add_argument("--crosswalk-rows", type=Path, required=True)
    parser.add_argument("--build-root", type=Path, required=True)
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--staff-rows", type=Path, default=None,
                        help="R37-03 reparse rows; rebuilds the staff tables (v37.2)")
    parser.add_argument("--user-lineage", type=Path, default=None,
                        help="R37-07 user-corpus cell lineage rows (JSONL)")
    parser.add_argument("--user-lineage-summary", type=Path, default=None,
                        help="R37-07 lineage summary carrying the source-rights binding")
    parser.add_argument("--successor-table", action="append", default=[], metavar="NAME=PATH",
                        help="carry a successor JSONL ledger as its own table beside the predecessor's")
    parser.add_argument(
        "--skip-source-verification",
        action="store_true",
        help="Only for a rebuild whose inputs were verified moments earlier; "
             "recorded in the receipt when used.",
    )
    args = parser.parse_args(argv)

    crosswalk = json.loads(args.crosswalk.read_text(encoding="utf-8"))
    crosswalk["rows"] = [
        json.loads(line)
        for line in args.crosswalk_rows.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    ledger_digest = hashlib.sha256(
        args.crosswalk.read_bytes() + args.crosswalk_rows.read_bytes()
    ).hexdigest()

    def jsonl(path: Path) -> list[dict[str, Any]]:
        with path.open(encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    staff_rows = jsonl(args.staff_rows) if args.staff_rows else None
    staff_digest = sha256_file(args.staff_rows) if args.staff_rows else None
    user_lineage = jsonl(args.user_lineage) if args.user_lineage else None
    source_rights = (json.loads(args.user_lineage_summary.read_text(encoding="utf-8"))["source_rights"]
                     if args.user_lineage_summary else None)
    lineage_digest = (hashlib.sha256(args.user_lineage.read_bytes() + args.user_lineage_summary.read_bytes())
                      .hexdigest() if args.user_lineage and args.user_lineage_summary else None)

    successor_tables = {}
    for spec in args.successor_table:
        name, _, path = spec.partition("=")
        ledger = Path(path)
        successor_tables[name] = (jsonl(ledger), sha256_file(ledger))

    build_root = args.build_root.resolve()
    try:
        outcome = replay_and_compare(
            predecessor=args.predecessor.resolve(),
            crosswalk=crosswalk,
            crosswalk_sha256=ledger_digest,
            first_root=build_root / "build_a",
            second_root=build_root / "build_b",
            predecessor_sha256=args.predecessor_sha256 or None,
            staff_rows=staff_rows,
            staff_rows_sha256=staff_digest,
            user_lineage=user_lineage,
            source_rights=source_rights,
            lineage_sha256=lineage_digest,
            successor_tables=successor_tables or None,
        )
    except CorrectedReleaseError as error:
        receipt = {
            "label": "Cycle #37 - Attempt #2 - ACTUAL_STATE",
            "cycle_number": 37,
            "attempt_number": 2,
            "state": "ACTUAL_STATE",
            "result": "FAILED_CLOSED",
            "error": str(error),
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        _bas_atomic.write_text(args.out, json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print("FAILED CLOSED:", error)
        return 1

    identity = outcome["first"]["content_identity"]
    # Content-addressed: the release lives at its own identity, and a second
    # build of the same inputs resolves to the same address.
    published = args.release_root.resolve() / "sha256" / identity
    database = published / "CYCLE37_CORRECTED_NATIONAL_RELEASE.sqlite"
    if database.exists():
        # An identical content identity is already published. It is kept, not
        # replaced: a published release is never deleted or rewritten.
        existing = sha256_file(database)
        print("already published at this identity; kept (file sha256", existing + ")")
    else:
        published.mkdir(parents=True, exist_ok=True)
        shutil.copy2(outcome["first"]["database"], database)
    pointer = args.release_root.resolve() / "CURRENT_RELEASE.json"
    previous = json.loads(pointer.read_text(encoding="utf-8")) if pointer.is_file() else None
    _bas_atomic.write_text(pointer, json.dumps({
        "label": "Cycle #37 - Attempt #2 - ACTUAL_STATE", "cycle_number": 37, "attempt_number": 2,
        "content_identity": identity, "database_name": database.name,
        "release_version": outcome["first"]["release_version"],
        "supersedes": (previous or {}).get("content_identity") or sorted(
            p.name for p in (args.release_root.resolve() / "sha256").iterdir() if p.name != identity),
        "superseded_releases_kept": True,
        "activation_state": "NOT_ACTIVATED_SEPARATE_OWNER_DECISION",
    }, indent=2) + "\n", encoding="utf-8")

    receipt: dict[str, Any] = {
        "label": "Cycle #37 - Attempt #2 - ACTUAL_STATE",
        "cycle_number": 37,
        "attempt_number": 2,
        "state": "ACTUAL_STATE",
        "requirement": "R37-07",
        "result": "BUILT",
        "release_version": outcome["first"]["release_version"],
        "content_identity": identity,
        "staff_reparse_ledger_sha256": staff_digest,
        "user_corpus_lineage_ledger_sha256": lineage_digest,
        "successor_tables": {name: {"ledger": spec.split("=", 1)[1], "sha256": digest, "rows": len(rows)}
                             for spec in args.successor_table
                             for name, (rows, digest) in [(spec.split("=", 1)[0],
                                                           successor_tables[spec.split("=", 1)[0]])]},
        "published_release": str(database),
        "published_sha256": sha256_file(database),
        "predecessor": str(args.predecessor),
        "predecessor_sha256": outcome["first"]["predecessor_verification"]["predecessor_sha256"],
        "predecessor_modified": False,
        "predecessor_sha256_after": sha256_file(args.predecessor),
        "correction_ledger_sha256": ledger_digest,
        "changes": outcome["first"]["changes"],
        "table_counts": outcome["first"]["table_counts"],
        "input_verification": outcome["first"]["predecessor_verification"],
        "determinism": {
            "built_twice_in_separate_roots": True,
            "content_identity_matches": outcome["content_identity_matches"],
            "tables_compared": outcome["comparison"]["tables_compared"],
            "all_identical_at_scientific_grain": outcome["comparison"][
                "all_identical_at_scientific_grain"
            ],
            "differing_tables": sorted(
                name
                for name, row in outcome["comparison"]["per_table"].items()
                if not row["identical"]
            ),
            "excluded": outcome["comparison"]["excluded_tables"],
            "why_excluded": outcome["comparison"]["why_excluded"],
        },
        "scientific_tables": sorted(outcome["first"]["tables"]),
        "activation_state": "NOT_ACTIVATED_SEPARATE_OWNER_DECISION",
        "builder": builder_provenance(),
        "not_claimed": (
            "This is a corrected successor with explicit input lineage. It is "
            "not activated, not independently accepted, and building it grants "
            "nothing."
        ),
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(args.out, json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("content identity :", identity)
    print("published        :", database)
    print("rebound rows     :", outcome["first"]["changes"]["rebound"])
    print("flagged rows     :", outcome["first"]["changes"]["flagged"])
    print("deterministic    :", outcome["comparison"]["all_identical_at_scientific_grain"],
          "| identity match:", outcome["content_identity_matches"])
    print("predecessor unchanged:",
          receipt["predecessor_sha256"] == receipt["predecessor_sha256_after"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
